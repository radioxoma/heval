from __future__ import annotations

import dataclasses
import enum
import functools
import operator
import typing
from operator import attrgetter


class HumanSex(enum.IntEnum):
    """Human body constitution based on sex."""

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


@dataclasses.dataclass
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
    book_kurek2009 = Abbr("Курек 2009", "Курек, Кулагин Анестезия и ИТ у детей, 2009")
    book_kurek2013 = Abbr("Курек 2013", "В.В. Курек, А.Е. Кулагин «Анестезия и интенсивная терапия у детей» 3-е изд. 2013")
    book_pos_dej = Abbr("ПосДеж", "Пособие дежуранта, С.А. Деревщиков, 2014 г")
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
    iu = Abbr("IU", "International units")
    kdigo = Abbr("KDIGO", "Kidney Disease: Improving Global Outcomes")
    kult = Abbr("KULT", "Ketones, uremia, lactate, toxins")
    mv = Abbr("MV", "Minute ventilation, L/min")
    nagma = Abbr("NAGMA", "Normal anion gap metabolic acidosis")
    nota_bene = Abbr("NB!", "Nota bene")
    nmt = Abbr("NMT", "Neuromuscular monitoring")
    plt = Abbr("PLT", "Platelets")
    prbc = Abbr("pRBC", "Packed red blood cells")
    rbw = Abbr("RBW", "Real body weight, kg")
    resp_rate = Abbr("RR", "Respiratory rate")
    ru_ls = Abbr("ЛС", "Лекарственные средства")
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


@dataclasses.dataclass(slots=True)
class LabRef:
    lld: float | None = None
    ll: float | None = None
    l: float | None = None  # noqa: E741
    default: float | None = None  # For user interface. Target healthy value?
    # mean: float = None  # Numeric mean between 'l' and 'h'
    h: float | None = None
    hh: float | None = None
    hhd: float | None = None
    unit: str = ""


@dataclasses.dataclass(slots=True)
class LabType:
    name: str
    ref: LabRef = dataclasses.field(default_factory=LabRef)
    # Lab assay IDs collection: LOINC, ESLI etc
    mapping: tuple[str, ...] = dataclasses.field(default_factory=tuple)
    # lambda k: k * heval.abg.kPa
    converter: typing.Callable = dataclasses.field(default=lambda k: k, repr=False)
    # unit: str = dataclasses.field(default_factory=str)  # Unit expected by converter?
    attr: str = dataclasses.field(default_factory=str, init=False)

    def __set_name__(self, owner, name):
        if not self.attr:
            self.attr = name
        if not self.name:
            self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        raise AttributeError(
            "LabType is a class-level descriptor, access via class only"
        )

    def __set__(self, instance, value):
        raise AttributeError("LabType descriptors are read-only on instance")


