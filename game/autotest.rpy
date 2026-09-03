## Self-check: when launched with RENPY_POC_AUTOTEST=1, renders every preset
## to poc_shots/ and quits. When launched with RENPY_POC_VIDEO=1, plays the
## scripted video demo (see videodemo.rpy). Neither affects the normal game.

init python:
    import os
    _poc_autotest = os.environ.get("RENPY_POC_AUTOTEST", "") == "1"
    _poc_video = os.environ.get("RENPY_POC_VIDEO", "") == "1"

label splashscreen:

    if _poc_autotest:
        jump poc_autotest

    if _poc_video:
        jump poc_video

    return

label poc_autotest:

    python:
        _shots = [
            # name, background, sprite?, master layer transform (None = off), settle time
            ("original", "bg cafe", False, None, 0.4),
            ("rgb4096", "bg cafe", False, pc98_rgb4(), 0.4),
            ("pal16_classic", "bg cafe", False, pc98(palette="classic"), 0.4),
            ("pal16_cafe", "bg cafe", False, pc98(palette="cafe"), 0.4),
            ("pal16_cafe_nodeadzone", "bg cafe", False, pc98(palette="cafe", flat=0.0), 0.4),
            ("dither_off", "bg sunset", False, pc98(palette="sunset", dither=0), 0.4),
            ("dither_2", "bg sunset", False, pc98(palette="sunset", dither=2), 0.4),
            ("dither_4", "bg sunset", False, pc98(palette="sunset", dither=4), 0.4),
            ("dither_8", "bg sunset", False, pc98(palette="sunset", dither=8), 0.4),
            ("sprite_cafe", "bg cafe", True, pc98(palette="cafe"), 0.4),
            ("sprite_classic", "bg cafe", True, pc98(palette="classic"), 0.4),
            ("candles_off", "bg candles", False, pc98(palette="candles", ambient=(0.30, 0.28, 0.38)), 0.4),
            ("candles", "bg candles", False, pc98_candles(), 0.4),
            ("flashlight", "bg cafe", False, pc98(palette="cafe", ambient=(0.22, 0.26, 0.42), light1=(0.62, 0.55, 0.28), light1_color=(1.15, 1.05, 0.80)), 0.4),
            ("fade_mid", "bg cafe", False, pc98_fade_in(palette="cafe", duration=2.0), 0.9),
            ("night", "bg cafe", False, pc98(palette="cafe", display="cafe_night"), 0.4),
            ("lightning", "bg rooftop", False, pc98(palette="rooftop", display="rooftop_night", tint=(2.5, 2.5, 2.5)), 0.4),
            ("cycle", "bg street", False, pc98_cycle(palette="street", period=0.25, indices=pc98_siren("street")), 0.4),
            ("scanlines", "bg cafe", False, pc98(palette="cafe", scanline=0.6), 0.4),
            ("digital8", "bg sunset", False, pc98_digital8(), 0.4),
        ]

        outdir = os.path.join(config.gamedir, "..", "poc_shots")
        if not os.path.isdir(outdir):
            os.makedirs(outdir)

        for _name, _bg, _sprite, _t, _settle in _shots:
            renpy.scene()
            renpy.show(_bg, at_list=[street_still] if _bg == "bg street" else [])
            if _sprite:
                renpy.show("claire", at_list=[claire_stage])
            renpy.layer_at_list([_t] if _t is not None else [], "master")
            renpy.pause(_settle, hard=True)
            renpy.screenshot(os.path.join(outdir, "poc_%s.png" % _name))

        renpy.quit()

    return
