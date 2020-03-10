# -*- coding: utf-8 -*-
"""
Electrolyte disturbances and correction.

Author: Eugene Dvoretsky
"""

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


def electrolyte_Na(weight, Na_serum, verbose=True):
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
    :param float Na_serum: mmol/L
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
    return info


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
