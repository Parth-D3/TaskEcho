# TaskEcho
Local-first AI meeting notes agent.

## Features
- Records meeting audio locally
- Transcribes using faster-whisper
- Summarizes using Ollama
- Extracts action items
- Outputs Markdown notes

## Quickstart
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama pull llama3.2
python record_meeting.py --list
python record_meeting.py --device 3 --out meeting.wav
python meeting_notes.py meeting.wav
