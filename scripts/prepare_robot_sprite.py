"""Prepare the robot sprite sheet and transparent animation frames."""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="Remove sprite background and split robot frames.")
    parser.add_argument("--source", default="pics/fantuan_robot.png", help="Source sprite sheet path.")
    parser.add_argument("--output-sheet", default="assets/robot/fantuan_robot_transparent.png")
    parser.add_argument("--frame-dir", default="assets/robot/fantuan_jump")
    parser.add_argument("--rows", type=int, default=2)
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--threshold", type=int, default=34, help="RGB distance threshold for edge background.")
    return parser.parse_args()


def main() -> None:
    """Create a transparent sprite sheet and split it into frame PNGs."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("缺少 Pillow。请先执行：pip install Pillow") from exc

    args = parse_args()
    source_path = Path(args.source)
    output_sheet = Path(args.output_sheet)
    frame_dir = Path(args.frame_dir)

    image = Image.open(source_path).convert("RGBA")
    transparent = _remove_edge_background(image, threshold=args.threshold)

    output_sheet.parent.mkdir(parents=True, exist_ok=True)
    frame_dir.mkdir(parents=True, exist_ok=True)
    transparent.save(output_sheet)

    frame_width = transparent.width // args.columns
    frame_height = transparent.height // args.rows
    for row in range(args.rows):
        for column in range(args.columns):
            index = row * args.columns + column
            box = (
                column * frame_width,
                row * frame_height,
                (column + 1) * frame_width,
                (row + 1) * frame_height,
            )
            frame = transparent.crop(box)
            frame.save(frame_dir / f"frame_{index:02d}.png")

    print(f"Transparent sheet: {output_sheet}")
    print(f"Frames: {frame_dir}")


def _remove_edge_background(image, *, threshold: int):
    """Make edge-connected near-white background pixels transparent."""
    pixels = image.load()
    width, height = image.size
    visited: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()

    for x in range(width):
        queue.append((x, 0))
        queue.append((x, height - 1))
    for y in range(height):
        queue.append((0, y))
        queue.append((width - 1, y))

    while queue:
        x, y = queue.popleft()
        if (x, y) in visited or not (0 <= x < width and 0 <= y < height):
            continue
        visited.add((x, y))

        red, green, blue, alpha = pixels[x, y]
        if alpha == 0 or not _is_background_pixel(red, green, blue, threshold):
            continue

        pixels[x, y] = (red, green, blue, 0)
        queue.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    return image


def _is_background_pixel(red: int, green: int, blue: int, threshold: int) -> bool:
    return abs(red - 255) <= threshold and abs(green - 255) <= threshold and abs(blue - 255) <= threshold


if __name__ == "__main__":
    main()
