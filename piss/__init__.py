"""piss - the world's most fluid programming language."""

from .errors import Blocked, Burst, Evaporated, Splash, Uphill, WaterFault
from .interp import Interpreter
from .parser import parse

__all__ = [
    "Blocked",
    "Burst",
    "Evaporated",
    "Splash",
    "Uphill",
    "WaterFault",
    "Interpreter",
    "parse",
    "run",
]
__version__ = "0.1.0"


def run(source: str, decay: int = 6) -> str:
    """Run a program and return everything it leaked."""
    interp = Interpreter(decay=decay)
    interp.run(parse(source))
    return "\n".join(interp.output)
