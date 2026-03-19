from __future__ import annotations

from dataclasses import dataclass
import enum
import functools
import operator


class HumanSex(enum.IntEnum):
    """Human body constitution based on sex.

    Male/female integers comply EMIAS database and belarusian sick leave documents.
    """

    MALE = 1
    FEMALE = 2
    CHILD = 3  # For <12 years old
    M = MALE
    F = FEMALE
    C = CHILD


class FlagSeverity(enum.IntEnum):
    """Severity color codes.

    https://en.wikipedia.org/wiki/Triage_tag
    https://en.wikipedia.org/wiki/ISO_22324
    """

    # Numbers according to METTAG
    BLACK = 0  # Do not resuscitate, immediate death
    RED = 1  # Life-threatening
    YELLOW = 2  # Non-life-threatening
    GREEN = 3  # No color highlight


@dataclass
class Flag:
    """An issue with a given human.

    Issue is mandatory, description and solution are optional.
    action_required: medical intervention required.

        Flag(
            reason="Hypoglycemia",
            severity=FlagSeverity.BLACK,
            description="cGlu < 1.5 mmol/L",
            solution="Bolus administration of intravenous glucose",
            action_required=True,
        )
    """

    reason: str  # Unique, used as dict key
    severity: FlagSeverity = FlagSeverity.GREEN
    description: str = ""
    solution: str = ""
    action_required: bool = False

    def __str__(self):
        return f"{self.severity}: {self.reason}"

    @functools.cached_property
    def html(self) -> str:
        style = list()

        if self.severity == FlagSeverity.BLACK:
            style.append("color:white;")
            style.append("background-color:black;")
        elif self.severity == FlagSeverity.RED:
            style.append("color:red;")
        elif self.severity == FlagSeverity.YELLOW:
            style.append("background-color:lightyellow;")
        elif self.severity == FlagSeverity.GREEN:
            pass  # No color highlight
        else:
            style.append("color:" + self.severity.name.lower())
        return f"""<span style="{";".join(style)}">{self.reason}</span>: {self.description} {self.solution}"""


class FlagWarnings:
    """Auto discovered clinical data that should be considered."""

    def __init__(self):
        self._flags: dict[str, Flag] = dict()

    def add(self, flag: Flag):
        self._flags[flag.reason] = flag

    def render(self) -> str:
        """Render flags in triage order."""
        items = list()
        for f in sorted(self._flags.values(), key=operator.attrgetter("severity")):
            if f.description:  # Not empty
                items.append(f.html)
        if items:
            return "<ul><li>" + "</li><li>".join(items) + "</li></ul>"
        return ""
