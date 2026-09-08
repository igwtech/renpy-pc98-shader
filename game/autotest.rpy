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
            ("original", "bg alice", False, None, 0.4),
            ("rgb4096", "bg alice", False, pc98_rgb4(), 0.4),
            ("pal16_alice", "bg alice", False, pc98(palette="alice"), 0.4),
            ("pal16_alice_nodeadzone", "bg alice", False, pc98(palette="alice", flat=0.0), 0.4),
            ("dither_off", "bg alice", False, pc98(palette="alice", dither=0), 0.4),
            ("dither_2", "bg alice", False, pc98(palette="alice", dither=2), 0.4),
            ("dither_4", "bg alice", False, pc98(palette="alice", dither=4), 0.4),
            ("dither_8", "bg alice", False, pc98(palette="alice", dither=8), 0.4),
            ("reimu_original", "bg reimu", False, None, 0.4),
            ("reimu_classic", "bg reimu", False, pc98(palette="classic"), 0.4),
            ("reimu_scene", "bg reimu", False, pc98(palette="reimu"), 0.4),
            ("lamps_off", "bg hallway", False, pc98(palette="hallway", ambient=(0.22, 0.21, 0.30)), 0.4),
            ("lamps", "bg hallway", False, pc98_lamps(), 0.4),
            ("flashlight", "bg hallwaydark", False, pc98(palette="hallwaydark", ambient=(0.35, 0.38, 0.55), light1=(0.62, 0.55, 0.28), light1_color=(1.15, 1.05, 0.80)), 0.4),
            ("fade_mid", "bg alice", False, pc98_fade_in(palette="alice", duration=2.0), 0.9),
            ("night", "bg hallway", False, pc98(palette="hallway", display="hallway_night"), 0.4),
            ("lightning", "bg hallwaydark", False, pc98(palette="hallwaydark", tint=(2.5, 2.5, 2.5)), 0.4),
            ("cycle", "bg alice", False, pc98_cycle(palette="alice", period=0.25, indices=pc98_sky("alice")), 0.4),
            ("scanlines", "bg reimu", False, pc98(palette="reimu", scanline=0.6), 0.4),
            ("digital8", "bg alice", False, pc98_digital8(), 0.4),
        ]

        outdir = os.path.join(config.gamedir, "..", "poc_shots")
        if not os.path.isdir(outdir):
            os.makedirs(outdir)

        for _name, _bg, _sprite, _t, _settle in _shots:
            renpy.scene()
            renpy.show(_bg)
            renpy.layer_at_list([_t] if _t is not None else [], "master")
            renpy.pause(_settle, hard=True)
            renpy.screenshot(os.path.join(outdir, "poc_%s.png" % _name))

        renpy.quit()

    return
