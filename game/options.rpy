## Minimal options for the PC-98 shader proof of concept.

define config.name = _("RenpyPC98 — PoC Shaders")
define config.version = "0.1"
define gui.about = _("Proof of concept: PC-98 limited palette, ordered dithering and light effects as a Ren'Py shader.")

define build.name = "RenpyPC98"

define config.has_sound = True
define config.has_music = True
define config.has_voice = False

define config.save_directory = "RenpyPC98-PoC"

define config.window_icon = None

## Skip the main menu and go straight to the demo.
define config.main_menu_music = None

label main_menu:
    return

init python:
    build.classify('**~', None)
    build.classify('**.bak', None)
    build.classify('**/.**', None)
    build.classify('**/#**', None)
    build.classify('**/thumbs.db', None)
