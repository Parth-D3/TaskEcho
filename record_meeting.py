"""
record_meeting.py — capture meeting audio LOCALLY to a WAV file.

Works for ANY meeting app (Zoom, Google Meet, Teams) because it records at the
operating-system audio layer, not from inside the app. No cloud, no cost.

--------------------------------------------------------------------------
PREREQUISITE: a virtual audio device so the call audio is a recordable INPUT
--------------------------------------------------------------------------
  macOS:    BlackHole (free)   ->  brew install blackhole-2ch
  Windows:  VB-CABLE (free)    OR  the built-in WASAPI loopback
  Linux:    PulseAudio / PipeWire "monitor" source  (built in, nothing to install)

You also need to send the meeting app's OUTPUT to that virtual device
(e.g. in Zoom: Settings > Audio > Speaker = "BlackHole"/"CABLE Input").
To also capture YOUR OWN mic, combine mic + virtual device into one input:
  macOS: create an "Aggregate Device" in Audio MIDI Setup
  Windows: use VoiceMeeter (free) or OBS to mix mic + system audio

--------------------------------------------------------------------------
INSTALL
--------------------------------------------------------------------------
  pip install sounddevice soundfile numpy

--------------------------------------------------------------------------
USAGE
--------------------------------------------------------------------------
  python record_meeting.py --list                  # find your device number
  python record_meeting.py --device 3 --out call.wav
  #   ...hold your meeting..., press Ctrl+C to stop
  python meeting_notes.py call.wav                 # your existing pipeline
"""

import argparse
import queue
import sys
import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 16000   # Whisper expects 16 kHz; mono is plenty for speech
CHANNELS = 1


def list_devices():
    print(sd.query_devices())
    print("\nPick the INDEX of your virtual/loopback INPUT — e.g. a device named "
          "'BlackHole', 'CABLE Output', or one ending in '.monitor'.")


def record(device: int, out_path: str):
    audio_q: "queue.Queue" = queue.Queue()

    def callback(indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        audio_q.put(indata.copy())

    print(f"Recording from device {device} -> {out_path}")
    print("Press Ctrl+C to stop.\n")
    with sf.SoundFile(out_path, mode="w", samplerate=SAMPLE_RATE,
                      channels=CHANNELS, subtype="PCM_16") as f:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                            device=device, callback=callback):
            try:
                while True:
                    f.write(audio_q.get())
            except KeyboardInterrupt:
                print(f"\nStopped. Saved -> {out_path}")
                print(f"Next: python meeting_notes.py {out_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--list", action="store_true", help="list audio devices and exit")
    p.add_argument("--device", type=int, help="input device index to record from")
    p.add_argument("--out", default="meeting.wav", help="output WAV path")
    args = p.parse_args()

    if args.list or args.device is None:
        list_devices()
        sys.exit(0)
    record(args.device, args.out)
