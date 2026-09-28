#!/usr/bin/env python3
"""
VideoNut TTS Provider Adapters
==============================

One thin adapter per text-to-speech backend. Every adapter exposes the same
contract so the engine never needs provider-specific branching:

    provider = get_provider("elevenlabs", settings)
    provider.check_ready()                  -> (bool, reason)
    provider.synthesize(text, style, out)   -> path to an audio file on disk

Selection guidance (see docs/VOICE_AGENT.md for the full benchmark write-up):

  elevenlabs  Most expressive English narration; inline audio tags map 1:1 onto
              VideoNut's voice cues; instant + professional voice cloning.
              `eleven_multilingual_v2` is the stable long-form workhorse,
              `eleven_v3` the expressive model (shorter per-request cap).
  sarvam      Purpose-built for Indian languages (Bulbul). Materially better
              than global models on Telugu/Hindi/Tamil prosody, Indian names,
              and Hinglish/Tanglish code-switching.
  gemini      Very strong quality-per-rupee, prompt-steerable delivery,
              multi-speaker. Returns raw 24kHz PCM that we wrap into WAV.
  openai      Cheap, dependable, `instructions` field for delivery steering.
  piper       Fully offline, MIT-licensed, zero cost. Draft passes / air-gapped.
  edge        Free network voices via the `edge-tts` CLI. Draft passes only.
  mock        Deterministic silent audio. Used by tests and `--cli mock`.

No provider SDKs are required: everything is plain HTTPS via `requests`, which
is already a VideoNut dependency. That keeps `pip install` light and avoids
version churn from six vendor SDKs.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import time
import wave
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

try:
    import requests
except ImportError:  # pragma: no cover - requests is in requirements.txt
    requests = None


# ──────────────────────────────────────────────────────────────────────────────
# Language mapping
# ──────────────────────────────────────────────────────────────────────────────

# config.yaml `audio_language` -> provider-specific language identifiers.
LANGUAGE_MAP: Dict[str, Dict[str, str]] = {
    "english":   {"bcp47": "en-IN", "iso639_1": "en", "iso639_3": "eng", "sarvam": "en-IN"},
    "hindi":     {"bcp47": "hi-IN", "iso639_1": "hi", "iso639_3": "hin", "sarvam": "hi-IN"},
    "telugu":    {"bcp47": "te-IN", "iso639_1": "te", "iso639_3": "tel", "sarvam": "te-IN"},
    "tamil":     {"bcp47": "ta-IN", "iso639_1": "ta", "iso639_3": "tam", "sarvam": "ta-IN"},
    "kannada":   {"bcp47": "kn-IN", "iso639_1": "kn", "iso639_3": "kan", "sarvam": "kn-IN"},
    "malayalam": {"bcp47": "ml-IN", "iso639_1": "ml", "iso639_3": "mal", "sarvam": "ml-IN"},
    "marathi":   {"bcp47": "mr-IN", "iso639_1": "mr", "iso639_3": "mar", "sarvam": "mr-IN"},
    "bengali":   {"bcp47": "bn-IN", "iso639_1": "bn", "iso639_3": "ben", "sarvam": "bn-IN"},
    "gujarati":  {"bcp47": "gu-IN", "iso639_1": "gu", "iso639_3": "guj", "sarvam": "gu-IN"},
    "punjabi":   {"bcp47": "pa-IN", "iso639_1": "pa", "iso639_3": "pan", "sarvam": "pa-IN"},
    "odia":      {"bcp47": "od-IN", "iso639_1": "or", "iso639_3": "ory", "sarvam": "od-IN"},
}

INDIC_LANGUAGES = {
    "hindi", "telugu", "tamil", "kannada", "malayalam",
    "marathi", "bengali", "gujarati", "punjabi", "odia",
}


def language_codes(language: str) -> Dict[str, str]:
    return LANGUAGE_MAP.get((language or "english").strip().lower(), LANGUAGE_MAP["english"])


# Every spelling of an Indic language we might be handed: the English name
# ("Hindi"), the BCP-47 tag ("hi-IN"), and the bare ISO 639-1 code ("hi").
# config.yaml uses names, but agents and CLI flags routinely pass codes.
INDIC_ALIASES = set(INDIC_LANGUAGES)
for _name in INDIC_LANGUAGES:
    _codes = LANGUAGE_MAP[_name]
    INDIC_ALIASES.add(_codes["bcp47"].lower())
    INDIC_ALIASES.add(_codes["iso639_1"].lower())
    INDIC_ALIASES.add(_codes["iso639_3"].lower())
INDIC_ALIASES.update({"hinglish", "tanglish", "telglish", "indian english"})


def is_indic(language: str) -> bool:
    """True for any spelling of an Indic language: 'Hindi', 'hi-IN', 'hi', 'hin'."""
    value = (language or "").strip().lower().replace("_", "-")
    if value in INDIC_ALIASES:
        return True
    # "hi-in", "ta-IN-x-something" -> try the primary subtag as well.
    primary = value.split("-")[0]
    return bool(primary) and primary in INDIC_ALIASES


# ──────────────────────────────────────────────────────────────────────────────
# Capability table
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class ProviderProfile:
    """Static facts about a backend, used for routing, chunking and costing."""

    name: str
    dialect: str                 # plain | audio_tags | ssml | style_prompt
    max_chars: int               # conservative per-request cap
    audio_ext: str               # native output container
    usd_per_1k_chars: float      # indicative list price, override in config.yaml
    env_keys: Tuple[str, ...] = ()
    supports_indic: bool = False
    supports_cloning: bool = False
    offline: bool = False
    notes: str = ""


PROFILES: Dict[str, ProviderProfile] = {
    "elevenlabs": ProviderProfile(
        name="elevenlabs",
        dialect="audio_tags",
        max_chars=2500,
        audio_ext="mp3",
        usd_per_1k_chars=0.10,
        env_keys=("ELEVENLABS_API_KEY", "ELEVEN_API_KEY"),
        supports_indic=True,
        supports_cloning=True,
        notes="eleven_multilingual_v2 for stable long-form; eleven_v3 for expressive audio tags.",
    ),
    "sarvam": ProviderProfile(
        name="sarvam",
        dialect="plain",
        max_chars=2000,
        audio_ext="mp3",
        usd_per_1k_chars=0.036,
        env_keys=("SARVAM_API_KEY", "SARVAM_SUBSCRIPTION_KEY"),
        supports_indic=True,
        notes="Bulbul. Best-in-class Indic prosody, Indian names, and code-switching.",
    ),
    "gemini": ProviderProfile(
        name="gemini",
        dialect="style_prompt",
        max_chars=3000,
        audio_ext="wav",
        usd_per_1k_chars=0.017,
        env_keys=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        supports_indic=True,
        notes="Returns 24kHz signed 16-bit mono PCM; wrapped into WAV locally.",
    ),
    "openai": ProviderProfile(
        name="openai",
        dialect="style_prompt",
        max_chars=3500,
        audio_ext="mp3",
        usd_per_1k_chars=0.015,
        env_keys=("OPENAI_API_KEY",),
        notes="gpt-4o-mini-tts with the `instructions` field for delivery steering.",
    ),
    "piper": ProviderProfile(
        name="piper",
        dialect="plain",
        max_chars=6000,
        audio_ext="wav",
        usd_per_1k_chars=0.0,
        supports_indic=False,
        offline=True,
        notes="Local MIT-licensed neural TTS. Zero cost, no network, draft quality.",
    ),
    "edge": ProviderProfile(
        name="edge",
        dialect="plain",
        max_chars=4000,
        audio_ext="mp3",
        usd_per_1k_chars=0.0,
        supports_indic=True,
        notes="Free `edge-tts` CLI voices. Draft/preview only - confirm terms before commercial use.",
    ),
    "mock": ProviderProfile(
        name="mock",
        dialect="plain",
        max_chars=100000,
        audio_ext="wav",
        usd_per_1k_chars=0.0,
        offline=True,
        notes="Deterministic silence for offline tests and dry runs.",
    ),
}


# Default voices per provider/language so a first run works with zero tuning.
DEFAULT_VOICES: Dict[str, Dict[str, str]] = {
    "elevenlabs": {"default": "JBFqnCBsd6RMkjVDRZzb"},  # "George" - documentary baritone
    "sarvam": {
        "default": "shubh",
        "english": "shubh",
        "hindi": "shubh",
        "telugu": "shubh",
        "tamil": "shubh",
    },
    "gemini": {"default": "Charon"},   # deep, measured narration voice
    "openai": {"default": "onyx"},
    "piper": {"default": "en_US-lessac-medium"},
    "edge": {
        "default": "en-US-GuyNeural",
        "hindi": "hi-IN-MadhurNeural",
        "telugu": "te-IN-MohanNeural",
        "tamil": "ta-IN-ValluvarNeural",
    },
    "mock": {"default": "mock-narrator"},
}


class ProviderError(RuntimeError):
    """Raised when a backend fails in a way the engine should surface."""


# ──────────────────────────────────────────────────────────────────────────────
# Base adapter
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class ProviderSettings:
    language: str = "English"
    voice: str = ""
    model: str = ""
    pace: float = 1.0
    stability: float = 0.45
    similarity: float = 0.8
    style_prompt: str = ""
    timeout: int = 180
    extra: Dict = field(default_factory=dict)


class BaseProvider:
    profile: ProviderProfile

    def __init__(self, settings: ProviderSettings):
        self.settings = settings

    # -- helpers ------------------------------------------------------------
    def api_key(self) -> Optional[str]:
        for key in self.profile.env_keys:
            value = os.environ.get(key)
            if value:
                return value.strip()
        return None

    def resolved_voice(self) -> str:
        if self.settings.voice:
            return self.settings.voice
        table = DEFAULT_VOICES.get(self.profile.name, {})
        return table.get((self.settings.language or "").strip().lower(), table.get("default", ""))

    def check_ready(self) -> Tuple[bool, str]:
        if self.profile.env_keys and not self.api_key():
            return False, (
                f"Missing API key. Set one of: {', '.join(self.profile.env_keys)} "
                f"(put it in .env at the repo root, never in config.yaml)."
            )
        if requests is None and not self.profile.offline:
            return False, "The `requests` package is not installed (pip install -r requirements.txt)."
        return True, "ready"

    def synthesize(self, text: str, style: str, out_path: str) -> str:  # pragma: no cover
        raise NotImplementedError

    # -- shared plumbing ----------------------------------------------------
    @staticmethod
    def _write_bytes(path: str, payload: bytes) -> str:
        if not payload:
            raise ProviderError("Provider returned an empty audio payload.")
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(payload)
        return path

    @staticmethod
    def _write_pcm_as_wav(path: str, pcm: bytes, rate: int = 24000) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with wave.open(path, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(pcm)
        return path

    def _post(self, url: str, **kwargs):
        kwargs.setdefault("timeout", self.settings.timeout)
        response = requests.post(url, **kwargs)
        if response.status_code == 401 or response.status_code == 403:
            raise ProviderError(f"{self.profile.name}: authentication failed ({response.status_code}). Check the API key.")
        if response.status_code == 429:
            raise ProviderError(f"{self.profile.name}: rate limited (429). Reduce --concurrency or retry later.")
        if response.status_code >= 400:
            snippet = (response.text or "")[:400]
            raise ProviderError(f"{self.profile.name}: HTTP {response.status_code} - {snippet}")
        return response


# ──────────────────────────────────────────────────────────────────────────────
# Concrete adapters
# ──────────────────────────────────────────────────────────────────────────────


class ElevenLabsProvider(BaseProvider):
    profile = PROFILES["elevenlabs"]
    BASE = "https://api.elevenlabs.io/v1/text-to-speech"

    def synthesize(self, text: str, style: str, out_path: str) -> str:
        model = self.settings.model or "eleven_multilingual_v2"
        voice = self.resolved_voice()
        url = f"{self.BASE}/{voice}"
        payload = {
            "text": text,
            "model_id": model,
            "voice_settings": {
                "stability": self.settings.stability,
                "similarity_boost": self.settings.similarity,
                "style": 0.0,
                "use_speaker_boost": True,
            },
        }
        codes = language_codes(self.settings.language)
        if model.startswith("eleven_v3") or model in ("eleven_turbo_v2_5", "eleven_flash_v2_5"):
            payload["language_code"] = codes["iso639_1"]
        response = self._post(
            url,
            headers={"xi-api-key": self.api_key(), "Content-Type": "application/json"},
            params={"output_format": "mp3_44100_128"},
            json=payload,
        )
        return self._write_bytes(out_path, response.content)


class SarvamProvider(BaseProvider):
    profile = PROFILES["sarvam"]
    URL = "https://api.sarvam.ai/text-to-speech"

    def synthesize(self, text: str, style: str, out_path: str) -> str:
        codes = language_codes(self.settings.language)
        payload = {
            "text": text,
            "target_language_code": codes["sarvam"],
            "speaker": self.resolved_voice(),
            "model": self.settings.model or "bulbul:v3",
            "pace": self.settings.pace,
            "output_audio_codec": "mp3",
        }
        response = self._post(
            self.URL,
            headers={"api-subscription-key": self.api_key(), "Content-Type": "application/json"},
            json=payload,
        )
        try:
            audios = response.json().get("audios") or []
        except json.JSONDecodeError as exc:
            raise ProviderError(f"sarvam: malformed JSON response ({exc}).")
        if not audios:
            raise ProviderError("sarvam: response contained no audio.")
        return self._write_bytes(out_path, base64.b64decode("".join(audios)))


class GeminiProvider(BaseProvider):
    profile = PROFILES["gemini"]
    BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def synthesize(self, text: str, style: str, out_path: str) -> str:
        model = self.settings.model or "gemini-2.5-flash-preview-tts"
        codes = language_codes(self.settings.language)
        prompt = f"Read the following aloud, {style}:\n{text}" if style else text
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "languageCode": codes["bcp47"],
                    "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": self.resolved_voice()}},
                },
            },
        }
        response = self._post(
            f"{self.BASE}/{model}:generateContent",
            headers={"x-goog-api-key": self.api_key(), "Content-Type": "application/json"},
            json=payload,
        )
        body = response.json()
        try:
            part = body["candidates"][0]["content"]["parts"][0]["inlineData"]
        except (KeyError, IndexError, TypeError):
            raise ProviderError(f"gemini: no audio part in response - {json.dumps(body)[:300]}")
        rate = 24000
        mime = part.get("mimeType", "")
        if "rate=" in mime:
            try:
                rate = int(mime.split("rate=")[1].split(";")[0])
            except (ValueError, IndexError):
                rate = 24000
        return self._write_pcm_as_wav(out_path, base64.b64decode(part["data"]), rate)


class OpenAIProvider(BaseProvider):
    profile = PROFILES["openai"]
    URL = "https://api.openai.com/v1/audio/speech"

    def synthesize(self, text: str, style: str, out_path: str) -> str:
        payload = {
            "model": self.settings.model or "gpt-4o-mini-tts",
            "voice": self.resolved_voice(),
            "input": text,
            "response_format": "mp3",
            "speed": self.settings.pace,
        }
        if style:
            payload["instructions"] = style
        response = self._post(
            self.URL,
            headers={"Authorization": f"Bearer {self.api_key()}", "Content-Type": "application/json"},
            json=payload,
        )
        return self._write_bytes(out_path, response.content)


class PiperProvider(BaseProvider):
    profile = PROFILES["piper"]

    def check_ready(self) -> Tuple[bool, str]:
        if not shutil.which("piper"):
            return False, "`piper` is not on PATH. Install from https://github.com/rhasspy/piper."
        if not self.resolved_voice():
            return False, "No piper voice model configured (voice.providers.piper.voice)."
        return True, "ready"

    def synthesize(self, text: str, style: str, out_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        cmd = ["piper", "--model", self.resolved_voice(), "--output_file", out_path]
        result = subprocess.run(cmd, input=text.encode("utf-8"), capture_output=True)
        if result.returncode != 0 or not os.path.exists(out_path):
            raise ProviderError(f"piper failed: {result.stderr.decode('utf-8', 'ignore')[:300]}")
        return out_path


class EdgeProvider(BaseProvider):
    profile = PROFILES["edge"]

    def check_ready(self) -> Tuple[bool, str]:
        if not shutil.which("edge-tts"):
            return False, "`edge-tts` is not on PATH. Install with `pip install edge-tts`."
        return True, "ready"

    def synthesize(self, text: str, style: str, out_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        cmd = [
            "edge-tts",
            "--voice", self.resolved_voice(),
            "--text", text,
            "--write-media", out_path,
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0 or not os.path.exists(out_path):
            raise ProviderError(f"edge-tts failed: {result.stderr.decode('utf-8', 'ignore')[:300]}")
        return out_path


class MockProvider(BaseProvider):
    """Deterministic offline provider: 1 second of silence per 15 words."""

    profile = PROFILES["mock"]

    def check_ready(self) -> Tuple[bool, str]:
        return True, "ready"

    def synthesize(self, text: str, style: str, out_path: str) -> str:
        seconds = max(0.5, len(text.split()) / 2.5)  # ~150 wpm
        frames = int(24000 * seconds)
        return self._write_pcm_as_wav(out_path, b"\x00\x00" * frames, 24000)


REGISTRY = {
    "elevenlabs": ElevenLabsProvider,
    "sarvam": SarvamProvider,
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "piper": PiperProvider,
    "edge": EdgeProvider,
    "mock": MockProvider,
}


def get_provider(name: str, settings: ProviderSettings) -> BaseProvider:
    key = (name or "").strip().lower()
    if key not in REGISTRY:
        raise ProviderError(
            f"Unknown TTS provider '{name}'. Available: {', '.join(sorted(REGISTRY))}."
        )
    return REGISTRY[key](settings)


def available_providers(language: str = "English") -> Dict[str, Tuple[bool, str]]:
    """Readiness probe for every provider - powers `check_env.py` and the agent menu."""
    report = {}
    for name in REGISTRY:
        provider = get_provider(name, ProviderSettings(language=language))
        report[name] = provider.check_ready()
    return report


def resolve_auto_provider(language: str, preference: Optional[list] = None) -> Tuple[str, str]:
    """
    Pick the best *ready* provider for a language.

    Routing policy (overridable via config.yaml voice.fallback_chain):
      Indic languages -> sarvam  > elevenlabs > gemini > edge > mock
      Everything else -> elevenlabs > gemini > openai > edge > mock
    """
    if preference:
        chain = list(preference)
    elif is_indic(language):
        chain = ["sarvam", "elevenlabs", "gemini", "edge", "piper", "mock"]
    else:
        chain = ["elevenlabs", "gemini", "openai", "edge", "piper", "mock"]

    reasons = []
    for name in chain:
        if name not in REGISTRY:
            reasons.append(f"{name}: unknown provider")
            continue
        ready, why = get_provider(name, ProviderSettings(language=language)).check_ready()
        if ready:
            return name, f"auto-selected '{name}' for language '{language}'"
        reasons.append(f"{name}: {why}")
    return "mock", "no configured provider is ready -> falling back to 'mock'. " + " | ".join(reasons)


def retry(callable_, attempts: int = 3, base_delay: float = 2.0):
    """Exponential backoff around a provider call."""
    last = None
    for attempt in range(1, attempts + 1):
        try:
            return callable_()
        except ProviderError as exc:
            last = exc
            if attempt == attempts:
                break
            delay = base_delay * (2 ** (attempt - 1))
            print(f"  [RETRY] attempt {attempt}/{attempts} failed ({exc}); retrying in {delay:.0f}s")
            time.sleep(delay)
        except Exception as exc:  # network blips, JSON errors, etc.
            last = ProviderError(str(exc))
            if attempt == attempts:
                break
            time.sleep(base_delay * (2 ** (attempt - 1)))
    raise last if last else ProviderError("unknown provider failure")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    lang = sys.argv[1] if len(sys.argv) > 1 else "English"
    print(f"[SCAN] TTS provider readiness (language: {lang})")
    print("-" * 60)
    for provider_name, (ok, detail) in available_providers(lang).items():
        icon = "[OK]  " if ok else "[MISS]"
        prof = PROFILES[provider_name]
        print(f"{icon} {provider_name:<11} {detail}")
        print(f"        {prof.notes}")
    chosen, why = resolve_auto_provider(lang)
    print("-" * 60)
    print(f"[AUTO] {why}")
