"""Electrolyte disturbances and correction.

Author: Eugene Dvoretsky
"""
import textwrap
from itertools import chain

from heval import abg, human

M_C6H12O6 = 180
M_Crea = 88.40  # cCrea (μmol/L) = 88.40 * cCrea (mg/dL)
M_KCl = 74.5
M_NaCl = 58.5
M_NaHCO3 = 84  # g/mol or mg/mmol
M_Hb = 16.1140  # g/mol

norm_sbe = (-2, 2)  # mEq/L

# NB! Changing 'norm_gap' will affect Gap-Gap calculation
norm_gap = (7, 16)  # mEq/L without potassium [Курек 2013, с 47],

# Minimal low value has been chosen (<280), as I believe it
# corresponds to mOsm reference range without BUN
# https://en.wikipedia.org/wiki/Reference_ranges_for_blood_tests
norm_mOsm = (275, 295)  # mOsm/kg

norm_K = (3.5, 5.3)  # mmol/L, Radiometer, adult

# norm_Na = (130, 155)  # mmol/L, Radiometer, adult
# norm_Na = (130, 150)  # Курек 2013 c 133, children
norm_Na = (135, 145)  # https://en.wikipedia.org/wiki/Hypernatremia
norm_Cl = (98, 115)  # mmol/L, Radiometer, adult

# Mean fasting glucose level https://en.wikipedia.org/wiki/Blood_sugar_level
# Used as initial value for mOsm calculation.
norm_cGlu_mean = 5.5  # mmol/L
norm_cGlu = (4.1, 6.1)  # mmol/L < 6.1 is perfect for septic patients
# 10 mmol/L stands for glucose renal threshold
norm_cGlu_target = (4.5, 10)  # ICU target range
# Note: gap between lower norm_cGlu and norm_cGlu_target

# Various https://www.healthcare.uiowa.edu/path_handbook/appendix/heme/pediatric_normals.html
hct_norm_male = (0.407, 0.503)
hct_norm_female = (0.361, 0.443)
hct_norm_child = (0.31, 0.41)

# https://www.mayoclinic.org/tests-procedures/hemoglobin-test/about/pac-20385075
hb_norm_male = (13.5, 17.5)  # g/dl, 130-160 g/L
hb_norm_female = (12.0, 15.5)  # g/dl, 120-140 g/L
hb_norm_child = (11, 16)  # g/dl


