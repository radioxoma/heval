# -*- coding: utf-8 -*-
"""
Arterial blood gas interpreter.

Eugene Dvoretsky, 2015-05-20

$ md5sum *
41f8e7d98fcc26ea2319ac8da72ed8cd ABL800 Reference Manual English US.pdf
a00e5f337bd2c65e513fda1202827c6a ABL800 Operators Manual English US.pdf

Main statements:
    * This code may be considered as reference realization of multiple
      interconnected compatible algorithms.
    * You need deep theoretical background to understand this code,
        ABG is hard and functions' docs couldn't be self-explaining
    * Use International System of Units (m, kPa, mmol/L)
    * No algebraic optimizations reducing readability
    * Entities should not be multiplied without necessity
        * Use simple and validated formula. REPRODUCIBILITY IS CRUCIAL
        * Don't use formula improvements and sophistications from single
            authors: it may be a solution for their systematic error
    * All voodoo calculations shell be outside class and documented
    * Heuristic can be anywhere - it complicated anyway.
        At least class can gather all parameters in one place.

Main pitfalls:
  * Multiple "slightly" different formulas for the same parameter
    * E.g. AG must be calculated without potassium to use it's value in
      Delta Gap calculation. Also specific reference 7-16 mEq/L shall be used.

  * Authors are humans and mix formulas, coefficients and reference ranges
    * Constants vary from one source to another
      * Mean cAlb, K_target or Na_target changes without notice and rationale
    * Reference range for the same parameter varies
      * Though it's normal for different human populations
    * Reference range for the same parameter depends on calculation formula
      * Plenty of messed up "formula-reference range" pairs
    * Authors cite each other, but not the initial paper
      * Hard to trace original article with complete description

    * Featured formula may not work at all. Author got PhD - job-is-done (#жобиздан).

Main approach:
0. Read this https://web.archive.org/web/20170711053144/http://fitsweb.uchc.edu/student/selectives/TimurGraham/Stepwise_approach.html
1. Describe ABG with `abg_approach_stable(pH, pCO2)`
2. Calculate HCO3act, BE
3. *Always* calculate and check anion gap, even if no primary metabolic acidosis
    * You must use AG without potassium, as Anion Gap (K+) is incompatible
        with Delta gap. Also K is tricky to measure.
    * Use albumin correction if AG is low
    * If AG is high, calculate Delta gap
"""

import textwrap
from itertools import chain
try:
    from uncertainties import umath as math
except ImportError:
    import math
from heval import electrolytes


# Units conversion
kPa = 0.133322368  # kPa to mmHg, 1 mmHg = 0.133322368 kPa
m_Crea = 88.40  # cCrea (μmol/L) = 88.40 * cCrea (mg/dL)


# Reference blood test ranges
norm_pH = (7.35, 7.45)
norm_pH_mean = 7.40
norm_pH_alive = (6.8, 7.8)  # Live borders
norm_sbe = (-2, 2)  # mEq/L

norm_pCO2 = (4.666, 6)  # kPa
# norm_pCO2mmHg = (35, 45)
norm_pCO2mmHg_mean = 40.0  # mmHg

norm_HCO3 = (22, 26)  # mEq/L
norm_pO2 = (80, 100)  # mmHg

# NB! Changing 'norm_gap' will affect Gap-Gap calculation
norm_gap = (7, 16)  # mEq/L without potassium [Курек 2013, с 47],

# Minimal low value has been chosen (<280), as I believe it
# corresponds to mOsm reference range without BUN
norm_mOsm = (275, 295)  # mOsm/kg  https://en.wikipedia.org/wiki/Reference_ranges_for_blood_tests

# Mean fasting glucose level https://en.wikipedia.org/wiki/Blood_sugar_level
# Used as initial value for mOsm calculation.
norm_cGlu_mean = 5.5  # mmol/L
norm_cGlu = (4.1, 6.1)  # mmol/L < 6.1 is perfect for septic patients
norm_cGlu_target = (4.5, 10)  # ICU target range. 10 mmol/L stands for glucose renal threshold
# Note: gap between lower norm_cGlu and norm_cGlu_target

# Mean albumin level. Used to normalize anion gap value in low cAlb case
# See Anion Gap calculation for reference
norm_ctAlb_mean = 4.4  # g/dL
norm_ctAlb = (3.5, 5)  # g/dL


