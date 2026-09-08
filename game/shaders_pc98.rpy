## ============================================================================
## PC-98 look as a Ren'Py shader: limited palette + ordered dithering + light.
##
## Pipeline for every screen pixel (all in the fragment shader):
##
##   1. PIXELATE   - snap the UV to a coarse grid (u_grid, default 640x360;
##                   the PC-98 was 640x400) and sample the cell centre
##                   (optional 2x2 supersample with u_aa).
##   2. LIGHT      - multiply by u_ambient and add up to two point lights
##                   (u_lightN_pos.xy in screen UV, .z = radius; u_lightN_color).
##                   This happens BEFORE quantisation, so light gradients turn
##                   into dither patterns, like hand-dithered PC-98 art.
##   3. QUANTISE   - u_mode 0: N levels per channel (u_levels 15 = 4 bits =
##                   the 4096-colour PC-98 hardware space; 1 = 8-colour PC-88).
##                   u_mode 1: 16-colour palette (u_pal0..15), the on-screen
##                   limit of a PC-98. Both use an ordered Bayer dither
##                   (u_dither 0/2/4/8) computed in emulated-pixel space.
##   4. REGISTERS  - in palette mode the matched index is looked up in a
##                   *display* palette (u_out0..15). Normally display == match
##                   palette, but swapping/interpolating u_out* gives
##                   hardware-accurate fades, night tints, flashes and colour
##                   cycling where every pixel keeps its colour index.
##                   u_post_tint multiplies the final colour in either mode.
##   5. DISPLAY    - optional CRT scanline darkening between emulated rows.
##
## No array constructors or const arrays are used, so the GLSL is valid both
## as GLSL 1.20 (desktop gl2) and GLSL ES 1.00 (ANGLE / GLES).
## ============================================================================

