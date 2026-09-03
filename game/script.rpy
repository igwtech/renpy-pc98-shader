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

## Backgrounds are 1408x768: zoom to the screen height and centre them.
image bg cafe = Transform("images/bg_cafe.webp", zoom=config.screen_height / 768.0, xalign=0.5)
image bg sunset = Transform("images/bg_sunset.webp", zoom=config.screen_height / 768.0, xalign=0.5)
image bg candles = Transform("images/bg_candles.webp", zoom=config.screen_height / 768.0, xalign=0.5)
image bg rooftop = Transform("images/bg_rooftop.webp", zoom=config.screen_height / 768.0, xalign=0.5)

## Flat sprite, straight from the file.
image claire = "images/claire.png"

## Sprite placement: scaled to 95% of the screen height whatever the source size.
init python:
    def _claire_zoom():
        w, h = renpy.image_size("images/claire.png")
        return config.screen_height * 0.95 / float(h)

transform claire_stage:
    zoom _claire_zoom()
    xalign 0.5
    yalign 1.0

init python:
    def pc98_off():
        """Removes every transform from the master layer."""
        renpy.layer_at_list([], "master")


label start:

    scene bg cafe with dissolve
    narrator_c "Proof of concept: the {b}PC-98 look{/b} (16-colour palette, ordered dithering, palette-register light effects) as a Ren'Py shader on the master layer. This is the original 1920x1080 background."

    show layer master at pc98(palette="cafe")
    narrator_c "The same background through the shader: 640x360 pixels, 16 colours chosen for this scene, 2x2 Bayer dither. The text box lives on another layer, so it stays crisp."

    jump hub


label hub:

    $ pc98_off()

    menu:
        narrator_c "What should we look at?"

        "Original vs 4096 colours vs 16 colours":
            jump scene_modes

        "Dither matrix size (off / 2x2 / 4x4 / 8x8)":
            jump scene_dither

        "Generic palette vs per-scene palette":
            jump scene_palettes

        "A sprite on the same layer":
            jump scene_sprite

        "Candles: flickering point lights":
            jump scene_candles

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
    scene bg cafe with dissolve
    narrator_c "{b}Original{/b}: the 1920x1080 background as painted, millions of colours."

    show layer master at pc98_rgb4()
    narrator_c "{b}4096 colours{/b}: 640x360, 4 bits per channel (the PC-98 hardware colour space) with a 2x2 ordered dither. Still far more colours than the machine could show at once."

    show layer master at pc98(palette="cafe")
    narrator_c "{b}16 colours{/b}: the real on-screen limit. A palette picked for this scene, and a two-candidate ordered dither against it. Gradients become the classic checkerboard patterns."
    jump hub


label scene_dither:
    scene bg sunset with dissolve
    show layer master at pc98(palette="sunset", dither=0)
    narrator_c "{b}No dither{/b}: nearest palette colour only. Big flat bands in the sky."

    show layer master at pc98(palette="sunset", dither=2)
    narrator_c "{b}2x2 Bayer{/b}: the PC-98 signature. Only 50/50 checkerboards, but the bands shrink."

    show layer master at pc98(palette="sunset", dither=4)
    narrator_c "{b}4x4 Bayer{/b}: 16 mix ratios, smoother gradients, visible pattern."

    show layer master at pc98(palette="sunset", dither=8)
    narrator_c "{b}8x8 Bayer{/b}: 64 ratios. Smoothest, but the texture gets busy. Most PC-98 art stayed at 2x2 or 4x4."
    jump hub
 

label scene_palettes:
    scene bg cafe with dissolve
    show layer master at pc98(palette="classic")
    narrator_c "{b}Generic palette{/b}: 16 hand-picked colours (greys, skin tones, primaries). Serviceable, but the warm wood turns muddy."

    show layer master at pc98(palette="cafe")
    narrator_c "{b}Per-scene palette{/b}: 16 colours extracted from this background by tools/make_palettes.py and snapped to 4 bits per channel. That is what PC-98 artists did: one palette per scene."
    jump hub


label scene_sprite:
    scene bg cafe
    show claire at claire_stage
    with dissolve
    show layer master at pc98(palette="cafe")
    narrator_c "Sprites live on the master layer too, so they get the same pixel grid, palette and dither. The palette has no skin tones, so her face is approximated with wood colours, exactly the compromise a real palette forces."

    show layer master at pc98(palette="classic")
    narrator_c "With the generic palette (which does have skin tones) the character reads better and the background suffers. Palette choice is a design decision."
    jump hub


label scene_candles:
    scene bg candles with dissolve
    show layer master at pc98(palette="candles", ambient=(0.30, 0.28, 0.38))
    narrator_c "{b}Candles{/b}, lights off: the scene darkened by a cold ambient multiplier before quantisation."

    show layer master at pc98_candles()
    narrator_c "Two warm {i}point lights{/i} on the candles, flickering through ATL. Because lighting happens before the palette step, the halos become concentric dither rings, the way hand-drawn PC-98 candlelight looked."
    jump hub


label scene_flashlight:
    scene bg cafe with dissolve
    show layer master at pc98_flashlight(palette="cafe")
    narrator_c "{b}Night{/b}: a cold ambient and a flashlight that follows the mouse. Dismiss this box and sweep the cursor around."
    pause
    jump hub


label scene_fade:
    scene bg cafe with dissolve
    show layer master at pc98_fade_in(palette="cafe", duration=2.0)
    narrator_c "{b}Hardware fade-in{/b}: the match palette stays fixed while the {i}display{/i} registers ramp from black to the scene palette. Every pixel keeps its colour index; only the register values move."

    show layer master at pc98_to_night(palette="cafe", duration=2.5)
    narrator_c "{b}Day to night{/b}: same trick, interpolating towards a cold version of the palette built register by register. No re-quantisation, no dither crawl: a pure palette swap, as on the real machine."
    jump hub


label scene_registers:
    scene bg rooftop with dissolve
    show layer master at pc98_lightning(palette="rooftop")
    narrator_c "{b}Lightning{/b}: night palette, then every register slams to white for a couple of frames and decays. u_post_tint on the output colour, no extra draw."

    show layer master at pc98_cycle(palette="rooftop", period=0.12)
    narrator_c "{b}Colour cycling{/b}: the two brightest registers swap every few frames, so the tower and city lights blink without any animated asset."
    jump hub


label scene_scanlines:
    scene bg cafe with dissolve
    show layer master at pc98(palette="cafe", scanline=0.6)
    narrator_c "{b}CRT scanlines{/b}: a dark gap between emulated rows. Pure display effect, applied after quantisation."
    jump hub


label scene_digital:
    scene bg sunset with dissolve
    show layer master at pc98_digital8()
    narrator_c "{b}8 colours{/b}: 1 bit per channel with a 2x2 dither, the PC-88 / early PC-98 digital palette. Everything is built out of black, white and the six primaries."
    jump hub