class HumanBloodModel(object):
    """Represents an human blood ABG status."""

    def __init__(self, parent=None):
        self.parent = parent
        self._int_prop = ("pH", "pCO2", "cK", "cNa", "cCl", "cGlu", "ctAlb", "ctHb")
        self._txt_prop = ()

        self.pH = None
        self.pCO2 = None  # kPa

        self.cK = None  # mmol/L
        self.cNa = None  # mmol/L
        self.cCl = None  # mmol/L

        self.ctAlb = None  # g/dL albumin
        self.cGlu = None  # mmol/L
        self.ctHb = None  # g/dl, haemoglobin
        # self.ctBun = None  # May be for osmolarity in future

    def __str__(self):
        int_prop = {}
        for attr in chain(self._int_prop, self._txt_prop):
            int_prop[attr] = getattr(self, attr)
        return f"HumanBlood: {int_prop}"

    def populate(self, properties):
        """Populate model from data structure.

        NB! Function changes passed property dictionary.

        :param dict properties: Dictionary with model properties to set.
            Key names must be equal to class properties names.
        :return:
            Not applied properties
        :rtype: dict
        """
        for item in self._int_prop:
            if item in properties:
                setattr(self, item, float(properties.pop(item)))
        for item in self._txt_prop:
            if item in properties:
                setattr(self, item, properties.pop(item))
        return properties

    # def __str__(self):
    #     pass

    # def is_init(self):
    #     pass

    @property
    def sbe(self):
        return abg.calculate_cbase(self.pH, self.pCO2)

    @property
    def hco3p(self):
        return abg.calculate_hco3p(self.pH, self.pCO2)

    @property
    def anion_gapk(self):
        """Anion gap (K+), usually not used."""
        if self.cK is not None:
            return abg.calculate_anion_gap(
                Na=self.cNa,
                Cl=self.cCl,
                HCO3act=self.hco3p,
                K=self.cK,
                albumin=self.ctAlb,
            )
        else:
            raise ValueError("No potassium specified")

    @property
    def anion_gap(self):
        """Calculate anion gap without potassium. Preferred method."""
        return abg.calculate_anion_gap(
            Na=self.cNa, Cl=self.cCl, HCO3act=self.hco3p, albumin=self.ctAlb
        )

    @property
    def sid_abbr(self):
        """Strong ion difference."""
        return abg.calculate_sid_abbr(self.cNa, self.cCl, self.ctAlb)

    @property
    def osmolarity(self):
        return abg.calculate_osmolarity(self.cNa, self.cGlu)

    @property
    def hct_calc(self):
        """Haematocrit."""
        return abg.calculate_hct(self.ctHb * 10 / M_Hb)

    def describe_osmolarity(self):
        """Verbally describe osmolarity impact on human.

        Diabetes mellitus decompensation:
          1 type - DKA (no insulin enables ketogenesis).
            dehydration (osmotic diuresis and vomiting)
            cGlu 15-30 mmol/L, SBE < -18.4 (ketoacidosis), HAGMA
          2 type - HHNS (cells not sensitive to Ins)
            dehydration (osmotic diuresis)
            cGlu >30, mOsm >320, no acidosis and ketone bodies)
        """
        info = "Osmolarity is "
        if self.osmolarity > norm_mOsm[1]:
            info += "high"
        elif self.osmolarity < norm_mOsm[0]:
            info += "low"
        else:
            info += "ok"
        info += f" {self.osmolarity:.0f} ({norm_mOsm[0]:.0f}-{norm_mOsm[1]:.0f} mOsm/L)"

        # Hyperosmolarity flags
        # if self.osmolarity >=282: # mOsm/kg
        #     info += " vasopressin released"
        if self.osmolarity > 290:  # mOsm/kg
            # plasma thirst point reached
            info += ", human is thirsty (>290 mOsm/kg)"
        if self.osmolarity > 320:  # mOsm/kg
            # >320 mOsm/kg Acute kidney injury cause https://www.ncbi.nlm.nih.gov/pubmed/9387687
            info += ", acute kidney injury risk (>320 mOsm/kg)"
        if self.osmolarity > 330:  # mOsm/kg
            # >330 mOsm/kg hyperosmolar hyperglycemic coma https://www.ncbi.nlm.nih.gov/pubmed/9387687
            info += ", coma (>330 mOsm/kg)"

        # SBE>-18.4 - same as (pH>7.3 and hco3p>15 mEq/L) https://emedicine.medscape.com/article/1914705-overview
        if all((self.osmolarity > 320, self.cGlu > 30, self.sbe > -18.4)):
            # https://www.aafp.org/afp/2005/0501/p1723.html
            # IV insulin drip and crystalloids
            info += " Diabetes mellitus type 2 with hyperosmolar hyperglycemic state? Check for HAGMA and ketonuria to exclude DKA. Look for infection or another underlying illness that caused the hyperglycemic crisis."
        return info

    def describe_abg(self):
        """Describe pH and pCO2 - an old implementation considered stable."""
        info = textwrap.dedent(
            f"""\
            pCO2    {self.pCO2:2.1f} kPa
            HCO3(P) {self.hco3p:2.1f} mmol/L
            Conclusion: {abg.abg_approach_stable(self.pH, self.pCO2)[0]}\n"""
        )
        if self.parent.debug:
            info += "\n-- Manual compensatory response check --------------\n"
            # info += "Abg Ryabov:\n{}\n".format(textwrap.indent(abg_approach_ryabov(self.pH, self.pCO2), '  '))
            info += abg.abg_approach_research(self.pH, self.pCO2)
        return info

    def describe_anion_gap(self):
        info = "-- Anion gap ---------------------------------------\n"
        desc = f"{self.anion_gap:.1f} ({norm_gap[0]:.0f}-{norm_gap[1]:.0f} mEq/L)"
        if abg.abg_approach_stable(self.pH, self.pCO2)[1] == "metabolic_acidosis":
            if norm_gap[1] < self.anion_gap:
                # Since AG elevated, calculate delta ratio to test for coexistent NAGMA or metabolic alkalosis
                info += f"HAGMA {desc} (KULT?), "
                info += abg.calculate_anion_gap_delta(self.anion_gap, self.hco3p)
            elif self.anion_gap < norm_gap[0]:
                info += f"Low AG {desc} - hypoalbuminemia or low Na?"
            else:
                # Hypocorticism [Henessy 2018, с 113 (Clinical case 23)]
                info += f"NAGMA {desc}. Diarrhea or renal tubular acidosis?"
        else:
            if norm_gap[1] < self.anion_gap:
                info += f"Unexpected high AG {desc} without main metabolic acidosis; "
                # Can catch COPD or concurrent metabolic alkalosis here
                info += abg.calculate_anion_gap_delta(self.anion_gap, self.hco3p)
            elif self.anion_gap < norm_gap[0]:
                info += f"Unexpected low AG {desc}. Starved patient with low albumin? Check your input and enter ctAlb if known."
            else:
                info += f"AG is ok {desc}"

        if self.parent.debug:
            """Strong ion difference.

            Sometimes Na and Cl don't changes simultaneously.
            Try distinguish Na-Cl balance in case high/low osmolarity.
            Should help to choose better fluid for correction.
            """
            SIDabbr_norm = (-5, 5)  # Arbitrary threshold
            ref_str = f"{self.sid_abbr:.1f} ({SIDabbr_norm[0]:.0f}-{SIDabbr_norm[1]:.0f} mEq/L)"
            info += "\nSIDabbr [Na⁺-Cl⁻-38] "
            if self.sid_abbr > SIDabbr_norm[1]:
                info += f"is alkalotic {ref_str}, relative Na⁺ excess"
            elif self.sid_abbr < SIDabbr_norm[0]:
                info += f"is acidotic {ref_str}, relative Cl⁻ excess"
            else:
                info += f"is ok {ref_str}"
            info += f", BDE gap {self.sbe - self.sid_abbr:.01f} mEq/L"  # Lactate?
        return info

    def describe_sbe(self):
        """Calculate needed NaHCO3 for metabolic acidosis correction.

        Using SBE (not pH) as threshold point guaranties that bicarbonate
        administration won't be suggested in case of respiratory acidosis.
        https://en.wikipedia.org/wiki/Intravenous_sodium_bicarbonate

        * Acid poisoning for adults: NaHCO3 4% 5-15 ml/kg [МЗ РБ 2004-08-12 приказ 200 приложение 2 КП отравления, с 53]
        * В книге Рябова вводили 600 mmol/24h на метаболический ацидоз, пациент перенёс без особенностей


        First approach
        --------------
        "pH < 7.26 or hco3p < 15" requires correction with NaHCO3 [Курек 2013, с 47],
        but both values pretty close to BE -9 meq/L, so I use it as threshold.

        Max dose of NaHCO3 is 4-5 mmol/kg (between ABG checks or 24h?) [Курек 273]


        Second approach
        ---------------
        According to BICAR-ICU 2018:
          * Using more restrictive threshold pH 7.11, which is
              correspondent to BE -15 mEq/L.
          * Tip only for AKI patients
          * https://pubmed.ncbi.nlm.nih.gov/29910040/
          * https://en.wikipedia.org/wiki/Metabolic_acidosis
        """
        NaHCO3_threshold = -15  # was -9 mEq/L
        info = ""
        if self.sbe > norm_sbe[1]:
            # FIXME: can be high if chloride is low. Calculate SID?
            # https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2856150
            # https://en.wikipedia.org/wiki/Contraction_alkalosis
            # Acetazolamide https://en.wikipedia.org/wiki/Carbonic_anhydrase_inhibitor
            info += f"SBE is high {self.sbe:.1f} ({norm_sbe[0]:.0f}-{norm_sbe[1]:.0f} mEq/L). Check Cl⁻. Hypoalbuminemia? NaHCO₃ overdose?"
        elif self.sbe < norm_sbe[0]:
            if self.sbe <= NaHCO3_threshold:
                info += f"SBE is drastically low {self.sbe:.1f} ({norm_sbe[0]:.0f}-{norm_sbe[1]:.0f} mEq/L), consider NaHCO₃ in AKI patients to reach target pH 7.3:\n"
                info += "  * Fast ACLS tip (all ages): load dose 1 mmol/kg, then 0.5 mmol/kg every 10 min [Курек 2013, 273]\n"
                # info += "NaHCO3 {:.0f} mmol during 30-60 minutes\n".format(0.5 * (24 - self.hco3p) * self.parent.weight)  # Doesn't looks accurate, won't use it [Курек 2013, с 47]
                NaHCO3_mmol = -0.3 * self.sbe * self.parent.weight  # mmol/L
                NaHCO3_mmol_24h = self.parent.weight * 5  # mmol/L
                NaHCO3_g = NaHCO3_mmol / 1000 * M_NaHCO3  # gram
                NaHCO3_g_24h = NaHCO3_mmol_24h / 1000 * M_NaHCO3
                # Курек 273, Рябов 73 for children and adult
                info += f"  * NaHCO₃ {NaHCO3_mmol:.0f} mmol (-0.3*SBE/kg) during 30-60 min, daily dose {NaHCO3_mmol_24h:.0f} mmol/24h (5 mmol/kg/24h):\n"
                # info += "  * NaHCO₃ {:.0f} mmol (-(SBE - 8)/kg/4)\n".format(
                #     -(self.sbe - 8) * self.parent.weight / 4, NaHCO3_mmol_24h)  # Плохой 152
                for dilution in (4, 8.4):
                    NaHCO3_ml = NaHCO3_g / dilution * 100
                    NaHCO3_ml_24h = NaHCO3_g_24h / dilution * 100
                    info += f"    * NaHCO3 {dilution:.1f}% {NaHCO3_ml:.0f} ml, daily dose {NaHCO3_ml_24h:.0f} ml/24h\n"
                if self.parent.debug:
                    info += textwrap.dedent(
                        """\
                        Confirmed NaHCO₃ use cases:
                          * Metabolic acidosis correction leads to decreased 28 day mortality only in AKI patients (target pH 7.3) [BICAR-ICU 2018]
                          * TCA poisoning with prolonged QT interval (target pH 7.45-7.55 [Костюченко 204])
                          * In hyperkalemia (when pH increases, K⁺ level decreases)
                        Main concepts of usage:
                          * Must hyperventilate to make use of bicarbonate buffer
                          * Control ABG after each NaHCO₃ infusion or every 4 hours
                          * Target urine pH 8, serum 7.34 [ПосДеж, с 379]"""
                    )
            else:
                info += f"SBE is low {self.sbe:.1f} ({norm_sbe[0]:.0f}-{norm_sbe[1]:.0f} mEq/L), but NaHCO₃ won't improve outcome when BE > {NaHCO3_threshold:.0f} mEq/L"
        else:
            info += (
                f"SBE is ok {self.sbe:.1f} ({norm_sbe[0]:.0f}-{norm_sbe[1]:.0f} mEq/L)"
            )
        return info

    def describe_electrolytes(self):
        info = [
            "-- Electrolyte and osmolar abnormalities -----------",
            self.describe_osmolarity(),
            electrolyte_K(self.parent.weight, self.cK),
            electrolyte_Na(self.parent.weight, self.cNa, self.cGlu, self.parent.debug),
            electrolyte_Cl(self.cCl),
        ]
        return "\n".join(info) + "\n"

    def describe_glucose(self):
        """Assess glucose level.

        https://en.wikipedia.org/wiki/Renal_threshold
        https://en.wikipedia.org/wiki/Glycosuria
        """
        info = ""
        if self.cGlu > norm_cGlu[1]:
            if self.cGlu <= norm_cGlu_target[1]:
                info += f"cGlu is above ideal {self.cGlu:.1f} (target {norm_cGlu_target[0]:.1f}-{norm_cGlu_target[1]:.1f} mmol/L), but acceptable"
            else:
                info += f"Hyperglycemia {self.cGlu:.1f} (target {norm_cGlu_target[0]:.1f}-{norm_cGlu_target[1]:.1f} mmol/L) causes glycosuria with osmotic diuresis"
                if self.cGlu <= 20:  # Arbitrary threshold
                    info += f", consider insulin {insulin_by_glucose(self.cGlu):.0f} IU subcut for adult"
                else:
                    info += f", refer to DKE/HHS protocol (HAGMA and urine ketone), start fluid and I/V insulin {self.parent.weight * 0.1:.1f} IU/h (0.1 IU/kg/h)"

        elif self.cGlu < norm_cGlu[0]:
            if self.cGlu > 3:  # Hypoglycemia <3.3 mmol/L for pregnant?
                info += f"cGlu is below ideal {self.cGlu:.1f} (target {norm_cGlu_target[0]:.1f}-{norm_cGlu_target[1]:.1f} mmol/L), repeat blood work, don't miss hypoglycemic state"
            else:
                info += "Severe hypoglycemia, IMMEDIATELY INJECT BOLUS GLUCOSE 10 % 2.5 mL/kg:\n"
                # https://litfl.com/glucose/
                # For all ages: dextrose 10% bolus 2.5 mL/kg (0.25 g/kg) [mistake Курек, с 302]
                info += solution_glucose(
                    0.25 * self.parent.weight, self.parent.weight, add_insuline=False
                )
                # High lactate + refractory low cGlu marks liver failure: expect death in 24-48 hours
                info += "Check cGlu after 20 min, repeat bolus and use continuous infusion, if refractory. In case of sepsis, liver failure may be the cause."

        else:
            info += f"cGlu is ok {self.cGlu:.1f} ({norm_cGlu[0]:.1f}-{norm_cGlu[1]:.1f} mmol/L)"
        return info

    def describe_albumin(self):
        """Albumin as nutrition marker in adults."""
        ctalb_range = f"{self.ctAlb} ({abg.norm_ctAlb[0]}-{abg.norm_ctAlb[1]} g/dL)"
        if abg.norm_ctAlb[1] < self.ctAlb:
            info = f"ctAlb is high {ctalb_range}. Dehydration?"
        elif abg.norm_ctAlb[0] <= self.ctAlb <= abg.norm_ctAlb[1]:
            info = f"ctAlb is ok {ctalb_range}"
        elif 3 <= self.ctAlb < abg.norm_ctAlb[0]:
            info = f"ctAlb is low: light hypoalbuminemia {ctalb_range}"
        elif 2.5 <= self.ctAlb < 3:
            info = f"ctAlb is low: medium hypoalbuminemia {ctalb_range}"
        elif self.ctAlb < 2.5:
            info = f"ctAlb is low: severe hypoalbuminemia {ctalb_range}. Expect oncotic edema"
        return info

    def describe_Hb(self):
        """Describe Hb and hct_calc.

        References
        ----------
        [1] https://en.wikipedia.org/wiki/Hematocrit#cite_ref-3
        [2] https://www.healthcare.uiowa.edu/path_handbook/appendix/heme/pediatric_normals.html
        """
        # Top hct value for free water deficit calculation.
        if self.parent.sex == human.HumanSex.male:
            hb_norm = hb_norm_male
            hct_norm = hct_norm_male
        elif self.parent.sex == human.HumanSex.female:
            hb_norm = hb_norm_female
            hct_norm = hct_norm_female
        elif self.parent.sex == human.HumanSex.child:
            hb_norm = hb_norm_child
            hct_norm = hct_norm_child
        hct_target = hct_norm[0] + (hct_norm[1] - hct_norm[0]) / 2  # Mean
        vol_def = volume_deficit_hct(self.parent.weight, self.hct_calc, hct_target)

        desc_hb = f"{self.ctHb:.1f} ({hb_norm[0]:.1f}-{hb_norm[1]:.1f} g/dl)"
        desc_hct = f"{self.hct_calc:.3f} ({hct_norm[0]:.3f}-{hct_norm[1]:.3f})"
        info = ""
        if self.ctHb < 7:  # Generic threshold
            info += f"Hb is low {desc_hb}, consider transfusion. "
        else:
            info += f"Hb {desc_hb}. "

        if self.hct_calc > hct_norm[1]:
            info += f"Hct is high {desc_hct}"
        elif self.hct_calc < hct_norm[0]:
            info += f"Hct is low {desc_hct}"
        else:
            info += f"Hct is ok {desc_hct}"

        if self.hct_calc > hct_target + 0.01:  # Age-independent threshold
            info += f", free water deficit {vol_def:.0f} ml (limitations: valid if no anemia, osmolarity and Na⁺ are more specific)."

        if self.parent.sex == human.HumanSex.child:
            info += " \nNote that normal Hb and Hct values in children greatly dependent from age."
        return info