init -10 python:

    ## Hand-picked generic palette (4 bits per channel), for scenes without
    ## a dedicated one. tools/make_palettes.py adds one palette per background
    ## (see palettes_generated.rpy).
    def _p4(r, g, b):
        return (r / 15.0, g / 15.0, b / 15.0)

    pc98_palettes = {
        "classic": [
            _p4(0, 0, 0),     # black
            _p4(2, 2, 4),     # near black (blue)
            _p4(5, 5, 7),     # dark grey
            _p4(9, 9, 10),    # grey
            _p4(13, 13, 13),  # light grey
            _p4(15, 15, 15),  # white
            _p4(15, 13, 11),  # skin light
            _p4(14, 10, 8),   # skin mid
            _p4(11, 6, 5),    # skin shadow / brown
            _p4(6, 3, 2),     # dark brown
            _p4(13, 3, 3),    # red
            _p4(15, 11, 3),   # yellow / orange
            _p4(3, 9, 4),     # green
            _p4(3, 6, 12),    # blue
            _p4(7, 11, 15),   # light blue
            _p4(10, 5, 12),   # purple
        ],
        "black": [(0.0, 0.0, 0.0)] * 16,
    }

    def pc98_pal(name, i):
        """Colour i of palette `name` as an (r, g, b) tuple in 0..1.
        Palettes shorter than 16 entries repeat their last colour."""
        pal = pc98_palettes[name]
        return tuple(pal[i] if i < len(pal) else pal[-1])

    class PC98PaletteFade(object):
        """ATL `function`: interpolates the DISPLAY palette registers
        (u_out*) from palette `src` to palette `dst` over `duration` seconds.
        Pixels keep their colour index; only the register values move. This
        is how a PC-98 game faded to black, went to night or flashed white."""

        def __init__(self, src, dst, duration):
            self.src = src
            self.dst = dst
            self.duration = duration

        def __call__(self, trans, st, at):
            t = min(st / self.duration, 1.0) if self.duration > 0 else 1.0
            for i in range(16):
                a = pc98_palettes[self.src][i]
                b = pc98_palettes[self.dst][i]
                setattr(trans, "u_out%d" % i, tuple(a[k] + (b[k] - a[k]) * t for k in range(3)))
            if t >= 1.0:
                return None
            return 0

    class PC98ColorCycle(object):
        """ATL `function`: rotates a set of display registers every `period`
        seconds (neon, water, blinking lights - the classic palette-cycling
        animation). `indices` picks the registers; by default the `count`
        brightest entries. With two indices it is a plain swap, e.g. the red
        and blue of a police siren."""

        def __init__(self, palette, period=0.12, count=2, indices=None):
            self.palette = palette
            self.period = period
            pal = pc98_palettes[palette]
            self.indices = list(indices) if indices else list(range(len(pal) - count, len(pal)))

        def __call__(self, trans, st, at):
            pal = pc98_palettes[self.palette]
            n = len(self.indices)
            shift = int(st / self.period) % n
            for i in range(16):
                j = i
                if i in self.indices:
                    k = self.indices.index(i)
                    j = self.indices[(k + shift) % n]
                setattr(trans, "u_out%d" % i, tuple(pal[j]))
            return 0

    def pc98_find_color(palette, which):
        """Index of the most saturated red / green / blue register of a palette."""
        pal = pc98_palettes[palette]
        ch = {"red": 0, "green": 1, "blue": 2}[which]
        return max(range(len(pal)), key=lambda i: pal[i][ch] - max(pal[i][(ch + 1) % 3], pal[i][(ch + 2) % 3]))

    def pc98_siren(palette):
        """(red index, blue index) of a palette, for police-light cycling."""
        return (pc98_find_color(palette, "red"), pc98_find_color(palette, "blue"))

    def pc98_sky(palette, n=3):
        """Indices of up to n light blue / cyan registers (sky, water) for
        colour cycling. Dark blues (a bow, a night shadow) are left alone."""
        pal = pc98_palettes[palette]
        def coolness(c):
            return (c[1] + c[2]) / 2.0 - c[0]
        cand = [i for i in range(len(pal)) if pal[i][2] > 0.55 and coolness(pal[i]) > 0.05 and (pal[i][0] + pal[i][1] + pal[i][2]) / 3.0 > 0.45]
        cand.sort(key=lambda i: coolness(pal[i]), reverse=True)
        if len(cand) < 2:
            cand = sorted(range(len(pal)), key=lambda i: coolness(pal[i]), reverse=True)
        return tuple(cand[:n])

    class PC98MouseLight(object):
        """ATL `function`: point light 1 follows the mouse (the layer is the
        whole screen, so UV = mouse / screen size)."""

        def __init__(self, radius=0.28):
            self.radius = radius

        def __call__(self, trans, st, at):
            mx, my = renpy.get_mouse_pos()
            trans.u_light1_pos = (mx / float(config.screen_width), my / float(config.screen_height), self.radius)
            return 0


