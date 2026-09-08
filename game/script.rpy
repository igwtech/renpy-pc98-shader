## ============================================================================
## PoC: PC-98 look (16-colour palette, ordered dithering, light effects) as a
## Ren'Py shader applied to the master layer.
##
## Backgrounds and the sprite are ordinary 1920x1080 assets; the shader in
## shaders_pc98.rpy pixelates them to 640x360, lights them, quantises them
## to a 16-colour palette with Bayer dithering and (optionally) plays with
## the palette registers, all on the GPU. The say window is on the "screens"
## layer, so it stays crisp.
## ============================================================================

define narrator_c = Character(None, what_italic=True)

## Test scenes (all 1280x720, Creative Commons artwork, see CREDITS.md):
##   alice       "Alice (PC-98)" by sodaodaoda (Newgrounds, CC BY-NC-SA 3.0)
##   reimu       "[PC-98 Touhou] Reimu Hakurei" by RouRenzu (Newgrounds, CC BY-NC 3.0)
##   hallway     "Hallway (day+night)" by LisadiKaprio (OpenGameArt, CC BY 4.0)
image bg alice = "images/bg_alice.png"
image bg reimu = "images/bg_reimu.png"
image bg hallway = "images/bg_hallway.png"
image bg hallwaydark = "images/bg_hallwaydark.png"

init python:
    def pc98_off():
        """Removes every transform from the master layer."""
        renpy.layer_at_list([], "master")


label start:

    scene bg alice with dissolve
    narrator_c "Proof of concept: the {b}PC-98 look{/b} (16-colour palette, ordered dithering, palette-register light effects) as a Ren'Py shader on the master layer. This is the original painting at 1920x1080."

    show layer master at pc98(palette="alice")
    narrator_c "The same painting through the shader: 640x360 pixels, 16 colours chosen for this image, 2x2 Bayer dither. The text box lives on another layer, so it stays crisp."

    jump hub


label hub:

    $ pc98_off()

    menu:
        narrator_c "What should we look at?"

        "Original vs 4096 colours vs 16 colours":
            jump scene_modes

        "Dither matrix size (off / 2x2 / 4x4 / 8x8)":
            jump scene_dither

        "Generic palette vs per-image palette":
            jump scene_palettes

        "Lamps: flickering point lights":
            jump scene_lamps

        "Night + flashlight following the mouse":
            jump scene_flashlight

        "Hardware palette fade-in and day -> night swap":
            jump scene_fade

        "Lightning flash and colour cycling (register tricks)":
            jump scene_registers

        "CRT scanlines":
            jump scene_scanlines

        "8-colour digital palette (PC-88 style)":
            jump scene_digital

        "Quit":
            return


label scene_modes:
    scene bg alice with dissolve
    narrator_c "{b}Original{/b}: the painting as drawn, millions of colours."

    show layer master at pc98_rgb4()
    narrator_c "{b}4096 colours{/b}: 640x360, 4 bits per channel (the PC-98 hardware colour space) with a 2x2 ordered dither. Still far more colours than the machine could show at once."

    show layer master at pc98(palette="alice")
    narrator_c "{b}16 colours{/b}: the real on-screen limit. A palette picked for this image, and a two-candidate ordered dither against it. Gradients become the classic checkerboard patterns."
    jump hub


label scene_dither:
    scene bg alice with dissolve
    show layer master at pc98(palette="alice", dither=0)
    narrator_c "{b}No dither{/b}: nearest palette colour only. Big flat bands in the sky."

    show layer master at pc98(palette="alice", dither=2)
    narrator_c "{b}2x2 Bayer{/b}: the PC-98 signature. Only 50/50 checkerboards, but the bands shrink."

    show layer master at pc98(palette="alice", dither=4)
    narrator_c "{b}4x4 Bayer{/b}: 16 mix ratios, smoother gradients, visible pattern."

    show layer master at pc98(palette="alice", dither=8)
    narrator_c "{b}8x8 Bayer{/b}: 64 ratios. Smoothest, but the texture gets busy. Most PC-98 art stayed at 2x2 or 4x4."
    jump hub


label scene_palettes:
    scene bg reimu with dissolve
    show layer master at pc98(palette="classic")
    narrator_c "{b}Generic palette{/b}: 16 hand-picked colours (greys, skin tones, primaries). Serviceable, but the purple hair and the warm backdrop turn muddy."

    show layer master at pc98(palette="reimu")
    narrator_c "{b}Per-image palette{/b}: 16 colours extracted from this illustration by tools/make_palettes.py and snapped to 4 bits per channel. That is what PC-98 artists did: one palette per scene."
    jump hub


label scene_lamps:
    scene bg hallway with dissolve
    show layer master at pc98(palette="hallway", ambient=(0.22, 0.21, 0.30))
    narrator_c "{b}Lamps{/b}, lights off: the hallway darkened by a cold ambient multiplier before quantisation."

    show layer master at pc98_lamps()
    narrator_c "Two warm {i}point lights{/i}, flickering through ATL. Because lighting happens before the palette step, the halos become concentric dither rings, the way hand-drawn PC-98 lamplight looked."
    jump hub


label scene_flashlight:
    scene bg hallwaydark with dissolve
    show layer master at pc98_flashlight()
    narrator_c "{b}Night{/b}: a cold ambient and a flashlight that follows the mouse. Dismiss this box and sweep the cursor around."
    pause
    jump hub


label scene_fade:
    scene bg alice with dissolve
    show layer master at pc98_fade_in(palette="alice", duration=2.0)
    narrator_c "{b}Hardware fade-in{/b}: the match palette stays fixed while the {i}display{/i} registers ramp from black to the scene palette. Every pixel keeps its colour index; only the register values move."

    scene bg hallway with dissolve
    show layer master at pc98_to_night(palette="hallway", duration=2.5)
    narrator_c "{b}Day to night{/b}: same trick, interpolating towards a cold version of the palette built register by register. No re-quantisation, no dither crawl: a pure palette swap, as on the real machine."
    jump hub


label scene_registers:
    scene bg hallwaydark with dissolve
    show layer master at pc98_lightning()
    narrator_c "{b}Lightning{/b}: every register slams to white for a couple of frames and decays. u_post_tint on the output colour, no extra draw."

    scene bg alice with dissolve
    show layer master at pc98_cycle(palette="alice", period=0.25, indices=pc98_sky("alice"))
    narrator_c "{b}Colour cycling{/b}: the three blue registers of the sky rotate every few frames, so the sky shimmers without any animated asset."
    jump hub


label scene_scanlines:
    scene bg reimu with dissolve
    show layer master at pc98(palette="reimu", scanline=0.6)
    narrator_c "{b}CRT scanlines{/b}: a dark gap between emulated rows. Pure display effect, applied after quantisation."
    jump hub


label scene_digital:
    scene bg alice with dissolve
    show layer master at pc98_digital8()
    narrator_c "{b}8 colours{/b}: 1 bit per channel with a 2x2 dither, the PC-88 / early PC-98 digital palette. Everything is built out of black, white and the six primaries."
    jump hub
