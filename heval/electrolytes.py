#!/usr/bin/env python
# -*- coding: utf-8 -*-

__EASTER_TEXT__ = ("It's got what plants crave!", "It's got electrolytes!")
M_NaHCO3 = 84  # g/mol or mg/mmol
M_C6H12O6 = 180
M_NaCl = 58.5
M_KCl = 74.5

"""
Electrolyte disturbances and correction.

Author: Eugene Dvoretsky

Натрий и вода
-------------
1. Потеря чистой выоды через лёгкие и при потоотделении (лихорадка)
    Жажда появляется при дефиците воды массой 2 % от RBW, концентрированная моча, высокий Hct, Na 160 mmol/L, осмоляльность >300 мосм/кг.
    Вводить D50 до снижения осмоляльности до 290 мосм/кг, снижения Na до 140 mmol/L.
2. Потеря внеклеточной жидкости (кишечная непроходимость - 3-е пространство, рвота, понос)
    * Рвота - метаболический алкозоз, восполнять Cl- физраствором
    * Понос - метаболический алкалоз? восполнять NaHCO3, NaCL, KCl?

    deficiency = (1 - 0.4 / Hct) * 0.2 * body_weight  # [Рябов 1994, с 36]
    Каждые 3 mmol сверх 145 mmol/L соответствуют дефициту 1 литра дистиллированной воды [Рябов 1994, с 37, 43]

Если слишком высокий или слишком низкий, то
    * Предупреждать об опасных диапазонах электролитов
    * предлагат расчётные болюсы для коррекции:
        шиперкалиемия - глюкоза с инсулином (детский на кг и взрослый)
        гиперкалиемия - сода
        гипонатриемия - натрия хлорид гипертонический

Рассчитывать осмоляльность?
Na, Cl, CO2 - проверка достоверности результатов [Рябов 1994, с 42]
"""

def glucosae_solution(glu_mass, body_weight):
    """Глюкоза и инсулин.

    :param float glu_mass: масса глюкозы, г
    :param float body_weight: patient body weight, kg

    Соотношение глюкоза/инсулин, видимо, верно для питания и для болюсов при гиперкалиемии.

    * 1 ЕД на 3-5 г сухой глюкозы, скорость инфузии <= 0.5 г/кг/ч чтобы избежать глюкозурии [Мартов, Карманный справочник врача; RLSNET, Крылов Нейрореаниматология] (Ins 0.33-0.2 UI/г)
    * 1 ЕД на 4 г сухой глюкозы (если глюкозурия, то добавить инсулин или снизить скорость введения) [Курек, с 143; калькулятор BBraun; другие источники]
        * 0.25 IU/g
    """
    glu_mol = glu_mass / M_C6H12O6  # mmol/L
    ins_dosage = 0.25  # IU/g
    insulinum = glu_mass * ins_dosage

    # Glucose nutrition
    # Heat of combustion, higher value is 670 kcal/mol ~ 3.74 kcal/g https://en.wikipedia.org/wiki/Glucose
    # Usually referenced as 4.1 kcal/g
    # It's convenient to start with 0.15-0.2 g/kg/h, increasing speed up
    # to 0.5 g/kg/h. If hyperglycemia occurs, slow down or add more insulinum
    # to avoid glycosuria:
    # Hyperglycemia -> renal threshold (8.9-10 mmol/L) -> glycosuria
    info = "Glu {:.3f} g ({:.2f} mmol, {:.0f} kcal) + Ins {:.1f} IU ({:.2f} IU/g):\n".format(glu_mass, glu_mol, glu_mass * 4.1, insulinum, ins_dosage)

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


def kurek_electrolytes_K(weight, K_serum):
    """Расчёт дефицита и избытка K+.

    :param float weight: Real body weight, kg
    :param float K_serum: Potassium serum level, mmol/L

    Гипокалиемия (восполнение калия <3.5 mmol/L)
    --------------------------------------------
    # Комментарий:
    # 1. Так как на практике рассчитать дефицит калия невозможно, то вводим его
    # непрерывно в/в со скоростью 10 mmol/h и контролируем по КЩС каждые 2-4 часа в остром периоде
    #     * При изменениях на ЭКГ и мышечной дисфункции ускоряем до 20 mmol/h [Курек 2009 с 557]
    # 2. При выраженной гипокалиемии (<= 3 mmol/L) вводим сначала с физраствором
    #     * При восстановлении калия > 3 mmol/L вводим с глюкозо-инсулиновой смесью

    * Содержание K до 5 лет значительно выше [Курек 2013 с 38]
    * Если K+ <3 mmol/L, то введение глюкозы с инсулином может усугубить гипокалиемию, поэтому K+ вводить вместе с NaCl. [Курек ИТ 557]
    * Metabolic acidosis raises plasma K+ level by displacing it from cells [Рябов 1994, с 70]

    [130]:
        * Высшая суточная доза 4 mmol/kg/24h
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

    Гиперкалиемия
    -------------
    Неотложеные мероприятия при K >= 7 mmol/L или ЭКГ-признаках гиперкалиемии [131]
        * Glu 20 % 0.5 g/kg + Ins 0.3 IU/g

    Уменьшние количества ионизированного калия:
        * NaHCO3 2 mmol/kg (за 10-20 минут)
        * CaCl2 - только если есть изменения на ЭКГ [PICU: Electrolyte Emergencies]
        * гипервентиляция
    """
    K_high = 6  # Курек 2013, p 47 (6 mmol/L, 131 (7 mmol/L)
    K_target = 5.0  # mmol/L Not from book
    K_low = 3.5  # Курек 132

    info = ''
    if K_serum < K_low:
        info += "K is dangerously low (<{:.0f} mmol/L). Often associated with low Mg (Mg should be at least 1 mmol/L) and low Cl-.\n".format(K_low)
        info += "NB! Potassium calculations considered inaccurate, so use standard replacement speed and check ABG every 2-4 hours: "
        if weight < 40:
            info += "KCl {:.0f}-{:.0f} mmol/h for paed.\n".format(0.25 * weight, 0.5 * weight)
        else:
            info += "KCl 10-20 mmol/h (standard speed) for all adults will be ok.\n"

        # coefficient = 0.45  # новорождённые
        # coefficient = 0.4   # грудные
        # coefficient = 0.3   # < 5 лет
        coefficient = 0.2   # >5 лет

        K_deficiency = (K_target - K_serum) * weight * coefficient
        # K_deficiency += weight * 1  # mmol/kg/24h Should I add also суточная потребность?

        info += "Estimated K_deficiency (for paed too?) is {:.0f} mmol + ".format(K_deficiency)
        if K_deficiency > 4 * weight:
            info += "Too much potassium for 24 hours"

        glu_mass = K_deficiency * 2.5  # 2.5 g/mmol, ~10 kcal/mmol
        info += glucosae_solution(glu_mass, weight)

    elif K_serum >= K_high:
        glu_mass = 0.5 * weight
        info += "K is dangerously high (>{} mmol/L)\n".format(K_high)
        info += "Inject bolus for paed "
        info += glucosae_solution(glu_mass, weight)
        info += "Or standard adult Glu 40% 60 ml + Ins 10 IU [ПосДеж]\n"
        info += "RBW NaHCO3 4% {:.0f} ml (x2={:.0f} mmol) [Курек 2013]\n".format(2 * weight * M_NaHCO3 / 40, 2 * weight)
        info += "Don't forget furesemide, hyperventilation\n"
        info += "Don't forget Ca gluconate if ECG changes [PICU: Electrolyte Emergencies]"
    else:
        info += "K is ok"
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


