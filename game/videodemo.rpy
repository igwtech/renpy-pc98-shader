## Scripted, non-interactive run of the PoC, meant to be screen-recorded
## (see record_video.sh). Launch with RENPY_POC_VIDEO=1. It follows the video
## outline (hook -> pixelate/quantise/dither -> palettes -> light effects ->
## integration) with narration on a timer, then quits.
##
## If vo/durations.json exists (see make_voiceover.py), each scene's pause is
## stretched to fit its voice-over clip, and poc_video_cues.json records the
## exact time each scene starts (relative to the start marker) so the clips
## can be mixed in at the right offsets afterwards (mix_voiceover.py).

init python:

    import json
    import time

    _vo_durations = {}
    _video_cues = {}
    _video_t0 = None

    def _poc_path(name):
        import os
        return os.path.join(config.gamedir, "..", name)

    def vstart():
        """Load VO durations and drop the marker that starts the recording."""
        global _video_t0
        import os
        p = _poc_path("vo/durations.json")
        if os.path.exists(p):
            with open(p) as f:
                _vo_durations.update(json.load(f))
        _video_t0 = time.time()
        with open(_poc_path("poc_video_start_marker"), "w") as f:
            f.write("go")

    def vcue(name):
        """Record when this scene started, for audio placement."""
        _video_cues[name] = round(time.time() - _video_t0, 3)
        with open(_poc_path("poc_video_cues.json"), "w") as f:
            json.dump(_video_cues, f, indent=2)

    def vdur(name, base):
        """Scene hold time: at least base, and long enough for the VO clip."""
        return max(base, _vo_durations.get(name, 0.0) + 1.5)

    def vsay(name, txt, base):
        """Show narration without waiting for a click, hold for the scene."""
        vcue(name)
        renpy.say(narrator_c, txt, interact=False)
        renpy.pause(vdur(name, base), hard=True)

    def vhold(name, base):
        """Cue + hold with no narration box (title / cards)."""
        vcue(name)
        renpy.pause(vdur(name, base), hard=True)

    def vmark(name):
        """Drop a marker file so the recording script can sync (mouse path)."""
        with open(_poc_path(name), "w") as f:
            f.write("go")


image bg dark = Solid("#0b0b0e")

## --- Cards -----------------------------------------------------------------

image video_title = Text(
    "{b}Emulating PC-98 Limited Color Palette\nLighting Effects on Modern Ren'Py Sprites{/b}\n{size=26}{color=#9ab}one GLSL shader  ·  16-colour palettes  ·  Bayer dithering  ·  palette-register light tricks{/color}{/size}",
    size=46, text_align=0.5, layout="subtitle")

image dither_card = Window(Text(
    "{color=#8fa}// pc98.retro — 16-colour ordered dither (excerpt){/color}\n"
    "float t  = pc98_bayer(cell, u_dither);        {color=#8fa}// Bayer threshold{/color}\n"
    "int   i1 = pc98_nearest(c);                   {color=#8fa}// best palette colour{/color}\n"
    "int   i2 = pc98_nearest(c + (c - c1));        {color=#8fa}// other side of the error{/color}\n"
    "float f  = clamp(dot(c - c1, d) / dot(d, d), 0.0, 1.0);\n"
    "return (t < f) ? pc98_out_at(i2) : pc98_out_at(i1);",
    font="DejaVuSansMono.ttf", size=20, color="#e8eef5"), background="#000000cc", padding=(22, 14, 22, 14), xfill=False, xminimum=0)

image light_card = Window(Text(
    "{color=#8fa}// light BEFORE quantisation -> gradients become dither rings{/color}\n"
    "vec3 light = u_ambient\n"
    "           + u_light1_color * pc98_point_light(cuv, u_light1_pos, aspect)\n"
    "           + u_light2_color * pc98_point_light(cuv, u_light2_pos, aspect);\n"
    "rgb = clamp(rgb * light, 0.0, 1.0);\n"
    "rgb = pc98_palette_dither(rgb, t, u_dither);   {color=#8fa}// then 16 colours{/color}",
    font="DejaVuSansMono.ttf", size=20, color="#e8eef5"), background="#000000cc", padding=(22, 14, 22, 14), xfill=False, xminimum=0)

image regs_card = Window(Text(
    "{color=#8fa}// match against u_palN, DISPLAY u_outN  ->  hardware palette tricks{/color}\n"
    "transform pc98_fade_in(palette, duration):\n"
    "    pc98(palette=palette, display=\"black\")\n"
    "    function PC98PaletteFade(\"black\", palette, duration)",
    font="DejaVuSansMono.ttf", size=20, color="#e8eef5"), background="#000000cc", padding=(22, 14, 22, 14), xfill=False, xminimum=0)

