#!/usr/bin/env python3
"""Swappable TTS backend implementations for the synthetic pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from html import unescape
import json
from pathlib import Path
import re
import shutil
from typing import Any, Callable, Sequence


DEFAULT_BACKEND = "kokoro"
DEFAULT_MODEL_ID = "onnx-community/Kokoro-82M-v1.0-ONNX"
DEFAULT_MODEL_FILE = "onnx/model_quantized.onnx"
DEFAULT_VOICE = "af_heart"
DEFAULT_SPEED = 1.0
KOKORO_SAMPLE_RATE = 24000
KOKORO_MAX_INPUT_TOKENS = 510

SUPPORTED_BACKENDS = (DEFAULT_BACKEND,)

_TAG_SUBSTITUTIONS = (
    (re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE), ". "),
    (re.compile(r"<\s*/\s*(?:div|p|ul|ol|section)\s*>", re.IGNORECASE), " "),
    (re.compile(r"<\s*/\s*li\s*>", re.IGNORECASE), ". "),
    (re.compile(r"<\s*li\b[^>]*>", re.IGNORECASE), " "),
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_CLAUSE_SPLIT_RE = re.compile(r"(?<=[;:])\s+|(?<=,)\s+(?=[A-Za-z])")
_REPEATED_TERMINATOR_RE = re.compile(r"([.!?])(?:\s*[.!?])+")
_LETTER_AFTER_TERMINATOR_RE = re.compile(r"([.!?;:])(?=[A-Za-z])")
_WHITESPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([.!?;:,])")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class TTSBackendConfig:
    """Configuration for a TTS backend instance."""

    backend: str = DEFAULT_BACKEND
    model_id: str = DEFAULT_MODEL_ID
    model_path: str | None = None
    model_file: str = DEFAULT_MODEL_FILE
    voice: str = DEFAULT_VOICE
    speed: float = DEFAULT_SPEED
    allow_download: bool = True


@dataclass(frozen=True)
class PreparedUtterance:
    """Speech-ready text chunk produced by a backend."""

    text: str
    phonemes: str
    token_ids: tuple[int, ...]


class TTSBackend(ABC):
    """Abstract TTS backend."""

    name: str
    sample_rate: int

    @abstractmethod
    def prepare(self, text: str) -> list[PreparedUtterance]:
        """Normalize and segment raw text into backend-ready utterances."""

    @abstractmethod
    def synthesize(self, utterance: PreparedUtterance) -> list[float]:
        """Synthesize a single prepared utterance into audio samples."""


def normalize_tts_text(text: str) -> str:
    """Convert raw FHIR/HTML text into speech-friendly plain text."""
    normalized = unescape(text or "")
    for pattern, replacement in _TAG_SUBSTITUTIONS:
        normalized = pattern.sub(replacement, normalized)
    normalized = _HTML_TAG_RE.sub(" ", normalized)
    normalized = normalized.replace("\n", " ")
    normalized = _REPEATED_TERMINATOR_RE.sub(r"\1", normalized)
    normalized = _LETTER_AFTER_TERMINATOR_RE.sub(r"\1 ", normalized)
    normalized = _WHITESPACE_BEFORE_PUNCT_RE.sub(r"\1", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized


def chunk_text_to_limit(
    text: str,
    max_tokens: int,
    token_counter: Callable[[str], int],
) -> list[str]:
    """Split text conservatively so each chunk fits within a token limit."""
    stripped = text.strip()
    if not stripped:
        return []
    if token_counter(stripped) <= max_tokens:
        return [stripped]

    for splitter in (_SENTENCE_SPLIT_RE, _CLAUSE_SPLIT_RE):
        parts = _split_nonempty_parts(stripped, splitter)
        if len(parts) <= 1:
            continue
        return _pack_recursive_chunks(parts, max_tokens, token_counter)

    return _chunk_words(stripped, max_tokens, token_counter)


def _split_nonempty_parts(
    text: str,
    splitter: re.Pattern[str],
) -> list[str]:
    return [part.strip() for part in splitter.split(text) if part.strip()]


def _pack_recursive_chunks(
    parts: Sequence[str],
    max_tokens: int,
    token_counter: Callable[[str], int],
) -> list[str]:
    chunks: list[str] = []
    for part in parts:
        subchunks = chunk_text_to_limit(part, max_tokens, token_counter)
        for subchunk in subchunks:
            if not chunks:
                chunks.append(subchunk)
                continue

            candidate = f"{chunks[-1]} {subchunk}"
            if token_counter(candidate) <= max_tokens:
                chunks[-1] = candidate
            else:
                chunks.append(subchunk)
    return chunks


def _chunk_words(
    text: str,
    max_tokens: int,
    token_counter: Callable[[str], int],
) -> list[str]:
    words = text.split()
    if len(words) <= 1:
        raise RuntimeError(
            "A single text fragment exceeds Kokoro's token limit. "
            "Shorten the manifest text or adjust preprocessing."
        )

    chunks = []
    current: list[str] = []
    for word in words:
        candidate_words = current + [word]
        candidate_text = " ".join(candidate_words)
        if current and token_counter(candidate_text) > max_tokens:
            chunks.append(" ".join(current))
            current = [word]
            continue
        current = candidate_words

    if current:
        final_chunk = " ".join(current)
        if token_counter(final_chunk) > max_tokens:
            raise RuntimeError(
                "A single word exceeds Kokoro's token limit after "
                "phonemization."
            )
        chunks.append(final_chunk)
    return chunks


def resolve_model_snapshot(
    model_id: str,
    *,
    model_path: str | None,
    allow_download: bool,
    allow_patterns: Sequence[str],
) -> Path:
    """Resolve a Hugging Face snapshot path, preferring the local cache."""
    if model_path:
        return Path(model_path).expanduser().resolve()

    try:
        snapshot_path = _snapshot_download(
            repo_id=model_id,
            repo_type="model",
            local_files_only=True,
            allow_patterns=list(allow_patterns),
        )
    except Exception as cache_exc:
        if not allow_download:
            raise RuntimeError(
                f"Model '{model_id}' is not available in the local "
                "Hugging Face cache "
                "and downloads are disabled."
            ) from cache_exc
        try:
            snapshot_path = _snapshot_download(
                repo_id=model_id,
                repo_type="model",
                allow_patterns=list(allow_patterns),
            )
        except Exception as download_exc:
            raise RuntimeError(
                f"Failed to resolve model '{model_id}' from Hugging Face."
            ) from download_exc

    return Path(snapshot_path).expanduser().resolve()


def load_kokoro_vocab(tokenizer_path: Path) -> dict[str, int]:
    """Load Kokoro's phoneme vocabulary from tokenizer.json."""
    with tokenizer_path.open("r", encoding="utf-8") as handle:
        tokenizer = json.load(handle)
    vocab = tokenizer.get("model", {}).get("vocab")
    if not isinstance(vocab, dict):
        raise RuntimeError(f"Invalid Kokoro tokenizer format: {tokenizer_path}")
    return {str(symbol): int(token_id) for symbol, token_id in vocab.items()}