init python:

    renpy.register_shader("pc98.retro", variables="""
        uniform sampler2D tex0;
        uniform vec2 u_model_size;
        uniform vec2 u_grid;
        uniform float u_mode;
        uniform float u_levels;
        uniform float u_dither;
        uniform float u_spread;
        uniform float u_aa;
        uniform vec3 u_ambient;
        uniform vec3 u_light1_pos;
        uniform vec3 u_light1_color;
        uniform vec3 u_light2_pos;
        uniform vec3 u_light2_color;
        uniform vec3 u_post_tint;
        uniform float u_scanline;
        uniform float u_flat;
        uniform vec3 u_pal0;
        uniform vec3 u_pal1;
        uniform vec3 u_pal2;
        uniform vec3 u_pal3;
        uniform vec3 u_pal4;
        uniform vec3 u_pal5;
        uniform vec3 u_pal6;
        uniform vec3 u_pal7;
        uniform vec3 u_pal8;
        uniform vec3 u_pal9;
        uniform vec3 u_pal10;
        uniform vec3 u_pal11;
        uniform vec3 u_pal12;
        uniform vec3 u_pal13;
        uniform vec3 u_pal14;
        uniform vec3 u_pal15;
        uniform vec3 u_out0;
        uniform vec3 u_out1;
        uniform vec3 u_out2;
        uniform vec3 u_out3;
        uniform vec3 u_out4;
        uniform vec3 u_out5;
        uniform vec3 u_out6;
        uniform vec3 u_out7;
        uniform vec3 u_out8;
        uniform vec3 u_out9;
        uniform vec3 u_out10;
        uniform vec3 u_out11;
        uniform vec3 u_out12;
        uniform vec3 u_out13;
        uniform vec3 u_out14;
        uniform vec3 u_out15;
        attribute vec2 a_tex_coord;
        varying vec2 v_tex_coord;
    """, vertex_300="""
        v_tex_coord = a_tex_coord;
    """, fragment_functions="""
        vec3 g_pal[16];
        vec3 g_out[16];

        // Ordered (Bayer) dither threshold in (0,1) for an emulated pixel.
        // Built recursively (the 2x2 pattern at the finest level is the most
        // significant digit), so no matrix constants are needed.
        float pc98_bayer(vec2 cell, float size) {
            if (size < 1.5) {
                return 0.5;
            }
            float n = size * size;
            float mult = n / 4.0;
            float v = 0.0;
            vec2 p = floor(cell);
            for (int i = 0; i < 3; i++) {
                if (mult < 0.5) {
                    break;
                }
                vec2 b = mod(p, 2.0);
                v += (mod(b.x + b.y, 2.0) * 2.0 + b.y) * mult;
                p = floor(p / 2.0);
                mult /= 4.0;
            }
            return (v + 0.5) / n;
        }

        // Perceptual-ish squared distance (green matters most).
        float pc98_dist(vec3 a, vec3 b) {
            vec3 d = a - b;
            return dot(d * d, vec3(0.30, 0.59, 0.11));
        }

        int pc98_nearest(vec3 c) {
            int best = 0;
            float bd = 1.0e9;
            for (int i = 0; i < 16; i++) {
                float d = pc98_dist(c, g_pal[i]);
                if (d < bd) {
                    bd = d;
                    best = i;
                }
            }
            return best;
        }

        // Dynamic array indexing is not allowed in GLSL ES 1.00 fragment
        // shaders, so the lookups walk the array with a constant loop index.
        vec3 pc98_pal_at(int idx) {
            for (int i = 0; i < 16; i++) {
                if (i == idx) {
                    return g_pal[i];
                }
            }
            return g_pal[0];
        }

        vec3 pc98_out_at(int idx) {
            for (int i = 0; i < 16; i++) {
                if (i == idx) {
                    return g_out[i];
                }
            }
            return g_out[0];
        }

        // Two-candidate ordered dither against an arbitrary palette: find the
        // nearest colour c1, then the nearest colour to the point reflected
        // across c1 (c2, "the other side" of the error), and mix them in the
        // proportion that best reproduces c, using the Bayer threshold.
        // Returns the DISPLAY register of the chosen index.
        vec3 pc98_palette_dither(vec3 c, float t, float dither, float flat_frac) {
            int i1 = pc98_nearest(c);
            if (dither < 1.5) {
                return pc98_out_at(i1);
            }
            vec3 c1 = pc98_pal_at(i1);
            int i2 = pc98_nearest(c + (c - c1));
            vec3 c2 = pc98_pal_at(i2);
            vec3 d = c2 - c1;
            float dd = dot(d, d);
            if (dd < 1.0e-6) {
                return pc98_out_at(i1);
            }
            float f = clamp(dot(c - c1, d) / dd, 0.0, 1.0);
            // Dead zone, RELATIVE to the distance between the two candidates:
            // a colour that would get fewer than `flat_frac` of c2 pixels is
            // drawn flat. This kills speckle on near-flat areas without
            // creating plateaus in smooth gradients (an absolute dead zone
            // did: with entries two steps apart nothing was dithered at all).
            if (f < flat_frac) {
                return pc98_out_at(i1);
            }
            return (t < f) ? pc98_out_at(i2) : pc98_out_at(i1);
        }

        // Per-channel quantisation to `levels` steps with ordered dither.
        // spread 0 = plain rounding, 1 = full-strength Bayer dither.
        vec3 pc98_rgb_dither(vec3 c, float t, float levels, float spread) {
            vec3 s = c * levels + 0.5 + (t - 0.5) * spread;
            return floor(s) / levels;
        }

        // Smooth point light: 1 at the centre, 0 at `radius` (UV units,
        // measured against the screen height; x is aspect-corrected).
        float pc98_point_light(vec2 uv, vec3 lp, float aspect) {
            vec2 d = (uv - lp.xy) * vec2(aspect, 1.0);
            float x = clamp(length(d) / max(lp.z, 0.001), 0.0, 1.0);
            float f = 1.0 - x * x;
            return f * f;
        }
    """, fragment_350="""
        vec2 grid = max(u_grid, vec2(1.0));
        vec2 cell = floor(v_tex_coord * grid);
        vec2 cuv = (cell + 0.5) / grid;

        // 1. Pixelate.
        vec4 col;
        if (u_aa > 0.5) {
            vec2 o = 0.25 / grid;
            col = 0.25 * (texture2D(tex0, cuv + vec2(-o.x, -o.y))
                        + texture2D(tex0, cuv + vec2( o.x, -o.y))
                        + texture2D(tex0, cuv + vec2(-o.x,  o.y))
                        + texture2D(tex0, cuv + vec2( o.x,  o.y)));
        } else {
            col = texture2D(tex0, cuv);
        }

        // Ren'Py textures are premultiplied: work on straight colour.
        float a = col.a;
        vec3 rgb = (a > 0.001) ? col.rgb / a : vec3(0.0);

        // 2. Light (before quantisation, so it dithers).
        float aspect = u_model_size.x / u_model_size.y;
        vec3 light = u_ambient
                   + u_light1_color * pc98_point_light(cuv, u_light1_pos, aspect)
                   + u_light2_color * pc98_point_light(cuv, u_light2_pos, aspect);
        rgb = clamp(rgb * light, 0.0, 1.0);

        // 3. Quantise + dither (in emulated pixel space).
        float t = pc98_bayer(cell, u_dither);
        if (u_mode > 0.5) {
            // Palette registers are loaded here (not in a helper) because
            // Ren'Py only declares the uniforms referenced by a stage body.
            g_pal[0] = u_pal0; g_out[0] = u_out0;
            g_pal[1] = u_pal1; g_out[1] = u_out1;
            g_pal[2] = u_pal2; g_out[2] = u_out2;
            g_pal[3] = u_pal3; g_out[3] = u_out3;
            g_pal[4] = u_pal4; g_out[4] = u_out4;
            g_pal[5] = u_pal5; g_out[5] = u_out5;
            g_pal[6] = u_pal6; g_out[6] = u_out6;
            g_pal[7] = u_pal7; g_out[7] = u_out7;
            g_pal[8] = u_pal8; g_out[8] = u_out8;
            g_pal[9] = u_pal9; g_out[9] = u_out9;
            g_pal[10] = u_pal10; g_out[10] = u_out10;
            g_pal[11] = u_pal11; g_out[11] = u_out11;
            g_pal[12] = u_pal12; g_out[12] = u_out12;
            g_pal[13] = u_pal13; g_out[13] = u_out13;
            g_pal[14] = u_pal14; g_out[14] = u_out14;
            g_pal[15] = u_pal15; g_out[15] = u_out15;
            rgb = pc98_palette_dither(rgb, t, u_dither, u_flat);   // 4. registers inside
        } else {
            float spread = (u_dither > 1.5) ? u_spread : 0.0;
            rgb = pc98_rgb_dither(rgb, t, max(u_levels, 1.0), spread);
        }
        rgb *= u_post_tint;

        // 5. CRT scanlines between emulated rows.
        if (u_scanline > 0.001) {
            float fy = fract(v_tex_coord.y * grid.y);
            rgb *= 1.0 - u_scanline * smoothstep(0.62, 0.95, fy);
        }

        gl_FragColor = vec4(rgb * a, a);
    """)