class HumanBloodModel(object):
    """Represents an human blood ABG status."""

    def __init__(self, parent=None):
        self.parent = parent
        self._int_prop = ('pH', 'pCO2', 'cK', 'cNa', 'cCl', 'cGlu', 'ctAlb')
        self._txt_prop = ()

        self.pH = None
        self.pCO2 = None        # kPa

        self.cK = None          # mmol/L
        self.cNa = None         # mmol/L
        self.cCl = None         # mmol/L

        self.ctAlb = None       # g/dL albumin
        self.cGlu = None        # mmol/L
        # self.ctBun = None  # May be for osmolarity in future

    def __str__(self):
        int_prop = {}
        for attr in chain(self._int_prop, self._txt_prop):
            int_prop[attr] = getattr(self, attr)
        return "HumanBlood: {}".format(str(int_prop))

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
        return calculate_cbase(self.pH, self.pCO2)

    @property
    def hco3p(self):
        return calculate_hco3p(self.pH, self.pCO2)

    @property
    def anion_gapk(self):
        """Anion gap (K+), usually not used."""
        if self.cK is not None:
            return calculate_anion_gap(
                Na=self.cNa, Cl=self.cCl, HCO3act=self.hco3p,
                K=self.cK, albumin=self.ctAlb)
        else:
            raise ValueError("No potassium specified")

    @property
    def anion_gap(self):
        """Calculate anion gap without potassium. Preferred method."""
        return calculate_anion_gap(
            Na=self.cNa, Cl=self.cCl, HCO3act=self.hco3p,
            albumin=self.ctAlb)

    @property
    def sid_abbr(self):
        """Strong ion difference.

        Strong ion gap (SIG).

        * increased SID (>0) leads to alkalosis
            dehydration: concentrates the alkalinity
            increased unmeasured anions
        * decreased SID (<0) acidosis
            overhydration dilutes the alkaline state (dilutional acidosis) and decreases SID
            increased unmeasured cations

        apparent SID = SIDa = (Na+ + K+ + Ca2+ + Mg2+) – (Cl– – L-lactate – urate)
        Abbreviated SID = (Na+) – (Cl–)

        Normal difference:
            38 = 140     - 102
            42 = 140 + 4 - 102  # Potassium

        If SBE is normal but patient is acidotic must all be from CO2
        If SBE is abnormal must explain by SID, weak acids, or unmeasured strong ions

        References
        ----------
        [1] https://litfl.com/strong-ion-difference/
        [2] https://wikem.org/wiki/Acid-base_disorders
        """
        sid = self.cNa - self.cCl - 38
        if self.ctAlb:
            sid += 2.5 * (norm_ctAlb_mean - self.ctAlb)
        return sid

    @property
    def osmolarity(self):
        return calculate_osmolarity(self.cNa, self.cGlu)

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
        info += " {:.0f} ({:.0f}-{:.0f} mOsm/L)".format(self.osmolarity, norm_mOsm[0], norm_mOsm[1])

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
        info = textwrap.dedent("""\
        pCO2    {:2.1f} kPa
        HCO3(P) {:2.1f} mmol/L
        Conclusion: {}\n""".format(
            self.pCO2,
            self.hco3p,
            abg_approach_stable(self.pH, self.pCO2)[0]))
        if self.parent.debug:
            info += "\n-- Manual compensatory response check --------------\n"
            # info += "Abg Ryabov:\n{}\n".format(textwrap.indent(abg_approach_ryabov(self.pH, self.pCO2), '  '))
            info += "{}".format(abg_approach_research(self.pH, self.pCO2))
        return info

    def describe_anion_gap(self):
        info = "-- Anion gap ---------------------------------------\n"
        desc = "{:.1f} ({:.0f}-{:.0f} mEq/L)".format(self.anion_gap, *norm_gap)
        if abg_approach_stable(self.pH, self.pCO2)[1] == "metabolic_acidosis":
            if norm_gap[1] < self.anion_gap:
                # Since AG elevated, calculate delta ratio to test for coexistent NAGMA or metabolic alcalosis
                info += "HAGMA {} (KULT?), ".format(desc)
                info += "{}".format(calculate_anion_gap_delta(self.anion_gap, self.hco3p))
            elif self.anion_gap < norm_gap[0]:
                info += "Low AG {} - hypoalbuminemia or low Na?".format(desc)
            else:
                # Hypocorticism [Henessy 2018, с 113 (Clinical case 23)]
                info += "NAGMA {}. Diarrhea or renal tubular acidosis?".format(desc)
        else:
            if norm_gap[1] < self.anion_gap:
                info += "Unexpected high AG {} without main metabolic acidosis; ".format(desc)
                # Can catch COPD or concurrent metabolic alcalosis here
                info += "{}".format(calculate_anion_gap_delta(self.anion_gap, self.hco3p))
            elif self.anion_gap < norm_gap[0]:
                info += "Unexpected low AG {}. Starved patient with low albumin? Check your input and enter ctAlb if known.".format(desc)
            else:
                info += "AG is ok {}".format(desc)

        if self.parent.debug:
            """Strong ion difference.

            Sometimes Na and Cl don't changes simultaneously.
            Try distinguish Na-Cl balance in case high/low osmolarity.
            Should help to choose better fluid for correction.
            """
            SIDabbr_norm = (-5, 5)  # Arbitrary threshold
            ref_str = "{:.1f} ({:.0f}-{:.0f} mEq/L)".format(self.sid_abbr, SIDabbr_norm[0], SIDabbr_norm[1])
            info += "\nSIDabbr [Na⁺-Cl⁻-38] "
            if self.sid_abbr > SIDabbr_norm[1]:
                info += "is alcalotic {}, relative Na⁺ excess".format(ref_str)
            elif self.sid_abbr < SIDabbr_norm[0]:
                info += "is acidotic {}, relative Cl⁻ excess".format(ref_str)
            else:
                info += "is ok {}".format(ref_str)
            info += ", BDE gap {:.01f} mEq/L".format(self.sbe - self.sid_abbr)  # Lactate?
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
            # FIXME: can be high if cloride is low. Calculate SID?
            # https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2856150
            # https://en.wikipedia.org/wiki/Contraction_alkalosis
            # Acetazolamide https://en.wikipedia.org/wiki/Carbonic_anhydrase_inhibitor
            info += "SBE is high {:.1f} ({:.0f}-{:.0f} mEq/L). Check Cl⁻. Hypoalbuminemia? NaHCO₃ overdose?".format(self.sbe, norm_sbe[0], norm_sbe[1])
        elif self.sbe < norm_sbe[0]:
            if self.sbe <= NaHCO3_threshold:
                info += "SBE is drastically low {:.1f} ({:.0f}-{:.0f} mEq/L), consider NaHCO₃ in AKI patients to reach target pH 7.3:\n".format(self.sbe, norm_sbe[0], norm_sbe[1])
                info += "  * Fast ACLS tip (all ages): load dose 1 mmol/kg, then 0.5 mmol/kg every 10 min [Курек 2013, 273]\n"
                # info += "NaHCO3 {:.0f} mmol during 30-60 minutes\n".format(0.5 * (24 - self.hco3p) * self.parent.weight)  # Doesn't looks accurate, won't use it [Курек 2013, с 47]
                NaHCO3_mmol = -0.3 * self.sbe * self.parent.weight  # mmol/L
                NaHCO3_mmol_24h = self.parent.weight * 5  # mmol/L
                NaHCO3_g = NaHCO3_mmol / 1000 * electrolytes.M_NaHCO3  # gram
                NaHCO3_g_24h = NaHCO3_mmol_24h / 1000 * electrolytes.M_NaHCO3
                info += "  * NaHCO₃ {:.0f} mmol (-0.3*SBE/kg) during 30-60 min, daily dose {:.0f} mmol/24h (5 mmol/kg/24h):\n".format(NaHCO3_mmol, NaHCO3_mmol_24h)  # Курек 273, Рябов 73 for children and adult
                # info += "  * NaHCO₃ {:.0f} mmol (-(SBE - 8)/kg/4)\n".format(
                #     -(self.sbe - 8) * self.parent.weight / 4, NaHCO3_mmol_24h)  # Плохой 152
                for dilution in (4, 8.4):
                    NaHCO3_ml = NaHCO3_g / dilution * 100
                    NaHCO3_ml_24h = NaHCO3_g_24h / dilution * 100
                    info += "    * NaHCO3 {:.1f}% {:.0f} ml, daily dose {:.0f} ml/24h\n".format(dilution, NaHCO3_ml, NaHCO3_ml_24h)
                if self.parent.debug:
                    info += textwrap.dedent("""\
                        Confirmed NaHCO₃ use cases:
                          * Metabolic acidosis correction leads to decreased 28 day mortality only in AKI patients (target pH 7.3) [BICAR-ICU 2018]
                          * TCA poisoning with prolonged QT interval (target pH 7.45-7.55 [Костюченко 204])
                          * In hyperkalemia (when pH increases, K⁺ level decreases)
                        Main concepts of usage:
                          * Must hyperventilate to make use of bicarbonate buffer
                          * Control ABG after each NaHCO₃ infusion or every 4 hours
                          * Target urine pH 8, serum 7.34 [ПосДеж, с 379]""")
            else:
                info += "SBE is low {:.1f} ({:.0f}-{:.0f} mEq/L), but NaHCO₃ won't improve outcome when BE > {:.0f} mEq/L".format(self.sbe, norm_sbe[0], norm_sbe[1], NaHCO3_threshold)
        else:
            info += "SBE is ok {:.1f} ({:.0f}-{:.0f} mEq/L)".format(self.sbe, norm_sbe[0], norm_sbe[1])
        return info

    def describe_electrolytes(self):
        info = "- Electrolyte and osmolar abnormalities ------------\n"
        info += "{}\n\n".format(self.describe_osmolarity())
        info += "{}\n\n".format(electrolytes.electrolyte_K(self.parent.weight, self.cK))
        info += "{}\n\n".format(electrolytes.electrolyte_Na(self.parent.weight, self.cNa, self.cGlu, self.parent.debug))
        info += "{}\n".format(electrolytes.electrolyte_Cl(self.cCl))
        return info

    def describe_glucose(self):
        """Assess glucose level.

        https://en.wikipedia.org/wiki/Renal_threshold
        https://en.wikipedia.org/wiki/Glycosuria
        """
        info = ""
        if self.cGlu > norm_cGlu[1]:
            if self.cGlu <= norm_cGlu_target[1]:
                info += "cGlu is above ideal {:.1f} (target {:.1f}-{:.1f} mmol/L), but acceptable".format(self.cGlu, norm_cGlu_target[0], norm_cGlu_target[1])
            else:
                info += "Hyperglycemia {:.1f} (target {:.1f}-{:.1f} mmol/L) causes glycosuria with osmotic diuresis".format(self.cGlu, norm_cGlu_target[0], norm_cGlu_target[1])
                if self.cGlu <= 20:  # Arbitrary threshold
                    info += ", consider insulin {:.0f} IU subcut for adult".format(insulin_by_glucose(self.cGlu))
                else:
                    info += ", refer to DKE/HHS protocol (HAGMA and urine ketone), start fluid and I/V insulin {:.1f} IU/h (0.1 IU/kg/h)".format(self.parent.weight * 0.1)

        elif self.cGlu < norm_cGlu[0]:
            if self.cGlu > 3:  # Hypoglycemia <3.3 mmol/L for pregnant?
                info += "cGlu is below ideal {:.1f} (target {:.1f}-{:.1f} mmol/L), repeat blood work, don't miss hypoglycemic state".format(self.cGlu, norm_cGlu_target[0], norm_cGlu_target[1])
            else:
                info += "Severe hypoglycemia, IMMEDIATELY INJECT BOLUS GLUCOSE 10 % 2.5 mL/kg:\n"
                # https://litfl.com/glucose/
                # For all ages: dextrose 10% bolus 2.5 mL/kg (0.25 g/kg) [mistake Курек, с 302]
                info += electrolytes.solution_glucose(0.25 * self.parent.weight, self.parent.weight, add_insuline=False)
                info += "Check cGlu after 20 min, repeat bolus and use continuous infusion, if refractory"

        else:
            info += "cGlu is ok {:.1f} ({:.1f}-{:.1f} mmol/L)".format(self.cGlu, norm_cGlu[0], norm_cGlu[1])
        return info

    def describe_albumin(self):
        """Albumin as nutrition marker in adults."""
        ctalb_range = "{} ({}-{} g/dL)".format(self.ctAlb, norm_ctAlb[0], norm_ctAlb[1])
        if norm_ctAlb[1] < self.ctAlb:
            info = "ctAlb is high {}. Dehydration?".format(ctalb_range)
        elif norm_ctAlb[0] <= self.ctAlb <= norm_ctAlb[1]:
            info = "ctAlb is ok {}".format(ctalb_range)
        elif 3 <= self.ctAlb < norm_ctAlb[0]:
            info = "ctAlb is low: light hypoalbuminemia {}".format(ctalb_range)
        elif 2.5 <= self.ctAlb < 3:
            info = "ctAlb is low: medium hypoalbuminemia {}".format(ctalb_range)
        elif self.ctAlb < 2.5:
            info = "ctAlb is low: severe hypoalbuminemia {}. Expect oncotic edema".format(ctalb_range)
        return info


