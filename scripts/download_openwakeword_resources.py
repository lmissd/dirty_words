"""Download the openWakeWord runtime resources needed on Raspberry Pi."""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    """Ensure feature-extraction models and Silero VAD exist locally."""
    try:
        import openwakeword
        from openwakeword import FEATURE_MODELS, VAD_MODELS
        from openwakeword.utils import download_file
    except ImportError as exc:
        raise RuntimeError("缺少 openwakeword 依赖，请先执行 pip install -r requirements.txt") from exc

    target_dir = Path(openwakeword.__file__).resolve().parent / "resources" / "models"
    target_dir.mkdir(parents=True, exist_ok=True)

    download_urls: list[str] = []
    for feature_model in FEATURE_MODELS.values():
        feature_url = str(feature_model["download_url"])
        download_urls.append(feature_url)
        download_urls.append(feature_url.replace(".tflite", ".onnx"))
    for vad_model in VAD_MODELS.values():
        download_urls.append(str(vad_model["download_url"]))

    downloaded: list[str] = []
    skipped: list[str] = []
    for url in download_urls:
        filename = Path(url).name
        output_path = target_dir / filename
        if output_path.exists():
            skipped.append(filename)
            continue
        print(f"Downloading {filename}")
        download_file(url, str(target_dir))
        downloaded.append(filename)

    required_vad_path = target_dir / "silero_vad.onnx"
    if not required_vad_path.exists():
        raise RuntimeError(f"VAD 模型下载后仍不存在：{required_vad_path}")

    print(f"openWakeWord resources ready: {target_dir}")
    print(f"Downloaded: {len(downloaded)} file(s)")
    if downloaded:
        for name in downloaded:
            print(f"  - {name}")
    print(f"Already present: {len(skipped)} file(s)")
    if skipped:
        for name in skipped:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