## ----------------------------------------------------------------------------
## The transform. Apply it to a layer (`show layer master at pc98(...)`) or to
## any displayable. Every argument maps to a shader uniform.
##
##   palette      match palette name (pc98_palettes key), palette mode only
##   display      display palette name (defaults to `palette`)
##   mode         1 = 16-colour palette, 0 = per-channel levels
##   levels       steps per channel in mode 0 (15 = 4 bit / 4096 colours,
##                7 = 512 colours, 1 = 8 colours)
##   grid         emulated resolution
##   dither       Bayer matrix size: 0 (off), 2, 4 or 8
##   spread       dither strength in mode 0 (0..1)
##   aa           1.0 = 2x2 supersample per emulated pixel
##   ambient      colour multiplier applied before quantisation
##   light1/2     (x, y, radius) in screen UV; lightN_color additive colour
##   tint         post-quantisation multiplier (register fade / flash)
##   scanline     0..1 CRT scanline darkness
##   flat         dead zone as a fraction of the distance between the two
##                dither candidates (0..0.5): below it the pixel is drawn flat.
##                0 = always dither, 0.12 = kills speckle, keeps gradients smooth
## ----------------------------------------------------------------------------
transform pc98(palette="classic", display=None, mode=1, levels=15.0, grid=(640, 360), dither=2, spread=1.0, aa=1.0, ambient=(1.0, 1.0, 1.0), light1=(0.5, 0.5, 0.0), light1_color=(0.0, 0.0, 0.0), light2=(0.5, 0.5, 0.0), light2_color=(0.0, 0.0, 0.0), tint=(1.0, 1.0, 1.0), scanline=0.0, flat=0.12):
    mesh True
    shader "pc98.retro"
    u_grid (float(grid[0]), float(grid[1]))
    u_mode float(mode)
    u_levels float(levels)
    u_dither float(dither)
    u_spread float(spread)
    u_aa float(aa)
    u_ambient ambient
    u_light1_pos light1
    u_light1_color light1_color
    u_light2_pos light2
    u_light2_color light2_color
    u_post_tint tint
    u_scanline float(scanline)
    u_flat float(flat)
    u_pal0 pc98_pal(palette, 0)
    u_pal1 pc98_pal(palette, 1)
    u_pal2 pc98_pal(palette, 2)
    u_pal3 pc98_pal(palette, 3)
    u_pal4 pc98_pal(palette, 4)
    u_pal5 pc98_pal(palette, 5)
    u_pal6 pc98_pal(palette, 6)
    u_pal7 pc98_pal(palette, 7)
    u_pal8 pc98_pal(palette, 8)
    u_pal9 pc98_pal(palette, 9)
    u_pal10 pc98_pal(palette, 10)
    u_pal11 pc98_pal(palette, 11)
    u_pal12 pc98_pal(palette, 12)
    u_pal13 pc98_pal(palette, 13)
    u_pal14 pc98_pal(palette, 14)
    u_pal15 pc98_pal(palette, 15)
    u_out0 pc98_pal(display or palette, 0)
    u_out1 pc98_pal(display or palette, 1)
    u_out2 pc98_pal(display or palette, 2)
    u_out3 pc98_pal(display or palette, 3)
    u_out4 pc98_pal(display or palette, 4)
    u_out5 pc98_pal(display or palette, 5)
    u_out6 pc98_pal(display or palette, 6)
    u_out7 pc98_pal(display or palette, 7)
    u_out8 pc98_pal(display or palette, 8)
    u_out9 pc98_pal(display or palette, 9)
    u_out10 pc98_pal(display or palette, 10)
    u_out11 pc98_pal(display or palette, 11)
    u_out12 pc98_pal(display or palette, 12)
    u_out13 pc98_pal(display or palette, 13)
    u_out14 pc98_pal(display or palette, 14)
    u_out15 pc98_pal(display or palette, 15)


