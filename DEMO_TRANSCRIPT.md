# Demo Transcript

## Environment

- Python virtual environment active.
- Core CLI does not require API keys.
- Optional OpenAI ASR voice demo requires `OPENAI_API_KEY` in the environment.
- API keys are not committed or included in the archive.

## 1. Automated Tests

Command:

```bash
python -m unittest discover -s tests
```

Result:

```text
Ran 23 tests in 0.073s

OK
```

This verifies core routing, file safety, voice helper imports, microphone utilities, and other non-hardware checks.

## 2. Required Week 3 End-to-End Demo

Command:

```bash
python main.py --demo
```

Observed result summary:

### Flow A: Personal Knowledge

- Intent: `knowledge`
- Agents: Orchestrator -> Knowledge Agent -> General Assistant
- Citation returned: `workspace/notes/last-weeks-meeting.md`

### Flow B: External Research

- Intent: `research`
- Agents: Orchestrator -> Research Agent -> General Assistant
- Source returned: `https://en.wikipedia.org/wiki/Model_Context_Protocol`

### Flow C: Research and Save Report

- Intent: `research_save`
- Agents: Orchestrator -> Research Agent -> Report Writer -> File / Workspace Agent -> General Assistant
- Report saved successfully.
- Saved path: `reports/vector-dbs.md`
- Sources:
  - `https://milvus.io/`
  - `https://weaviate.io/`
  - `https://qdrant.tech/`

## 3. Individual Agent Checks

Command:

```bash
python main.py --trace "hello"
```

Expected:

- Intent: `general`
- Agent: General Assistant

Command:

```bash
python main.py --trace "What is in my note about last week's meeting?"
```

Expected:

- Intent: `knowledge`
- Agents: Knowledge Agent, General Assistant
- Citation: `workspace/notes/last-weeks-meeting.md`

Command:

```bash
python main.py --trace "Look up the Model Context Protocol and summarize it."
```

Expected:

- Intent: `research`
- Agents: Research Agent, General Assistant
- Source URL returned.

Command:

```bash
python main.py --force --trace "Research the top three vector databases and save a report to reports/vector-dbs.md."
```

Expected:

- Intent: `research_save`
- Agents: Research Agent, Report Writer, File / Workspace Agent, General Assistant
- Final status: report saved.

Command:

```bash
python main.py --trace "Read file reports/vector-dbs.md"
```

Expected:

- Intent: `file_read`
- File read succeeds.

Command:

```bash
python main.py --trace "Create file notes/agent-test.md with This file was created by the File Agent."
```

Expected:

- Intent: `file_create`
- File created inside workspace.

Command:

```bash
python main.py --trace "Create file ../secret.md with should not work"
```

Expected:

- Unsafe path rejected.
- Message: `Path is outside the safe workspace.`

Command:

```bash
python main.py --trace "What is in my note about totally unknown topic?"
```

Expected:

- Intent: `knowledge`
- No matching note found.
- Graceful no-result response.

## 4. Optional Voice Bonus: OpenAI ASR Live Voice Demo

This is an optional bonus and is not required for the core assignment.

Command:

```bash
python main.py --voice --asr-provider openai --voice-language en --voice-device-index 1 --trace --force --voice-timeout 12 --voice-phrase-limit 8 --voice-pause-threshold 1.5
```

Observed successful result:

```text
[VOICE] Using microphone index: 1
[VOICE] Listening...
[ASR] Recognizing speech with OpenAI...
[ASR] OpenAI language: en
[ASR] Transcript: What is in my note about last week's meetings?
[TRACE] Intent: knowledge
[TRACE] selected agents: Orchestrator -> Knowledge Agent -> General Assistant
[TRACE] knowledge snippets: 1 | citations: workspace/notes/last-weeks-meeting.md
[TTS] Speaking...
```

This verifies the live voice pipeline:

```text
Microphone -> OpenAI ASR -> Orchestrator -> Knowledge Agent -> General Assistant -> TTS
```

Fallback and diagnostics:

- `--voice-text --trace --force` remains the reliable fallback if microphone or API access is unavailable.
- `--test-mic --test-mic-seconds 3 --voice-device-index 1` can verify microphone capture without calling ASR.
- Do not include `.env`, API keys, or `workspace/mic-test.wav` in the submission archive.

## 5. Final Status

- Automated tests passed: yes, 23 tests.
- Required Flow A passed: yes.
- Required Flow B passed: yes.
- Required Flow C passed: yes.
- File safety check passed: yes.
- Local MCP-compatible filesystem boundary used: yes.
- CLI interface verified: yes.
- Optional OpenAI ASR voice bonus verified: yes.
- API key included in submission: no.