def kurek_electrolytes_Na(weight, Na_serum):
    """Расчёт дефицита и избытка Na+ [Курек 2013 стр. 130, 132].

    :param float weight: kg
    :param float Na_serum: mmol/L

    Гипонатриемия
    -------------
    Целевой 140 mmol/L выглядит неплохо.
    Корректировать Na медленно, иначе:
        * Было много Na (>145 mmol/L) {и вводится D50} -> отёк мозга
        * Было мало Na {вводится NaCl гипертонический} -> быстрое увличение осмолярности -> центральный понтинный миелинолиз

    Коррекция гипонатриемии в течение 2-3 суток путем инфузии NaCl 3% со скоростью 0,25-0,5 мл/кг/час [ПосДеж 90]

    Гипернатриеамия
    ---------------
        * Устраняется постепенно за 48 часов
        * Скорость снижния Na <0.5 ммоль/л час или 12-15 ммоль/24h

    Маневич, Плохой с. 116:
        * Na_target 140 mmol/L
        * coefficient 0.2
        * Скорость снижения не быстрее 20 ммоль/л в сутки
    """
    Na_high = 150  # Курек 133
    Na_target = 140  # mmol/L (just mean value, from Маневич и Плохой, в Куреке не указано)
    Na_low = 130  # Курек 133

    info = ''
    if Na_serum > Na_high:
        info += "Na is dangerously high (>{} mmol/L), expect coma, use D50 & furesemide, NOT IMPLEMENTED".format(Na_high)
    elif Na_serum < Na_low:
        # Коэффициенты общие для восполнения дефицита Na, K?
        # coefficient = 0.45  # новорождённые
        # coefficient = 0.4   # грудные
        # coefficient = 0.3   # < 5 лет
        coefficient = 0.2   # >5 лет [Курек 2013, Маневич и Плохой]
        info += "Na is dangerously low (<{} mmol/L), expect seizure\n".format(Na_low)
        Na_deficiency = (Na_target - Na_serum) * weight * coefficient
        info += "Na_deficiency is {:.0f} mmol [Курек]".format(Na_deficiency)
    else:
        info += "Na is ok"
    return info


def krylov_electrolytes_Na(weight, Na_serum):
    """Восполнение дефицита Na согласно [Нейрореаниматология: практическое руководство 2017]

    :param float weight: kg
    :param float Na_serum: mmol/L

    Гипонатриемия
    -------------
    Формула отличается от Курека только коэффицинтом и указанием Na_target.
    Необходимое количество натрия (ммоль) = [125 или желаемая концентрация Na+ − Na+ фактический (ммоль/л)] × 0,6 × масса (кг)
    Концентрацию натрия следует медленно (со скоростью 0,5-1 ммоль/л/ч) повышать до достижения уровня 125-130 ммоль/л.

    Осмоляльность (мОсм/кг) = 2×(Na+ + K+) + Глю/18 + Моч/2,8 {Норма 280-285 мОсм/кг воды}
    """
    coefficient = 0.6
    Na_target = 125  # mmol/L, minimal acceptable value from book
    Na_low = Na_target

    info = ''
    if Na_serum < Na_target:
        info += "Na is dangerously low (<{} mmol/L)\n".format(Na_low)
        Na_deficiency = (Na_target - Na_serum) * weight * coefficient
        info += "Na_deficiency is {} mmol [Крылов]".format(Na_deficiency)
    else:
        raise NotImplementedError
    return info


if __name__ == '__main__':
    WEIGHT = 60  # kg
    NA_SERUM = 145
    K_SERUM = 2.
    # print(kurek_electrolytes_Na(WEIGHT, NA_SERUM))
    # print(krylov_electrolytes_Na(WEIGHT, NA_SERUM))
    print(kurek_electrolytes_K(WEIGHT, K_SERUM))
