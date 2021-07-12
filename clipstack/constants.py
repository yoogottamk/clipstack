from enum import Enum

CLIPSTACK_WM_NAME = "ClipStack"
CLIPSTACK_SPY_WM_NAME = "ClipStack Spy"
MAX_SIZE = int(1e6)

class Selection(Enum):
    PRIMARY = "PRIMARY"
    CLIPBOARD = "CLIPBOARD"
    # SECONDARY = "SECONDARY"