def solution_glucose(glu_mass, body_weight, add_insuline=True):
    """Glucose and insulin solution calculation.

    :param float glu_mass: glucose mass, grams
    :param float body_weight: patient body weight, kg
    :param bool add_insuline: Set False if bolus intended for hypoglycemic state

    Probably such glucose/insulin ratio can be used for both nutrition
    and as hyperkalemia bolus.

    * 1 ЕД на 3-5 г сухой глюкозы, скорость инфузии <= 0.5 г/кг/ч чтобы избежать глюкозурии [Мартов, Карманный справочник врача; RLSNET, Крылов Нейрореаниматология] (Ins 0.33-0.2 UI/г)
    * 1 ЕД на 4 г сухой глюкозы (если глюкозурия, то добавить инсулин или снизить скорость введения) [Курек, с 143; калькулятор BBraun; другие источники]
        * 0.25 IU/g
    """
    glu_mol = glu_mass / M_C6H12O6  # mmol/L
    # Glucose nutrition
    # Heat of combustion, higher value is 670 kcal/mol ~ 3.74 kcal/g https://en.wikipedia.org/wiki/Glucose
    # Usually referenced as 4.1 kcal/g

    # It's convenient to start with 0.15-0.2 g/kg/h, increasing speed up
    # to 0.5 g/kg/h. If hyperglycemia occurs, slow down or add more insulinum
    # to avoid glycosuria:
    # Hyperglycemia -> renal threshold (8.9-10 mmol/L) -> glycosuria

    # This rate correlates with normal liver glucose production rate
    # 5-8 mg/kg/min in an infant and about 3-5 mg/kg/min in an older child
    # https://emedicine.medscape.com/article/921936-treatment
    info = f"Glu {glu_mass:.1f} g ({glu_mol:.2f} mmol, {glu_mass * 4.1:.0f} kcal)"
    if add_insuline:
        ins_dosage = 0.25  # IU/g
        insulinum = glu_mass * ins_dosage
        info += f" + Ins {insulinum:.1f} IU ({ins_dosage:.2f} IU/g)"
    info += ":\n"

    for dilution in (5, 10, 40):
        g_low, g_max = 0.15, 0.5  # g/kg/h
        speed_low = (g_low * body_weight) / dilution * 100
        speed_max = (g_max * body_weight) / dilution * 100
        vol = glu_mass / dilution * 100
        info += f" * Glu {dilution:>2.0f}% {vol:>4.0f} ml ({speed_low:>3.0f}-{speed_max:>3.0f} ml/h = {g_low:.3f}-{g_max:.2f} g/kg/h)"
        if dilution == 5:
            info += " isotonic"
        info += "\n"
    return info