def calculate_anion_gap(Na, Cl, HCO3act, K=0, albumin=norm_ctAlb_mean):
    """Calculate serum 'Anion gap' or 'Anion gap (K+)' if potassium is given.

    May be known as AG. Don't get confused with 'osmol gap'. Usually used
    without potassium.
        * Normal value without potassium 7-16 mEq/L [Курек 2013, с 47]
        * Normal value with potassium 10-20 mEq/L [Курек 2013, с 47]

    Corresponds to phosphates, sulphates, proteins (albumin).
    Helpful in distinguishing causes of metabolic acidosis like KULT:
        K — Ketoacidosis (DKA, Alcoholic ketoacidosis, AKA)
        U — Uremia
        L — Lactic acidosis
        T — Toxins (Ethylene glycol, methanol, as well as drugs, such as aspirin, Metformin)

    High gap
    --------
    Acute kidney injury, lactate, ketoacidosis, salicylate ->
        secondary loss of HCO3− which is a buffer, without a concurrent
        increase in Cl− for electroneutrality equilibrium support.

    Low gap
    -------
    increase in Cl−, low albumin.

    Anion gap is surprisingly low in starved patients because of low albumin.
    Multiplier 2.5 mEq/L is widely accepted, though blood pH
         has influence on albumin charge and respectively AG
        pH 7.0 2.3 mEq/L
        pH 7.4 2.8 mEq/L
        pH 7.6 3.0 mEq/L

    Normal (target) albumin value varies 4-4.5 g/dl among papers and books:
        * Radiometer states nothing
        * 4.0 g/dl https://litfl.com/anion-gap/ https://www.mdcalc.com/anion-gap
        * 4.4 g/dl https://en.wikipedia.org/wiki/Anion_gap


    See also Delta Ratio - an derived calculation to asses acidosis cause and
    mixed disturbances.

    References
    ----------
    [1] https://en.wikipedia.org/wiki/Anion_gap
    [2] Patrick J Neligan MA MB FCARCSI, Clifford S Deutschman MS MD FCCM
        Acid base balance in critical care medicine
    [4] Hypoalbuminemia correction: Anion gap and hypoalbuminemia Figge 1998 10.1097/00003246-199811000-00019 https://journals.lww.com/ccmjournal/Citation/2000/05000/Reliability_of_the_Anion_Gap.101.aspx

    Examples
    --------
    Typical usage, potassium usually not included:
    >>> calculate_anion_gap(Na=140, Cl=102, HCO3act=24)
    14.0

    With albumin:
    >>> calculate_anion_gap(Na=137, Cl=108, HCO3act=calculate_hco3p(pH=7.499, pCO2=4.77294), K=0, albumin=3.39)
    3.9175115055719747

    To reproduce 'Radiometer ABL800 Flex' Anion gap calculation:
    >>> calculate_anion_gap(173, 77, calculate_hco3p(pH=6.656, pCO2=3.71))
    93.07578958435911

    :param float Na: Serum sodium, mmol/L.
    :param float Cl: Serum chloride, mmol/L.
    :param float HCO3act: Serum actual bicarbonate (HCO3(P)), mmol/L.
    :param float K: Serum potassium, mmol/L.
        If not given returns AG, otherwise AG(K). Serum potassium value
        usually low and frequently omitted. Usually not used.
    :param float albumin: Protein correction, g/dL. If not given,
        hypoalbuminemia leads to lower anion gap.
    :return: Anion gap or Anion gap (K+), mEq/L.
    :rtype: float
    """
    anion_gap = (Na + K) - (Cl + HCO3act)
    anion_gap += 2.5 * (norm_ctAlb_mean - albumin)
    return anion_gap