image tips_card = Text(
    "{b}Performance notes{/b}\n"
    "{size=30}"
    "• one pass per layer, no render-to-texture ping-pong\n"
    "• palettes precomputed offline (tools/make_palettes.py)\n"
    "• palette search capped at 16 iterations, 2 lookups per pixel\n"
    "• u_aa 0.0 on mobile: 1 texture tap instead of 4\n"
    "• no dynamic array indexing → compiles on GLES / ANGLE\n"
    "• ~130 uniform floats: fine on desktop and ES 3.0"
    "{/size}",
    size=40, text_align=0.0, layout="subtitle")

image video_end = Text(
    "{b}Vintage constraints. Modern pipeline.{/b}\n{size=26}{color=#9ab}Ren'Py 8.6  ·  register_shader()  ·  one transform on the master layer{/color}{/size}\n{size=26}{color=#9ab}full source on GitHub — link in the description{/color}{/size}",
    size=44, text_align=0.5, layout="subtitle")

image sits_tag = Text("{size=24}{color=#9ab}in production in {i}Shafted in the Snow{/i}{/color}{/size}", size=24)

image pal_card = Window(VBox(
    Image("images/pal_cafe_claire.png"),
    Text("{color=#9ab}pal_cafe_claire.png — 16 colours, 4 bits/channel, black at index 0{/color}", size=22, xalign=0.5),
    spacing=10), background="#000000cc", padding=(22, 16, 22, 14), xfill=False, xminimum=0)

transform card_top:
    xalign 0.5
    yalign 0.04

transform sits_tag_pos:
    xalign 0.98
    yalign 0.03