@dataclasses.dataclass(slots=True)
class LabTypeMapper:
    """Mapping codes must have result in comparable quantitative units.

    I.e.:
        * ctHb level from ABG machine is unstable and must not be compared to
            Hb from hematologic analyzer (EDTA vial). Better not to use it at all.
        * cK, cNa, cCl treated as interchangeable.

    References:
        * https://en.wikipedia.org/wiki/Reference_ranges_for_blood_tests
        * https://www.healthcare.uiowa.edu/path_handbook/appendix/heme/pediatric_normals.html
    """

    # Hematology
    # https://www.mayoclinic.org/tests-procedures/hemoglobin-test/about/pac-20385075
    # hb_male = (135, 175)  # 130-160 g/L
    # hb_female = (120, 155)  # 120-140 g/L
    # hb_child = (110, 160)  # g/L
    blood_cbc_hb = LabType("Hb", ref=LabRef(default=140, unit="g/L"))
    # hct_male = (0.407, 0.503)
    # hct_female = (0.361, 0.443)
    # hct_child = (0.31, 0.41)
    blood_cbc_hct = LabType("HCT")
    blood_cbc_mcv = LabType("MCV", ref=LabRef(default=90, unit="fL"))
    # Фракция незрелых ретикулоцитов, %
    blood_cbc_retFraq = LabType("RET", ref=LabRef(default=1, unit="%"))
    blood_cbc_plt = LabType("PLT", LabRef(default=300, unit="10⁹/L"))
    blood_cbc_plt_microscopy = LabType(
        "PLT microscopy", ref=LabRef(default=300, unit="10⁹/L")
    )
    blood_cbc_ley = LabType("LEY", ref=LabRef(unit="10⁹/L"))
    # Относительное количество нейтрофилов, %
    blood_cbc_neu_fraq = LabType("NEU", ref=LabRef(unit="%"))
    # Абсолютное количество лимфоцитов
    blood_cbc_lym = LabType("LYM", ref=LabRef(unit="10⁹/L"))

    # Coagulation
    blood_coag_fib = LabType("Fib", ref=LabRef(default=3, unit="g/L"))
    blood_coag_inr = LabType("INR", ref=LabRef(default=1, hh=4, unit="Fraq"))
    blood_coag_ptt = LabType("PTT")  # АЧТВ
    blood_coag_ddimer = LabType("dDimer", ref=LabRef(default=300, unit="ng/ml"))
    blood_coag_antix = LabType("Anti-Xa")
    # Активность антитромбина III, %
    blood_coag_at3 = LabType("AT III", ref=LabRef(unit="%"))

    # Blood type
    blood_type_ab0 = LabType("AB0")
    blood_type_rh = LabType("Rh")
    blood_type_rh_phenotype = LabType("Rh-фенотип")
    blood_type_cw = LabType("Сw")
    blood_type_kell = LabType("Kell")
    blood_type_coombs_indirect = LabType("Проба Кумбса непрямая")
    blood_type_coombs_direct = LabType("Проба Кумбса прямая")
    blood_type_er_antibody = LabType("Антиэритроцитарные антитела")

    # ABG
    # pH — кислотно-основное состояние крови, усл.ед.
    blood_abg_pH = LabType(
        "pH крови", ref=LabRef(lld=6.8, ll=7.15, l=7.35, default=7.4, h=7.45, hhd=7.8)
    )
    # pO2 — парциальное давление кислорода в крови, мм.рт.ст.
    blood_abg_pO2 = LabType("pO2", ref=LabRef(l=80, default=95, h=100, unit="mmHg"))
    # blood_abg_p50 = LabType("", ("ESLI.LI_TEST.772",))  # No data, see ESLI.LI_TEST.787  # # p50 — 50% насыщение гемоглобина кислородом
    # ref_pCO2mmHg = LabRef(l=35, default=40, h=45)  # mmHg
    # pCO2 — парциальное давление углекислого газа в крови, мм.рт.ст.
    blood_abg_pCO2 = LabType("pCO2", ref=LabRef(l=4.666, h=6, unit="kPa"))
    blood_abg_ctCO2A = LabType("tCO2A")  # tCO2A - общая двуокись углерода крови
    # tHb — концентрация общего гемоглобина в крови, г/л, usage discouraged
    blood_abg_ctHb = LabType("ctHb", ref=LabRef(unit="g/L"))
    blood_abg_hct = LabType("Hct calculated")  # Hct, %
    blood_abg_FO2Hb = LabType("FO2Hb")  # FO2Hb — фракция оксигемоглобина в крови
    blood_abg_FCOHb = LabType("FCOHb")  # FCOHb — фракция карбоксигемоглобина в крови
    blood_abg_FMetHb = LabType("FMetHb")  # FMetHb — фракция метгемоглобина в крови
    # FHHb — фракция восстановленного гемоглобина в крови
    blood_abg_FHHb = LabType("FHHb")
    blood_abg_FHbF = LabType("FHbF")  # FHbF — фракция фетального гемоглобина в крови
    # blood_abg_ = LabType("")  # # H+ - концентрация водородных ионов крови
    blood_abg_sO2 = LabType("sO2")  # sO2 — насыщение кислородом крови, %
    blood_abg_tO2 = LabType("tO2")  # # tO2 — общее содержание кислорода крови
    # Концентрация кислорода в вдыхаемом воздухе
    blood_abg_FiO2 = LabType("FiO2", ref=LabRef(default=0.21, unit="Fraq"))
    blood_abg_Aa_gradient = LabType("", ref=LabRef(l=5, h=20, unit="mmHg"))
    # blood_abg_ = LabType("")  # # Концентрация углекислого газ в вдыхаемом воздухе
    # blood_abg_ = LabType("")  # # Концентрация сурфактанта в вдыхаемом воздухе
    # p50 — парциальное давление кислорода при 50% насыщении крови
    blood_abg_p50 = LabType("р50")
    # blood_abg_ = LabType("")  # # Px — показатель экстракции кислорода в тканях
    # cHCO3 — концентрация бикарбоната — ацидоза/алкалоза, мМоль/л
    blood_abg_cHCO3 = LabType("cHCO3", ref=LabRef(l=22, h=26, unit="mEq/L"))
    blood_abg_sbc = LabType("SBC")  # SBC- стандартный бикарбонат крови

    # -15 is NaHCO3 infusion threshold
    # BE - избыток оснований, мМоль/л
    blood_abg_be = LabType("BE", ref=LabRef(ll=-15, l=-2, default=0, h=2, unit="mEq/L"))
    # blood_abg_ = LabType("")  # # BBA - буферные основания крови

    # ref_K = LabRef(l=3.5, default=4, h=5.3)  # mmol/L, Radiometer, adult
    # K+ — концентрация ионов калия в крови, мМоль/л
    blood_abg_cK = LabType(
        "cK+", ref=LabRef(lld=1.5, ll=3.1, l=3.5, default=4, h=5.3, hh=7)
    )
    # Cl- — концентрация ионов хлора в крови. Radiometer, adult
    blood_abg_cCl = LabType("cCl-", ref=LabRef(l=98, default=105, h=115, unit="mmol/L"))
    # Ca2+ — концентрация ионов кальция в крови, мМоль/л
    blood_abg_cCa = LabType("cCa2+")

    # https://en.wikipedia.org/wiki/Hypernatremia
    # Na = (130, 155)  # mmol/L, Radiometer, adult
    # Na = (130, 150)  # Курек 2013 c 133, children
    # Na+ — концентрация ионов натрия в крови, мМоль/л
    blood_abg_cNa = LabType("cNa", ref=LabRef(l=135, default=140, h=145))

    # Mean fasting glucose level https://en.wikipedia.org/wiki/Blood_sugar_level
    # Note: gap between lower cGlu and cGlu_target
    # Used as initial value for mOsm calculation.
    # <6.1 mmol/L  is perfect for septic patients
    # 10 mmol/L stands for glucose renal threshold
    # cGlu_target = (4.5, 10)  # ICU target range
    # ref_Glu = LabRef(lld=1.5, ll=None, default=None, l=7.8, h=10)  # NICE-SUGAR trial?
    # Glu — концентрация глюкозы, мМоль/л
    blood_abg_cGlu = LabType("cGlu", ref=LabRef(l=4.1, default=5.5, h=6.1, hh=10))
    # Lac — концентрация лактата, мМоль/л
    blood_abg_cLac = LabType("cLac", ref=LabRef(default=1, h=4, hh=8, hhd=15))
    # cCrea — концентрации креатинина
    blood_abg_cCrea = LabType("cCrea", ref=LabRef(default=75, unit="μmol/L"))
    # ctBil — концентрации билирубина
    blood_abg_ctBil = LabType("ctBil", ref=LabRef(default=10, unit="μmol/L"))

    # NB! Changing 'gap' range will affect Gap-Gap calculation
    # mEq/L without potassium [Курек 2013, с 47]
    blood_abg_anionGap = LabType("Anion gap", LabRef(l=7, h=16))
    # Strong ion difference. Arbitrary threshold
    blood_abg_SIDAbbr = LabType("", LabRef(l=-5, h=5))

    # Minimal low value has been chosen (<280), as I believe it corresponds to mOsm reference range without BUN
    # Осмолярность (sic!). De-facto 2*Na+cGlu
    blood_abg_osmolarity = LabType("Osm", LabRef(l=275, h=295, unit="mOsm/kg"))
    blood_abg_osmolality = LabType("ОсмоляЛЬность")

    # Biochemistry
    blood_bchem_ctBilDir = LabType("Бил. кон (блок)")  # Non-toxic
    # Toxin некон/непрям
    blood_bchem_ctBilIndir = LabType(
        "Бил. некон (liver failure, гемолиз)", ref=LabRef(default=10, unit="μmol/L")
    )
    blood_bchem_urea = LabType("Urea", ref=LabRef(default=7, unit="mmol/L"))
    blood_bchem_cMg = LabType("Mg2+")
    blood_bchem_Fe = LabType("Fe общее")
    blood_bchem_NTproBNP = LabType("NT-proBNP")  # Brain natriuretic peptide
    blood_bchem_crp = LabType("ЦРБ")
    blood_bchem_pct = LabType("PCT")
    blood_bchem_alt = LabType("ALT")
    blood_bchem_ast = LabType("AST")
    blood_bchem_aamylase = LabType("α-амилаза")
    blood_bchem_b9 = LabType("B9 (фолиевая)")
    blood_bchem_b12 = LabType("B12")
    blood_bchem_total_protein = LabType("Общий белок")
    # Mean albumin level used to normalize anion gap value in low cAlb case
    # Albumin <25 for oncotic oedema
    blood_bchem_albumin = LabType(
        "Albumin", ref=LabRef(ll=25, l=35, default=44, h=50, unit="g/L")
    )
    # Several test systems with different reference ranges
    blood_bchem_troponin_i = LabType("Troponine I")

    # Urine
    urine_any_ketone = LabType("UrineKetone")
    urine_any_er = LabType("UrineBlood")
    urine_nitrite = LabType("UrineNitrite")
    urine_any_ley = LabType("UrineLEY")

    # Serology
    blood_serology_trep = LabType("")  # 1147 since 10.03.2025
    blood_serology_hbs_ag = LabType("")
    blood_serology_hcv_ab = LabType("")
    blood_serology_hiv_abag = LabType("")

    sofa = LabType("SOFA")  # Sequential Organ Failure Assessment (SOFA) Score

    @classmethod
    def print_codes(cls):
        """Print mapping codes in order."""
        codes = list()
        for v in cls.__dict__.values():
            if isinstance(v, LabType):
                v.mapping = tuple(sorted(v.mapping))
                codes.append(v)
        codes.sort(key=attrgetter("mapping"))
        return "\n".join([str(k) for k in codes])