def calculate_anion_gap_delta(AG, HCO3act):
    """Delta gap, delta ratio, gap-gap to assess elevated anion gap metabolic acidosis.

    Formula "gg = (AG - 12) / (24 - HCO3act)" reveals combinations of
    concurrent metabolic processes:

    < 1 HAGMA + NAGMA
        Sometimes it can be causes chronic respiratory alkalosis (with
        compensating non-anion gap acidosis), or a low anion gap
        (hypoalbuminemia) state

    ~ 1 HAGMA pure
        AG and BE shifts are equal - acidosis caused by non-measured anion.
        Increase in the AG should be equal to the decrease in bicarbonate:

        AG = [Na+] - [Cl-] - [HCO3-]  # Increase by low [Cl-] or low [HCO3-]
        HA + [HCO3-] = [A-] + H2O + CO2↑

        If a wide-anion-gap metabolic acidosis is the only disturbance, then the
        change in value of the anion gap should equal the change in bicarbonate (ie) ↑ AG = ↓ HCO3-
        The delta gap = increase AG - decrease HCO3-
        For purposes of calculation take normal AG as 12 and normal HCO3- as 24
        Shortcut calculation: Δ AG - Δ HCO3- = (AG -12) - (24 - HCO3-) = Na+ - Cl- - 36

    > 1 HAGMA + concurrent metabolic alcalosis
        Other causes are chronic respiratory acidosis (with compensating
        metabolic alkalosis), or a non-acidotic high anion gap state


    References
    ----------
    [1] Kostuchenko S.S., ABB in the ICU, 2009, p. 63
    [2] https://en.wikipedia.org/wiki/Delta_Ratio
    [3] http://webcache.googleusercontent.com/search?q=cache:LVnXtJaMahkJ:www.emed.ie/Toxicology/ABG_Blood_Gases.php
    [4] https://www.merckmanuals.com/medical-calculators/AnionGapDeltaGradient.htm

    :param float AG: Anion gap without potassium, mEq/L.
    :param float HCO3act: Actual bicarbonate, mmol/L.
    :return: Opinion.
    :rtype: str
    """
    # 12 - normal anion gap without potassium
    # 24 - normal HCO3-, mmol/L
    gg = (AG - 12) / (24 - HCO3act)
    info = ""
    # info += "Delta gap ({:.1f} - 12) / (24 - {:.1f}) = {:.1f}\n".format(AG, HCO3act, gg)
    info += "delta ratio {:.1f} ".format(gg)
    if gg < 0.4:
        # Usually due to mass transfusion of NaCl (dilution acidosis)
        # Normal gap because kidney excrete HCO3-
        return info + "(gg < 0.4): hyperchloremic normal anion gap metabolic acidosis (NAGMA)"
    elif 0.4 <= gg <= 0.8:
        # Consider combined high AG & normal AG acidosis BUT note that the
        # ratio is often < 1 in acidosis associated with renal failure
        # Renal tubular acidosis https://web.archive.org/web/20170802021754/http://fitsweb.uchc.edu/student/selectives/TimurGraham/Case_5.html
        return info + "(0.4 ≤ gg ≤ 0.8): combined HAGMA + NAGMA (gg ratio <1 often associated with renal failure - check urine electrolytes and kidney function)"
    elif 0.8 < gg < 1:
        return info + "(0.8 < gg < 1): most likely caused by diabetic ketoacidosis due to urine ketone bodies loss (when patient not dehydrated yet)"
    elif 1 <= gg <= 2:
        # Usual for uncomplicated high-AG acidosis - "pure metabolic acidosis"?
        # * lactic acidosis: average value 1.6
        # * DKA more likely to have a ratio closer to 1 due to urine ketone loss (especially if patient not dehydrated).
        # Absence of ketones in the urine can be seen in early DKA due to the
        # predominance of beta-hydroxybutyrate. The dipstick test for ketones
        # detect acetoacetate but not beta-hydroxybutyrate.
        # https://web.archive.org/web/20170831093311/http://fitsweb.uchc.edu/student/selectives/TimurGraham/Case_2.html
        return info + "(1 ≤ gg ≤ 2): classic high anion gap acidosis"
    elif 2 < gg:
        # Suggests a pre-existing elevated [HCO3-] level so consider:
        #   * a concurrent metabolic alcalosis
        #   * a pre-existing compensated respiratory acidosis
        # tiazide diuretics?
        return info + "(2 < gg): concurrent metabolic alcalosis or chronic respiratory acidosis with high HCO₃⁻"


