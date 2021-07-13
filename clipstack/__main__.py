import logging
import os

from Xlib.display import Display

from clipstack.spy import ClipboardSpy
from clipstack.clipboard import Clipboard

if os.getenv("CLIPSTACK_DEBUG"):
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s]  %(name)s: %(message)s")
else:
    logging.basicConfig(
        level=logging.WARNING, format="[%(levelname)s]  %(name)s: %(message)s"
    )

if __name__ == "__main__":
    display = Display()

    cb_spy = ClipboardSpy(display)
    cb = Clipboard(display)

    for content in cb_spy.spy():
        # this can't handle images yet
        targets = [display.get_atom_name(k) for k in content.keys()]
        content_is_img = any(["image" in target for target in targets])

        # ignore images
        # let the original applications handle it
        # the stack will remain intact
        if content_is_img:
            logging.warning("Skipping content since we can't handle it right now")
            continue

        cb.copy_content(content)
