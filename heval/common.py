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


class Abbr:
    def __init__(self, short: str, full: str):
        self.short = short
        self.full = full

    def __str__(self):
        return f"""<abbr title="{self.full}">{self.short}</abbr>"""


class A:
    """Abbreviation namespace."""

    ru_ls = Abbr("ЛС", "Лекарственные средства")
    ru_pos_dej = Abbr("ПосДеж", "Пособие дежуранта, С.А. Деревщиков, 2014 г")
    abg = Abbr("ABG", "Arterial blood gas test")
    aki = Abbr("AKI", "Acute kidney injury")
    anion_gap = Abbr("AG", "Anion gap")
    bmi = Abbr("BMI", "Body mass index")
    bmr = Abbr("BMR", "Basal metabolic rate")
    bsa = Abbr("BSA", "Body surface area, m²")
    ckd = Abbr("CKD", "Chronic kidney disease")
    crrt = Abbr("CRRT", "Continuous renal replacement therapy")
    d5w = Abbr("D5, D5W", "Dextrose 5%")
    dke = Abbr("DKE", "Diabetic ketoacidosis")
    egfr = Abbr("eGFR", "Estimated glomerular filtration rate")
    ganest = Abbr("GA", "General anesthesia")
    gapgap = Abbr("gg", "Gap-gap, delta gap")
    hagma = Abbr("HAGMA", "High anion gap metabolic acidosis")
    hhs = Abbr("HHS", "Hyperosmolar hyperglycemic state")
    ibw = Abbr("IBW", "Ideal body weight, kg")
    iv = Abbr("IV, I/V", "Intravenous")
    kult = Abbr("KULT", "Ketones, uremia, lactate, toxins")
    mv = Abbr("MV", "Minute volume")
    nagma = Abbr("NAGMA", "Normal anion gap metabolic acidosis")
    nmt = Abbr("NMT", "Neuromuscular monitoring")
    prbc = Abbr("pRBC", "Packed red blood cells")
    rbw = Abbr("RBW", "Real body weight, kg")
    resp_rate = Abbr("RR", "Respiratory rate")
    sbe = Abbr("SBE", "Standard base excess")
    tiva = Abbr("TIVA", "Total intravenous anesthesia")
    tof = Abbr("TOF", "Train of four")
    tv = Abbr("TV", "Tidal volume")
    urea_nitrogen = Abbr("UUN", "Urine Urea Nitrogen")
    vd_airway = Abbr("VDaw", "Dead space airway volume")
