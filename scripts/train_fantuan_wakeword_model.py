"""Train a compact openWakeWord-compatible ONNX wakeword model from real samples."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
import sys
from zipfile import ZipFile

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.utils.config_loader import load_config

TARGET_FRAMES = 16
FEATURE_DIM = 96
SAMPLE_RATE = 16000
CLIP_SECONDS = 2.0
TARGET_SAMPLES = int(SAMPLE_RATE * CLIP_SECONDS)
DEFAULT_BUNDLE = Path("exports/fantuan_fantuan_training_bundle.zip")
DEFAULT_OUTPUT_MODEL = Path("models/openwakeword/fantuan_fantuan.onnx")
DEFAULT_OUTPUT_REPORT = Path("models/openwakeword/fantuan_fantuan_training_report.json")


@dataclass(frozen=True, slots=True)
class SampleExample:
    """One training example with its label."""

    audio: np.ndarray
    label: int
    source: str


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="训练饭团饭团本地离线唤醒模型。")
    parser.add_argument("--config", default="config/config.yaml", help="配置文件路径。")
    parser.add_argument("--bundle", default=str(DEFAULT_BUNDLE), help="训练包 zip 路径。")
    parser.add_argument("--output-model", default=str(DEFAULT_OUTPUT_MODEL), help="输出 ONNX 模型路径。")
    parser.add_argument("--output-report", default=str(DEFAULT_OUTPUT_REPORT), help="输出训练报告路径。")
    parser.add_argument("--augment-copies", type=int, default=5, help="每条样本生成多少个随机增强副本。")
    parser.add_argument("--seed", type=int, default=7, help="随机种子。")
    return parser.parse_args()


def main() -> None:
    """Train and export the wakeword model."""
    args = parse_args()
    _ = load_config(Path(args.config))

    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from openwakeword.utils import AudioFeatures

    rng = np.random.default_rng(args.seed)

    bundle_path = Path(args.bundle)
    if not bundle_path.exists():
        raise FileNotFoundError(f"未找到训练包：{bundle_path}")

    examples = load_examples(bundle_path)
    if len(examples) < 10:
        raise RuntimeError("训练样本太少，无法训练。")

    clips = []
    labels = []
    sources = []
    for example in examples:
        for copy_index in range(max(1, args.augment_copies)):
            augmented = augment_audio(example.audio, rng, copy_index)
            clips.append(augmented)
            labels.append(example.label)
            sources.append(example.source)

    featurizer = AudioFeatures(inference_framework="onnx")
    batched = np.stack(clips).astype(np.int16)
    embeddings = featurizer.embed_clips(batched, batch_size=32, ncpu=1)

    if embeddings.shape[1] != TARGET_FRAMES or embeddings.shape[2] != FEATURE_DIM:
        raise RuntimeError(
            f"特征维度不符合预期：{embeddings.shape}，期望 (*, {TARGET_FRAMES}, {FEATURE_DIM})"
        )

    features = embeddings.reshape(embeddings.shape[0], -1)
    labels_arr = np.asarray(labels, dtype=np.int64)

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels_arr,
        test_size=0.2,
        random_state=args.seed,
        stratify=labels_arr,
    )

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    clf = LogisticRegression(max_iter=5000, class_weight="balanced", random_state=args.seed)
    clf.fit(x_train_scaled, y_train)

    train_prob = clf.predict_proba(x_train_scaled)[:, 1]
    test_prob = clf.predict_proba(x_test_scaled)[:, 1]
    test_pred = (test_prob >= 0.5).astype(int)

    metrics = {
        "train_accuracy": float(accuracy_score(y_train, (train_prob >= 0.5).astype(int))),
        "test_accuracy": float(accuracy_score(y_test, test_pred)),
        "test_precision": float(precision_score(y_test, test_pred, zero_division=0)),
        "test_recall": float(recall_score(y_test, test_pred, zero_division=0)),
        "test_auc": float(roc_auc_score(y_test, test_prob)) if len(set(y_test)) > 1 else 0.0,
        "positive_examples": int(labels_arr.sum()),
        "negative_examples": int((labels_arr == 0).sum()),
        "feature_shape": list(embeddings.shape[1:]),
    }

    output_model = Path(args.output_model)
    output_model.parent.mkdir(parents=True, exist_ok=True)
    export_linear_onnx(
        output_model,
        coef=clf.coef_[0],
        intercept=float(clf.intercept_[0]),
        mean=scaler.mean_,
        scale=scaler.scale_,
        input_frames=TARGET_FRAMES,
        feature_dim=FEATURE_DIM,
    )

    report_path = Path(args.output_report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"模型已导出：{output_model}")
    print(f"训练报告：{report_path}")


def load_examples(bundle_path: Path) -> list[SampleExample]:
    """Load examples from the exported training bundle."""
    examples: list[SampleExample] = []
    with ZipFile(bundle_path, "r") as archive:
        names = archive.namelist()
        positive_names = [name for name in names if name.startswith("positive/") and name.lower().endswith(".wav")]
        negative_names = [name for name in names if name.startswith("negative/") and name.lower().endswith(".wav")]

        for name in positive_names:
            audio = load_wav_from_zip(archive, name)
            examples.append(SampleExample(audio=audio, label=1, source=name))
        for name in negative_names:
            audio = load_wav_from_zip(archive, name)
            examples.append(SampleExample(audio=audio, label=0, source=name))
    return examples


def load_wav_from_zip(archive: ZipFile, name: str) -> np.ndarray:
    """Read a WAV file from the bundle and resample to 16 kHz mono int16."""
    from scipy.io import wavfile
    from scipy.signal import resample_poly
    import io

    with archive.open(name) as file:
        raw = file.read()
    sample_rate, audio = wavfile.read(io.BytesIO(raw))
    audio = to_mono_int16(audio)
    if sample_rate != SAMPLE_RATE:
        audio = resample_to_16k(audio, sample_rate)
    audio = fit_clip(audio)
    return audio.astype(np.int16, copy=False)


def to_mono_int16(audio: np.ndarray) -> np.ndarray:
    """Convert audio to mono int16."""
    if audio.ndim == 2:
        audio = np.mean(audio.astype(np.float32), axis=1)
    if audio.dtype != np.int16:
        if np.issubdtype(audio.dtype, np.floating):
            audio = np.clip(audio * 32767.0, -32768, 32767)
        audio = audio.astype(np.int16)
    return audio


def resample_to_16k(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """Resample audio to 16 kHz."""
    from scipy.signal import resample_poly

    if sample_rate == SAMPLE_RATE:
        return audio
    gcd = np.gcd(sample_rate, SAMPLE_RATE)
    up = SAMPLE_RATE // gcd
    down = sample_rate // gcd
    resampled = resample_poly(audio.astype(np.float32), up, down)
    return np.clip(np.rint(resampled), -32768, 32767).astype(np.int16)


def fit_clip(audio: np.ndarray) -> np.ndarray:
    """Pad or trim audio to the fixed clip length used for training."""
    if audio.shape[0] > TARGET_SAMPLES:
        return audio[:TARGET_SAMPLES]
    if audio.shape[0] < TARGET_SAMPLES:
        padded = np.zeros(TARGET_SAMPLES, dtype=np.int16)
        padded[: audio.shape[0]] = audio
        return padded
    return audio


def augment_audio(audio: np.ndarray, rng: np.random.Generator, index: int) -> np.ndarray:
    """Apply light augmentation to a clip."""
    shifted = random_shift(audio, rng)
    gain = rng.uniform(0.85, 1.15)
    noise_level = rng.uniform(0.0, 0.008)
    noisy = shifted.astype(np.float32) * gain
    if noise_level > 0:
        noisy += rng.normal(0.0, 32767.0 * noise_level, size=noisy.shape[0])
    clipped = np.clip(np.rint(noisy), -32768, 32767).astype(np.int16)
    return fit_clip(clipped)


def random_shift(audio: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Randomly shift the clip within a small window."""
    max_shift = int(0.15 * SAMPLE_RATE)
    shift = int(rng.integers(-max_shift, max_shift + 1))
    if shift == 0:
        return audio
    rolled = np.roll(audio, shift)
    if shift > 0:
        rolled[:shift] = 0
    else:
        rolled[shift:] = 0
    return rolled