## ----------------------------------------------------------------------------
## Presets used by the demo.
## ----------------------------------------------------------------------------

## 4096-colour hardware space (4 bits/channel) with Bayer dither: what a PC-98
## could show if it were not limited to 16 colours at once.
transform pc98_rgb4(dither=2, grid=(640, 360)):
    pc98(mode=0, levels=15.0, dither=dither, grid=grid)

## 8 colours, 1 bit per channel: PC-88 / early PC-98 digital palette.
transform pc98_digital8(dither=2):
    pc98(mode=0, levels=1.0, dither=dither, spread=1.0)

## Lamp-lit hallway: two warm point lights, flickering. Pre-quantisation light
## means the halos turn into dither rings.
transform pc98_lamps(palette="hallway"):
    pc98(palette=palette, ambient=(0.22, 0.21, 0.30), light1=(0.30, 0.10, 0.60), light1_color=(1.30, 0.95, 0.55), light2=(0.78, 0.62, 0.42), light2_color=(1.10, 0.80, 0.50))
    block:
        linear 0.09 u_light1_color (1.15, 0.82, 0.46) u_light1_pos (0.302, 0.098, 0.57) u_light2_color (1.20, 0.88, 0.55)
        linear 0.13 u_light1_color (1.42, 1.02, 0.60) u_light1_pos (0.298, 0.104, 0.63) u_light2_color (0.98, 0.72, 0.44)
        linear 0.07 u_light1_color (1.24, 0.90, 0.52) u_light1_pos (0.301, 0.101, 0.59) u_light2_color (1.14, 0.84, 0.52)
        linear 0.11 u_light1_color (1.38, 0.98, 0.58) u_light1_pos (0.299, 0.103, 0.62) u_light2_color (1.05, 0.78, 0.47)
        linear 0.10 u_light1_color (1.18, 0.85, 0.49) u_light1_pos (0.301, 0.099, 0.58) u_light2_color (1.22, 0.90, 0.56)
        repeat

