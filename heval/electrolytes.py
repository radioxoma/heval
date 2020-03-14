# -*- coding: utf-8 -*-
"""
Electrolyte disturbances and correction.

Author: Eugene Dvoretsky
"""
import textwrap
from itertools import chain

from heval.abg import calculate_cbase, calculate_hco3p, calculate_anion_gap, norm_ctAlb_mean, calculate_osmolarity, \
    norm_mOsm, norm_gap, calculate_anion_gap_delta, norm_sbe, norm_cGlu, norm_cGlu_target, norm_ctAlb, M_Crea, kPa, \
    norm_pH, norm_pCO2

M_NaHCO3 = 84  # g/mol or mg/mmol
M_C6H12O6 = 180
M_NaCl = 58.5
M_KCl = 74.5

norm_K = (3.5, 5.3)   # mmol/L, Radiometer, adult
# norm_Na = (130, 155)  # mmol/L, Radiometer, adult
# norm_Na = (130, 150)  # Курек 2013 c 133, children
norm_Na = (135, 145)  # https://en.wikipedia.org/wiki/Hypernatremia
norm_Cl = (98, 115)   # mmol/L, Radiometer, adult


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
    info = "Glu {:.1f} g ({:.2f} mmol, {:.0f} kcal)".format(glu_mass, glu_mol, glu_mass * 4.1)
    if add_insuline:
        ins_dosage = 0.25  # IU/g
        insulinum = glu_mass * ins_dosage
        info += " + Ins {:.1f} IU ({:.2f} IU/g)".format(insulinum, ins_dosage)
    info += ":\n"

    for dilution in (5, 10, 40):
        g_low, g_max = 0.15, 0.5  # g/kg/h
        speed_low = (g_low * body_weight) / dilution * 100
        speed_max = (g_max * body_weight) / dilution * 100
        vol = glu_mass / dilution * 100
        info += " * Glu {:>2.0f}% {:>4.0f} ml ({:>3.0f}-{:>3.0f} ml/h = {:.3f}-{:.2f} g/kg/h)".format(dilution, vol, speed_low, speed_max, g_low, g_max)
        if dilution == 5:
            info += " isotonic"
        info += "\n"
    return info


def solution_kcl4(salt_mmol):
    """Convert mmol of KCl to volume of saline solution.

    :param float salt_mmol: KCl, amount of substance, mmol
    :return: KCl 4 % ml solution, ml
    :rtype: str
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

    :param float salt_mmol: Amount of substance (NaCl or single ion ecvivalent), mmol
    :return: Info string
    """
    info = ''
    for dilution in (0.9, 3, 5, 10):
        conc = 1000 * (dilution / 100) / M_NaCl  # mmol/ml
        vol = salt_mmol / conc  # ml
        info += " * NaCl {:>4.1f}% {:>4.0f} ml".format(dilution, vol)
        if dilution == 0.9:
            info += " isotonic"
        info += "\n"
    return info


def electrolyte_Na_classic(total_body_water, Na_serum, Na_target=140, Na_shift_rate=0.5):
    """Correct hyper- hyponatremia correction with two classic formulas.

    Calculates amount of pure water or Na.

    References
    ----------
    Original paper is unknown. Plenty simplified calculations among the books.
    [1] http://www.medcalc.com/sodium.html

    Parameters
    ----------
    :param float total_body_water: Liters
    :param float Na_serum: Serum sodium level, mmol/L
    :param float Na_target: 140 mmol/L by default
    :param float Na_shift_rate: 0.5 mmol/L/h by default is safe
    :return: Text describing Na deficit/excess and solutions dosage to correct.
    :rtupe: str
    """
    info = ""
    Na_shift_hours = abs(Na_target - Na_serum) / Na_shift_rate
    if Na_serum > Na_target:
        # Classic hypernatremia formula
        # water_deficit = total_body_water * (Na_serum - Na_target) / Na_target * 1000  # Equal
        water_deficit = total_body_water * (Na_serum / Na_target - 1) * 1000  # ml
        info += "Free water deficit is {:.0f} ml, ".format(water_deficit)
        info += "replace it with D5 at rate {:.1f} ml/h during {:.0f} hours. ".format(
            water_deficit / Na_shift_hours, Na_shift_hours)
    elif Na_serum < Na_target:
        # Classic hyponatremia formula
        Na_deficit = (Na_target - Na_serum) * total_body_water  # mmol
        info += "Na⁺ deficit is {:.0f} mmol, which equals to:\n".format(Na_deficit)
        info += solution_normal_saline(Na_deficit)
        info += "Replace Na⁺ at rate {:.1f} mmol/L/h during {:.0f} hours:\n".format(
            Na_shift_rate, Na_shift_hours)
        info += solution_normal_saline(Na_deficit / Na_shift_hours)
    return info