def calculate_osmolarity(Na, glucosae):
    """Calculate serum osmotic concentration (osmolarity, mOsm/L).

    NB! This is not an osmolality (mOsm/kg), measured by an osmometer.


    References
    ----------
    [1] Radiometer ABL800 Flex Reference Manual English US.
        chapter 6-41, p. 277, equation 48.
    [2] https://en.wikipedia.org/wiki/Osmotic_concentration

    :param float Na: mmol/L
    :param float glucosae: mmol/L
    :return: Serum osmolarity, mmol/L (mOsm/L).
    :rtype: float
    """
    # Sometimes `2 * (Na + K) + Glucose + Urea` all in mmol/L
    # Also ethanol can cause https://en.wikipedia.org/wiki/Osmol_gap
    return 2 * Na + glucosae


def simple_hco3(pH, pCO2):
    """Calculate actual bicarbonate concentration in plasma.

    Also known as cHCO3(P), HCO3act.

    Generic approximation of Henderson-Hasselbalch equation.
    Good for water solutions, lower precision in lipemia cases.


    References
    ----------
    [1] http://www-users.med.cornell.edu/~spon/picu/calc/basecalc.htm

    :param float pH:
    :param float pCO2: kPa
    :return: cHCO3(P), mmol/L.
    :rtype: float
    """
    # 0.03 - CO2 solubility coefficient mmol/L/mmHg
    # 6.1 - dissociation constant for H2CO3
    return 0.03 * pCO2 / kPa * 10 ** (pH - 6.1)


def calculate_hco3p(pH, pCO2):
    """Calculate actual bicarbonate aka cHCO3(P) concentration in plasma.

    Also known as cHCO3(P), HCO3act [1].

    Sophisticated calculation by [1]. Good for water solutions,
    lower precision in lipemia cases.


    References
    ----------
    [1] Radiometer ABL800 Flex Reference Manual English US.
        chapter 6-28, p. 264, equation 4.
    [2] Siggaard-Andersen O, Wimberley PD, Fogh-Andersen N, Gøthgen IH.
        Measured and derived quantities with modern pH and blood gas equipment:
        calculation algorithms with 54 equations. Scand J Clin Lab Invest 1988;
        48, Suppl 189: 7-15. p. 11, equations 6, 7.

    :param float pH:
    :param float pCO2: kPa
    :return: cHCO3(P), mmol/L.
    :rtype: float
    """
    pKp = 6.125 - math.log10(1 + 10 ** (pH - 8.7))  # Dissociation constant
    # aCO2(P) solubility coefficient for 37 °C = 0.230 mmol/L/kPa
    return 0.230 * pCO2 * 10 ** (pH - pKp)


def calculate_hco3pst(pH, pCO2, ctHb, sO2):
    """Calculate standard bicarbonate aka cHCO3(P,st) concentration in plasma.

    Also known as cHCO3(P,st)) [1].

    Standard Bicarbonate, the concentration of HCO3- in the plasma
    from blood which is equilibrated with a gas mixture with
    pCO2 = 5.33 kPa (40 mmHg) and pO2 >= 13.33 kPa (100 mmHg) at 37 °C.
    (Normal pCO2 and pO2 level enough to saturate Hb.)


    References
    ----------
    [1] Radiometer ABL800 Flex Reference Manual English US.
        chapter 6-29, p. 265, equation 9.

    :param float pH:
    :param float pCO2: CO2 partial pressure, kPa
    :param float ctHb: Concentration of total hemoglobin in blood, mmol/L
    :param float sO2: Fraction of saturated hemoglobin, fraction.
    :return: cHCO3(P,st), mmol/L.
    :rtype: float
    """
    a = 4.04 * 10 ** -3 + 4.25 * 10 ** -4 * ctHb
    Z = calculate_cbase(pH, pCO2, ctHb=ctHb) - 0.3062 * ctHb * (1 - sO2)
    return 24.47 + 0.919 * Z + Z * a * (Z - 8)


def simple_be(pH, HCO3act):
    """Calculate base excess (BE), Siggaard Andersen approximation.

    Synonym for cBase(Ecf) and SBE?

    To reproduce original [1] calculations:
    simple_be(simple_hco3(pH, pCO2))


    References
    ----------
    [1] http://www-users.med.cornell.edu/~spon/picu/calc/basecalc.htm
    [2] http://www.acid-base.com/computing.php

    :param float pH:
    :param float HCO3act: mmol/L
    :return: Base excess, mEq/L.
    :rtype: float
    """
    return 0.9287 * HCO3act + 13.77 * pH - 124.58


def calculate_cbase(pH, pCO2, ctHb=3):
    """Calculate base excess.

    Calculate standard base excess, known as SBE, cBase(Ecf) or
    actual base excess, known as ABE, cBase(B) if ctHb is given.


    References
    ----------
    [1] Radiometer ABL800 Flex Reference Manual English US.
        chapter 6-29, p. 265, equation 5.

    [2] Siggaard-Andersen O. The acid-base status of the blood.
        4th revised ed. Copenhagen: Munksgaard, 1976.
        http://www.cabdirect.org/abstracts/19751427824.html

    :param float pH:
    :param float pCO2: kPa
    :param float ctHb: Concentration of total hemoglobin in blood, mmol/L
        If given, calculates ABE, if not - SBE.
    :return: Standard base excess (SBE) or actual base excess (ABE), mEq/L.
    :rtype: float
    """
    a = 4.04 * 10 ** -3 + 4.25 * 10 ** -4 * ctHb
    pHHb = 4.06 * 10 ** -2 * ctHb + 5.98 - 1.92 * 10 ** (-0.16169 * ctHb)
    log_pCO2Hb = -1.7674 * (10 ** -2) * ctHb + 3.4046 + 2.12 * 10 ** (
        -0.15158 * ctHb)
    pHst = pH + math.log10(5.33 / pCO2) * (
        (pHHb - pH) / (log_pCO2Hb - math.log10(7.5006 * pCO2)))
    cHCO3_533 = 0.23 * 5.33 * 10 ** ((pHst - 6.161) / 0.9524)
    # There is no comments, as there is no place for weak man
    cBase = 0.5 * ((8 * a - 0.919) / a) + 0.5 * math.sqrt(
        (((0.919 - 8 * a) / a) ** 2) - 4 * ((24.47 - cHCO3_533) / a))
    return cBase