## Night: cold ambient + a flashlight that follows the mouse.
transform pc98_flashlight(palette="hallwaydark", display=None, radius=0.28):
    pc98(palette=palette, display=display, ambient=(0.35, 0.38, 0.55), light1=(0.5, 0.5, radius), light1_color=(1.15, 1.05, 0.80))
    function PC98MouseLight(radius)

## Hardware palette fade-in from black (display registers ramp from black
## to the scene palette).
transform pc98_fade_in(palette="alice", duration=2.0):
    pc98(palette=palette, display="black")
    function PC98PaletteFade("black", palette, duration)

## Palette swap day -> night, register by register.
transform pc98_to_night(palette="hallway", duration=2.5):
    pc98(palette=palette)
    pause 0.8
    function PC98PaletteFade(palette, palette + "_night", duration)

## Lightning: every register slams to white for a couple of frames, decays.
transform pc98_lightning(palette="hallwaydark"):
    pc98(palette=palette)
    block:
        pause 0.7
        u_post_tint (6.0, 6.0, 6.0)
        pause 0.06
        u_post_tint (1.0, 1.0, 1.0)
        pause 0.10
        u_post_tint (6.0, 6.0, 6.0)
        linear 0.35 u_post_tint (1.0, 1.0, 1.0)
        pause 2.5
        repeat

## Palette colour cycling: rotates display registers (blinking lights). With
## indices=pc98_siren(palette) it swaps the red and blue registers: police lights.
transform pc98_cycle(palette="alice", period=0.12, indices=None):
    pc98(palette=palette)
    function PC98ColorCycle(palette, period, indices=indices)
