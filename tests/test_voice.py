from __future__ import annotations

import importlib
import io
import os
import sys
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
import tempfile

import main


class VoiceBonusTests(unittest.TestCase):
    def test_voice_modules_import_without_optional_dependencies(self) -> None:
        importlib.import_module("voice.asr")
        importlib.import_module("voice.tts")
        importlib.import_module("voice.voice_loop")

    def test_clean_text_for_speech(self) -> None:
        from voice.tts import clean_text_for_speech

        cleaned = clean_text_for_speech(
            "# Title\n\nHere is a [link](https://example.com) and `code`.\n```python\nprint('x')\n```"
        )
        self.assertEqual(cleaned, "Title Here is a link and code.")

    def test_cli_still_works_without_voice_flags(self) -> None:
        output = io.StringIO()
        with patch.object(sys, "argv", ["main.py", "hello"]), redirect_stdout(output):
            main.main()
        self.assertIn("I can help with general questions", output.getvalue())

    def test_voice_text_flag_routes_into_voice_mode(self) -> None:
        with patch.object(sys, "argv", ["main.py", "--voice-text"]), patch(
            "main._run_voice_mode"
        ) as run_voice_mode:
            main.main()
        run_voice_mode.assert_called_once()

    def test_asr_timeout_returns_empty_transcript(self) -> None:
        from voice import asr

        class FakeWaitTimeoutError(Exception):
            pass

        class FakeUnknownValueError(Exception):
            pass

        class FakeRequestError(Exception):
            pass

        class FakeRecognizer:
            def __init__(self) -> None:
                self.pause_threshold = 0.0
                self.operation_timeout = None
                self.energy_threshold = 123.0

            def adjust_for_ambient_noise(self, source, duration: float = 0.5) -> None:
                return None

            def listen(self, source, timeout: int, phrase_time_limit: int) -> object:
                return object()

            def recognize_google(self, audio, language: str) -> str:
                raise TimeoutError("network timed out")

        class FakeMicrophone:
            def __init__(self, device_index=None) -> None:
                self.device_index = device_index

            def __enter__(self):
                return object()

            def __exit__(self, exc_type, exc, traceback) -> bool:
                return False

        fake_sr = types.SimpleNamespace(
            Recognizer=FakeRecognizer,
            Microphone=FakeMicrophone,
            WaitTimeoutError=FakeWaitTimeoutError,
            UnknownValueError=FakeUnknownValueError,
            RequestError=FakeRequestError,
        )

        output = io.StringIO()
        with patch.object(asr, "import_module", return_value=fake_sr), redirect_stdout(output):
            recognizer = asr.SpeechRecognizer()
            transcript = recognizer.listen_once()

        self.assertEqual(transcript, "")
        self.assertEqual(recognizer.last_error, "network-failure")
        self.assertIn("Online speech recognition timed out or failed", output.getvalue())

    def test_asr_uses_requested_microphone_device_index(self) -> None:
        from voice import asr

        class FakeRecognizer:
            def __init__(self) -> None:
                self.pause_threshold = 0.0
                self.operation_timeout = None
                self.energy_threshold = 123.0

            def adjust_for_ambient_noise(self, source, duration: float = 0.5) -> None:
                return None

            def listen(self, source, timeout: int, phrase_time_limit: int) -> object:
                return object()

            def recognize_google(self, audio, language: str) -> str:
                return "hello"

        captured_device_indexes: list[int | None] = []

        class FakeMicrophone:
            def __init__(self, device_index=None) -> None:
                captured_device_indexes.append(device_index)

            def __enter__(self):
                return object()

            def __exit__(self, exc_type, exc, traceback) -> bool:
                return False

        fake_sr = types.SimpleNamespace(
            Recognizer=FakeRecognizer,
            Microphone=FakeMicrophone,
            WaitTimeoutError=TimeoutError,
            UnknownValueError=ValueError,
            RequestError=RuntimeError,
        )

        output = io.StringIO()
        with patch.object(asr, "import_module", return_value=fake_sr), redirect_stdout(output):
            recognizer = asr.SpeechRecognizer(device_index=1)
            transcript = recognizer.listen_once()

        self.assertEqual(transcript, "hello")
        self.assertEqual(captured_device_indexes, [1])
        self.assertIn("[VOICE] Using microphone index: 1", output.getvalue())
        self.assertIn("[VOICE] Energy threshold:", output.getvalue())

    def test_openai_asr_provider_transcribes_audio(self) -> None:
        from voice import asr

        class FakeAudio:
            def get_wav_data(self) -> bytes:
                return b"wav-bytes"

        class FakeTranscriptionResponse:
            text = "openai transcript"

        class FakeTranscriptions:
            def create(self, model, file, response_format, language, prompt):
                self.model = model
                self.filename = file.name
                self.payload = file.read()
                self.response_format = response_format
                self.language = language
                self.prompt = prompt
                return FakeTranscriptionResponse()

        fake_transcriptions = FakeTranscriptions()

        class FakeAudioNamespace:
            transcriptions = fake_transcriptions

        class FakeOpenAIClient:
            audio = FakeAudioNamespace()

        fake_openai = types.SimpleNamespace(OpenAI=lambda: FakeOpenAIClient())

        def fake_import_module(name: str):
            if name == "openai":
                return fake_openai
            raise AssertionError(f"Unexpected import: {name}")

        output = io.StringIO()
        with patch.object(asr, "import_module", side_effect=fake_import_module), patch.dict(
            os.environ, {"OPENAI_API_KEY": "test-key"}
        ), redirect_stdout(output):
            recognizer = asr.SpeechRecognizer(
                asr_provider="openai",
                openai_transcribe_model="gpt-4o-mini-transcribe",
            )
            transcript = recognizer._recognize_audio_openai(FakeAudio())

        self.assertEqual(transcript, "openai transcript")
        self.assertEqual(fake_transcriptions.model, "gpt-4o-mini-transcribe")
        self.assertEqual(fake_transcriptions.filename, "speech.wav")
        self.assertEqual(fake_transcriptions.payload, b"wav-bytes")
        self.assertEqual(fake_transcriptions.response_format, "json")
        self.assertEqual(fake_transcriptions.language, "en")
        self.assertIn("Personal Research Assistant", fake_transcriptions.prompt)
        self.assertIn("Recognizing speech with OpenAI", output.getvalue())
        self.assertIn("OpenAI language: en", output.getvalue())

    def test_openai_language_mapping(self) -> None:
        from voice.asr import SpeechRecognizer

        self.assertEqual(SpeechRecognizer(language="en-US")._openai_language_code(), "en")
        self.assertEqual(SpeechRecognizer(language="ar-SA")._openai_language_code(), "ar")
        self.assertEqual(SpeechRecognizer(language="en")._openai_language_code(), "en")
        self.assertEqual(SpeechRecognizer(language="ar")._openai_language_code(), "ar")
        self.assertEqual(SpeechRecognizer(language="fr-FR")._openai_language_code(), "fr")

    def test_openai_custom_prompt_is_passed(self) -> None:
        from voice import asr

        class FakeAudio:
            def get_wav_data(self) -> bytes:
                return b"wav-bytes"

        class FakeTranscriptionResponse:
            text = "custom prompt transcript"

        class FakeTranscriptions:
            def create(self, model, file, response_format, language, prompt):
                self.prompt = prompt
                self.language = language
                return FakeTranscriptionResponse()

        fake_transcriptions = FakeTranscriptions()

        class FakeAudioNamespace:
            transcriptions = fake_transcriptions

        class FakeOpenAIClient:
            audio = FakeAudioNamespace()

        fake_openai = types.SimpleNamespace(OpenAI=lambda: FakeOpenAIClient())

        def fake_import_module(name: str):
            if name == "openai":
                return fake_openai
            raise AssertionError(f"Unexpected import: {name}")

        output = io.StringIO()
        with patch.object(asr, "import_module", side_effect=fake_import_module), patch.dict(
            os.environ, {"OPENAI_API_KEY": "test-key"}
        ), redirect_stdout(output):
            recognizer = asr.SpeechRecognizer(
                asr_provider="openai",
                language="ar-SA",
                openai_transcribe_prompt="Custom assistant command prompt.",
            )
            transcript = recognizer._recognize_audio_openai(FakeAudio())

        self.assertEqual(transcript, "custom prompt transcript")
        self.assertEqual(fake_transcriptions.language, "ar")
        self.assertEqual(fake_transcriptions.prompt, "Custom assistant command prompt.")

    def test_openai_asr_missing_api_key_returns_empty(self) -> None:
        from voice import asr

        class FakeAudio:
            def get_wav_data(self) -> bytes:
                return b"wav-bytes"

        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), redirect_stdout(output):
            recognizer = asr.SpeechRecognizer(asr_provider="openai")
            transcript = recognizer._recognize_audio_openai(FakeAudio())

        self.assertEqual(transcript, "")
        self.assertEqual(recognizer.last_error, "missing-api-key")
        self.assertIn("OPENAI_API_KEY is not set", output.getvalue())

    def test_list_microphones_prints_indexes(self) -> None:
        fake_sr = types.ModuleType("speech_recognition")

        class FakeMicrophone:
            @staticmethod
            def list_microphone_names():
                return ["Microphone Array", "Headset Microphone"]

        fake_sr.Microphone = FakeMicrophone

        output = io.StringIO()
        with patch.dict(sys.modules, {"speech_recognition": fake_sr}):
            with redirect_stdout(output):
                main._list_microphones()

        self.assertIn("[0] Microphone Array", output.getvalue())
        self.assertIn("[1] Headset Microphone", output.getvalue())

    def test_mic_test_records_without_google_asr(self) -> None:
        from voice import asr

        class FakeRecognizer:
            def __init__(self) -> None:
                self.pause_threshold = 0.0
                self.operation_timeout = None
                self.energy_threshold = 111.0

            def adjust_for_ambient_noise(self, source, duration: float = 0.5) -> None:
                return None

            def listen(self, source, timeout: int, phrase_time_limit: int) -> object:
                raise AssertionError("listen() should not be used in mic test")

            def record(self, source, duration: int) -> object:
                class FakeAudio:
                    def get_wav_data(self_nonlocal) -> bytes:
                        return b"fake-wav"

                return FakeAudio()

            def recognize_google(self, audio, language: str) -> str:
                raise AssertionError("recognize_google() must not be called in mic test")

        class FakeMicrophone:
            def __init__(self, device_index=None) -> None:
                self.device_index = device_index

            def __enter__(self):
                return object()

            def __exit__(self, exc_type, exc, traceback) -> bool:
                return False

        fake_sr = types.SimpleNamespace(
            Recognizer=FakeRecognizer,
            Microphone=FakeMicrophone,
            WaitTimeoutError=TimeoutError,
            UnknownValueError=ValueError,
            RequestError=RuntimeError,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output_file = Path(tmp) / "workspace" / "mic-test.wav"
            output = io.StringIO()
            with patch.object(asr, "import_module", return_value=fake_sr), redirect_stdout(output):
                recognizer = asr.SpeechRecognizer(device_index=2)
                ok = recognizer.record_test_audio(2, output_file)

            self.assertTrue(ok)
            self.assertTrue(output_file.exists())
            self.assertEqual(output_file.read_bytes(), b"fake-wav")
            self.assertIn("[MIC TEST] Recording...", output.getvalue())
            self.assertIn("[MIC TEST] Saved to", output.getvalue())

    def test_test_mic_flag_routes_into_mic_test(self) -> None:
        with patch.object(sys, "argv", ["main.py", "--test-mic"]), patch(
            "main._run_mic_test"
        ) as run_mic_test:
            main.main()
        run_mic_test.assert_called_once()


if __name__ == "__main__":
    unittest.main()