def calculate_hct(ctHb):
    """Calculate hematocrit.

    The ratio between the volume of erythrocytes and the volume of whole blood.
    See [4] for interpretating caveats.


    References
    ----------
    [1] Radiometer ABL800 Flex Reference Manual English US.
        chapter 6-30, p. 266, equation 13.
    [2] http://www.derangedphysiology.com/php/Arterial-blood-gases/
        Haematocrit-is-a-derived-measurment-in-the-blood-gas-analyser.php
    [3] http://www.ncbi.nlm.nih.gov/pubmed/2128562
    [4] http://www.derangedphysiology.com/php/Arterial-blood-gases/
        Haematocrit-is-a-derived-measurment-in-the-blood-gas-analyser.php

    :param float ctHb: Concentration of total hemoglobin in blood, mmol/L.
    :return: Hematocrit, fraction (not %).
    :rtype: float
    """
    # ctHb(mmol/L) == ctHb(g/dL) / 1.61140 == ctHb(g/dL) * 0.62058
    # By [1] p. 6-14 or 6-49.
    return 0.0485 * ctHb + 8.3 * 10 ** -3


def calculate_pHT(pH, t):
    """Calculate pH of blood at patient body temperature.

    References
    ----------
    [1] Radiometer ABL800 Flex Reference Manual English US.
        chapter 6-28, p. 264, equation 1.

    Examples
    --------
    >>> calculate_pHT(6.919, 39.6)
    6.8891689
    >>> calculate_pHT(7.509, 38.6)
    7.4845064

    :param float pH:
    :param float t: Body temperature, °C.
    :return: pH of blood at given temperature.
    :rtype: float
    """
    # 37 °C is temperature of measurement in device
    return pH - (0.0146 + 0.0065 * (pH - 7.40)) * (t - 37)


def calculate_pCO2T(pCO2, t):
    """Partial pressure of CO2 in blood at patient temperature.

    References
    ----------
    [1] Radiometer ABL800 Flex Reference Manual English US.
        chapter 6-28, p. 264, equation 3.

    :param float pCO2: kPa
    :param float t: Body temperature, °C.
    :return:
        Partial pressure of CO2 at given temperature, kPa
    :rtype: float
    """
    return pCO2 * 10 ** (0.021 * (t - 37))


def calculate_ctO2(pO2, sO2, FCOHb, FMetHb, ctHb):
    """Total oxygen concentration of blood (O2 content).

    Also known as ctO2(B).


    References
    ----------
    [1] Radiometer ABL800 Flex Reference Manual English US.
        chapter 6-35, p. 271, equation 27.

    :param float pO2: kPa
    :param float sO2: fraction
    :param float FCOHb: fraction
    :param float FMetHb: fraction
    :param float ctHb: mmol/L
    :return: O2 content, mmol/L.
    :rtype: float
    """
    # May be negative FMetHb replased with zero?
    # if FMetHb < 0:
    #     FMetHb = 0

    # ctHb(mmol/L) == ctHb(g/dL) / 1.61140 == ctHb(g/dL) * 0.62058
    # Vol % == 2.241 (mmol/L)
    # By [1] p. 6-14 or 6-49.
    # O2 solubility coefficient in blood at 37 °C.
    alphaO2 = 9.83 * 10 ** -3  # mmol/L/kPa
    return alphaO2 * pO2 + sO2 * (1 - FCOHb - FMetHb) * ctHb


def calculate_pO2_FO2_fraction(pO2, FiO2):
    """pO2(a)/FO2(I) - the ratio of pO2 and fraction of inspired oxygen.

    Simplest calculation to diagnose ARDS. Known as:
        * PaO2/FiO2 ratio
        * p/f ratio

    [1] Radiometer ABL800 Flex Reference Manual English US.
        chapter 6-32, p. 268, equation 17.
    [2] https://en.wikipedia.org/wiki/Fraction_of_inspired_oxygen#PaO2.2FFiO2_ratio
    [3] https://litfl.com/pao2-fio2-ratio

    :param float pO2: kPa
    :param float FO2: Fraction of oxygen in dry inspired air, fraction.
    :return:
        pO2(a)/FO2(I), dimensionless quantity - no units
        if pf < 100:
            return "Severe, 45% mortality"
        elif 100 <= pf <= 200:
            return "Moderate 32% mortality"
        elif 200 <= pf <= 300:
            return "Mild, 27% mortality"
        else:
            return "All well, no ARDS"
    :rtype: float
    """
    # Example: mmHg/oxygen fraction, i.e. 105 / 0.21 = 500
    return pO2 / kPa / FiO2


def calculate_Aa_gradient(pCO2, pO2, FiO2=0.21):
    """Calculate Alveolar–arterial gradient.

    Determine source of hypoxemia: low air pO2 or damaged alveolar wall.

    [1] https://en.wikipedia.org/wiki/Alveolar–arterial_gradient

    Normal A-a gradient is:
        * Normal   PAO2, kPa  < 2.6 [Hennessey, Alan G Japp, 2 ed. 2018, p 65]
        * Expected PAO2, kPa = (age + 10) / 4 * kPa [https://www.ncbi.nlm.nih.gov/books/NBK545153/]
            ((40 / 4) + 4) * kPa == 1.866513152

    :param float pCO2: CO2 partial pressure, kPa
    :param float pO2: O2 partial pressure, kPa
    :param float FiO2: FiO2 fraction, uses 0.21 (atmosphere air), if not given
    :return: Alveolar–arterial gradient.
    :rtype: float
    """
    # Also PAO2 = (20 - 5 / 4 * pCO2) - pO2 [1]
    PAO2 = FiO2 * 93.8 - pCO2 * 1.2  # [Hennessey, Alan G Japp, 2 ed. 2018, p 65]
    return PAO2 - pO2


