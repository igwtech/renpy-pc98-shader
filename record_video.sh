#!/bin/bash
## Records the PoC video demo (game/videodemo.rpy) into poc_video.mp4.
## Runs the game on a virtual X server (Xvfb) and captures it with ffmpeg,
## so it doesn't touch your desktop session. Requires: Xvfb, ffmpeg, xdotool.
##
## Full pipeline:
##   python3 make_voiceover.py      # Gemini TTS clips -> vo/*.wav + vo/durations.json
##   ./record_video.sh              # -> poc_video.mp4 + poc_video_cues.json
##   python3 mix_voiceover.py       # -> poc_video_vo.mp4

set -e
cd "$(dirname "$0")"

DISP=:99
OUT="${1:-poc_video.mp4}"
MARKER="poc_video_mouse_marker"
START_MARKER="poc_video_start_marker"

rm -f "$MARKER" "$START_MARKER" poc_video_cues.json

## Virtual X server, larger than the game window so Ren'Py keeps the exact
## 1280x720 window size the demo asks for.
Xvfb "$DISP" -screen 0 1920x1080x24 -nolisten tcp &
XVFB_PID=$!
trap 'kill $XVFB_PID 2>/dev/null || true' EXIT
sleep 1

## Launch the scripted demo with a throwaway savedir (no remembered window size).
SAVEDIR="$(mktemp -d)"
env -u WAYLAND_DISPLAY DISPLAY="$DISP" SDL_VIDEODRIVER=x11 SDL_AUDIODRIVER=dummy \
    RENPY_POC_VIDEO=1 ./renpy-sdk/renpy.sh . --savedir "$SAVEDIR" &
GAME_PID=$!

## Wait for the demo's start marker so the recording (and the timeline in
## poc_video_cues.json) begins at the demo's t=0.
for i in $(seq 1 600); do
    [ -f "$START_MARKER" ] && break
    sleep 0.1
done

## Find the game window's exact rectangle to capture.
WID=$(DISPLAY="$DISP" xdotool search --name "RenpyPC98" | head -1)
eval "$(DISPLAY="$DISP" xdotool getwindowgeometry --shell "$WID")"
WIDTH=$((WIDTH / 2 * 2))
HEIGHT=$((HEIGHT / 2 * 2))
echo "Capturing window ${WIDTH}x${HEIGHT} at +${X},${Y}"

## Park the cursor out of the way.
DISPLAY="$DISP" xdotool mousemove $((X + WIDTH - 1)) $((Y + HEIGHT - 1))

ffmpeg -y -loglevel error -f x11grab -framerate 30 -video_size "${WIDTH}x${HEIGHT}" -i "$DISP+${X},${Y}" \
    -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -movflags +faststart \
    "$OUT" &
FF_PID=$!

## When the flashlight scene starts, sweep the cursor so the light follows it.
(
    while kill -0 "$GAME_PID" 2>/dev/null; do
        if [ -f "$MARKER" ]; then
            WIN_X="$X" WIN_Y="$Y" WIN_W="$WIDTH" WIN_H="$HEIGHT" python3 - <<'PY'
import math, os, subprocess, time
env = dict(os.environ, DISPLAY=":99")
wx, wy = int(os.environ["WIN_X"]), int(os.environ["WIN_Y"])
ww, wh = int(os.environ["WIN_W"]), int(os.environ["WIN_H"])
t0 = time.time()
while time.time() - t0 < 14.0:
    t = time.time() - t0
    x = wx + ww * 0.50 + ww * 0.30 * math.sin(t * 0.9)
    y = wy + wh * 0.50 + wh * 0.25 * math.sin(t * 0.6 + 1.3)
    subprocess.run(["xdotool", "mousemove", str(int(x)), str(int(y))], env=env)
    time.sleep(0.03)
subprocess.run(["xdotool", "mousemove", str(wx + ww - 1), str(wy + wh - 1)], env=env)
PY
            break
        fi
        sleep 0.4
    done
) &

wait "$GAME_PID" || true
sleep 1
kill -INT "$FF_PID" 2>/dev/null || true
wait "$FF_PID" || true
rm -f "$MARKER"

echo "Video saved to: $OUT"