def solution_kcl4(salt_mmol):
    """Convert mmol of KCl to volume of saline solution.

    :param float salt_mmol: KCl, amount of substance, mmol
    :return: KCl 4 % ml solution, ml
    :rtype: float
    """
    return salt_mmol / 1000 * M_KCl / 4 * 100


def solution_normal_saline(salt_mmol):
    """Convert mmol of NaCl to volume of saline solution (several dilutions).

    Administration rate limiting:
        By ml/min for bolus
        By ml/h for continuous
        By mmol/h of sodioum

    NaCl 0.9%, 0.15385 mmol/ml
    NaCl 3%  , 0.51282 mmol/ml
    NaCl 10% , 1.70940 mmol/ml

    :param float salt_mmol: Amount of substance (NaCl or single ion equivalent), mmol
    :return: Info string
    """
    info = ""
    for dilution in (0.9, 3, 5, 10):
        conc = 1000 * (dilution / 100) / M_NaCl  # mmol/ml
        vol = salt_mmol / conc  # ml
        info += f" * NaCl {dilution:>4.1f}% {vol:>4.0f} ml"
        if dilution == 0.9:
            info += " isotonic"
        info += "\n"
    return info


def electrolyte_Na_classic(
    total_body_water: float,
    Na_serum: float,
    Na_target: float = 140,
    Na_shift_rate: float = 0.5,
) -> str:
    """Correct hyper- hyponatremia correction with two classic formulas.

    Calculates amount of pure water or Na.

    References:
        Original paper is unknown. Plenty simplified calculations among the books.
        [1] http://www.medcalc.com/sodium.html

    Args:
        total_body_water: Liters
        Na_serum: Serum sodium level, mmol/L
        Na_target: 140 mmol/L by default
        Na_shift_rate: 0.5 mmol/L/h by default is safe

    Returns:
        Text describing Na deficit/excess and solutions dosage to correct.
    """
    info = ""
    Na_shift_hours = abs(Na_target - Na_serum) / Na_shift_rate
    if Na_serum > Na_target:
        # Classic hypernatremia formula
        # water_deficit = total_body_water * (Na_serum - Na_target) / Na_target * 1000  # Equal
        water_deficit = total_body_water * (Na_serum / Na_target - 1) * 1000  # ml
        info += f"Free water deficit is {water_deficit:.0f} ml, "
        info += f"replace it with D5 at rate {water_deficit / Na_shift_hours:.1f} ml/h during {Na_shift_hours:.0f} hours. "
    elif Na_serum < Na_target:
        # Classic hyponatremia formula
        Na_deficit = (Na_target - Na_serum) * total_body_water  # mmol
        info += f"Na⁺ deficit is {Na_deficit:.0f} mmol, which equals to:\n"
        info += solution_normal_saline(Na_deficit)
        info += f"Replace Na⁺ at rate {Na_shift_rate:.1f} mmol/L/h during {Na_shift_hours:.0f} hours:\n"
        info += solution_normal_saline(Na_deficit / Na_shift_hours)
    return info