def build_tts_backend(config: TTSBackendConfig) -> TTSBackend:
    """Instantiate the requested TTS backend."""
    if config.speed <= 0:
        raise ValueError("TTS speed must be greater than zero.")
    if config.backend == DEFAULT_BACKEND:
        return KokoroBackend(config)
    raise ValueError(
        f"Unsupported TTS backend '{config.backend}'. Supported backends: "
        f"{', '.join(SUPPORTED_BACKENDS)}"
    )


def _snapshot_download(
    *,
    repo_id: str,
    repo_type: str = "model",
    local_files_only: bool = False,
    allow_patterns: Sequence[str] | None = None,
) -> str:
    from huggingface_hub import snapshot_download

    snapshot_path = snapshot_download(
        repo_id=repo_id,
        repo_type=repo_type,
        local_files_only=local_files_only,
        allow_patterns=(list(allow_patterns) if allow_patterns else None),
    )
    return str(snapshot_path)


def _build_english_g2p(british: bool) -> Callable[[str], str]:
    try:
        from misaki import en
    except Exception as exc:
        raise RuntimeError(
            "Misaki is not available. Install the Kokoro text preprocessing "
            "dependencies from requirements-full.txt."
        ) from exc

    fallback = None
    has_espeak = shutil.which("espeak-ng") is not None
    if has_espeak:
        try:
            from misaki import espeak

            fallback = espeak.EspeakFallback(british=british)
        except Exception:
            fallback = None

    g2p = en.G2P(trf=False, british=british, fallback=fallback)

    def convert(text: str) -> str:
        phonemes, _ = g2p(text)
        if not isinstance(phonemes, str):
            raise RuntimeError("Misaki did not return a phoneme string.")
        phoneme_text = phonemes.strip()
        if not phoneme_text:
            raise RuntimeError("Misaki produced an empty phoneme sequence.")
        return phoneme_text

    return convert