def electrolyte_Na_adrogue(total_body_water, Na_serum, Na_target=140, Na_shift_rate=0.5):
    """Correct hyper- hyponatremia correction with Adrogue–Madias formula.

    Calculates amount of specific solution needed to correct Na.
    Considered as more precise then classic formula.

    If patient urinates during Na replacement, calculated dose may be excessive
    because total body water won't be increased as expected.

    References
    ----------
    [1] Adrogue, HJ; and Madias, NE. Primary Care: Hypernatremia. New England Journal of Medicine 2000.
        https://www.ncbi.nlm.nih.gov/pubmed/10824078
        https://www.ncbi.nlm.nih.gov/pubmed/10816188
    [2] Does the Adrogue–Madias formula accurately predict serum sodium levels in patients with dysnatremias?
        https://www.nature.com/articles/ncpneph0335
    [3] http://www.medcalc.com/sodium.html

    Parameters
    ----------
    :param float total_body_water: Liters
    :param float Na_serum: Serum sodium level, mmol/L
    :param float Na_target: 140 mmol/L by default
    :param float Na_shift_rate: 0.5 mmol/L/h by default is safe
    :return: Text describing Na deficit/excess and solutions dosage to correct.
    :rtupe: str
    """
    solutions = [
        # Hyper
        {'name': "NaCl 5%         (Na⁺ 855 mmol/L)", 'K_inf': 0, 'Na_inf': 855},
        {'name': "NaCl 3%         (Na⁺ 513 mmol/L)", 'K_inf': 0, 'Na_inf': 513},
        {'name': "NaCl 0.9%       (Na⁺ 154 mmol/L)", 'K_inf': 0, 'Na_inf': 154},
        # Iso
        {'name': "Sterofundin ISO (Na⁺ 145 mmol/L)", 'K_inf': 4, 'Na_inf': 145},  # BBraun
        {'name': "Ionosteril      (Na⁺ 137 mmol/L)", 'K_inf': 4, 'Na_inf': 137},  # Fresenius Kabi
        {'name': "Lactate Ringer  (Na⁺ 130 mmol/L)", 'K_inf': 4, 'Na_inf': 130},  # Hartmann's solution
        # Hypo
        {'name': "NaCl 0.45%      (Na⁺  77 mmol/L)", 'K_inf': 0, 'Na_inf': 77},
        {'name': "NaCl 0.2%       (Na⁺  34 mmol/L)", 'K_inf': 0, 'Na_inf': 34},
        {'name': "D5W or water    (Na⁺   0 mmol/L)", 'K_inf': 0, 'Na_inf': 0},
    ]
    Na_shift_hours = abs(Na_target - Na_serum) / Na_shift_rate
    info = ""
    for sol in solutions:
        Na_inf = sol['Na_inf']
        K_inf = sol['K_inf']
        if Na_serum == Na_inf + K_inf:
            # Prevent zero division if solution same as the patient Na
            continue
        vol = (Na_target - Na_serum) / (Na_inf + K_inf - Na_serum) * (total_body_water + 1) * 1000
        if vol < 0:
            # Wrong solution, will only make patient worse
            continue
        elif vol > 50000:
            # Will lead to volume overload, not an option
            # Using 50000 ml threshold to cut off unreal volumes
            continue
        info += " * {:<15} {:>6.0f} ml, {:6.1f} ml/h during {:.0f} hours\n".format(
            sol['name'], vol, vol / Na_shift_hours, Na_shift_hours)
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
        * На каждый mmol K+ вводить 10 kcal glucosae
            * Если принять калорийность глюкозы за 3.74-4.1 kcal/g, то нужно 2.67-2.44 g глюкозы, примерно 2.5 г
    [Курек 132]:
        * Вводить K+ со скоростью 0.25-0.5 mmol/kg/h (не быстрее)
            * Но для веса > 40 кг, получается скорость >20 mmol/h, чего быть не должно.
        * На каждый mmol K+ вводить
            * Glu 2.5 g/mmol + Ins 0.2-0.3 IU/mmol (потребность в инсулине у детей меньше)

    Готовый раствор:
        * Концентрация калия: периферия не более 40 mmol/L (KCl 0.3 % ?), CVC не более 100 mmol/L (KCl 0.74 % ?) [Курек 2009 с 557]
            Т.е. для периферии можно Sol. Glucosae 5 % 250 ml + KCl 7.5 % 10 ml, а для CVC KCl 7.5 % 25 ml?
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
            info += "K⁺ is dangerously high (>{:.1f} mmol/L)\n".format(K_high)
            info += "Inject bolus 0.5 g/kg "
            info += solution_glucose(glu_mass, weight)
            info += "Or standard adult bolus Glu 40% 60 ml + Ins 10 IU [ПосДеж]\n"
            # Use NaHCO3 if K greater or equal 6 mmol/L [Курек 2013, 47, 131]
            info += "NaHCO₃ 8.4% {:.0f} ml (RBWx2={:.0f} mmol) [Курек 2013]\n".format(
                2 * weight, 2 * weight)
            info += "Don't forget salbutamol, furesemide, hyperventilation. If ECG changes, use Ca gluconate [PICU: Electrolyte Emergencies]"
        else:
            info += "K⁺ on the upper acceptable border {:.1f} ({:.1f}-{:.1f} mmol/L)".format(K_serum, K_low, K_high)
    elif K_serum < norm_K[0]:
        if K_serum < K_low:
            info += "K⁺ is dangerously low (<{:.1f} mmol/L). Often associated with low Mg²⁺ (Mg²⁺ should be at least 1 mmol/L) and low Cl⁻.\n".format(K_low)

            info += "NB! Potassium calculations considered inaccurate, so use standard K⁺ replacement rate "
            if weight < 40:
                info += "{:.1f}-{:.1f} mmol/h (KCl 4 % {:.1f}-{:.1f} ml/h)".format(
                    0.25 * weight, 0.5 * weight,
                    solution_kcl4(0.25 * weight), solution_kcl4(0.5 * weight))
            else:
                info += "{:.0f}-{:.0f} mmol/h (KCl 4 % {:.1f}-{:.1f} ml/h)".format(
                    10, 20,
                    solution_kcl4(10), solution_kcl4(20))
            info += " and check ABG every 2-4 hours.\n"

            # coefficient = 0.45  # новорождённые
            # coefficient = 0.4   # грудные
            # coefficient = 0.3   # < 5 лет
            coefficient = 0.2   # >5 лет [Курек 2013]

            K_deficit = (K_target - K_serum) * weight * coefficient
            # K_deficit += weight * 1  # mmol/kg/24h Should I also add daily requirement?

            info += "Estimated K⁺ deficit is {:.0f} mmol (KCl 4 % {:.1f} ml) + ".format(K_deficit, solution_kcl4(K_deficit))
            if K_deficit > 4 * weight:
                info += "Too much potassium for 24 hours"

            glu_mass = K_deficit * 2.5  # 2.5 g/mmol, ~10 kcal/mmol
            info += solution_glucose(glu_mass, weight)
        else:
            info += "K⁺ on lower acceptable border {:.1f} ({:.1f}-{:.1f} mmol/L)".format(K_serum, K_low, K_high)
    else:
        info += "K⁺ is ok ({:.1f}-{:.1f} mmol/L)]".format(norm_K[0], norm_K[1])
    return info


