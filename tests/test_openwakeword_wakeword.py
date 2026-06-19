"""Tests for the openWakeWord wake detector helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from modules.app import _build_wakeword
from modules.utils.config_loader import AppConfig
from modules.utils.errors import ConfigurationError
from modules.wakeword.openwakeword_wakeword import (
    OpenWakeWordDetector,
    frame_sample_count,
    pcm16_rms,
    pcm16_bytes_to_mono,
    resample_pcm16_mono,
)


class FakeOpenWakeWordModel:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.reset_called = False

    def predict(self, frame):
        return {"fantuan_fantuan": 0.0}

    def reset(self) -> None:
        self.reset_called = True


class FailOnceForMissingVadModel:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(dict(kwargs))
        if len(self.calls) == 1:
            raise RuntimeError(
                "Load model from /tmp/silero_vad.onnx failed: File doesn't exist"
            )
        return FakeOpenWakeWordModel(**kwargs)


class FailOnceForMissingSpeexThenVadModel:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(dict(kwargs))
        if len(self.calls) == 1:
            raise ModuleNotFoundError("No module named 'speexdsp_ns'")
        if len(self.calls) == 2:
            raise RuntimeError("Load model from /tmp/silero_vad.onnx failed: File doesn't exist")
        return FakeOpenWakeWordModel(**kwargs)


class OpenWakeWordTests(unittest.TestCase):
    def test_frame_sample_count_uses_80ms_windows(self) -> None:
        self.assertEqual(frame_sample_count(48000, 80), 3840)
        self.assertEqual(frame_sample_count(16000, 80), 1280)

    def test_resample_48k_mono_to_16k_mono(self) -> None:
        samples = np.arange(3840, dtype=np.int16)

        resampled = resample_pcm16_mono(samples, source_rate=48000, target_rate=16000)

        self.assertEqual(resampled.dtype, np.int16)
        self.assertEqual(resampled.shape, (1280,))

    def test_pcm16_stereo_bytes_are_downmixed_to_mono(self) -> None:
        stereo = np.array([100, 300, -100, -300], dtype=np.int16)

        mono = pcm16_bytes_to_mono(stereo.tobytes(), channels=2)

        self.assertEqual(mono.tolist(), [200, -200])

    def test_pcm16_rms_matches_expected_level(self) -> None:
        samples = np.full(8, 300, dtype=np.int16)

        rms = pcm16_rms(samples)

        self.assertEqual(rms, 300)

    def test_missing_custom_model_has_clear_error(self) -> None:
        config = AppConfig(
            data={
                "wakeword": {
                    "engine": "openwakeword",
                    "model_paths": ["models/openwakeword/missing.onnx"],
                }
            },
            path=Path("config/config.example.yaml"),
        )
        detector = OpenWakeWordDetector(config, model_factory=FakeOpenWakeWordModel)

        with self.assertRaises(ConfigurationError) as context:
            detector._load_model()

        self.assertIn("openWakeWord 模型不存在", str(context.exception))
        self.assertIn("饭团饭团", str(context.exception))

    def test_model_factory_receives_configured_runtime_options(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "fantuan_fantuan.onnx"
            model_path.write_bytes(b"fake model")
            config = AppConfig(
                data={
                    "wakeword": {
                        "engine": "openwakeword",
                        "model_paths": [str(model_path)],
                        "inference_framework": "onnx",
                        "noise_suppression_enabled": False,
                        "vad_enabled": True,
                        "vad_threshold": 0.4,
                    }
                },
                path=Path("config/config.example.yaml"),
            )
            detector = OpenWakeWordDetector(config, model_factory=FakeOpenWakeWordModel)

            model = detector._load_model()

        self.assertEqual(model.kwargs["wakeword_models"], [str(model_path)])
        self.assertEqual(model.kwargs["inference_framework"], "onnx")
        self.assertFalse(model.kwargs["enable_speex_noise_suppression"])
        self.assertEqual(model.kwargs["vad_threshold"], 0.4)

    def test_prediction_requires_configured_patience(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "fantuan_fantuan.onnx"
            model_path.write_bytes(b"fake model")
            config = AppConfig(
                data={
                    "wakeword": {
                        "engine": "openwakeword",
                        "model_paths": [str(model_path)],
                        "target_labels": ["fantuan_fantuan"],
                        "threshold": 0.5,
                        "patience_frames": 2,
                        "debounce_seconds": 0,
                    }
                },
                path=Path("config/config.example.yaml"),
            )
            detector = OpenWakeWordDetector(config, model_factory=FakeOpenWakeWordModel)

            first = detector._match_predictions({"fantuan_fantuan": 0.7})
            second = detector._match_predictions({"fantuan_fantuan": 0.8})

        self.assertIsNone(first)
        self.assertEqual(second, "fantuan_fantuan")

    def test_silence_gate_blocks_prediction_until_audio_energy_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "fantuan_fantuan.onnx"
            model_path.write_bytes(b"fake model")
            config = AppConfig(
                data={
                    "wakeword": {
                        "engine": "openwakeword",
                        "model_paths": [str(model_path)],
                        "rms_threshold": 200,
                        "rms_patience_frames": 2,
                    }
                },
                path=Path("config/config.example.yaml"),
            )
            detector = OpenWakeWordDetector(config, model_factory=FakeOpenWakeWordModel)

            quiet = np.zeros(1280, dtype=np.int16)
            speech = np.full(1280, 400, dtype=np.int16)

            self.assertFalse(detector._should_process_frame(quiet))
            self.assertFalse(detector._should_process_frame(speech))
            self.assertTrue(detector._should_process_frame(speech))

    def test_missing_vad_model_retries_with_vad_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "fantuan_fantuan.onnx"
            model_path.write_bytes(b"fake model")
            factory = FailOnceForMissingVadModel()
            config = AppConfig(
                data={
                    "wakeword": {
                        "engine": "openwakeword",
                        "model_paths": [str(model_path)],
                        "vad_enabled": True,
                        "vad_threshold": 0.4,
                        "noise_suppression_enabled": False,
                    }
                },
                path=Path("config/config.example.yaml"),
            )
            detector = OpenWakeWordDetector(config, model_factory=factory)

            model = detector._load_model()

        self.assertIsInstance(model, FakeOpenWakeWordModel)
        self.assertEqual(len(factory.calls), 2)
        self.assertEqual(factory.calls[0]["vad_threshold"], 0.4)
        self.assertEqual(factory.calls[1]["vad_threshold"], 0.0)

    def test_missing_speex_then_vad_retries_through_both_fallbacks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "fantuan_fantuan.onnx"
            model_path.write_bytes(b"fake model")
            factory = FailOnceForMissingSpeexThenVadModel()
            config = AppConfig(
                data={
                    "wakeword": {
                        "engine": "openwakeword",
                        "model_paths": [str(model_path)],
                        "vad_enabled": True,
                        "vad_threshold": 0.4,
                        "noise_suppression_enabled": True,
                        "noise_suppression_fallback": True,
                    }
                },
                path=Path("config/config.example.yaml"),
            )
            detector = OpenWakeWordDetector(config, model_factory=factory)

            model = detector._load_model()

        self.assertIsInstance(model, FakeOpenWakeWordModel)
        self.assertEqual(len(factory.calls), 3)
        self.assertTrue(factory.calls[0]["enable_speex_noise_suppression"])
        self.assertFalse(factory.calls[1]["enable_speex_noise_suppression"])
        self.assertEqual(factory.calls[1]["vad_threshold"], 0.4)
        self.assertFalse(factory.calls[2]["enable_speex_noise_suppression"])
        self.assertEqual(factory.calls[2]["vad_threshold"], 0.0)

    def test_app_factory_supports_openwakeword_engine(self) -> None:
        config = AppConfig(
            data={"wakeword": {"engine": "openwakeword"}},
            path=Path("config/config.example.yaml"),
        )

        with patch("modules.wakeword.openwakeword_wakeword.OpenWakeWordDetector", return_value="detector") as detector:
            wakeword = _build_wakeword(config)

        self.assertEqual(wakeword, "detector")
        detector.assert_called_once_with(config)


if __name__ == "__main__":
    unittest.main()