def electrolyte_Na_adrogue(
    total_body_water: float,
    Na_serum: float,
    Na_target: float = 140.0,
    Na_shift_rate: float = 0.5,
) -> str:
    """Correct hyper- hyponatremia correction with Adrogue–Madias formula.

    Calculates amount of specific solution needed to correct Na.
    Considered as more precise then classic formula.

    If patient urinates during Na replacement, calculated dose may be excessive
    because total body water won't be increased as expected.

    References:
        [1] Adrogue, HJ; and Madias, NE. Primary Care: Hypernatremia. New England Journal of Medicine 2000.
            https://www.ncbi.nlm.nih.gov/pubmed/10824078
            https://www.ncbi.nlm.nih.gov/pubmed/10816188
        [2] Does the Adrogue–Madias formula accurately predict serum sodium levels in patients with dysnatremias?
            https://www.nature.com/articles/ncpneph0335
        [3] http://www.medcalc.com/sodium.html

    Args:
        total_body_water: Liters
        Na_serum: Serum sodium level, mmol/L
        Na_target: 140 mmol/L by default
        Na_shift_rate: 0.5 mmol/L/h by default is safe

    Returns:
            Text describing Na deficit/excess and solutions dosage to correct.
    """
    solutions: list[dict[str, str | float]] = [
        # Hyper
        {"name": "NaCl 5%         (Na⁺ 855 mmol/L)", "K_inf": 0, "Na_inf": 855},
        {"name": "NaCl 3%         (Na⁺ 513 mmol/L)", "K_inf": 0, "Na_inf": 513},
        {"name": "NaCl 0.9%       (Na⁺ 154 mmol/L)", "K_inf": 0, "Na_inf": 154},
        # Iso
        {
            "name": "Sterofundin ISO (Na⁺ 145 mmol/L)",
            "K_inf": 4,
            "Na_inf": 145,
        },  # BBraun
        {
            "name": "Ionosteril      (Na⁺ 137 mmol/L)",
            "K_inf": 4,
            "Na_inf": 137,
        },  # Fresenius Kabi
        {
            "name": "Lactate Ringer  (Na⁺ 130 mmol/L)",
            "K_inf": 4,
            "Na_inf": 130,
        },  # Hartmann's solution
        # Hypo
        {"name": "NaCl 0.45%      (Na⁺  77 mmol/L)", "K_inf": 0, "Na_inf": 77},
        {"name": "NaCl 0.2%       (Na⁺  34 mmol/L)", "K_inf": 0, "Na_inf": 34},
        {"name": "D5W or water    (Na⁺   0 mmol/L)", "K_inf": 0, "Na_inf": 0},
    ]
    Na_shift_hours = abs(Na_target - Na_serum) / Na_shift_rate
    info = ""
    for sol in solutions:
        Na_inf = float(sol["Na_inf"])
        K_inf = float(sol["K_inf"])
        if Na_serum == (Na_inf + K_inf):
            # Prevent zero division if solution same as the patient Na
            continue
        vol = (
            (Na_target - Na_serum)
            / (Na_inf + K_inf - Na_serum)
            * (total_body_water + 1)
            * 1000
        )
        if vol < 0:
            # Wrong solution, will only make patient worse
            continue
        elif vol > 50000:
            # Will lead to volume overload, not an option
            # Using 50000 ml threshold to cut off unreal volumes
            continue
        info += f" * {sol['name']:<15} {vol:>6.0f} ml, {vol / Na_shift_hours:6.1f} ml/h during {Na_shift_hours:.0f} hours\n"
    return info


def electrolyte_K(weight, K_serum):
    """Assess blood serum potassium level.

    :param float weight: Real body weight, kg
    :param float K_serum: Potassium serum level, mmol/L

    Hypokalemia (additional K if <3.5 mmol/L)
    -----------------------------------------
    1. As far it's practically impossible to calculate K deficit,
    administer continuously i/v with rate 10 mmol/h and check ABG  every 2-4 hour in acute period
        * If there are ECG changes and muscle relaxation, speed up to 20 mmol/h [Курек 2009 с 557; Ryabov, p 56]
    2. In severe hypokalemia (<= 3 mmol/L) administrate with NaCl, not glucose
        * When deficit compensated (> 3 mmol/L) it's now possible to switch to glucose+insulin

    * Содержание K до 5 лет значительно выше [Курек 2013 с 38]
    * Если K+ <3 mmol/L, то введение глюкозы с инсулином может усугубить гипокалиемию, поэтому K+ вводить вместе с NaCl. [Курек ИТ 557]
    * Metabolic acidosis raises plasma K+ level by displacing it from cells. E.g. in DKA [Рябов 1994, с 70]

    [Курек 130]:
        * Top 24h dose 4 mmol/kg/24h
        * Полностью восполнять дефицит не быстрее чем за 48 ч
        * Допустимая скорость 0.5 mmol/kg/h (тогда суточная доза введётся за 8 часов)
        * На каждый mmol K+ вводить 10 kcal glucose
            * Если принять калорийность глюкозы за 3.74-4.1 kcal/g, то нужно 2.67-2.44 g глюкозы, примерно 2.5 г
    [Курек 132]:
        * Вводить K+ со скоростью 0.25-0.5 mmol/kg/h (не быстрее)
            * Но для веса > 40 кг, получается скорость >20 mmol/h, чего быть не должно.
        * На каждый mmol K+ вводить
            * Glu 2.5 g/mmol + Ins 0.2-0.3 IU/mmol (потребность в инсулине у детей меньше)

    Готовый раствор:
        * Концентрация калия: периферия не более 40 mmol/L (KCl 0.3 % ?), CVC не более 100 mmol/L (KCl 0.74 % ?) [Курек 2009 с 557]
            Т.е. для периферии можно Sol. Glucose 5 % 250 ml + KCl 7.5 % 10 ml, а для CVC KCl 7.5 % 25 ml?
        * Раствор K+ должен быть разбавлен до 1-2 % [?]

    [Hypokalemia: a clinical update](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5881435/)
        Standard infusion rate KCl: 10 mmol/h

    Hyperkalemia
    ------------
    Неотложеные мероприятия при K >= 7 mmol/L или ЭКГ-признаках гиперкалиемии [131]
        * Glu 20 % 0.5 g/kg + Ins 0.3 IU/g
        * Salbutamol

    Уменьшние количества ионизированного калия:
        * NaHCO3 2 mmol/kg (за 10-20 минут)
        * CaCl2 - только если есть изменения на ЭКГ [PICU: Electrolyte Emergencies]
        * hyperventilation
    """
    K_high = 6  # Курек 2013, p 47 (6 mmol/L, 131 (7 mmol/L)
    K_target = 5.0  # mmol/L Not from book
    K_low = 3.5  # Курек 132

    info = ""
    if K_serum > norm_K[1]:
        if K_serum >= K_high:
            glu_mass = 0.5 * weight  # Child and adults
            info += f"K⁺ is dangerously high (>{K_high:.1f} mmol/L)\n"
            info += "Inject bolus 0.5 g/kg "
            info += solution_glucose(glu_mass, weight)
            info += "Or standard adult bolus Glu 40% 60 ml + Ins 10 IU [ПосДеж]\n"
            # Use NaHCO3 if K greater or equal 6 mmol/L [Курек 2013, 47, 131]
            info += f"NaHCO₃ 8.4% {2 * weight:.0f} ml (RBWx2={2 * weight:.0f} mmol) [Курек 2013]\n"
            info += "Don't forget salbutamol, furesemide, hyperventilation. If ECG changes, use Ca gluconate [PICU: Electrolyte Emergencies]"
        else:
            info += f"K⁺ on the upper acceptable border {K_serum:.1f} ({K_low:.1f}-{K_high:.1f} mmol/L)"
    elif K_serum < norm_K[0]:
        if K_serum < K_low:
            info += f"K⁺ is dangerously low (<{K_low:.1f} mmol/L). Often associated with low Mg²⁺ (Mg²⁺ should be at least 1 mmol/L) and low Cl⁻.\n"
            info += "NB! Potassium calculations considered inaccurate, so use standard K⁺ replacement rate "
            if weight < 40:
                info += "{:.1f}-{:.1f} mmol/h (KCl 4 % {:.1f}-{:.1f} ml/h)".format(
                    0.25 * weight,
                    0.5 * weight,
                    solution_kcl4(0.25 * weight),
                    solution_kcl4(0.5 * weight),
                )
            else:
                info += "{:.0f}-{:.0f} mmol/h (KCl 4 % {:.1f}-{:.1f} ml/h)".format(
                    10, 20, solution_kcl4(10), solution_kcl4(20)
                )
            info += " and check ABG every 2-4 hours.\n"

            # coefficient = 0.45  # новорождённые
            # coefficient = 0.4   # грудные
            # coefficient = 0.3   # < 5 лет
            coefficient = 0.2  # >5 лет [Курек 2013]

            K_deficit = (K_target - K_serum) * weight * coefficient
            # K_deficit += weight * 1  # mmol/kg/24h Should I also add daily requirement? https://nursemathmedblog.wordpress.com/2016/05/29/potassium-replacement-calculation/

            info += f"Estimated K⁺ deficit is {K_deficit:.0f} mmol (KCl 4 % {solution_kcl4(K_deficit):.1f} ml) + "
            if K_deficit > 4 * weight:
                info += "Too much potassium for 24 hours"

            glu_mass = K_deficit * 2.5  # 2.5 g/mmol, ~10 kcal/mmol
            info += solution_glucose(glu_mass, weight)
        else:
            info += f"K⁺ on lower acceptable border {K_serum:.1f} ({K_low:.1f}-{K_high:.1f} mmol/L)"
    else:
        info += f"K⁺ is ok ({norm_K[0]:.1f}-{norm_K[1]:.1f} mmol/L)]"
    return info