def electrolyte_Na(weight, Na_serum, cGlu, verbose=True):
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


    References
    ----------
    [1] http://www.medcalc.com/sodium.html

    Parameters
    ----------
    :param float weight: Real body weight, kg
    :param float Na_serum: Serum sodium level, mmol/L
    :param float cGlu: Serum glucose level, mmol/L
    :param bool verbose: Return all possible text if True
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
    desc = "{:.0f} ({:.0f}-{:.0f} mmol/L)".format(Na_serum, norm_Na[0], norm_Na[1])
    if Na_serum > norm_Na[1]:
        info += "Na⁺ is high {}, check osmolarity. Give enteral water if possible. ".format(desc)
        info += "Warning: Na⁺ decrement faster than {:.1f} mmol/L/h can cause cerebral edema.\n".format(Na_shift_rate)
        if verbose:
            info += "Classic replacement calculation: {}\n".format(electrolyte_Na_classic(total_body_water, Na_serum, Na_target=Na_target, Na_shift_rate=Na_shift_rate))
        info += "Adrogue replacement calculation:\n{}".format(electrolyte_Na_adrogue(total_body_water, Na_serum, Na_target=Na_target, Na_shift_rate=Na_shift_rate))
    elif Na_serum < norm_Na[0]:
        info += "Na⁺ is low {}, expect cerebral edema leading to seizures, coma and death. ".format(desc)
        info += "Warning: Na⁺ replacement faster than {:.1f} mmol/L/h can cause osmotic central pontine myelinolysis.\n".format(Na_shift_rate)
        # N.B.! Hypervolemic patient has low Na because of diluted plasma,
        # so it needs furosemide, not extra Na administration.
        if verbose:
            info += "Classic replacement calculation: {}".format(electrolyte_Na_classic(total_body_water, Na_serum, Na_target=Na_target, Na_shift_rate=Na_shift_rate))
        info += "Adrogue replacement calculation:\n{}".format(electrolyte_Na_adrogue(total_body_water, Na_serum, Na_target=Na_target, Na_shift_rate=Na_shift_rate))
    else:
        info += "Na⁺ is ok {}".format(desc)

    # Should corrected Na be used instead of Na_serum for replacement calculation?
    Na_corr = correct_Na_hyperosmolar(Na_serum, cGlu)
    if abs(Na_corr - Na_serum) > 5:  # Arbitrary threshold
        info += "\nHigh cGlu causes high osmolarity and apparent hyponatremia. Corrected Na⁺ is {:.0f} mmol/L.".format(Na_corr)
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