def calculate_Ca74(pH, Ca):
    """Ionized calcium at pH 7.4.

    References
    ----------
    [1] Radiometer ABL800 Flex Reference Manual English US.
        chapter 6-41, p. 277, equation 45.

    :param float pH: Due to biological variations this function can only be
        used for a pH value in the range 7.2-7.6 [1].
        Radiometer device returns '?' with pH=6.928, Ca=1.62.
    :param float Ca: mmol/L
    :return: cCa2+(7.4), mmol/L.
    :rtype: float
    """
    if not 7.2 <= pH <= 7.4:
        raise ValueError(
            "Can calculate only for pH 7.2-7.6 due to biological variations")
    return Ca * (1 - 0.53 * (7.4 - pH))


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
    >>> egfr_mdrd('male', 74.4, 27)
    109.36590492087734
    >>> egfr_mdrd('female', 100, 80, True)
    55.98942027449337

    :param str sex: Choose 'male', 'female'.
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
    egfr = 175 * (cCrea / m_Crea) ** -1.154 * age ** -0.203
    if sex == 'female':
        egfr *= 0.742
    elif sex == 'child':
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

    :param str sex: Choose 'male', 'female'.
    :param float cCrea: Serum creatinine (IDMS-calibrated), μmol/L
    :param float age: Human age, years
    :param bool black_skin: True for people with black skin (african american)
    :return: eGFR, mL/min/1.73 m2
    :rtype: float
    """
    cCrea /= m_Crea  # to mg/dl
    if sex == 'male':
        if cCrea <= 0.9:
            egfr = 141 * (cCrea / 0.9) ** -0.411 * 0.993 ** age
        else:
            egfr = 141 * (cCrea / 0.9) ** -1.209 * 0.993 ** age
    elif sex == 'female':
        if cCrea <= 0.7:
            egfr = 141 * (cCrea / 0.7) ** -0.329 * 0.993 ** age * 1.018
        else:
            egfr = 141 * (cCrea / 0.7) ** -1.209 * 0.993 ** age * 1.018
    elif sex == 'child':
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
    :return: eGFR, mL/min/1.73 m2.
    :rtype: float
    """
    cCrea /= m_Crea  # to mg/dl
    # k = 0.33  # First year of life, pre-term infants
    # k = 0.45  # First year of life, full-term infants
    # k = 0.55  # 1-12 years
    k = 0.413   # 1 to 16 years. Updated in 2009
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
        return "CKD4, severe loss of kidney function (29-15 %). Be prepared for dialysis"
    else:
        return "CKD5, kidney failure (<15 %). Needs dialysis or kidney transplant"


def resp_acidosis_pH(pCO2, status='acute'):
    """Calculate expected pH by pCO2 for simple respiratory acidosis.

    Metabolic acidosis compensated by respiratory alcalosis
    -------------------------------------------------------
    https://web.archive.org/web/20170824094226/http://fitsweb.uchc.edu/student/selectives/TimurGraham/Compensatory_responses_metabolic_acidosis.html
    Respiratory comp. results in a 1.2 mmHg reduction in PCO2 for every
    1.0 meq/L reduction in the plasma HCO3- concentration down to a
    minimum PCO2 of 10 to 15 mmHg:

        pCO2 = 40 - (24 - HCO3act) * 1.2,
        where 40 is normal pCO2, 24 is normal HCO2act and 1.2 - coefficient.

    So, if HCO3act is 9 mmHg, then expected pCO2 will be equal:

        40 - (24 - 9) * 1.2 = 22 mmHg

    pCO2 can be predicted more accurately by Winters' formula:

        pCO2_acid = 1.5 * HCO3act + 8  # mmHg


    Metabolic alcalosis, compensated by respiratory acidosis
    ---------------------------------------------------------
    https://web.archive.org/web/20170829100840/http://fitsweb.uchc.edu/student/selectives/TimurGraham/Compensatory_responses_metabolic_alkalosis.html

        pCO2 = (HCO3act - 24) * 0.7 + 40

    pCO2 can be predicted more accurately by Winters' formula:

        pCO2_alc = 0.7 * HCO3act + 20  # mmHg


    Respiratory acidosis
    --------------------
    https://web.archive.org/web/20170815212711/http://fitsweb.uchc.edu/student/selectives/TimurGraham/compensatory_responses_respiratory%20acidosis.html
    Note: COPD patient can tolerate 90-110 mmHg/
    Acutely, there is an increase in the plasma [HCO3-], averaging 1 meq/L for
    every 10 mmHg rise in the PCO2:

        Acute:   HCO3act = (pCO2 - 40) / 10 * 1   + 24
            also pH = 7.4 + 0.008 * (40 - pCO2)  # What is the original paper?
        Chronic: HCO3act = (pCO2 - 40) / 10 * 3.5 + 24
            also pH = 7.4 + 0.003 * (40 - pCO2)  # What is the original paper?

        pH = 6.1 + math.log10(HCO3act / (0.03 * pCO2))


    Respiratory alcalosis
    ---------------------
    https://web.archive.org/web/20170918201557/http://fitsweb.uchc.edu/student/selectives/TimurGraham/compensatory_responses_respiratory_alkalosis.html

        Acute:  HCO3act = 24 - ((40 - pCO2) / 10 * 2)
        Chronic HCO3act = 24 - ((40 - pCO2) / 10 * 4)

        pH = 6.1 + math.log10(HCO3act / (0.03 * pCO2))


    References
    ----------
    [1] Kostuchenko S.S., ABB in the ICU, 2009, p. 55.
    [2] Рябов 1994, p 67 - related to USA Cardiology assocoaton
    [3] Winters' formula https://en.wikipedia.org/wiki/Winters%27_formula
    [4] https://web.archive.org/web/20170904175146/http://fitsweb.uchc.edu/student/selectives/TimurGraham/Compensatory_responses_summary.html

    :param float pCO2: kPa
    :param str status: 'acute' (no renal compensation) or 'chronic'
        (renal compensation turns on after 3-5 days).
    :return:
        Expected pH.
    :rtype: float
    """
    if status == 'acute':
        return 7.4 + 0.008 * (40.0 - pCO2 / kPa)  # Acute
    else:
        return 7.4 + 0.003 * (40.0 - pCO2 / kPa)  # Chronic


