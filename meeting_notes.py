"""
meeting_notes.py — a fully LOCAL meeting-notes pipeline.

    audio file  ->  faster-whisper (local STT)  ->  Ollama (local LLM)  ->  Markdown notes file

No API keys. No cloud. No cost. Everything runs on your own machine.

--------------------------------------------------------------------------
ONE-TIME SETUP
--------------------------------------------------------------------------
1. Install Ollama (the local LLM runner): https://ollama.com
   Then pull a small model:
       ollama pull llama3.2
2. Install Python deps:
       pip install faster-whisper requests
3. Install ffmpeg (Whisper needs it to decode audio):
       macOS:  brew install ffmpeg
       Linux:  sudo apt install ffmpeg

--------------------------------------------------------------------------
RUN
--------------------------------------------------------------------------
       python meeting_notes.py meeting.mp3

Output: meeting_notes.md in the current folder.
"""

import sys
import json
import requests
from pathlib import Path
from faster_whisper import WhisperModel

# ----------------------------------------------------------------------------
# Config — all local. Pick a bigger Whisper model for accuracy, smaller for speed.
# ----------------------------------------------------------------------------
WHISPER_MODEL = "small"        # tiny | base | small | medium | large-v3
OLLAMA_MODEL  = "llama3.2"     # any model you've run `ollama pull` on
OLLAMA_URL    = "http://localhost:11434/api/generate"


# ----------------------------------------------------------------------------
# Step 1 — Speech to text, entirely on your machine.
# ----------------------------------------------------------------------------
def transcribe(audio_path: str) -> str:
    print(f"[1/3] Transcribing '{audio_path}' with Whisper '{WHISPER_MODEL}'...")
    # device="cpu", compute_type="int8" runs on any laptop with no GPU.
    # If you have an NVIDIA GPU: device="cuda", compute_type="float16".
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(audio_path)
    text = " ".join(seg.text.strip() for seg in segments)
    print(f"      ...{len(text)} characters transcribed.")
    return text


# ----------------------------------------------------------------------------
# Step 2 — Transcript -> structured summary + action items, via the local LLM.
# We ask Ollama for JSON and use its format="json" flag so the output parses.
# ----------------------------------------------------------------------------
def extract_notes(transcript: str) -> dict:
    print(f"[2/3] Summarizing with Ollama '{OLLAMA_MODEL}'...")
    prompt = (
        "You are a meeting assistant. Read the transcript below and respond with "
        "ONLY a JSON object of this exact shape:\n"
        '{"summary": "<3-4 sentence summary>", '
        '"action_items": [{"task": "<what needs doing>", '
        '"owner": "<who, or unassigned>", "due": "<when, or none>"}]}\n\n'
        f"Transcript:\n{transcript}"
    )
    resp = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",   # forces the model to return valid JSON
        },
        timeout=600,
    )
    resp.raise_for_status()
    raw = resp.json()["response"]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback so a malformed response doesn't crash the run.
        return {"summary": raw.strip(), "action_items": []}


# ----------------------------------------------------------------------------
# Step 3 — THE INTEGRATION: persist results to a local Markdown file.
# (This is your output sink. Later you can swap it for a calendar file,
#  a todo.txt, SQLite, or an MCP filesystem server — same pattern.)
# ----------------------------------------------------------------------------
def write_markdown(notes: dict, transcript: str, out_path: str) -> None:
    lines = [
        "# Meeting Notes\n",
        "## Summary\n",
        notes.get("summary", "_(none)_"),
        "\n## Action Items\n",
    ]
    items = notes.get("action_items", [])
    if not items:
        lines.append("_No action items found._")
    for item in items:
        task = item.get("task", "")
        owner = item.get("owner", "unassigned")
        due = item.get("due", "none")
        lines.append(f"- [ ] {task}  _(owner: {owner} · due: {due})_")
    lines += ["\n---\n", "<details><summary>Full transcript</summary>\n",
              transcript, "\n</details>"]
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"[3/3] Saved -> {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python meeting_notes.py <audio_file>")
        sys.exit(1)

    audio = sys.argv[1]
    transcript = transcribe(audio)
    notes = extract_notes(transcript)
    out = Path(audio).with_suffix("").name + "_notes.md"
    write_markdown(notes, transcript, out)
    print("Done.")