def electrolyte_Cl(Cl_serum):
    """Assess blood serum chloride level.

    :param float weight: Real body weight, kg
    :param float Cl_serum: mmol/L
    """
    info = ""
    Cl_low, Cl_high = norm_Cl[0], norm_Cl[1]
    if Cl_serum > Cl_high:
        info += "Cl⁻ is high (>{} mmol/L), excessive NaCl infusion or dehydration (check osmolarity).".format(Cl_high)
    elif Cl_serum < Cl_low:
        # KCl replacement?
        info += "Cl⁻ is low (<{} mmol/L). Vomiting? Diuretics abuse?".format(Cl_low)
    else:
        info += "Cl⁻ is ok ({:.0f}-{:.0f} mmol/L)".format(norm_Cl[0], norm_Cl[1])
    return info


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
                NaHCO3_g = NaHCO3_mmol / 1000 * M_NaHCO3  # gram
                NaHCO3_g_24h = NaHCO3_mmol_24h / 1000 * M_NaHCO3
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
        info += "{}\n\n".format(electrolyte_K(self.parent.weight, self.cK))
        info += "{}\n\n".format(electrolyte_Na(self.parent.weight, self.cNa, self.cGlu, self.parent.debug))
        info += "{}\n".format(electrolyte_Cl(self.cCl))
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
                info += solution_glucose(0.25 * self.parent.weight, self.parent.weight, add_insuline=False)
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
    egfr = 175 * (cCrea / M_Crea) ** -1.154 * age ** -0.203
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
    cCrea /= M_Crea  # to mg/dl
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
    cCrea /= M_Crea  # to mg/dl
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