def abg_approach_stable(pH, pCO2):
    """Evaluate arterial blood gas status for complex acid-base disorders.

    http://en.wikipedia.org/wiki/Arterial_blood_gas

    :param float pH:
    :param float pCO2: kPa
    :return: Two strings: verbose opinion and main disorder.
    :rtype: tuple
    """
    # Inspired by https://abg.ninja/abg

    # https://www.kernel.org/doc/Documentation/process/coding-style.rst
    # The answer to that is that if you need more than 3 levels of
    # indentation, you're screwed anyway, and should fix your program.

    def check_metabolic(pH, pCO2):
        """Check metabolic status by expected pH level.

        Does this pH and pCO2 means hidden metabolic process?
        """
        guess = ''
        # magic_threshold = 0.07
        magic_threshold = 0.04  # To conform this case: https://web.archive.org/web/20170729124831/http://fitsweb.uchc.edu/student/selectives/TimurGraham/Case_6.html
        ex_pH = resp_acidosis_pH(pCO2)
        if abs(pH - ex_pH) > magic_threshold:
            if pH > ex_pH:
                guess += "background metabolic alcalosis: "
            else:
                guess += "background metabolic acidosis: "
        return "{}expected pH {:.2f}".format(guess, ex_pH)

    if norm_pH[0] <= pH <= norm_pH[1]:  # pH is normal or compensated
        # Don't calculating expected CO2/pH values because both values are
        # normal or represent two opposed processes (no need for searching
        # hidden one)
        # pCO2 is abnormal, checking slight pH shifts
        if pCO2 < norm_pCO2[0]:
            # Low (respiratory alcalosis)
            if pH >= 7.41:
                return ("Respiratory alcalosis, full comp. by metabolic acidosis",
                        "respiratory_alcalosis")
            else:
                return ("Metabolic acidosis, full comp. by CO₂ alcalosis",
                        "metabolic_acidosis")
        elif pCO2 > norm_pCO2[1]:
            # High (respiratory acidosis)
            if pH <= 7.39:  # pH almost acidic
                # Classic "chronic" COPD gas
                return ("Respiratory acidosis, full comp. by metabolic alcalosis. COPD?",
                        "respiratory_acidosis")
            else:
                return ("Metabolic alcalosis, full comp. by CO₂ acidosis",
                        "metabolic_alcalosis")
        else:
            return ("Normal ABG", None)
    else:
        # pH decompensation
        if pCO2 < norm_pCO2[0]:  # Low (respiratory alcalosis)
            # Can this pH lead to given pCO2?
            if pH < norm_pH[0]:
                # Always check anion gap here
                return ("Metabolic acidosis, partial comp. by CO₂ alcalosis (check AG)",
                        "metabolic_acidosis")
            elif pH > norm_pH[1]:
                return ("Respiratory alcalosis ({})".format(check_metabolic(pH, pCO2)),
                        "respiratory_alcalosis")
        elif pCO2 > norm_pCO2[1]:
            if pH < norm_pH[0]:
                return ("Respiratory acidosis ({})".format(check_metabolic(pH, pCO2)),
                        "respiratory_acidosis")
            elif pH > norm_pH[1]:
                # Check blood and urine Cl [Курек 2013, 48]: Cl-dependent < 15-20 mmol/L < Cl-independent
                return ("Metabolic alcalosis, partial comp. by CO₂ acidosis (check Na, Cl, albumin)",
                        "metabolic_alcalosis")
        else:
            # Normal pCO2 (35 <= pCO2 <= 45 normal)
            if pH < norm_pH[0]:
                # Always check anion gap here
                return ("Metabolic acidosis, no respiratory comp.",
                        "metabolic_acidosis")
            elif pH > norm_pH[1]:
                return ("Metabolic alcalosis, no respiratory comp.",
                        "metabolic_alcalosis")


def abg_approach_ryabov(pH, pCO2):
    """Describe ABG by Ryabov algorithm.

    1. Calculate how measured pCO2 will change normal pH 7.4
    2. Compare measured and calculated pH. Big difference between measured and
       calculated pH points at hidden metabolic process
    3. Divide measured and calculated pH difference by 0.015 to calculate
       base excess (BE) approximation in mEq/L
    4. If extracellular fluid (HCO3- distribution volume) represents 25 % of
       real body weight (RBW), global base excess will be near "BE * 0.25 * RBW"


    Examples
    --------
    >>> abg_approach_ryabov(7.36, 55*kPa)
    'pH, calculated by pCO2, is 7.28, estimated SBE (7.36-7.28)/0.015=+5.33 mEq/L'


    References
    ----------
    [1] Рябов 1994, p 67 - три правила Ассоциации кардиологов США (AHA?)

    :param float pH:
    :param float pCO2: kPa
    :return: Opinion.
    :rtype: str
    """
    # Same as `pH_expected = resp_acidosis_pH(pCO2, status='acute')`
    pH_expected = 7.4 + 0.008 * (40 - pCO2 / kPa)  # What is the original paper?
    info = "pH, calculated by pCO2, is {:.02f}, ".format(pH_expected)
    pH_diff = pH - pH_expected
    sbe = pH_diff / 0.015
    info += "estimated SBE ({:.02f}-{:.02f})/0.015={:+.02f} mEq/L".format(pH, pH_expected, sbe)
    return info


def abg_approach_research(pH, pCO2):
    """Calculate expected ABG values.

    References
    ----------
    [1] Kostuchenko S.S., ABB in the ICU, 2009

    :param float pH:
    :param float pCO2: kPa
    :param float HCO3: mEq/L, standartized. Evaluated automatically if not
        provided
    :return: Opinion.
    :rtype: str
    """
    info = ""
    HCO3act = calculate_hco3p(pH, pCO2)
    # pCO2mmHg = pCO2 / kPa

    info += "pH by pCO2: acute {:.2f}, chronic {:.2f} for primary respiratory condition [AHA?]\n".format(
        resp_acidosis_pH(pCO2, 'acute'),
        resp_acidosis_pH(pCO2, 'chronic'))

    """
    Winters' formula - checks if respiratory response (pCO2 level) adequate
    for current metabolic acidosis or alcalosis (for given pH and pCO2)
      * Albert MS, Dell RB, Winters RW (February 1967). "Quantitative displacement of acid-base equilibrium in metabolic acidosis". Annals of Internal Medicine
      * https://www.ncbi.nlm.nih.gov/pubmed/6016545
      * https://en.wikipedia.org/wiki/Winters%27_formula
      * https://jasn.asnjournals.org/content/21/6/920
    """
    wint_ac = 1.5 * HCO3act + 8
    wint_alc = 0.7 * HCO3act + 20
    info += "pCO2 by cHCO3(P) - expected respiratory compensation [Winters]:\n"
    info += " * Met. acid. lungs will drop pCO2, but not lower than ≥{:.1f}-{:.1f} mmHg\n".format(wint_ac, wint_ac - 2, wint_ac + 2)
    info += " * Met. alc. lungs will save pCO2, but not higher than ≤{:.1f}-{:.1f} mmHg\n".format(wint_alc, wint_alc - 1.5, wint_alc + 1.5)
    # try:
    #     y = (7.4 - pH) / (pCO2mmHg - 40.0) * 100
    #     info += "y = ΔpH/ΔpCO2×100 = {:.2f} [needs table p 56 to assess]\n".format(y)
    # except ZeroDivisionError:
    #     pass
    return info


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
