#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Electrolyte disturbances and correction.

Author: Eugene Dvoretsky

If too low or too high, then
    * Warn of danger electrolyte values
    * Suggest correction boluses
"""

__EASTER_TEXT__ = ("It's got what plants crave!", "It's got electrolytes!")
M_NaHCO3 = 84  # g/mol or mg/mmol
M_C6H12O6 = 180
M_NaCl = 58.5
M_KCl = 74.5

norm_K = (3.5, 5.3)   # mmol/L, Radiometer, adult
norm_Na = (130, 155)  # mmol/L, Radiometer, adult
# norm_Na = (130, 150)  # Курек 2013 c 133, children
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


def electrolyte_K(weight, K_serum):
    """Assess blood serum potassium level.

    :param float weight: Real body weight, kg
    :param float K_serum: Potassium serum level, mmol/L

    Hypokalemia (additional K if <3.5 mmol/L)
    -----------------------------------------
    # Comment:
    # 1. As far it's practically impossible to calculate K deficiency,
    # administer continuously i/v with rate 10 mmol/h and check ABG  every 2-4 hour in acute period
    #     * If there are ECG changes and muscle relaxation, speed up to 20 mmol/h [Курек 2009 с 557]
    # 2. In severe hypokalemia (<= 3 mmol/L) administrate with NaCl, not glucose
    #     * When deficiency compensated (> 3 mmol/L) it's now possible to switch to glucose+insulin

    * Содержание K до 5 лет значительно выше [Курек 2013 с 38]
    * Если K+ <3 mmol/L, то введение глюкозы с инсулином может усугубить гипокалиемию, поэтому K+ вводить вместе с NaCl. [Курек ИТ 557]
    * Metabolic acidosis raises plasma K+ level by displacing it from cells. E.g. in DKA [Рябов 1994, с 70]

    [130]:
        * Top 24h dose 4 mmol/kg/24h
        * Полностью восполнять дефицит не быстрее чем за 48 ч
        * Допустимая скорость 0.5 mmol/kg/h (тогда суточная доза введётся за 8 часов)
        * На каждый mmol K+ вводить 10 kcal glucosae
            * Если принять калорийность глюкозы за 3.74-4.1 kcal/g, то нужно 2.67-2.44 g глюкозы, примерно 2.5 г
    [132]:
        * Вводить K+ со скоростью 0.25-0.5 mmol/kg/h (не быстрее)
            * Но для веса > 40 кг, получается скорость >20 mmol/h, чего быть не должно?
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

    Уменьшние количества ионизированного калия:
        * NaHCO3 2 mmol/kg (за 10-20 минут)
        * CaCl2 - только если есть изменения на ЭКГ [PICU: Electrolyte Emergencies]
        * гипервентиляция
    """
    if norm_K[0] <= K_serum <= norm_K[1]:
        return "K⁺ is ok ({:.1f}-{:.1f} mmol/L)".format(norm_K[0], norm_K[1])

    K_high = 6  # Курек 2013, p 47 (6 mmol/L, 131 (7 mmol/L)
    K_target = 5.0  # mmol/L Not from book
    K_low = 3.5  # Курек 132

    info = ''
    if K_serum < K_low:
        info += "K⁺ is dangerously low (<{:.0f} mmol/L). Often associated with low Mg²⁺ (Mg²⁺ should be at least 1 mmol/L) and low Cl⁻.\n".format(K_low)
        info += "NB! Potassium calculations considered inaccurate, so use standard replacement rate and check ABG every 2-4 hours: "
        if weight < 40:
            info += "KCl {:.0f}-{:.0f} mmol/h for child.\n".format(0.25 * weight, 0.5 * weight)
        else:
            info += "KCl 10-20 mmol/h (standard rate) for all adults will be ok.\n"

        # coefficient = 0.45  # новорождённые
        # coefficient = 0.4   # грудные
        # coefficient = 0.3   # < 5 лет
        coefficient = 0.2   # >5 лет [Курек 2013, Маневич и Плохой c. 116]

        K_deficiency = (K_target - K_serum) * weight * coefficient
        # K_deficiency += weight * 1  # mmol/kg/24h Should I also add daily requirement?

        info += "Estimated K⁺ deficiency (for children too?) is {:.0f} mmol + ".format(K_deficiency)
        if K_deficiency > 4 * weight:
            info += "Too much potassium for 24 hours"

        glu_mass = K_deficiency * 2.5  # 2.5 g/mmol, ~10 kcal/mmol
        info += solution_glucose(glu_mass, weight)

    elif K_serum >= K_high:
        glu_mass = 0.5 * weight
        info += "K⁺ is dangerously high (>{} mmol/L)\n".format(K_high)
        info += "Inject bolus for child "
        info += solution_glucose(glu_mass, weight)
        info += "Or standard adult Glu 40% 60 ml + Ins 10 IU [ПосДеж]\n"
        # Use NaHCO3 if K greater or equal 6 mmol/L [Курек 2013, 47, 131]
        info += "RBW NaHCO3 4% {:.0f} ml (x2={:.0f} mmol) [Курек 2013]\n".format(
            2 * weight * M_NaHCO3 / 40, 2 * weight)
        info += "Don't forget furesemide, hyperventilation\n"
        info += "If ECG changes, use Ca gluconate [PICU: Electrolyte Emergencies]"
    else:
        info += "K⁺ in range [{:.1f}-{:.1f} mmol/L]".format(K_low, K_high)
    return info


# def low_K(weight, K_serum, sex):
#     """Рябов Г.А. Синдромы критических состояний, 1994, с 47.
#     :param float weight: real body weight
#
#     Potassium pH correction http://www.scymed.com/en/smnxps/pshfp089.htm
#     """
#     if sex == 'male':
#         body_K = 45 * weight
#     elif sex == 'female':
#         body_K = 35 * weight
#     else:
#         raise NotImplementedError


