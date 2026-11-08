"""Every fault in PISS is a leak of some kind."""

from __future__ import annotations


class WaterFault(Exception):
    """Base class for everything that can go wrong."""

    kind = "fault"


class Blocked(WaterFault):
    """The text could not be read or parsed."""

    kind = "blocked"

    def __init__(self, message: str, line: int | None = None, col: int | None = None):
        self.line = line
        self.col = col
        where = f" ({line}:{col})" if line is not None else ""
        super().__init__(f"{message}{where}")


class Uphill(Blocked):
    """You tried to make water flow upwards."""

    kind = "uphill"


class Evaporated(WaterFault):
    """A binding went stale and was read anyway."""

    kind = "evaporated"

    def __init__(self, name: str, touched: int, now: int, decay: int):
        self.name = name
        self.touched = touched
        self.now = now
        self.decay = decay
        super().__init__(
            f"`{name}`: last touched at statement {touched}, "
            f"read at {now}, decay is {decay}"
        )


class Burst(WaterFault):
    """A pipe gave way at runtime: type errors, division by zero, bad calls."""

    kind = "burst"


class Splash(WaterFault):
    """A deliberate splash, raised by the program itself."""

    kind = "splash"

    def __init__(self, value):
        self.value = value
        super().__init__(f"the program splashed: {value}")
