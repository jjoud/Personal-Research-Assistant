from __future__ import annotations

import argparse
from pathlib import Path

from agents.orchestrator import Orchestrator


def build_orchestrator(force: bool = False) -> Orchestrator:
    project_root = Path(__file__).resolve().parent
    workspace_root = project_root / "workspace"
    return Orchestrator(workspace_root=workspace_root, force=force)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Personal Research Assistant command-line demo"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the three required Week 3 flows automatically.",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Show orchestrator trace output for the request.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow file overwrite/update without interactive confirmation.",
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Run the optional microphone-based voice loop bonus.",
    )
    parser.add_argument(
        "--voice-text",
        action="store_true",
        help="Run the optional voice loop using typed transcripts instead of a microphone.",
    )
    parser.add_argument(
        "--test-mic",
        action="store_true",
        help="Record microphone audio to workspace/mic-test.wav without using Google ASR.",
    )
    parser.add_argument(
        "--test-mic-seconds",
        type=int,
        default=3,
        help="Recording length for --test-mic.",
    )
    parser.add_argument(
        "--list-mics",
        action="store_true",
        help="List available microphone devices and exit.",
    )
    parser.add_argument(
        "--speak",
        action="store_true",
        help="Speak the final answer with text-to-speech for normal CLI requests and demo output.",
    )
    parser.add_argument(
        "--voice-language",
        default="en-US",
        help="Recognition language for the voice bonus.",
    )
    parser.add_argument(
        "--asr-provider",
        choices=["google", "openai"],
        default="google",
        help="ASR provider for microphone voice mode.",
    )
    parser.add_argument(
        "--openai-transcribe-model",
        default="gpt-4o-mini-transcribe",
        help="OpenAI transcription model when --asr-provider openai is used.",
    )
    parser.add_argument(
        "--openai-transcribe-prompt",
        default="",
        help="Optional custom prompt for OpenAI transcription.",
    )
    parser.add_argument(
        "--voice-timeout",
        type=int,
        default=8,
        help="Seconds to wait for speech before timing out in voice mode.",
    )
    parser.add_argument(
        "--voice-phrase-limit",
        type=int,
        default=12,
        help="Maximum phrase length for voice capture in seconds.",
    )
    parser.add_argument(
        "--voice-pause-threshold",
        type=float,
        default=0.8,
        help="Seconds of silence that marks the end of a voice phrase.",
    )
    parser.add_argument(
        "--voice-device-index",
        type=int,
        default=None,
        help="Microphone device index to use for voice mode.",
    )
    parser.add_argument(
        "--voice-timings",
        action="store_true",
        help="Show approximate ASR, agent, and TTS timings in voice mode.",
    )
    parser.add_argument(
        "request",
        nargs="*",
        help="User request, for example: Look up MCP and summarize it.",
    )
    args = parser.parse_args()

    if args.list_mics:
        _list_microphones()
        return

    if args.test_mic:
        _run_mic_test(args)
        return

    orchestrator = build_orchestrator(force=args.force or args.demo)

    if args.voice or args.voice_text:
        _run_voice_mode(orchestrator, args)
        return

    if args.demo:
        _run_demo(orchestrator, speak=args.speak)
        return

    if args.request:
        user_request = " ".join(args.request)
        if args.trace:
            result = orchestrator.run_request(user_request, trace=True)
            _print_trace(result.trace_lines)
            print(result.final_answer)
            _maybe_speak(result.final_answer, args.speak)
        else:
            final_answer = orchestrator.handle_request(user_request)
            print(final_answer)
            _maybe_speak(final_answer, args.speak)
        return

    print("Personal Research Assistant. Type 'exit' to quit.")
    while True:
        try:
            user_request = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_request.lower() in {"exit", "quit"}:
            break
        if not user_request:
            continue

        if args.trace:
            result = orchestrator.run_request(user_request, trace=True)
            _print_trace(result.trace_lines)
            print(result.final_answer)
            _maybe_speak(result.final_answer, args.speak)
        else:
            final_answer = orchestrator.handle_request(user_request)
            print(final_answer)
            _maybe_speak(final_answer, args.speak)


def _print_trace(trace_lines: list[str]) -> None:
    if not trace_lines:
        return
    for line in trace_lines:
        if line.startswith("[TRACE]"):
            print(line)
        else:
            print(f"[TRACE] {line}")


def _run_demo(orchestrator: Orchestrator, speak: bool = False) -> None:
    speaker = _maybe_create_speaker(speak)
    flows = [
        ("Flow A: Personal Knowledge", "What is in my note about last week's meeting?"),
        ("Flow B: External Research", "Look up the Model Context Protocol and summarize it."),
        (
            "Flow C: Research and Save Report",
            "Research the top three vector databases and save a report to reports/vector-dbs.md.",
        ),
    ]

    for title, request in flows:
        print(f"=== {title} ===")
        result = orchestrator.run_request(request, trace=True)
        _print_trace(result.trace_lines)
        print(result.final_answer)
        _speak_with_existing_speaker(speaker, result.final_answer)
        print()


def _run_voice_mode(orchestrator: Orchestrator, args: argparse.Namespace) -> None:
    from voice.voice_loop import run_voice_loop

    run_voice_loop(
        orchestrator,
        trace=args.trace,
        force=args.force or args.demo,
        language=args.voice_language,
        timeout=args.voice_timeout,
        phrase_time_limit=args.voice_phrase_limit,
        pause_threshold=args.voice_pause_threshold,
        device_index=args.voice_device_index,
        asr_provider=args.asr_provider,
        openai_transcribe_model=args.openai_transcribe_model,
        openai_transcribe_prompt=args.openai_transcribe_prompt,
        text_fallback=args.voice_text,
        timings=args.voice_timings,
    )


def _maybe_create_speaker(enabled: bool):
    if not enabled:
        return None
    from voice.tts import Speaker

    return Speaker()


def _speak_with_existing_speaker(speaker, text: str) -> None:
    if speaker is None:
        return
    speaker.speak(text)


def _maybe_speak(text: str, enabled: bool) -> None:
    speaker = _maybe_create_speaker(enabled)
    _speak_with_existing_speaker(speaker, text)


def _list_microphones() -> None:
    try:
        import speech_recognition as sr
    except ImportError:
        print("SpeechRecognition is not installed. Install requirements-voice.txt first.")
        return

    names = sr.Microphone.list_microphone_names()
    if not names:
        print("No microphones found.")
        return
    for index, name in enumerate(names):
        print(f"[{index}] {name}")


def _run_mic_test(args: argparse.Namespace) -> None:
    from voice.asr import SpeechRecognizer

    project_root = Path(__file__).resolve().parent
    output_path = project_root / "workspace" / "mic-test.wav"
    recognizer = SpeechRecognizer(device_index=args.voice_device_index)
    recognizer.record_test_audio(args.test_mic_seconds, output_path)


if __name__ == "__main__":
    main()
