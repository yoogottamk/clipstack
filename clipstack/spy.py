import logging

from Xlib import X
from Xlib.display import Display
from Xlib.ext.xfixes import XFixesSetSelectionOwnerNotifyMask

from clipstack.constants import (
    CLIPSTACK_WM_NAME,
    CLIPSTACK_SPY_WM_NAME,
    MAX_SIZE,
    Selection,
)

logger = logging.getLogger("clipstack.spy")


class ClipboardSpy:
    """
    Watches the X11 selection `CLIPBOARD` for change in owners

    In english, this detects whenever application copies stuff into the clipboard.
    """

    def __init__(self, display: Display, selection: Selection = Selection.CLIPBOARD):
        self.selection_atom = display.get_atom(selection.value)
        self.data_atom = display.get_atom("XSEL_DATA")

        self.window = display.screen().root.create_window(
            0, 0, 1, 1, 0, X.CopyFromParent
        )
        self.window.set_wm_name(CLIPSTACK_SPY_WM_NAME)

        self.display = display
        # for some weird reason, xfixes stuff doesn't work without querying this version first ¯\_(ツ)_/¯
        self.display.xfixes_query_version()
        # get events for `selection` owner changes
        self.display.xfixes_select_selection_input(
            self.window, self.selection_atom, XFixesSetSelectionOwnerNotifyMask
        )

    def validate_selection_xevent(self, xev, expected_target, expected_property):
        """
        Basic sanity checks
        """
        return (
            xev.requestor == self.window
            and xev.selection == self.selection_atom
            and xev.target == expected_target
            and xev.property == expected_property
        )

    def convert_selection(self, target_atom):
        """
        Requests for selection contents and gets it's value
        """
        self.window.convert_selection(
            self.selection_atom, target_atom, self.data_atom, X.CurrentTime
        )

        while True:
            xev = self.display.next_event()
            if xev.type == X.SelectionNotify:
                break

        if not self.validate_selection_xevent(xev, target_atom, self.data_atom):
            logger.info("Validate Selection Event failed")
            return None

        return self.window.get_full_property(
            self.data_atom, X.AnyPropertyType, sizehint=MAX_SIZE
        ).value

    def extract_selection_contents(self):
        """
        Extracts selection contents for all target types

        In english, copies all formats of data that the application supports from the clipboard (image, plain text, rich text, html, etc)
        """
        # ignore the events generated by `clipstack` clipboard
        selection_owner_wm_name = self.display.get_selection_owner(
            self.selection_atom
        ).get_wm_name()
        logger.info("Going to extract from %s", selection_owner_wm_name)
        if selection_owner_wm_name == CLIPSTACK_WM_NAME:
            logger.info("Owner is clipstack, ignoring")
            return None

        target_atom = self.display.get_atom("TARGETS")

        available_targets = self.convert_selection(target_atom)
        if available_targets is None:
            logger.info("Found no targets")
            return None

        clipboard_data = {}
        for target_atom in available_targets:
            logger.debug(
                "Extracting target %d[%s]",
                target_atom,
                self.display.get_atom_name(target_atom),
            )
            clipboard_data[target_atom] = self.convert_selection(target_atom)

        self.window.delete_property(self.data_atom)
        return clipboard_data

    def spy(self):
        """
        Waits for selection owner to change and then extracts selection contents
        """
        while True:
            xev = self.display.next_event()
            if (
                xev.type == self.display.extension_event.SetSelectionOwnerNotify[0]
                and xev.selection == self.selection_atom
            ):
                contents = self.extract_selection_contents()
                if contents is not None:
                    logger.info("Yielding clipboard contents")
                    yield contents


if __name__ == "__main__":
    display = Display()
    c = ClipboardSpy(display)
    for contents in c.spy():
        print(contents)
