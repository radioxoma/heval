"""Arterial blood gas interpreter.

Author: Eugene Dvoretsky, 2015-05-20

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

try:
    from uncertainties import umath as math
except ImportError:
    import math

# Units conversion
kPa = 0.133322368  # kPa to mmHg, 1 mmHg = 0.133322368 kPa

# Reference blood test ranges
norm_pH = (7.35, 7.45)
norm_pH_mean = 7.40
norm_pH_alive = (6.8, 7.8)  # Live borders

norm_pCO2 = (4.666, 6)  # kPa
# norm_pCO2mmHg = (35, 45)
norm_pCO2mmHg_mean = 40.0  # mmHg

norm_HCO3 = (22, 26)  # mEq/L
norm_pO2 = (80, 100)  # mmHg

# Mean albumin level. Used to normalize anion gap value in low cAlb case
# See Anion Gap calculation for reference
norm_ctAlb_mean = 4.4  # g/dL
norm_ctAlb = (3.5, 5)  # g/dL


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

    > 1 HAGMA + concurrent metabolic alkalosis
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
        info += "(gg < 0.4): hyperchloremic normal anion gap metabolic acidosis (NAGMA)"
        return info
    elif 0.4 <= gg <= 0.8:
        # Consider combined high AG & normal AG acidosis BUT note that the
        # ratio is often < 1 in acidosis associated with renal failure
        # Renal tubular acidosis https://web.archive.org/web/20170802021754/http://fitsweb.uchc.edu/student/selectives/TimurGraham/Case_5.html
        info += "(0.4 ≤ gg ≤ 0.8): combined HAGMA + NAGMA (gg ratio <1 often associated with renal failure - check urine electrolytes and kidney function)"
        return info
    elif 0.8 < gg < 1:
        info += "(0.8 < gg < 1): most likely caused by diabetic ketoacidosis due to urine ketone bodies loss (when patient not dehydrated yet)"
        return info
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
        #   * a concurrent metabolic alkalosis
        #   * a pre-existing compensated respiratory acidosis
        # tiazide diuretics?
        info += "(2 < gg): concurrent metabolic alkalosis or chronic respiratory acidosis with high HCO₃⁻"
        return info


def calculate_sid_abbr(cNa, cCl, ctAlb):
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
    :param float cNa: Na concentration, mmol/L
    :param float cCl: Cl concentration, mmol/L
    :param float ctAlb: Albumin, g/dL for correction.
    :return: Strong ion difference.
    :rtype: float
    """
    sid = cNa - cCl - 38
    if ctAlb:
        sid += 2.5 * (norm_ctAlb_mean - ctAlb)
    return sid


def calculate_osmolarity(cNa, cGlu):
    """Calculate serum osmotic concentration (osmolarity, mOsm/L).

    NB! This is not an osmolality (mOsm/kg), measured by an osmometer.


    References
    ----------
    [1] Radiometer ABL800 Flex Reference Manual English US.
        chapter 6-41, p. 277, equation 48.
    [2] https://en.wikipedia.org/wiki/Osmotic_concentration

    :param float cNa: Sodium, mmol/L
    :param float cGlu: Glucose, mmol/L
    :return: Serum osmolarity, mmol/L (mOsm/L).
    :rtype: float
    """
    # Sometimes `2 * (cNa + cK) + cGlu + Urea` all in mmol/L
    # Also ethanol can cause https://en.wikipedia.org/wiki/Osmol_gap
    return 2 * cNa + cGlu


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
    a = 4.04 * 10**-3 + 4.25 * 10**-4 * ctHb
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
    a = 4.04 * 10**-3 + 4.25 * 10**-4 * ctHb
    pHHb = 4.06 * 10**-2 * ctHb + 5.98 - 1.92 * 10 ** (-0.16169 * ctHb)
    log_pCO2Hb = -1.7674 * (10**-2) * ctHb + 3.4046 + 2.12 * 10 ** (-0.15158 * ctHb)
    pHst = pH + math.log10(5.33 / pCO2) * (
        (pHHb - pH) / (log_pCO2Hb - math.log10(7.5006 * pCO2))
    )
    cHCO3_533 = 0.23 * 5.33 * 10 ** ((pHst - 6.161) / 0.9524)
    # There is no comments, as there is no place for weak man
    cBase = 0.5 * ((8 * a - 0.919) / a) + 0.5 * math.sqrt(
        (((0.919 - 8 * a) / a) ** 2) - 4 * ((24.47 - cHCO3_533) / a)
    )
    return cBase