label poc_video:

    ## Clean frame: no quick menu, and an exact 1280x720 window (Ren'Py
    ## otherwise opens smaller than the screen).
    $ quick_menu = False
    window hide
    $ renpy.set_physical_size((1280, 720))
    $ renpy.pause(0.5, hard=True)

    $ vstart()

    ## Small black hold so the recording never misses the start.
    scene bg dark
    $ renpy.pause(2.0, hard=True)

    ## === 1. The magic of PC-98 visuals in modern engines =====================

    show video_title at truecenter with dissolve
    $ vhold("title", 6.0)
    hide video_title with dissolve

    scene bg cafe
    show claire at claire_stage
    with dissolve
    $ vsay("hook_plain", "A modern Ren'Py scene: painted 1080p background, flat character sprite.", 6.0)

    show layer master at pc98(palette="cafe_claire")
    $ vsay("hook_pc98", "{b}show layer master at pc98(palette=\"cafe_claire\"){/b} — 640x360, 16 colours, ordered dithering. Live.", 8.0)

    scene bg sunset
    show claire at claire_stage
    with dissolve
    show layer master at pc98(palette="sunset_claire", dither=2)
    $ vsay("why16", "{b}Why 16 colours?{/b} A deliberate, high-contrast colour script per scene. Gradients become checkerboard texture with real weight.", 12.0)

    scene bg cafe
    show claire at claire_stage
    with dissolve
    show layer master at pc98_flashlight(palette="cafe_claire")
    $ vsay("hurdle", "{b}The hurdle{/b}: PC-98 artists hand-dithered every frame. Dozens of sprites x expressions x lighting = thousands of frames. It has to be computed on the GPU, every frame.", 14.0)

    ## === 2. Pixelate -> quantise -> dither =====================================

    show layer master at pc98_rgb4(dither=0)
    $ vsay("step_pixelate", "{b}Step 1 — pixelate + 4 bits/channel.{/b} One shader on the master layer: 640x360 grid, then 4096 hardware colours. Retro, but far more colours than a PC-98 could show at once.", 13.0)

    show layer master at pc98(palette="cafe_claire", dither=0)
    $ vsay("step_palette", "{b}Step 2 — 16 colours.{/b} Every pixel snaps to the nearest palette entry. No dither: gradients collapse into flat bands. The real on-screen limit.", 12.0)

    show layer master at pc98(palette="cafe_claire", dither=2)
    show dither_card onlayer overlay at card_top with dissolve
    $ vsay("pipeline_2", "{b}2x2 Bayer{/b}: each pixel is compared with a threshold pattern and picks between the two best palette colours. Authentic cross-hatching.", 13.0)
    hide dither_card onlayer overlay with dissolve

    show layer master at pc98(palette="cafe_claire", dither=4)
    $ vsay("pipeline_4", "{b}4x4 Bayer{/b}: 16 mix ratios, smoother ramps, busier texture.", 9.0)

    scene bg sunset
    show claire at claire_stage
    with dissolve
    show layer master at pc98(palette="sunset_claire", dither=8)
    $ vsay("pipeline_8", "{b}8x8 Bayer{/b}: 64 ratios. The threshold is computed per emulated pixel, so the pattern stays locked to the grid.", 12.0)

    ## === 3. Palettes =============================================================

    scene bg cafe
    show claire at claire_stage
    with dissolve
    show layer master at pc98(palette="classic", dither=2)
    $ vsay("pal_static", "{b}Static palette{/b}: a generic 16-colour set with skin tones. The character reads everywhere; the background turns muddy.", 10.0)

    show layer master at pc98(palette="cafe_claire", dither=2)
    $ vsay("pal_scene", "{b}Per-scene palette{/b}: 16 colours extracted from background + character, snapped to 4 bits per channel.", 10.0)

    show pal_card onlayer overlay at card_top with dissolve
    $ vsay("pal_tool", "{b}tools/make_palettes.py{/b}: median-cut on background + sprite, farthest-point pick, snap to 4 bits, black at index 0.", 12.0)
    hide pal_card onlayer overlay with dissolve

    ## === 4. Light, the PC-98 way ==================================================

    scene bg candles
    show claire at claire_stage
    with dissolve
    show layer master at pc98(palette="candles_claire", ambient=(0.26, 0.24, 0.34))
    $ vsay("candles_off", "{b}Step 3 — light.{/b} Before quantisation the frame is multiplied by an ambient colour and up to two point lights are added. Ambient only: the room goes dark.", 11.0)

    show layer master at pc98_candles(palette="candles_claire")
    show light_card onlayer overlay at card_top with dissolve
    $ vsay("candles", "Two warm {i}point lights{/i} on the candles, flickering through ATL. Lighting happens before the palette step, so the halos become concentric dither rings.", 12.0)
    hide light_card onlayer overlay with dissolve

    scene bg cafe
    show claire at claire_stage
    with dissolve
    show layer master at pc98_flashlight(palette="cafe_claire")
    $ vmark("poc_video_mouse_marker")
    $ vsay("flashlight", "Cold ambient + a flashlight following the mouse. Any light you can write as a uniform becomes dithered 16-colour light.", 13.0)

    show layer master at pc98_fade_in(palette="cafe_claire", duration=2.5)
    show regs_card onlayer overlay at card_top with dissolve
    $ vsay("fade_in", "{b}Hardware tricks{/b}: match against one palette, {i}display{/i} another. Ramp the display registers from black: every pixel keeps its index, only the register values move.", 14.0)
    hide regs_card onlayer overlay with dissolve

    show layer master at pc98_to_night(palette="cafe_claire", duration=3.0)
    $ vsay("pal_swap", "{b}Palette swap{/b}: day to night is a register swap towards a cold version of the same palette. No re-quantisation, no dither crawl.", 14.0)

    scene bg rooftop with dissolve
    show layer master at pc98_lightning(palette="rooftop")
    $ vsay("lightning", "{b}Lightning{/b}: every register slams to white for two frames and decays. One uniform, no extra draw.", 10.0)

    show layer master at pc98_cycle(palette="rooftop", period=0.12)
    $ vsay("cycle", "{b}Colour cycling{/b}: the two brightest registers swap every few frames. Lights blink without any animated asset.", 9.0)

    scene bg cafe
    show claire at claire_stage
    with dissolve
    show layer master at pc98(palette="cafe_claire", scanline=0.6)
    $ vsay("scanlines", "{b}CRT scanlines{/b}: a dark gap between emulated rows, applied after quantisation.", 8.0)

    ## === 5. Integration + performance ==============================================

    show layer master at pc98(palette="cafe_claire")
    show sits_tag onlayer overlay at sits_tag_pos
    $ vsay("integrate", "{b}In a real project{/b}: one transform on the master layer. Dialogue stays crisp on its own layer. Already shipping in {i}Shafted in the Snow{/i}.", 12.0)
    hide sits_tag onlayer overlay

    $ pc98_off()
    scene bg dark with dissolve
    show tips_card at truecenter with dissolve
    $ vhold("optimize", 14.0)
    hide tips_card with dissolve

    ## --- End card ----------------------------------------------------------

    window hide
    scene bg dark with dissolve
    show video_end at truecenter with dissolve
    $ vhold("end", 7.0)

    scene bg dark with dissolve
    $ renpy.pause(1.5, hard=True)

    $ renpy.quit()

    return