def electrolyte_Na(weight: float, Na_serum: float, cGlu: float, verbose: bool = True):
    """Assess blood serum sodium level.

    Current human body fluid model status in context of Na replacement:
    1. total body water = intracellular + extracellular + interstitial fluid
    2. total body water = ideal_weight * 0.6
        * Coefficients of TBW (0.6) may vary
        * Some Na bound to bones and not included in model calculation
        * Sodium and water almost freely moves within TBW compartments,
            so proportion-like formulas are used
    4. Formulas:
        * Two "classic" formulas: for high and low Na can calculate:
            * Hypernatremia - volume of pure water
            * Hyponatremia - required Na
        * Newer Adrogue formula for both high and low Na and able to calculate
            volume of the specific solution.

    Hyperglycemia decreases Na_serum concentration https://www.ncbi.nlm.nih.gov/pubmed/10225241

    Hyponatremia
    ------------
    Common chromic causes: SIADH, CHF, cirrosis.
    Rare acute causes: psychogenic polydipsia, thiazide diuretics, postoperative

    Slow Na replacement:
        * Rapid Na increase -> serum osmolarity increase -> central pontine myelinolysis
        * Na increase not faster than 1-2 mmol/L/h for hyponatremia (central pontine myelinolysis risk)
        * Slow 0.5-1 mmol/L/h inctease to 125-130 mmol/L [Нейрореаниматология: практическое руководство 2017 - Гипонатриемия]
        * Коррекция гипонатриемии в течение 2-3 суток путем инфузии NaCl 3% со скоростью 0.25-0.5 мл/кг/час [ПосДеж 90]
        * Возможно имеется гипокортицизм и потребуется вводить гидрокортизон


    Hypernatremia
    -------------
    Slow Na decrease:
        * Na decrease not faster than 0.5-1 mmol/L/h for hypernatremia (cerebral edema risk)
        * Скорость снижения Na_serum <0.5 ммоль/л/ч или 12-15 ммоль/24h
        * Скорость снижения не быстрее 20 ммоль/л в сутки
        * Устраняется постепенно за 48 часов [Маневич, Плохой 2000 с. 116]
        * If Na>150 mmol/L use D5 or NaCl 0.45 %
        * If Na<150 use enteral water (https://med.virginia.edu/ginutrition/wp-content/uploads/sites/199/2014/06/Parrish_Rosner-Dec-14.pdf)
        * Spironolactone 25 mg, Furosemide 10-20 mg

    References:
        [1] http://www.medcalc.com/sodium.html

    Args:
        weight: Real body weight, kg
        Na_serum: Serum sodium level, mmol/L
        cGlu: Serum glucose level, mmol/L
        verbose: Return all possible text if True
    """
    Na_target = 140  # mmol/L just mean value, from Маневич и Плохой

    # Na decrease not faster than 0.5-1 mmol/L/h for hypernatremia (cerebral edema risk)
    # Na increase not faster than 1-2 mmol/L/h for hyponatremia (central pontine myelinolysis risk)
    Na_shift_rate = 0.5  # mmol/L/h. May be set to 1 in future

    # Коэффициенты разные для восполнения дефицита Na, K?
    coef = 0.6  # for adult, non-elderly males (**default for hyponatremia**);
    # coef = 0.5  # for adult elderly males, malnourished males, or females;
    # coef = 0.45  # for adult elderly or malnourished females.
    total_body_water = weight * coef  # Liters

    info = ""
    desc = f"{Na_serum:.0f} ({norm_Na[0]:.0f}-{norm_Na[1]:.0f} mmol/L)"
    if Na_serum > norm_Na[1]:
        info += (
            f"Na⁺ is high {desc}, check osmolarity. Give enteral water if possible. "
        )
        info += f"Warning: Na⁺ decrement faster than {Na_shift_rate:.1f} mmol/L/h can cause cerebral edema.\n"
        if verbose:
            info += "Classic replacement calculation:\n" + electrolyte_Na_classic(
                total_body_water,
                Na_serum,
                Na_target=Na_target,
                Na_shift_rate=Na_shift_rate,
            )
        info += "Adrogue replacement calculation:\n" + electrolyte_Na_adrogue(
            total_body_water,
            Na_serum,
            Na_target=Na_target,
            Na_shift_rate=Na_shift_rate,
        )
    elif Na_serum < norm_Na[0]:
        info += f"Na⁺ is low {desc}, expect cerebral edema leading to seizures, coma and death. "
        info += f"Warning: Na⁺ replacement faster than {Na_shift_rate:.1f} mmol/L/h can cause osmotic central pontine myelinolysis.\n"
        # N.B.! Hypervolemic patient has low Na because of diluted plasma,
        # so it needs furosemide, not extra Na administration.
        if verbose:
            info += "Classic replacement calculation: " + electrolyte_Na_classic(
                total_body_water,
                Na_serum,
                Na_target=Na_target,
                Na_shift_rate=Na_shift_rate,
            )
        info += "Adrogue replacement calculation:\n" + electrolyte_Na_adrogue(
            total_body_water,
            Na_serum,
            Na_target=Na_target,
            Na_shift_rate=Na_shift_rate,
        )
    else:
        info += f"Na⁺ is ok {desc}"

    # Should corrected Na be used instead of Na_serum for replacement calculation?
    Na_corr = correct_Na_hyperosmolar(Na_serum, cGlu)
    if abs(Na_corr - Na_serum) > 5:  # Arbitrary threshold
        info += f"\nHigh cGlu causes high osmolarity and apparent hyponatremia. Corrected Na⁺ is {Na_corr:.0f} mmol/L."
    return info


