from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from voice.asr import SpeechRecognizer
from voice.tts import Speaker


@dataclass(slots=True)
class VoiceTurnResult:
    transcript: str
    final_answer: str
    trace_lines: list[str]
    asr_seconds: float = 0.0
    agent_seconds: float = 0.0
    tts_seconds: float = 0.0
    total_seconds: float = 0.0


def run_voice_turn(
    orchestrator,
    transcript: str,
    trace: bool = False,
    force: bool = False,
    speaker: Speaker | None = None,
    asr_seconds: float = 0.0,
    timings: bool = False,
) -> VoiceTurnResult:
    start_total = perf_counter()
    speaker = speaker or Speaker()
    if force and hasattr(orchestrator, "file_agent"):
        try:
            orchestrator.force = True
            orchestrator.file_agent.force = True
        except Exception:
            pass

    filler_needed = _needs_filler_phrase(transcript)
    if filler_needed:
        print("[VOICE] Let me check that for you.")
        speaker.speak("Let me check that for you.")

    agent_start = perf_counter()
    result = orchestrator.run_request(transcript, trace=trace)
    agent_seconds = perf_counter() - agent_start

    if trace:
        for line in result.trace_lines:
            if line.startswith("[TRACE]"):
                print(line)
            else:
                print(f"[TRACE] {line}")

    print(result.final_answer)

    tts_start = perf_counter()
    speaker.speak(result.final_answer)
    tts_seconds = perf_counter() - tts_start
    total_seconds = perf_counter() - start_total

    if timings:
        _print_timings(asr_seconds, agent_seconds, tts_seconds, total_seconds)

    return VoiceTurnResult(
        transcript=transcript,
        final_answer=result.final_answer,
        trace_lines=result.trace_lines,
        asr_seconds=asr_seconds,
        agent_seconds=agent_seconds,
        tts_seconds=tts_seconds,
        total_seconds=total_seconds,
    )


def run_voice_loop(
    orchestrator,
    trace: bool = False,
    force: bool = False,
    language: str = "en-US",
    timeout: int = 8,
    phrase_time_limit: int = 12,
    pause_threshold: float = 0.8,
    device_index: int | None = None,
    asr_provider: str = "google",
    openai_transcribe_model: str = "gpt-4o-mini-transcribe",
    openai_transcribe_prompt: str = "",
    text_fallback: bool = False,
    timings: bool = False,
):
    recognizer = SpeechRecognizer(
        language=language,
        timeout=timeout,
        phrase_time_limit=phrase_time_limit,
        pause_threshold=pause_threshold,
        device_index=device_index,
        asr_provider=asr_provider,
        openai_transcribe_model=openai_transcribe_model,
        openai_transcribe_prompt=openai_transcribe_prompt,
    )
    speaker = Speaker()

    if force and hasattr(orchestrator, "file_agent"):
        try:
            orchestrator.force = True
            orchestrator.file_agent.force = True
        except Exception:
            pass

    print("Voice mode active. Say exit, quit, or stop to leave.")
    try:
        while True:
            if text_fallback:
                try:
                    print("[VOICE] Type the transcript, or type exit to stop.")
                    asr_start = perf_counter()
                    transcript = input("> ").strip()
                    asr_seconds = perf_counter() - asr_start
                except EOFError:
                    print("[VOICE] Session ended.")
                    break
                recognizer.last_error = ""
            else:
                asr_start = perf_counter()
                transcript = recognizer.listen_once().strip()
                asr_seconds = perf_counter() - asr_start

            if not transcript:
                if recognizer.last_error in {"missing-dependency", "missing-microphone"}:
                    print("[VOICE] Voice input is unavailable. Use --voice-text or install requirements-voice.txt.")
                    break
                if recognizer.last_error == "network-failure":
                    print("[VOICE] ASR failed for this turn. Try speaking again, or use --voice-text for a reliable demo.")
                    continue
                continue

            lowered = transcript.lower()
            if lowered in {"exit", "quit", "stop"}:
                print("[VOICE] Session ended.")
                break

            result = run_voice_turn(
                orchestrator,
                transcript,
                trace=trace,
                force=force,
                speaker=speaker,
                asr_seconds=asr_seconds,
                timings=timings,
            )

            if trace and not result.trace_lines:
                print("[TRACE] No trace available.")
    except KeyboardInterrupt:
        print("[VOICE] Session ended.")


def _needs_filler_phrase(transcript: str) -> bool:
    text = transcript.lower()
    return any(
        phrase in text
        for phrase in [
            "look up",
            "lookup",
            "research",
            "save a report",
            "create file",
            "update file",
            "read file",
            "note about",
        ]
    )


def _print_timings(asr_seconds: float, agent_seconds: float, tts_seconds: float, total_seconds: float) -> None:
    print(f"[TIMING] ASR: {asr_seconds:.2f}s")
    print(f"[TIMING] Agent: {agent_seconds:.2f}s")
    print(f"[TIMING] TTS: {tts_seconds:.2f}s")
    print(f"[TIMING] Total: {total_seconds:.2f}s")
