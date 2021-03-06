import logging
import threading
from typing import List, Tuple

from Xlib import X, Xatom
from Xlib.display import Display
from Xlib.protocol import event

from clipstack.constants import Selection, CLIPSTACK_WM_NAME
from clipstack.content_manager import StackContentManager, ContentManager

logger = logging.getLogger("clipstack.clipboard")


class BadSelectionRequestError(Exception):
    pass


class Clipboard:
    """
    Proxy object for the selection
    Ideally, `clipstack` should __always__ own the desired selection
    """

    def __init__(
        self,
        display: Display,
        selection: Selection = Selection.CLIPBOARD,
        content_manager: ContentManager = StackContentManager(),
    ):
        self.selection_atom = display.get_atom(selection.value)
        self.targets_atom = display.get_atom("TARGETS")

        self.window = display.screen().root.create_window(
            0, 0, 1, 1, 0, X.CopyFromParent
        )
        self.window.set_wm_name(CLIPSTACK_WM_NAME)

        self.display = display
        self.content_manager = content_manager

        # weird hack for fixing weird selection request patterns
        # see _check_update_contents for more details
        self.event_obj = None

    def handle_targets_query(self) -> Tuple[List, int, int]:
        """
        Someone queried for the type of targets currently available
        """
        # get available targets
        prop_value = list(self.content_manager.get().keys())
        # these should be set to those
        prop_type = Xatom.ATOM
        prop_format = 32

        return (prop_value, prop_type, prop_format)

    def handle_paste_request(self, target_atom: int) -> Tuple[bytes, int, int]:
        """
        Someone requested the content of type

        Raises:
            BadSelectionRequestError if unknown target is queried for
        """
        clipboard_item = self.content_manager.get()
        if target_atom not in clipboard_item:
            raise BadSelectionRequestError("Unknown target for selection")

        prop_value = clipboard_item[target_atom]
        prop_type = target_atom
        prop_format = 8

        return (prop_value, prop_type, prop_format)

    def handle_bad_request(self) -> Tuple:
        """
        Unknown / bad paste request
        """
        return (X.NONE, X.NONE, X.NONE)

    def handle_ownership_loss(self):
        """
        Some other application is the owner of selection now

        No worries, the spy should detect that and send the request here soon
        """
        pass

    def provide_selection_content(self, client, client_prop, details, xev):
        prop_value, prop_type, prop_format = details

        if client_prop != X.NONE:
            client.change_property(client_prop, prop_type, prop_format, prop_value)

        selection_notify_event = event.SelectionNotify(
            time=xev.time,
            requestor=xev.requestor,
            selection=xev.selection,
            target=xev.target,
            property=client_prop,
        )
        client.send_event(selection_notify_event)

    def _check_update_contents(self, timeout_ms=200):
        """
        Check if something actually got pasted and inform content_manager

        Issue:
            this was very confusing and took way longer to solve.
            the "solution" for this issue has changed multiple times

            so usually, applications check available TARGETS and then
            request for the target that they want ONCE and then
            kind of forget about it

            but, multiple applications (like my terminal emulator, firefox,
            and a lot of other apps) seem to request for the same target again

            this is an issue for me since I pop from the stack on a successful
            'paste'. However, these applications fail on their second request
            and nothing actually gets pasted

            sometimes, they ask for different types as well
            all requests look like a bunch of `TARGET`s and then a bunch of
            actual content requests. so if we clear on the next `TARGET`, it
            should be safe

            sometimes, applications don't ask for available `TARGET`s at all and
            randomly start demanding content

            some applications do the `TARGET`/content thing multiple times. WHY?!?!?!

        Fix:
            the only thing that separates these request chains is time
            wait for a while and check if some event has occured. if yes
            its the same request chain. if no, the previous paste was successful
        """
        self.event_obj = threading.Event()
        new_event_started = self.event_obj.wait(timeout=timeout_ms / 1000)

        if not new_event_started:
            logger.info("No new event. Assuming that request chain has finished")
            self.content_manager.on_consume()
            self.window.set_selection_owner(self.selection_atom, X.CurrentTime)
        else:
            logger.info("Got a new event, assuming it's from the same request chain")

        self.event_obj = None

    def copy_content(self, data: dict):
        # take ownership of selection
        self.window.set_selection_owner(self.selection_atom, X.CurrentTime)
        # inform content manager about the selection
        self.content_manager.put(data)

        while True:
            this_did_paste = False
            xev = self.display.next_event()

            if (
                xev.type == X.SelectionRequest
                and xev.owner == self.window
                and xev.selection == self.selection_atom
            ):
                if self.event_obj is not None:
                    self.event_obj.set()

                client = xev.requestor
                client_name = client.get_wm_name()
                logger.info("%s sent a selection request", client_name)

                if xev.property == X.NONE:
                    client_prop = xev.target
                else:
                    client_prop = xev.property

                logger.info("Request for %s", self.display.get_atom_name(xev.target))
                if xev.target == self.targets_atom:
                    logger.info("%s queried for available targets", client_name)
                    details = self.handle_targets_query()
                else:
                    try:
                        logger.info("Trying to get selection contents...")
                        details = self.handle_paste_request(xev.target)
                        this_did_paste = True
                        logger.info("Success")
                    except BadSelectionRequestError:
                        logger.warning(
                            "Failed to get selection contents for target %s",
                            self.display.get_atom_name(xev.target),
                        )
                        client_prop = X.NONE
                        details = self.handle_bad_request()

                self.provide_selection_content(client, client_prop, details, xev)
                if this_did_paste:
                    threading.Thread(target=self._check_update_contents).start()
            elif (
                xev.type == X.SelectionClear
                and xev.window == self.window
                and xev.atom == self.selection_atom
            ):
                # text was copied from some other application
                # we no longer have control over the selection
                # wait for spy to catch that and send to us
                self.handle_ownership_loss()
                return
