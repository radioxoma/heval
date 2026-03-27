from __future__ import annotations

import enum
import functools
import operator
from dataclasses import dataclass


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

    Examples:
        >>> Flag(
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
    def __init__(self, short: str, full: str, url: str = ""):
        self.short = short
        self.full = full
        self.url = url

    def __str__(self):
        return f"""<abbr title="{self.full}" tabindex="0">{self.short}</abbr>"""


class A:
    """Abbreviation namespace."""

    # fmt: off
    aa_gradient = Abbr("A-a gradient", "Alveolar-arterial gradient")
    abg = Abbr("ABG", "Arterial blood gas test")
    acls = Abbr("ACLS", "Advanced cardiovascular life support")
    aki = Abbr("AKI", "Acute kidney injury")
    anion_gap = Abbr("AG", "Anion gap")
    bmi = Abbr("BMI", "Body mass index")
    bmr = Abbr("BMR", "Basal metabolic rate")
    bsa = Abbr("BSA", "Body surface area, m²")
    ccrea = Abbr("cCrea", "Creatinine")
    chf = Abbr("CHF", "Congestive heart failure")
    ckd = Abbr("CKD", "Chronic kidney disease")
    crcl = Abbr("CrCl", "Creatinine clearance by Cockcroft-Gault")
    crrt = Abbr("CRRT", "Continuous renal replacement therapy")
    ctbil = Abbr("ctBil", "Total bilirubin", "https://en.wikipedia.org/wiki/Bilirubin")
    d5w = Abbr("D5, D5W", "Dextrose 5%")
    dka = Abbr("DKA", "Diabetic ketoacidosis", "https://en.wikipedia.org/wiki/Diabetic_ketoacidosis")
    eda = Abbr("EDA", "Epidural anesthesia")
    egfr = Abbr("eGFR", "Estimated glomerular filtration rate")
    espen = Abbr("ESPEN", "European Society for Clinical Nutrition and Metabolism")
    ffp = Abbr("FFP", "Fresh frozen plasma")
    fib = Abbr("Fib", "Fibrinogen")
    ganest = Abbr("GA", "General anesthesia")
    gapgap = Abbr("gg", "Gap-gap, delta gap")
    gi = Abbr("GI", "Gastrointestinal")
    hagma = Abbr("HAGMA", "High anion gap metabolic acidosis")
    hb = Abbr("Hb", "Hemoglobin")
    hct = Abbr("HCT", "Hematocrit", "https://en.wikipedia.org/wiki/Hematocrit")
    hhs = Abbr("HHS", "Hyperosmolar hyperglycemic state, hyperosmolar non-ketotic state (HONK)", "https://en.wikipedia.org/wiki/Hyperosmolar_hyperglycemic_state")
    ibw = Abbr("IBW", "Ideal body weight, kg")
    inr = Abbr("INR", "International normalized ratio")
    isth = Abbr("ISTH", "International Society on Thrombosis and Haemostasis")
    iv = Abbr("IV, I/V", "Intravenous")
    kdigo = Abbr("KDIGO", "Kidney Disease: Improving Global Outcomes")
    kult = Abbr("KULT", "Ketones, uremia, lactate, toxins")
    mv = Abbr("MV", "Minute ventilation, L/min")
    nagma = Abbr("NAGMA", "Normal anion gap metabolic acidosis")
    nmt = Abbr("NMT", "Neuromuscular monitoring")
    plt = Abbr("PLT", "Platelets")
    prbc = Abbr("pRBC", "Packed red blood cells")
    rbw = Abbr("RBW", "Real body weight, kg")
    resp_rate = Abbr("RR", "Respiratory rate")
    ru_ls = Abbr("ЛС", "Лекарственные средства")
    ru_pos_dej = Abbr("ПосДеж", "Пособие дежуранта, С.А. Деревщиков, 2014 г")
    sbe = Abbr("SBE", "Standard base excess")
    siadh = Abbr("SIADH", "Syndrome of inappropriate antidiuretic hormone secretion")
    tiva = Abbr("TIVA", "Total intravenous anesthesia")
    tof = Abbr("TOF", "Train of four")
    tpe = Abbr("TPE", "Therapeutic plasma exchange")
    tv = Abbr("TV", "Tidal volume, ml")
    uf = Abbr("UF", "Ultrafiltration")
    urea_nitrogen = Abbr("UUN", "Urine Urea Nitrogen")
    vd_airway = Abbr("VDaw", "Dead space airway volume, ml")
    # fmt: on
