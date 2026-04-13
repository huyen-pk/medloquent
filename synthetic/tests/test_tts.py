#!/usr/bin/env python3
"""Unit tests for the synthetic TTS refactor."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest import mock
import wave

from synthetic.pipeline import tts, tts_backends


class NormalizeTtsTextTests(unittest.TestCase):
    def test_normalize_tts_text_strips_html_and_entities(self) -> None:
        raw = (
            '<div>Care Plan for Respiratory therapy.<br/>'
            "Activities:<ul><li>Respiratory therapy</li><li>Follow-up "
            "&amp; review</li></ul></div>"
        )

        normalized = tts_backends.normalize_tts_text(raw)

        self.assertEqual(
            normalized,
            "Care Plan for Respiratory therapy. Activities: Respiratory "
            "therapy. Follow-up & review.",
        )


class ChunkingTests(unittest.TestCase):
    def test_chunk_text_to_limit_splits_words_when_needed(self) -> None:
        def count_words(text: str) -> int:
            return len(text.split())

        chunks = tts_backends.chunk_text_to_limit(
            "alpha beta gamma delta epsilon",
            2,
            count_words,
        )

        self.assertEqual(chunks, ["alpha beta", "gamma delta", "epsilon"])


class SnapshotResolutionTests(unittest.TestCase):
    def test_resolve_model_snapshot_prefers_cache_then_download(self) -> None:
        with mock.patch.object(
            tts_backends,
            "_snapshot_download",
            side_effect=[RuntimeError("missing cache"), "/tmp/kokoro-snapshot"],
        ) as download:
            resolved = tts_backends.resolve_model_snapshot(
                "onnx-community/Kokoro-82M-v1.0-ONNX",
                model_path=None,
                allow_download=True,
                allow_patterns=("onnx/model_quantized.onnx",),
            )

        self.assertEqual(resolved, Path("/tmp/kokoro-snapshot"))
        self.assertTrue(download.call_args_list[0].kwargs["local_files_only"])
        self.assertNotIn("local_files_only", download.call_args_list[1].kwargs)


class BackendFactoryTests(unittest.TestCase):
    def test_build_tts_backend_rejects_unknown_backend(self) -> None:
        with self.assertRaises(ValueError):
            tts_backends.build_tts_backend(
                tts_backends.TTSBackendConfig(backend="unknown")
            )


class AudioNormalizationTests(unittest.TestCase):
    def test_write_normalized_wav_creates_16k_mono_pcm(self) -> None:
        try:
            import numpy as np
        except Exception as exc:  # pragma: no cover - required dependency
            self.fail(f"numpy is required for this test: {exc}")

        stereo = np.column_stack(
            [np.linspace(-1.0, 1.0, 2400), np.linspace(1.0, -1.0, 2400)]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = Path(tmpdir) / "normalized.wav"
            tts.write_normalized_wav(str(wav_path), stereo, sample_rate=24000)

            with wave.open(str(wav_path), "rb") as handle:
                self.assertEqual(handle.getframerate(), 16000)
                self.assertEqual(handle.getnchannels(), 1)
                self.assertEqual(handle.getsampwidth(), 2)


if __name__ == "__main__":
    unittest.main()