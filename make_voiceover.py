#!/usr/bin/env python3
"""Generate the PoC voice-over clips with Gemini TTS.

Reads GEMINI_API_KEY from the environment or from a `.env` file next to this
script (GEMINI_API_KEY=...). Writes vo/<name>.wav clips and vo/durations.json
(used by videodemo.rpy to size each scene's pause). Existing clips are kept;
delete a wav to regenerate it.
"""

import base64
import json
import os
import struct
import subprocess
import sys
import urllib.request

VOICE = "Kore"
MODEL = "gemini-2.5-flash-preview-tts"
STYLE = "Narrate in a clear, warm, engaging tech-demo narrator voice, at a lively pace: "

LINES = [
    # --- 1. The magic of PC-98 visuals in modern engines ----------------------
    ("title", "Think you need modern 4K textures to make your visual novel look stunning? What if limiting your game to just sixteen colors actually makes it look better? Today we're bringing back the iconic, high-contrast PC-98 aesthetic inside Ren'Py with a single custom shader: limited palettes, ordered dithering, and the palette-register lighting tricks of the original hardware."),
    ("hook_plain", "Here is an ordinary modern Ren'Py scene. A painted 1080p background and a flat character sprite, millions of colors."),
    ("hook_pc98", "And here is the same scene, one line of code later. 640 by 360 pixels, sixteen colors, ordered dithering. A PC-98 game, rendered live from modern assets."),
    ("why16", "Why does this look so good? A sixteen-color palette forces every scene into a deliberate, high-contrast color script. Gradients become checkerboard textures with real visual weight. That grit is exactly what most smooth, flat-shaded indie games are missing."),
    ("hurdle", "The catch: real PC-98 artists hand-dithered every single frame. A modern visual novel has dozens of sprites, each with expressions, poses and lighting changes. Nobody is going to pixel-art thousands of frames by hand. The look has to be computed dynamically, on the GPU, every frame."),
    # --- 2. Pixelate -> quantise -> dither ----------------------------------------
    ("step_pixelate", "Step one. The shader runs once, on the whole master layer. It snaps the frame to a 640 by 360 grid, then quantizes every channel to four bits: the PC-98's 4096-color hardware space. Already retro, but still far more colors than the machine could show at once."),
    ("step_palette", "Step two: sixteen colors. Every pixel is matched to the nearest entry of a sixteen-color palette. With no dithering, the gradients collapse into flat bands. This is the real on-screen limit of a PC-98."),
    ("pipeline_2", "Now the Bayer matrix. A two-by-two ordered dither compares every pixel against a threshold pattern and picks between the two best palette colors. Smooth shading turns into the authentic checkerboard cross-hatching."),
    ("pipeline_4", "A four-by-four matrix gives sixteen mix ratios and smoother ramps, at the price of a busier texture. Most PC-98 art lived somewhere between the two."),
    ("pipeline_8", "Eight by eight gives sixty-four ratios. Smoothest, but the texture gets busy. The threshold is computed per emulated pixel, so the pattern stays locked to the pixel grid, just like on the real machine."),
    # --- 3. Palettes ----------------------------------------------------------------
    ("pal_static", "Palette choice is the real art here. A fixed, generic sixteen-color palette with skin tones keeps the character readable in any scene, but the background turns muddy."),
    ("pal_scene", "A palette extracted per scene, sixteen colors picked from background and character together and snapped to the PC-98's four bits per channel, keeps everything vibrant."),
    ("pal_tool", "The palettes come from a small offline script: median-cut quantization of background and sprite together, a farthest-point pick so highlights and accents survive, and every color snapped to four bits per channel so it is a legal PC-98 color. Sixteen swatches per scene, exactly what a PC-98 artist would have hand-picked."),
    # --- 4. Light, the PC-98 way ----------------------------------------------------
    ("candles_off", "Step three: light. Before quantization, the shader multiplies the frame by an ambient color and adds up to two point lights. With the ambient alone, the room goes dark."),
    ("candles", "Two warm point lights on the candles, flickering through ATL. Because lighting happens before the palette step, the halos turn into concentric dither rings, exactly how hand-drawn PC-98 candlelight looked."),
    ("flashlight", "A cold ambient and a flashlight that follows the mouse. Any light you can express as a uniform becomes dithered, sixteen-color light, for free."),
    ("fade_in", "Now the hardware tricks. The shader matches colors against one palette, but displays another. Ramp the display registers up from black and you get the classic PC-98 fade-in: every pixel keeps its color index, only the register values move."),
    ("pal_swap", "Day to night is the same idea: a register swap towards a cold version of the same palette. No re-quantization, no dither crawl. That is exactly how the original hardware did night scenes."),
    ("lightning", "Lightning. Every register slams to white for two frames and decays. One uniform, no extra draw call."),
    ("cycle", "Color cycling. Swap two palette registers every few frames, here the siren's red and blue, and the police lights flash without a single animated frame. On the real hardware this was free; here it is one uniform write per frame."),
    ("scanlines", "And for the CRT feel, an optional scanline pass darkens the gap between emulated rows, after quantization."),
    # --- 5. Integration + performance -------------------------------------------------
    ("integrate", "Dropping this into a real project takes one line: a transform on the master layer. Dialogue lives on its own layer, so the text stays crisp. I'm already running it in my own game, Shafted in the Snow."),
    ("optimize", "Performance tips. Keep it to a single pass per layer. Precompute palettes offline. Cap the palette search at sixteen iterations. Turn off the supersampling on mobile. And avoid dynamic array indexing, so the shader compiles on GLES and ANGLE for phones and Windows."),
    ("end", "Vintage hardware constraints, modern engine flexibility. Take the code, swap in your own art, and experiment. Full source on GitHub, link in the description."),
]



def load_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def tts(key, text):
    body = json.dumps({
        "contents": [{"parts": [{"text": STYLE + text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}},
        },
    }).encode()
    req = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % MODEL,
        data=body,
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    part = d["candidates"][0]["content"]["parts"][0]["inlineData"]
    assert part["mimeType"].startswith("audio/L16"), part["mimeType"]
    return base64.b64decode(part["data"])


def write_wav(path, pcm, rate=24000):
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVE")
        f.write(b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16))
        f.write(b"data" + struct.pack("<I", len(pcm)) + pcm)


def main():
    key = load_key()
    if not key:
        sys.exit("GEMINI_API_KEY is not set (export it or put GEMINI_API_KEY=... in .env)")

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs("vo", exist_ok=True)
    durations = {}

    for name, text in LINES:
        path = os.path.join("vo", name + ".wav")
        if not os.path.exists(path):
            for attempt in range(4):
                try:
                    pcm = tts(key, text)
                    break
                except Exception as e:  # network hiccups / timeouts
                    if attempt == 3:
                        raise
                    print("  retry %d for %s: %s" % (attempt + 1, name, e))
            write_wav(path, pcm)
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path]).decode().strip()
        durations[name] = float(out)
        print("%-13s %5.2fs  %s" % (name, durations[name], text[:60]))

    with open(os.path.join("vo", "durations.json"), "w") as f:
        json.dump(durations, f, indent=2)
    print("total %.1fs" % sum(durations.values()))


if __name__ == "__main__":
    main()
