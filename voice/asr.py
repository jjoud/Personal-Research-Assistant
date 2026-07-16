from __future__ import annotations

import http.client
import io
import os
import socket
import urllib.error
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path


@dataclass
class SpeechRecognizer:
    language: str = "en-US"
    timeout: int = 8
    phrase_time_limit: int = 12
    pause_threshold: float = 0.8
    device_index: int | None = None
    asr_provider: str = "google"
    openai_transcribe_model: str = "gpt-4o-mini-transcribe"
    openai_transcribe_prompt: str = ""
    last_error: str = field(default="", init=False)

    def listen_once(self) -> str:
        sr = self._load_speech_recognition()
        if sr is None:
            return ""

        recognizer = self._build_recognizer(sr)

        try:
            mic_label = "default" if self.device_index is None else str(self.device_index)
            print(f"[VOICE] Using microphone: {mic_label}" if self.device_index is None else f"[VOICE] Using microphone index: {mic_label}")
            with sr.Microphone(device_index=self.device_index) as source:
                print("[VOICE] Listening...")
                try:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                except Exception:
                    pass
                print(f"[VOICE] Energy threshold: {recognizer.energy_threshold}")
                audio = recognizer.listen(
                    source,
                    timeout=self.timeout,
                    phrase_time_limit=self.phrase_time_limit,
                )
        except sr.WaitTimeoutError:
            self.last_error = "timeout"
            print("[ASR] No speech detected before timeout.")
            return ""
        except Exception as exc:
            self.last_error = "missing-microphone"
            print(f"[VOICE] Microphone unavailable: {exc}. Install PyAudio or use --voice-text.")
            return ""

        return self._recognize_audio(sr, recognizer, audio)

    def record_test_audio(self, seconds: int, output_path: Path) -> bool:
        self.last_error = ""
        sr = self._load_speech_recognition()
        if sr is None:
            return False

        recognizer = self._build_recognizer(sr)

        try:
            mic_label = "default" if self.device_index is None else str(self.device_index)
            print(f"[VOICE] Using microphone: {mic_label}" if self.device_index is None else f"[VOICE] Using microphone index: {mic_label}")
            with sr.Microphone(device_index=self.device_index) as source:
                print("[MIC TEST] Recording...")
                try:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                except Exception:
                    pass
                print(f"[VOICE] Energy threshold: {recognizer.energy_threshold}")
                audio = recognizer.record(source, duration=seconds)
        except Exception as exc:
            self.last_error = "missing-microphone"
            print(f"[MIC TEST] Microphone unavailable: {exc}. Install PyAudio or choose another device.")
            return False

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(audio.get_wav_data())
        except Exception as exc:
            self.last_error = "recording-failed"
            print(f"[MIC TEST] Failed to save recording: {exc}")
            return False

        print(f"[MIC TEST] Saved to {output_path.as_posix()}")
        print("[MIC TEST] Play this file to confirm the microphone captured your voice.")
        return True

    def _load_speech_recognition(self):
        self.last_error = ""
        try:
            sr = import_module("speech_recognition")
        except ImportError:
            self.last_error = "missing-dependency"
            print("[VOICE] SpeechRecognition is not installed. Install requirements-voice.txt or use --voice-text.")
            return None
        return sr

    def _build_recognizer(self, sr):
        recognizer = sr.Recognizer()
        recognizer.pause_threshold = self.pause_threshold
        recognizer.operation_timeout = 8
        return recognizer

    def _recognize_audio(self, sr, recognizer, audio) -> str:
        if self.asr_provider == "openai":
            return self._recognize_audio_openai(audio)
        return self._recognize_audio_google(sr, recognizer, audio)

    def _recognize_audio_google(self, sr, recognizer, audio) -> str:
        try:
            print("[ASR] Recognizing speech...")
            transcript = recognizer.recognize_google(audio, language=self.language)
            transcript = transcript.strip()
            print(f"[ASR] Transcript: {transcript}")
            return transcript
        except sr.UnknownValueError:
            self.last_error = "unknown-speech"
            print("[ASR] Sorry, I could not understand the speech.")
        except (
            TimeoutError,
            socket.timeout,
            urllib.error.URLError,
            http.client.HTTPException,
            OSError,
            sr.RequestError,
        ):
            self.last_error = "network-failure"
            print("[ASR] Online speech recognition timed out or failed. Please try again or use --voice-text.")
        return ""

    def _recognize_audio_openai(self, audio) -> str:
        if not os.environ.get("OPENAI_API_KEY"):
            self.last_error = "missing-api-key"
            print("[ASR] OPENAI_API_KEY is not set. Use --voice-text or set the key.")
            return ""

        try:
            openai_module = import_module("openai")
        except ImportError:
            self.last_error = "missing-dependency"
            print("[ASR] OpenAI package is not installed. Run: pip install -r requirements-voice.txt")
            return ""

        try:
            print("[ASR] Recognizing speech with OpenAI...")
            openai_language = self._openai_language_code()
            prompt = self.openai_transcribe_prompt or self._default_openai_prompt(openai_language)
            print(f"[ASR] OpenAI language: {openai_language}")
            audio_file = io.BytesIO(audio.get_wav_data())
            audio_file.name = "speech.wav"
            client = openai_module.OpenAI()
            transcription = client.audio.transcriptions.create(
                model=self.openai_transcribe_model,
                file=audio_file,
                response_format="json",
                language=openai_language,
                prompt=prompt,
            )
            transcript = self._extract_openai_transcript(transcription)
            print(f"[ASR] Transcript: {transcript}")
            return transcript
        except Exception:
            self.last_error = "network-failure"
            print("[ASR] OpenAI speech recognition failed. Please try again or use --voice-text.")
            return ""

    def _openai_language_code(self) -> str:
        language = (self.language or "").strip()
        if not language:
            return "en"
        lowered = language.lower()
        if lowered == "en-us":
            return "en"
        if lowered == "ar-sa":
            return "ar"
        if "-" in lowered:
            return lowered.split("-", 1)[0]
        return lowered

    def _default_openai_prompt(self, openai_language: str) -> str:
        if openai_language == "ar":
            return "The speaker may speak Arabic or English commands for a Personal Research Assistant."
        return (
            "The speaker is giving commands to a Personal Research Assistant. Expected phrases include: "
            "What is in my note about last week's meeting, Look up the Model Context Protocol and summarize it, "
            "Research the top three vector databases and save a report."
        )

    def _extract_openai_transcript(self, transcription) -> str:
        text = getattr(transcription, "text", transcription)
        return str(text).strip()