def calculate_hct(ctHb):
    """Calculate haematocrit.

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

    Examples
    --------
    >>> calculate_hct(171 / 10 / 1.61140)
    0.5229766786645154

    :param float ctHb: Concentration of total hemoglobin in blood, mmol/L.
    :return: Haematocrit, fraction (not %).
    :rtype: float
    """
    # ctHb(mmol/L) == ctHb(g/dL) / 1.61140 == ctHb(g/dL) * 0.62058
    # By [1] p. 6-14 or 6-49.
    return 0.0485 * ctHb + 8.3 * 10**-3


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
    alphaO2 = 9.83 * 10**-3  # mmol/L/kPa
    return alphaO2 * pO2 + sO2 * (1 - FCOHb - FMetHb) * ctHb


def calculate_pO2_FO2_fraction(pO2, FiO2):
    """pO2(a)/FO2(I) - the ratio of pO2 and fraction of inspired oxygen measured at PEEP 5 mbar.

    Simplest calculation to diagnose ARDS. Known as:
        * PaO2/FiO2 ratio
        * p/f ratio

    References
    ----------
    [1] Radiometer ABL800 Flex Reference Manual English US.
        chapter 6-32, p. 268, equation 17.
    [2] https://en.wikipedia.org/wiki/Fraction_of_inspired_oxygen#PaO2/FiO2_ratio
    [3] https://litfl.com/pao2-fio2-ratio
    [4] https://litfl.com/acute-respiratory-distress-syndrome-definitions/

    Examples
    --------
    >>> calculate_pO2_FO2_fraction(15, 0.21)
    535.7583464807003

    :param float pO2: kPa
    :param float FiO2: Fraction of oxygen in dry inspired air, fraction.
    :return: pO2(a)/FO2(I), dimensionless quantity - no units
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
            "Can calculate only for pH 7.2-7.6 due to biological variations"
        )
    return Ca * (1 - 0.53 * (7.4 - pH))


def resp_acidosis_pH(pCO2, status="acute"):
    """Calculate expected pH by pCO2 for simple respiratory acidosis.

    Metabolic acidosis compensated by respiratory alkalosis
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


    Metabolic alkalosis, compensated by respiratory acidosis
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


    Respiratory alkalosis
    ---------------------
    https://web.archive.org/web/20170918201557/http://fitsweb.uchc.edu/student/selectives/TimurGraham/compensatory_responses_respiratory_alkalosis.html

        Acute:  HCO3act = 24 - ((40 - pCO2) / 10 * 2)
        Chronic HCO3act = 24 - ((40 - pCO2) / 10 * 4)

        pH = 6.1 + math.log10(HCO3act / (0.03 * pCO2))


    References
    ----------
    [1] Kostuchenko S.S., ABB in the ICU, 2009, p. 55.
    [2] Рябов 1994, p 67 - related to USA Cardiology association
    [3] Winters' formula https://en.wikipedia.org/wiki/Winters%27_formula
    [4] https://web.archive.org/web/20170904175146/http://fitsweb.uchc.edu/student/selectives/TimurGraham/Compensatory_responses_summary.html

    :param float pCO2: kPa
    :param str status: 'acute' (no renal compensation) or 'chronic'
        (renal compensation turns on after 3-5 days).
    :return:
        Expected pH.
    :rtype: float
    """
    if status == "acute":
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
        guess = ""
        # magic_threshold = 0.07
        magic_threshold = 0.04  # To conform this case: https://web.archive.org/web/20170729124831/http://fitsweb.uchc.edu/student/selectives/TimurGraham/Case_6.html
        ex_pH = resp_acidosis_pH(pCO2)
        if abs(pH - ex_pH) > magic_threshold:
            if pH > ex_pH:
                guess += "background metabolic alkalosis: "
            else:
                guess += "background metabolic acidosis: "
        return "{}expected pH {:.2f}".format(guess, ex_pH)

    if norm_pH[0] <= pH <= norm_pH[1]:  # pH is normal or compensated
        # Don't calculating expected CO2/pH values because both values are
        # normal or represent two opposed processes (no need for searching
        # hidden one)
        # pCO2 is abnormal, checking slight pH shifts
        if pCO2 < norm_pCO2[0]:
            # Low (respiratory alkalosis)
            if pH >= 7.41:
                return (
                    "Respiratory alkalosis, full comp. by metabolic acidosis",
                    "respiratory_alkalosis",
                )
            else:
                return (
                    "Metabolic acidosis, full comp. by CO₂ alkalosis",
                    "metabolic_acidosis",
                )
        elif pCO2 > norm_pCO2[1]:
            # High (respiratory acidosis)
            if pH <= 7.39:  # pH almost acidic
                # Classic "chronic" COPD gas
                return (
                    "Respiratory acidosis, full comp. by metabolic alkalosis. COPD?",
                    "respiratory_acidosis",
                )
            else:
                return (
                    "Metabolic alkalosis, full comp. by CO₂ acidosis",
                    "metabolic_alkalosis",
                )
        else:
            return "Normal ABG", None
    else:
        # pH decompensation
        if pCO2 < norm_pCO2[0]:  # Low (respiratory alkalosis)
            # Can this pH lead to given pCO2?
            if pH < norm_pH[0]:
                # Always check anion gap here
                return (
                    "Metabolic acidosis, partial comp. by CO₂ alkalosis (check AG)",
                    "metabolic_acidosis",
                )
            elif pH > norm_pH[1]:
                return (
                    "Respiratory alkalosis ({})".format(check_metabolic(pH, pCO2)),
                    "respiratory_alkalosis",
                )
        elif pCO2 > norm_pCO2[1]:
            if pH < norm_pH[0]:
                return (
                    "Respiratory acidosis ({})".format(check_metabolic(pH, pCO2)),
                    "respiratory_acidosis",
                )
            elif pH > norm_pH[1]:
                # Check blood and urine Cl [Курек 2013, 48]: Cl-dependent < 15-20 mmol/L < Cl-independent
                return (
                    "Metabolic alkalosis, partial comp. by CO₂ acidosis (check Na, Cl, albumin)",
                    "metabolic_alkalosis",
                )
        else:
            # Normal pCO2 (35 <= pCO2 <= 45 normal)
            if pH < norm_pH[0]:
                # Always check anion gap here
                return (
                    "Metabolic acidosis, no respiratory comp.",
                    "metabolic_acidosis",
                )
            elif pH > norm_pH[1]:
                return (
                    "Metabolic alkalosis, no respiratory comp.",
                    "metabolic_alkalosis",
                )


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
    info += "estimated SBE ({:.02f}-{:.02f})/0.015={:+.02f} mEq/L".format(
        pH, pH_expected, sbe
    )
    return info


def abg_approach_research(pH, pCO2):
    """Calculate expected ABG values.

    References
    ----------
    [1] Kostuchenko S.S., ABB in the ICU, 2009

    :param float pH:
    :param float pCO2: kPa
    :return: Opinion.
    :rtype: str
    """
    info = ""
    HCO3act = calculate_hco3p(pH, pCO2)
    # pCO2mmHg = pCO2 / kPa

    info += "pH by pCO2: acute {:.2f}, chronic {:.2f} for primary respiratory condition [AHA?]\n".format(
        resp_acidosis_pH(pCO2, "acute"), resp_acidosis_pH(pCO2, "chronic")
    )

    """
    Winters' formula - checks if respiratory response (pCO2 level) adequate
    for current metabolic acidosis or alkalosis (for given pH and pCO2)
      * Albert MS, Dell RB, Winters RW (February 1967). "Quantitative displacement of acid-base equilibrium in metabolic acidosis". Annals of Internal Medicine
      * https://www.ncbi.nlm.nih.gov/pubmed/6016545
      * https://en.wikipedia.org/wiki/Winters%27_formula
      * https://jasn.asnjournals.org/content/21/6/920
    """
    wint_ac = 1.5 * HCO3act + 8
    wint_alc = 0.7 * HCO3act + 20
    info += "pCO2 by cHCO3(P) - expected respiratory compensation [Winters]:\n"
    info += " * Met. acid. lungs will drop pCO2, but not lower than ≥{:.1f}-{:.1f} mmHg\n".format(
        wint_ac - 2, wint_ac + 2
    )
    info += " * Met. alc. lungs will save pCO2, but not higher than ≤{:.1f}-{:.1f} mmHg\n".format(
        wint_alc - 1.5, wint_alc + 1.5
    )
    # try:
    #     y = (7.4 - pH) / (pCO2mmHg - 40.0) * 100
    #     info += "y = ΔpH/ΔpCO2×100 = {:.2f} [needs table p 56 to assess]\n".format(y)
    # except ZeroDivisionError:
    #     pass
    return info
