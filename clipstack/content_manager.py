import logging
from abc import ABC
from collections import deque

from Xlib.display import Display

logger = logging.getLogger("clipstack.content_manager")

class ContentManager(ABC):
    def __init__(self):
        pass

    def put(self, data: dict):
        """
        Something was copied into the clipboard

        Args:
            data: a dictionary mapping target atoms to content
                {
                    display.get_atom("UTF8_STRING"): b"example text",
                    display.get_atom("ASCII"): b"example text",
                    ...
                }
        """

    def get(self) -> dict:
        """
        Should return the current item that should go on the clipboard
        """

    def on_consume(self):
        """
        The current item was successfully consumed
        (i.e., the requesting application got this data)
        (i.e., it got pasted)
        """


class StackContentManager(ContentManager):
    """
    Stack based clipboard content manager
    """

    def __init__(self):
        # could've used a list as well but
        # seems like deque is ever so slightly better than a simple list
        # https://stackoverflow.com/a/47493474
        self.clipboard_contents = deque()

        # need this for the default case
        display = Display()
        string_atom = display.get_atom("STRING")
        self.default_content = {string_atom: b"", display.get_atom("TARGETS"): [string_atom]}

    def put(self, data: dict):
        logger.info("Data was added")
        self.clipboard_contents.append(data)

    def get(self):
        logger.info("Requesting content")
        if len(self.clipboard_contents) == 0:
            # default clipboard to empty string text
            logger.warning("No content to provide, returning empty")
            return self.default_content

        return self.clipboard_contents[-1]

    def on_consume(self):
        if len(self.clipboard_contents) > 0:
            self.clipboard_contents.pop()
            logger.info("Content was consumed")
        else:
            logger.warning("No content to consume")


class RegularContentManager(ContentManager):
    """
    A simulation of how regular clipboard might act
    """

    def __init__(self):
        # need this for the default case
        display = Display()
        string_atom = display.get_atom("STRING")
        self.default_content = {string_atom: b"", display.get_atom("TARGETS"): [string_atom]}

        self.data = self.default_content

    def put(self, data: dict):
        self.data = data

    def get(self):
        return self.data

    def on_consume(self):
        pass
