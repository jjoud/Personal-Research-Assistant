from __future__ import annotations

import re
from importlib import import_module


def clean_text_for_speech(text: str) -> str:
    if not text:
        return ""

    cleaned = text
    cleaned = re.sub(r"```.*?```", " ", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", cleaned)
    cleaned = re.sub(r"^#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"[*_>]+", " ", cleaned)
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class Speaker:
    def __init__(self, rate: int = 175, volume: float = 1.0) -> None:
        self.rate = rate
        self.volume = volume
        self._engine = None

    def _load_engine(self):
        if self._engine is not None:
            return self._engine
        try:
            pyttsx3 = import_module("pyttsx3")
        except ImportError:
            print("[TTS] pyttsx3 is not installed. Install requirements-voice.txt or use the text demo.")
            return None

        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", self.volume)
        except Exception as exc:
            print(f"[TTS] Speaker unavailable: {exc}")
            return None

        self._engine = engine
        return engine

    def speak(self, text: str) -> None:
        cleaned = clean_text_for_speech(text)
        if not cleaned:
            return
        print("[TTS] Speaking...")
        engine = self._load_engine()
        if engine is None:
            return
        try:
            engine.say(cleaned)
            engine.runAndWait()
        except Exception as exc:
            print(f"[TTS] Speaking failed: {exc}")