def export_linear_onnx(
    output_model: Path,
    *,
    coef: np.ndarray,
    intercept: float,
    mean: np.ndarray,
    scale: np.ndarray,
    input_frames: int,
    feature_dim: int,
) -> None:
    """Export a standardised linear classifier to ONNX."""
    import onnx
    import onnx.helper as oh
    import onnx.numpy_helper as nh

    feature_count = input_frames * feature_dim
    fused_weight = (coef / scale).astype(np.float32)
    fused_bias = np.array([intercept - float(np.dot(mean / scale, coef))], dtype=np.float32)

    input_tensor = oh.make_tensor_value_info("input", onnx.TensorProto.FLOAT, [None, input_frames, feature_dim])
    output_tensor = oh.make_tensor_value_info("probability", onnx.TensorProto.FLOAT, [None, 1])

    reshape_shape = nh.from_array(np.array([-1, feature_count], dtype=np.int64), name="reshape_shape")
    weight = nh.from_array(fused_weight.reshape(feature_count, 1), name="weight")
    bias = nh.from_array(fused_bias, name="bias")

    nodes = [
        oh.make_node("Reshape", ["input", "reshape_shape"], ["flat"]),
        oh.make_node("Gemm", ["flat", "weight", "bias"], ["logits"], alpha=1.0, beta=1.0, transB=0),
        oh.make_node("Sigmoid", ["logits"], ["probability"]),
    ]

    graph = oh.make_graph(
        nodes,
        "fantuan_fantuan_linear_wakeword",
        [input_tensor],
        [output_tensor],
        initializer=[reshape_shape, weight, bias],
    )
    model = oh.make_model(graph, producer_name="dirty_words")
    model.ir_version = 9
    for opset in model.opset_import:
        if opset.domain == "":
            opset.version = 13
    onnx.checker.check_model(model)
    onnx.save(model, output_model)


if __name__ == "__main__":
    main()