class KokoroBackend(TTSBackend):
    """Kokoro ONNX Runtime backend."""

    name = DEFAULT_BACKEND
    sample_rate = KOKORO_SAMPLE_RATE

    def __init__(self, config: TTSBackendConfig):
        self.config = config
        self._session: Any | None = None
        self._vocab: dict[str, int] | None = None
        self._voice_vectors: Any | None = None
        self._phonemize: Callable[[str], str] | None = None

    def prepare(self, text: str) -> list[PreparedUtterance]:
        normalized = normalize_tts_text(text)
        if not normalized:
            return []

        def token_counter(value: str) -> int:
            phonemes = self._phonemize_text(value)
            return len(self._phonemes_to_ids(phonemes))

        chunks = chunk_text_to_limit(
            normalized,
            KOKORO_MAX_INPUT_TOKENS,
            token_counter,
        )
        prepared: list[PreparedUtterance] = []
        for chunk in chunks:
            phonemes = self._phonemize_text(chunk)
            token_ids = tuple(self._phonemes_to_ids(phonemes))
            if not token_ids:
                raise RuntimeError(
                    f"Kokoro produced no token ids for text chunk: {chunk!r}"
                )
            if len(token_ids) > KOKORO_MAX_INPUT_TOKENS:
                raise RuntimeError(
                    "A normalized chunk still exceeds Kokoro's token limit."
                )
            prepared.append(
                PreparedUtterance(
                    text=chunk,
                    phonemes=phonemes,
                    token_ids=token_ids,
                )
            )
        return prepared

    def synthesize(self, utterance: PreparedUtterance) -> list[float]:
        self._ensure_loaded()
        assert self._session is not None
        assert self._voice_vectors is not None

        try:
            import numpy as np
        except Exception as exc:
            raise RuntimeError(
                "numpy is required for Kokoro synthesis."
            ) from exc

        token_count = len(utterance.token_ids)
        if token_count >= int(self._voice_vectors.shape[0]):
            raise RuntimeError(
                f"Voice '{self.config.voice}' does not support "
                f"{token_count} Kokoro tokens."
            )

        inputs = {
            "input_ids": np.array(
                [[0, *utterance.token_ids, 0]],
                dtype=np.int64,
            ),
            "style": self._voice_vectors[token_count],
            "speed": np.array([self.config.speed], dtype=np.float32),
        }
        audio = self._session.run(None, inputs)[0]
        samples = np.asarray(audio, dtype=np.float32)
        if samples.ndim > 1:
            samples = samples[0]
        return [float(sample) for sample in samples.tolist()]

    def _ensure_loaded(self) -> None:
        if self._session is not None:
            return

        model_path, voice_path, tokenizer_path = self._resolve_artifacts()
        self._vocab = load_kokoro_vocab(tokenizer_path)
        self._phonemize = _build_english_g2p(
            _is_british_voice(self.config.voice)
        )

        try:
            import numpy as np
        except Exception as exc:
            raise RuntimeError(
                "numpy is required for Kokoro synthesis."
            ) from exc

        try:
            import onnxruntime as ort
        except Exception as exc:
            raise RuntimeError(
                "onnxruntime is not available. Install requirements-full.txt."
            ) from exc

        self._voice_vectors = np.fromfile(
            voice_path,
            dtype=np.float32,
        ).reshape(-1, 1, 256)
        self._session = ort.InferenceSession(
            str(model_path),
            providers=["CPUExecutionProvider"],
        )

    def _resolve_artifacts(self) -> tuple[Path, Path, Path]:
        snapshot_dir = resolve_model_snapshot(
            self.config.model_id,
            model_path=self.config.model_path,
            allow_download=self.config.allow_download,
            allow_patterns=(
                self.config.model_file,
                f"voices/{self.config.voice}.bin",
                "tokenizer.json",
            ),
        )
        model_path = snapshot_dir / self.config.model_file
        voice_path = snapshot_dir / "voices" / f"{self.config.voice}.bin"
        tokenizer_path = snapshot_dir / "tokenizer.json"
        missing = [
            str(path)
            for path in (model_path, voice_path, tokenizer_path)
            if not path.exists()
        ]
        if missing:
            raise RuntimeError(
                "Missing Kokoro model artifacts: " + ", ".join(missing)
            )
        return model_path, voice_path, tokenizer_path

    def _phonemize_text(self, text: str) -> str:
        self._ensure_loaded()
        assert self._phonemize is not None
        return self._phonemize(text)

    def _phonemes_to_ids(self, phonemes: str) -> list[int]:
        self._ensure_loaded()
        assert self._vocab is not None
        token_ids = [
            token_id
            for symbol in phonemes
            if symbol != "$"
            and (token_id := self._vocab.get(symbol)) is not None
        ]
        if not token_ids:
            raise RuntimeError(
                "Kokoro could not encode any tokens from phonemes: "
                f"{phonemes!r}"
            )
        return token_ids


def _is_british_voice(voice: str) -> bool:
    return voice.startswith("bf_") or voice.startswith("bm_")