def correct_Na_hyperosmolar(cNa, cGlu):
    """Sodium correction for high osmolarity (hyperglycemia).

    Elevated glucose (or mannitol) raise plasma tonicity which draws
    water from the intracellular compartment diluting plasma sodium and
    causing pseudohyponatremia.

    Other osmotic active molecules: mannitol, glycerol.

    Theoretically there is no difference between osmotic particles,
    e.g. glucose and mannitol, so formula could be transformed to work
    with arbitrary particles, trough chemical amount of substance,
    but anyway we can measure only glucose concentration.

    References
    ----------
    https://emedicine.medscape.com/article/767624-workup
    https://www.mdcalc.com/sodium-correction-hyperglycemia#evidence

    https://www.ncbi.nlm.nih.gov/pubmed/4763428
        Corrected Sodium (Katz, 1973) = Measured sodium + 0.016 * (Serum glucose - 100)
        Underestimates Na derease in comparison to [Hillier, 1999].

    https://www.ncbi.nlm.nih.gov/pubmed/10225241
        Corrected Sodium (Hillier, 1999) = Measured sodium + 0.024 * (Serum glucose - 100)

    Diagnosis and treatment of diabetic ketoacidosis and the hyperglycemic hyperosmolar state
        * Psychopathology and necessity of Na correction explained
        https://www.ncbi.nlm.nih.gov/pmc/articles/PMC151994/

    Examples
    --------
    # >>> correct_Na_hyperosmolar(126, 33.3)  # Katz, 1973
    # 133.9904
    >>> correct_Na_hyperosmolar(126, 33.3)  # Hillier, 1999
    137.9856

    :param float cNa: Na, mmol/L
    :param float cGlu: cGlu, mmol/L
    :return: Corrected cNa concentration, mmol/L
    :rtype: float
    """
    cGlu_mgdl = cGlu * M_C6H12O6 / 10
    # Na_shift = (cGlu_mgdl - 100) / 100 * 1.6  # Katz, 1973
    Na_shift = (cGlu_mgdl - 100) / 100 * 2.4  # Hillier, 1999
    return cNa + Na_shift


def volume_deficit_hct(weight, hct, hct_target=0.4):
    """Estimate intravascular volume deficit by hematocrit (hct).

    Use if Hct reliable: no bleeding or blood diseases, polycythemia etc.

    Na and water
    ------------
    1. Потеря чистой выоды через лёгкие и при потоотделении (лихорадка)
        Жажда появляется при дефиците воды массой 2 % от RBW, осмолярности >290 mOsm/kg. Концентрированная моча, высокий Hct
        Вводить D50 до снижения осмоляльности до 290 мосм/кг, снижения Na до 140 mmol/L.
    2. Потеря внеклеточной жидкости (кишечная непроходимость - 3-е пространство, рвота, понос)
        * Рвота - метаболический алкозоз, восполнять Cl- физраствором
        * Понос - метаболический алкалоз? восполнять NaHCO3, NaCL, KCl?

    References
    ----------
    [1] Рябов 1994, с 36
    [2] Маневич, Плохой, с 113
    [3] https://en.wikipedia.org/wiki/Hematocrit

    Examples
    --------
    >>> volume_deficit_hct(70, 0.55)  # 79 kg, hct 0.55
    3818.181818181818

    :param float weight: Real body weight, kg
    :param float hct: Hematocrit fraction, e.g 0.5
    :param float hct_target: Target hematocrit fraction, default 0.4
        for simplicity. May be 0.407–0.503 for men and 0.361-0.443 for women.
    :return: Volume deficiency, ml
    :rtype: float
    """
    # 40 % - mean hematocrit for adult women and men
    return (1 - hct_target / hct) * 0.2 * weight * 1000


def electrolyte_Cl(Cl_serum):
    """Assess blood serum chloride level.

    :param float Cl_serum: mmol/L
    """
    info = ""
    Cl_low, Cl_high = norm_Cl[0], norm_Cl[1]
    if Cl_serum > Cl_high:
        info += f"Cl⁻ is high (>{Cl_high} mmol/L), excessive NaCl infusion or dehydration (check osmolarity)."
    elif Cl_serum < Cl_low:
        # KCl replacement?
        info += f"Cl⁻ is low (<{Cl_low} mmol/L). Vomiting? Diuretics abuse?"
    else:
        info += f"Cl⁻ is ok ({norm_Cl[0]:.0f}-{norm_Cl[1]:.0f} mmol/L)"
    return info


