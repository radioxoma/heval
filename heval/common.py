from __future__ import annotations

from dataclasses import dataclass
import enum
import functools
import operator


class HumanSex(enum.IntEnum):
    """Human body constitution based on sex.

    Male/female integers comply EMIAS database and belarusian sick leave documents.
    """

    male = 1
    female = 2
    child = 3  # For <12 years old


class FlagSeverity(enum.Enum):
    """Severity color codes.

    https://en.wikipedia.org/wiki/Triage_tag
    https://en.wikipedia.org/wiki/ISO_22324
    """

    # Numbers according to METTAG
    BLACK = 0  # Do not resuscitate, immediate death,
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

    reason: str
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
            style.append("color:white")
            style.append("background-color:black")
        elif self.severity == FlagSeverity.RED:
            style.append("color:red")
        elif self.severity == FlagSeverity.YELLOW:
            style.append("background-color:yellow")
        elif self.severity == FlagSeverity.GREEN:
            pass  # No color highlight
        else:
            style.append("color:" + self.severity.name.lower())
        return f"""<span style="{";".join(style)}">{self.reason}</span>: {self.description} {self.solution}"""


def render_flags(flags: list[Flag]) -> str:
    """Render flags in triage order."""
    if flags:
        items = list()
        for flag in sorted(flags, key=operator.attrgetter("severity")):
            items.append(flag.html)
        text = "</li>\n<li>".join(items)
        return f"<ul>\n<li>{text}</li>\n</ul>"
    else:
        return ""
