#!/usr/bin/env python3
"""Mix the Gemini TTS voice-over into the recorded PoC video.

Reads poc_video_cues.json (scene start times written by videodemo.rpy) and
places each vo/<name>.wav at its cue in a single full-length track, then
muxes it under the video. Output: poc_video_vo.mp4 (or argv[2]).
"""

import json
import subprocess
import sys
import wave

VIDEO = sys.argv[1] if len(sys.argv) > 1 else "poc_video.mp4"
OUT = sys.argv[2] if len(sys.argv) > 2 else "poc_video_vo.mp4"
RATE = 24000
LEAD_IN = 0.35  # small beat after each scene appears

duration = float(subprocess.check_output(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "csv=p=0", VIDEO]).decode().strip())

cues = json.load(open("poc_video_cues.json"))

track = bytearray(int(duration * RATE) * 2)

for name, t in cues.items():
    with wave.open("vo/%s.wav" % name, "rb") as w:
        assert w.getframerate() == RATE and w.getnchannels() == 1
        pcm = w.readframes(w.getnframes())
    off = int((t + LEAD_IN) * RATE) * 2
    end = min(off + len(pcm), len(track))
    track[off:end] = pcm[: end - off]
    print("%-8s cue %7.2fs  clip %5.2fs" % (name, t + LEAD_IN, len(pcm) / 2.0 / RATE))

with wave.open("vo/full_track.wav", "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(RATE)
    w.writeframes(bytes(track))

subprocess.check_call([
    "ffmpeg", "-y", "-loglevel", "error",
    "-i", VIDEO, "-i", "vo/full_track.wav",
    "-map", "0:v", "-map", "1:a",
    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
    "-movflags", "+faststart",
    OUT,
])
print("Wrote", OUT)