def egfr_mdrd(sex, cCrea, age, black_skin=False):
    """Estimated glomerular filtration rate (MDRD 2005 revised study equation).

    For patients >18 years, can't be used for acute renal failure.


    References
    ----------
    [1] Radiometer ABL800 Flex Reference Manual English US.
        chapter 6-43, p. 279, equations 53, 54.
    [2] https://www.kidney.org/sites/default/files/docs/12-10-4004_abe_faqs_aboutgfrrev1b_singleb.pdf
    24. U.S Department of Health and Human Services, National Institutes of Health, National Institute of Diabetes and Digestive and Kidney Diseases: NKDEP National Kidney Disease Education Program. Rationale for Use and Reporting of Estimated GFR. NIH Publication No. 04-5509. Revised November 2005.
    25. Myers GL, Miller WG, Coresh J, Fleming J, Greenberg N, Greene T, Hostetter T, Levey AS, Panteghini M, Welch M, and Eckfeldt JH for the National Kidney Disease Education Program Laboratory Working Group. Clin Chem, 52:5-18, 2006; First published December 6, 2005, 10.1373/clinchem.2005.0525144.


    Examples
    --------
    >>> egfr_mdrd(human.HumanSex.male, 74.4, 27)
    109.36590492087734
    >>> egfr_mdrd(human.HumanSex.female, 100, 80, True)
    55.98942027449337

    :param human.HumanSex sex: Choose 'male', 'female'.
    :param float cCrea: Serum creatinine (IDMS-calibrated), μmol/L
    :param float age: Human age, years
    :param bool black_skin: True for people with black skin (african american)
    :return: eGFR, mL/min/1.73 m2
    :rtype: float
    """
    # Original equation from 1999 (non IDMS)
    # egfr = 186 * (cCrea / m_Crea) ** -1.154 * age ** -0.203

    # Revised equation from 2005, to accommodate for standardization of
    # creatinine assays over isotope dilution mass spectrometry (IDMS) SRM 967.
    # Equation being used by Radiometer devices
    egfr = 175 * (cCrea / M_Crea) ** -1.154 * age**-0.203
    if sex == human.HumanSex.female:
        egfr *= 0.742
    elif sex == human.HumanSex.child:
        raise ValueError("MDRD eGFR for children not supported")
    if black_skin:
        egfr *= 1.210
    return egfr


def egfr_ckd_epi(sex, cCrea, age, black_skin=False):
    """Estimated glomerular filtration rate (CKD-EPI 2009 formula).

    For patients >18 years. Appears as more accurate than MDRD, especially
    when actual GFR is greater than 60 mL/min per 1.73 m2.
    Cahexy, limb amputation will reduce creatinine production, so eGFR
    will look better than it is.

    References
    ----------
    [1] A new equation to estimate glomerular filtration rate. Ann Intern Med. 2009;150(9):604-12.
    [2] https://en.wikipedia.org/wiki/Renal_function#Glomerular_filtration_rate

    :param human.HumanSex sex: Choose 'male', 'female'.
    :param float cCrea: Serum creatinine (IDMS-calibrated), μmol/L
    :param float age: Human age, years
    :param bool black_skin: True for people with black skin (african american)
    :return: eGFR, mL/min/1.73 m2
    :rtype: float
    """
    cCrea /= M_Crea  # to mg/dl
    if sex == human.HumanSex.male:
        if cCrea <= 0.9:
            egfr = 141 * (cCrea / 0.9) ** -0.411 * 0.993**age
        else:
            egfr = 141 * (cCrea / 0.9) ** -1.209 * 0.993**age
    elif sex == human.HumanSex.female:
        if cCrea <= 0.7:
            egfr = 141 * (cCrea / 0.7) ** -0.329 * 0.993**age * 1.018
        else:
            egfr = 141 * (cCrea / 0.7) ** -1.209 * 0.993**age * 1.018
    elif sex == human.HumanSex.child:
        raise ValueError("CKD-EPI eGFR for children not supported")

    if black_skin:
        egfr *= 1.159
    return egfr


def egfr_schwartz(cCrea, height):
    """Estimated glomerular filtration rate (revised Schwartz formula for children).

    * Not for adults.
    * Revised Schwartz formula with fixed 'k = 0.413' for 1-16 years and
        IDMS-calibrated creatinine.
    * Most accurate in range 15-75 ml/min per 1.73 m2.

    Example
    -------
    >>> egfr_schwartz(40, 1.15)
    104.96395

    References
    ----------
    [1] New Equations to Estimate GFR in Children with CKD. J Am Soc Nephrol. 2009 Mar; 20(3): 629–637.
        https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2653687/

    [2] Creatinine Clearance: Revised Schwartz Estimate
        http://www-users.med.cornell.edu/~spon/picu/calc/crclsch2.htm

    :param float cCrea: Serum creatinine (IDMS-calibrated), μmol/L
    :param float height: Children height, meters
    :return: eGFR, mL/min/1.73 m2.
    :rtype: float
    """
    cCrea /= M_Crea  # to mg/dl
    # k = 0.33  # First year of life, pre-term infants
    # k = 0.45  # First year of life, full-term infants
    # k = 0.55  # 1-12 years
    k = 0.413  # 1 to 16 years. Updated in 2009
    return k * height * 100 / cCrea


def gfr_describe(gfr):
    """Describe GFR value meaning and stage of Chronic Kidney Disease."""
    if 90 <= gfr:
        return "Normal kidney function if no proteinuria, otherwise CKD1 (90-100 %)"
    elif 60 <= gfr < 90:
        return "CKD2 kidney damage with mild loss of kidney function (89-60 %). For most patients, a GFR over 60 mL/min/1.73 m2 is adequate"
    elif 45 <= gfr < 60:
        return "CKD3a, mild to moderate loss of kidney function (59-45 %). Evaluate progression"
    elif 30 <= gfr < 45:
        return "CKD3b, moderate to severe loss of kidney function (44-30 %). Evaluate progression"
    elif 15 <= gfr < 30:
        return (
            "CKD4, severe loss of kidney function (29-15 %). Be prepared for dialysis"
        )
    else:
        return "CKD5, kidney failure (<15 %). Needs dialysis or kidney transplant"


def insulin_by_glucose(cGlu):
    """Monoinsulin subcutaneous dose for a given serum glycemia level.

    Insulin sesnitivity at morning lower, then at evening.

    References
    ----------
    [1] Oleskevitch uses target 5 mmol/L: `(cGlu - 5) * 2`
    [2] Lipman, T. Let's abandon urine fractionals in TPN. Nutrition Support Services. 4:38-40, 1984.

    :param float cGlu: Serum glucose mmol/L
    :return: Insulin dose in IU. Returns zero if cGlu < 10 or cGlu > 25.
    :rtype: float
    """
    # cGlu mg/dl * 0.0555 = mmol/L
    # 0.55 = (100 / daily_iu) may be considered as sensetivity to ins
    target = 7  # Tagget glycemia, mmol/L
    if cGlu < 10 or 25 < cGlu:
        return 0
    else:
        return (cGlu - target) / 0.55