def electrolyte_Na(weight, Na_serum):
    """Assess blood serum sodium level.

    :param float weight: Real body weight, kg
    :param float Na_serum: mmol/L

    Расчёт дефицита и избытка Na+ [Курек 2013 стр. 130, 132]

    Hyponatremia
    ------------
    Корректировать Na медленно, иначе:
        * Было много Na (>145 mmol/L) {и вводится D5} -> отёк мозга
        * Было мало Na {вводится NaCl гипертонический} -> быстрое увличение осмолярности -> центральный понтинный миелинолиз
    Скорость:
        * Коррекция гипонатриемии в течение 2-3 суток путем инфузии NaCl 3% со скоростью 0,25-0,5 мл/кг/час [ПосДеж 90]
        * Восполнение Na не быстрее 10 mmol/L/24h    
    Возможно имеется гипокортицизм и потребуется вводить гидрокортизон.

    Hypernatremia
    -------------
        * Устраняется постепенно за 48 часов
        * Скорость снижения Na_serum <0.5 ммоль/л/ч или 12-15 ммоль/24h
        * If Na>150 mmol/L use D5 or NaCl 0.45 %


    Другие источники
    ================
        Маневич, Плохой 2000 с. 116:
            * Na_target 140 mmol/L
            * coefficient 0.2
            * Скорость снижения не быстрее 20 ммоль/л в сутки
            * Spironolactone 25 mg, Furosemide 10-20 mg

        Нейрореаниматология: практическое руководство 2017 - Гипонатриемия
            Формула отличается от Курека только другим коэффицинтом и Na_target.
            Необходимое количество натрия (ммоль) = [125 или желаемая концентрация Na+ − Na+ фактический (ммоль/л)] × 0.6 × масса (кг)
            Концентрацию натрия следует медленно (со скоростью 0,5-1 ммоль/л/ч) повышать до достижения уровня 125-130 ммоль/л.
    """
    if norm_Na[0] <= Na_serum <= norm_Na[1]:
        return "Na⁺ is ok ({:.0f}-{:.0f} mmol/L)".format(norm_Na[0], norm_Na[1])

    Na_high = norm_Na[1]
    Na_target = 140  # mmol/L (just mean value, from Маневич и Плохой, в Куреке не указано)
    Na_low = norm_Na[0]

    # Коэффициенты разные для восполнения дефицита Na, K?
    coef = 0.6  # for adult, non-elderly males (**default for hyponatremia**);
    # coef = 0.5  # for adult elderly males, malnourished males, or females;
    # coef = 0.45  # for adult elderly or malnourished females.
    total_body_water = weight * coef
    info = ''
    if Na_serum > Na_high:
        info += "Na⁺ is high (>{} mmol/L), expect coma, use D5, consider furesemide. ".format(Na_high)
        free_water_def = (1 - Na_target / Na_serum) * total_body_water * 1000  # ml just a proportion
        info += "Free water deficit is {:.0f} ml. Check osmolarity in ABG.".format(free_water_def)
        # Every 3 mmol above 145 mmol/L corresponds of 1 L volume deficiency [Рябов 1994, с 37, 43]
        # free_water_def2 = (Na_serum - 145) / 3 * 1000
        # info += " ('3 mmol' {:.0f} ml)\n".format(free_water_def2)

    elif Na_serum < Na_low:
        Na_deficiency = (Na_target - Na_serum) * total_body_water  # mmol
        # N.B.! Hypervolemic patient has low Na because of diluted plasma,
        # so it needs furosemide, not extra Na administration.
        info += "Na⁺ is low (<{} mmol/L), expect cerebral edema leading to seizures, coma and death. Na⁺ deficiency is {:.0f} mmol:\n".format(Na_low, Na_deficiency)
        info += "{}".format(solution_normal_saline(Na_deficiency))
    else:
        info += "Na⁺ in range ({:.0f}-{:.0f} mmol/L)".format(Na_low, Na_high)
    return info


def electrolyte_Cl(weight, Cl_serum):
    """Assess blood serum chloride level.

    :param float weight: Real body weight, kg
    :param float Cl_serum: mmol/L
    """
    Cl_low, Cl_high = norm_Cl[0], norm_Cl[1]
    if Cl_serum > Cl_high:
        return "Cl⁻ is high (>{} mmol/L), excessive NaCl infusion?".format(Cl_high)
    elif Cl_serum < Cl_low:
        # KCL replacement?
        return "Cl⁻ is low (<{} mmol/L). Vomit?".format(Cl_low)
    else:
        return "Cl⁻ is ok ({:.0f}-{:.0f} mmol/L)".format(norm_Cl[0], norm_Cl[1])
