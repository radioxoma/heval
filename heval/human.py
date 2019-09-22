#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
from drugs import *

"""
Calculations based on human height and weight.

Author: Eugene Dvoretsky

Function parameters tends to be in International System of Units.

------------------------

По росту и весу рассчитывается: BMI, BSA, идеальный вес.

На идеальный вес рассчитываются:
* Метаболические потребности: калории, масса пищи
    Курек 341
    При ожогах Курек 425-426
* Респираторные потребности: дыхательный объём, минутный объём, мёртвое пространство

На реальный вес рассчитываются:
* BMI, BSA
* Потребность в воде и электролитах?
    Курек 418
    + Перспирация ИВЛ/без ИВЛ?
* Диурез
* Дозировки некоторых лекарственных стредсв

Неизвестно:
* АД, ЧСС, ЧД.
"""

__abbr__ = """\
RBW - real body weight, kg
IBW - ideal body weight, kg, calculated
BSA - body surface area, m^2, calculated
BMI - body mass index, calculated
"""

# Average Belorussian male in 2008 >=18 years old
male_generic_by = {
    'height': 1.77,
    'weight': 69.,
    'sex': 'male',
    'body_temp': 36.6
    }

# Average Belorussian female in 2008 >=18 years old
female_generic_by = {
    'height': 1.65,
    'weight': 56.,
    'sex': 'female',
    'body_temp': 36.6
    }

female_owerweight_by = {
    'height': 1.62,
    'weight': 72.,
    'sex': 'female',
    'body_temp': 36.6
    }

male_thin = {  # Me
    'height': 1.86,
    'weight': 55.,
    'sex': 'male',
    'body_temp': 36.6
    }

paed = {  # 3 year old kid
    'height': 0.95,
    'weight': 16.5,
    'sex': 'paed',
    'body_temp': 36.6
    }


class HumanModel(object):
    def __init__(self):
        self._height = None
        self._sex = None
        self._age = None
        self.weight_ideal = None
        self._use_ibw = False

        self.comment = list()
        self.weight = None
        # self.age = age
        self.body_temp = 36.6
        self.drug_list = [
            Fentanyl(self),
            Propofol(self),
            Dithylin(self),
            Tracrium(self),
            Arduan(self),
            Esmeron(self)]

    def __str__(self):
        if not self.is_init():
            return "Human model not initialized with data"
        # Nutrition status
        info = "{} {:.0f}/{:.0f}:".format(self.sex.capitalize(), self.height * 100, self.weight)
        bmi_idx, bmi_comment = body_mass_index(height=self.height, weight=self.weight)
        if self.sex in ('male', 'female'):
            info += " BMI {:.1f} ({}),".format(bmi_idx, bmi_comment.lower())
        else:
            # Adult normal ranges cannot be applied to children
            info += " BMI {:.1f},".format(body_mass_index(height=self.height, weight=self.weight)[0])
        info += " BSA {:.3f} m^2.\n".format(body_surface_area(height=self.height, weight=self.weight))
        # Blood volume Human 77 ml/kg [https://en.wikipedia.org/wiki/Blood_volume]
        # Курек, Кулагин Анестезия и ИТ у детей, 2009 с 621; Курек 2013 231
        info += "RBW blood volume {:.0f}-{:.0f} ml (70-80 ml/kg для всех людей старше 3 мес, у новорождённых больше)\n".format(self.weight * 70, self.weight * 80)

        # if self.sex == 'paed':
        #     info += "{}\n".format(wetflag(weight=self.weight))
        info += "\n--- IN -----------------------------------------\n"
        info += "{}\n".format(self._info_in_respiration())
        info += "\n{}".format(self._info_in_fluids())
        info += "\n{}\n".format(self._info_in_electrolytes())
        info += "\n{}\n".format(self._info_in_energy())
        info += "\n--- OUT ----------------------------------------\n"  # Also CO2, feces
        info += "{}\n".format(self._info_out_fluids())
        if self.comment:
            info += "\nComments:\n{}\n".format('\n'.join(self.comment))
        return info

    def is_init(self):
        """Is class got all necessary data for calculations."""
        return all((self.height, self.weight, self.sex))

    @property
    def use_ibw(self):
        return self._use_ibw

    @use_ibw.setter
    def use_ibw(self, value):
        """Set flag to use calculated IBW instead real weight

        :param value bool: Use or not IBW, bool
        """
        self._use_ibw = value

    @property
    def sex(self):
        return self._sex

    @sex.setter
    def sex(self, value):
        self._sex = value
        self.reinit()

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        self._height = value
        self.reinit()

    @property
    def weight(self):
        if self._use_ibw:
            return self.weight_ideal
        else:
            return self._weight

    @weight.setter
    def weight(self, value):
        """You always can set real body weight, but not get it.

        Never use 'self._weight' directly beyond setter/getter code.
        """
        self._weight = value

    @property
    def age(self):
        return self._age

    @age.setter        
    def age(self, value):
        """Human age in years."""
        self._age = value

    def reinit(self):
        if self._sex and self._height:
            self.weight_ideal = self.body_mass_ideal(sex=self._sex, height=self._height)

    def _info_in_respiration(self):
        """Calulate optimal Tidal Volume for given patient (any gase mixture).

        IBW - ideal body weight
        RBW - real body weight

        Главное - рассчитать безопасный дыхательный объём (TV) при
            * повреждённых лёгких 6.5 ml/kg (ARDSNET, normal volume ventilation)
            * при здоровых лёгких 8.5 ml/kg (Drager documentation, типичная вентиляция во время ОЭТН)
        Если при вентиляции с таким рассчитанным TV Ppeak >35 (если пациент не поддыхивает и не кашляет)
        и Pplato > 30 (даже если поддыхивает), то TV уменьшается [видео Owning Oxylog].

        Расчёт минутного объёма (MV) не так важен, поскольку всё равно не будут совпадать с расчётным:
            * целевая норма ETCO2 35-45 mmHg (не ниже 28 mmHg - спазм сосудов ГМ и риск ишемического инсульта)
                pCO2 в артериаьной крови может быть на 5 mmHg выше у здорорых (с нормальным сердечным выбросом)
                или ОЧЕНЬ сильно выше (даже 60-80 mmHg) у пациентов с сердечной недостаточностью / ХОБЛ.
            * при повшении ETCO2/pCO2 пациент начинает делать дополнительные вдохи сам:
                * В случае вспомогательной ИВЛ в сознании нужно настроить триггер вентилятора и Psupp
                * Во время ОЭТН увеличить MV, чтобы подавить самостоятельные вдохи и снизить использование миорелаксантов, беспокойство хирургов
            * Во время анестезии использовать TV вместе с более-менее подходщей частатой дыхания.
                Настройка подходящего для данного пациента MV (за счёт F или TV) в соответствии с ETCO2 монитора или pCO2 по КЩС.
                Удерживать на нижней границе нормы, чтобы не поддыхивал

        
        Dead space is 2.2 ml/kg IBW for both adults and paed, so TV _must_ be
        double of 2.2 ml/kg [Hamilton p.455; Курек 2013 стр. 63]

        По дыхательным объёмам у детей TV одинаковый, F у новорождённых больше, MV разный.
        [Курек 2013 стр. 63, 71]
        """
        VDaw = 2.2 * self.weight_ideal
        Tv_min = 2 * VDaw  # ml Lowest reasonable tidal volume

        def normal_minute_ventilation(ibw):
            """Calculate normal minute ventilation for humans with IBw >=3 kg.

            Calculation accomplished according to ASV ventilation mode from
            Hamilton G5 Ventilator - Operators manual en v2.6x 2016-03-07 p 451 or C-11

            Example
            mv, l/kg * ibw, kg = Vd, l/min
            0.2 l/kg * 15 kg = 3 l/min

            :param float ibw: Ideal body mass for given adult or paed >=3 kg.
            :return: l/kg/min
            """
            # Approximation to Hamilton graph
            if ibw < 3:
                print("WARNING: MV calculation for paed <3 kg is not supported")
                mv = 0
            elif 3 <= ibw < 5:
                mv = 0.3
            elif 5 <= ibw < 15:
                mv = 0.3 - 0.1 / 10 * (ibw - 5)
            elif 15 <= ibw < 30:
                mv = 0.2 - 0.1 / 15 * (ibw - 15)
            else:  # >= 30:
                mv = 0.1
            return mv

        info = ""
        mv = normal_minute_ventilation(self.weight_ideal)  
        Vd = mv * self.weight_ideal  # l/min
        if self.weight_ideal < 3:
            info += " * WARNING: MV calculation for paed <3 kg is not supported\n"
        else:
            info += "IBW respiration for {} {:.1f} kg [Hamilton ASV]\n".format(self.sex, self.weight_ideal)
            info += "MV x{:.2f} L/kg/min={:.3f} L/min. ".format(mv, Vd)
            info += "VDaw is {:.0f} ml, so TV must be >{:.0f} ml\n".format(VDaw, Tv_min)
            info += " * TV x6.5={:.0f} ml, RR {:.0f}/min\n".format(self.weight_ideal * 6.5, Vd * 1000 / (self.weight_ideal * 6.5))
            info += " * TV x8.5={:.0f} ml, RR {:.0f}/min".format(self.weight_ideal * 8.5, Vd * 1000 / (self.weight_ideal * 8.5))
        return info

    def _info_in_fluids(self):
        """Fluids.
        """
        # Панкреатит жидкость 50-70 мл/кг/сут, [Пособие дежуранта 2014, стр. 259]
        info = ""
        info = "BSA all ages fluids demand {:.0f} ml/24h\n".format(body_surface_area(height=self.height, weight=self.weight) * 1750)
        if self.sex in ('male', 'female'):
            h2o_min = 30 * self.weight
            h2o_max = 35 * self.weight
            info += "RBW adult fluids demand {:.0f}-{:.0f} ml/24h (30-35 ml/kg/24h) [ПосДеж]\n".format(h2o_min, h2o_max)
            info += "Max speed {:.0f} ml/h (120 ml/kg/h) [Курек]\n".format(2 * 60 * self.weight)  # [2.0 ml/kg/min Курек 2013 с 127]
            info += "Bolus {:.0f} ml (20-30 ml/kg)".format(self.weight * 25)

            # Видимо к жидкости потребления нужно добавлять перспирационные потери
            # persp_ros = 10 * self.weight + 500 * (self.body_temp - 36.6)
            # info += "\nRBW Perspiration: {:.0f} ml/24h [Расенок]".format(persp_ros)

            # Перспирационные потери – 5-7 мл/кг/сут на каждый градус выше 37°С [Пособие дежуранта 2014, стр. 230]
            # Точная оценка перспирационных потерь невозможна. Формула из "Пособия дежуранта" примерно соответствует [таблице 1.6 Рябов 1994, с 31 (Condon R.E. 1975)]
            if self.body_temp > 37:
                deg = self.body_temp - 37
                info += "\n + perspiration fluid loss {:.0f}-{:.0f} ml/24h (5-7 ml/kg/24h for each °C above 37°С)".format(
                    5 * self.weight * deg,
                    7 * self.weight * deg)
        elif self.sex == 'paed':
            """
            Объём инфузии = ЖП + текущие потери

            * ФП рассчитывается по формуле Валлачи `100 - (3 х возраст в годах) = ml/kg/24h`
            * Холидей и Сигар (https://meduniver.com/Medical/nefrologia/raschet_poddergivaiuchei_infuzionnoi_terapii.html).
            """
            hs_fluid = fluid_req_holidaysegar_mod(self.weight)
            info += "RBW paed fluids demand {:.0f} ml/24h or {:.0f} ml/h [Holliday-Segar]\n".format(hs_fluid, hs_fluid/24)
            info += "Max speed {:.0f} ml/h (72 ml/kg/h) [Курек]".format(1.2 * 60 * self.weight)  # [1.2 ml/kg/min Курек 2013 с 127]
            """
            Тестовый болюс при низком давлении у детей 20 мл/кг?
            [IV Fluids in Children](https://www.ncbi.nlm.nih.gov/books/NBK349484/)
                * fluids, calculated on the basis of insensible losses within the range 300–400 ml/m2/24 hours plus urinary output
                * Т.е. количество утилизированный на метаболические нужды воды + диурез + перспирация + другие потери
            """
        return info

    def _info_in_electrolytes(self):
        """Daily electrolytes demand.

         [Заболоцкий Д.В. 20-я сессия МНОАР в Голицыно 2019]: Предупреждение о невозможности коррекции Na, K за одни сутки без угрозы
            * быстрого увеличения Na после коррекции гипонатриемии > Быстрого увличения осмолярности > центрального понтинного миелинолиза.
            * Восполнение Na не быстрее 10 mmol/L/24h
        """
        if self.sex in ('male', 'female'):
            info = " * Na+\t{:.0f} mmol/24h [~1 mmol/kg/24h]\n".format(self.weight)
            info += " * K+\t{:.0f} mmol/24h [~1 mmol/kg/24h]".format(self.weight)
            return info
        else:
            return "Don't know how to calculate electrolytes for paed. Check Курек 2013 расчёт дефицита K, Na стр. 130"

    def _info_in_energy(self):
        """Attempt to calculate energy requirements for an human.

        Взрослый мужчина
        3. Суточная потребность в энергии составляет 24-30 ккал/кг [тесты БелМАПО]
        1. _Минимальная_ дневная потребность в глюкозе 2 г/кг в сутки
        2. Дневная потребность в аминокислотах 0,7 г/кг в сутки
        4. Суточная потребность в жирах 2 г/кг в сутки

        Толстым рассчитывать на идеальный, истощённым на реальный [РМАНПО]
        Углеводы <=5-6 г/кг/24h если выше, то риск жирового гепатоза [РМАНПО]
        Липиды <=0.2 г/кг/час независимо от возраста [Курек 2013], 0.15 г/кг/час [РМАНПО]

        Нейрореаниматология: практическое руководство 2017
        --------------------------------------------------
        20-25, 30-35 ккал/сут

        Баланс азота? Азот в моче говорит о катаболизме.

        Белок 1-2 г/кг/сут (на 1 г белка должно быть >=150 ккал небелковых)
        Жир 1-1.5 г/кг/сут (30-35 % энергетических потребностей)
        Угеводы 5-6 г/кг/сут (50-70 % небелковых карорий). Скорость окисления глюкозы у человека не быстрее 7 мг/кг/мин ~ 0,5 г/кг/ч,
        поэтому вводить глюкозу не быстрее 5 мг/кг/мин.

        Лейдерман И.Н. и соаторы 2004
        -----------------------------
          * Белки 4.2 ккал/г (5.4 при сжигании)
          * Жиры 9.3 ккал/г
          * Углеводы 4.1 ккал/г

        Костючёнко Нутритивная терапия 2016, с. 9
        -----------------------------------------
          * Использование формулы Харриса-Бенедикта не несет преимуществ по
            сравнению с использованием упрощенного предиктивного уравнения
          * 25-30 kcal/kg/24h

        Пособие дежуранта 2014
        ----------------------
          * Расчёт на идеальный вес "25 * (self.height * 100 - 100)" [с 232]
          * Энергия 20-30 ккал/кг, ожоги – до 40 ккал/кг [с 238]
          * Жидкость 20-40 мл/кг

        Соотношение 1:1:4
        Таблица 2, с 238.
        Белки        1.0-1.5 г/кг, Аминокислоты 1.2-1.5 г/кг
        Жиры         1.0-1.5 г/кг (30-40% от общей энергии)
        Глюкоза      4.0-5.0 г/кг (60-70% от общей энергии)
        """
        info = ''
        if self.sex in ('male', 'female'):
            info += "Суточная потребность в энергии для взрослых [ПосДеж]:\n"
            info += " * {:.0f} kcal/24h ({} kcal/kg/24h IBW):\n".format(25 * self.weight_ideal, 25)
            info += " * Аминокислоты {:3.0f}-{:3.0f} г/24h (1.2-1.5 г/кг/24h)\n".format(1.2 * self.weight_ideal, 1.5 * self.weight_ideal)
            info += " * Жиры         {:3.0f}-{:3.0f} г/24h (1.0-1.5 г/кг/24h) (30-40% от общей энергии)\n".format(1.0 * self.weight_ideal, 1.5 * self.weight_ideal)
            info += " * Глюкоза      {:3.0f}-{:3.0f} г/24h (4.0-5.0 г/кг/24h) (60-70% от общей энергии)\n".format(4.0 * self.weight_ideal, 5.0 * self.weight_ideal)
            if self.age:
                info += "Basal metabolic rate for adults:\n"
                info += " * {:.0f} kcal/24h Harris-Benedict (1984) \n".format(bmr_harris_benedict(self.height, self.weight, self.sex, self.age))
                info += " * {:.0f} kcal/24h Mifflin (1990)\n".format(bmr_mifflin(self.height, self.weight, self.sex, self.age))
            else:
                info += "Enter age to calculate BMR"
        else:
            # Looks like paed needs more then 25 kcal/kg/24h (up to 100?) [Курек p. 163]
            # стартовые дозы глюкозы [Курек с 143]
            info += "Don't know how to calculate energy for paed. Check Курек АиИТ у детей 3-е изд. 2013, стр. 137"
        return info


    def _info_out_fluids(self):
        """Minimal required urinary output 0.5-1 ml/kg/h.

        У детей диурез значительно выше, у новорождённых 2.5 ml/kg/h.
        Выделение мочи <0.5 мл/кг/ч >6 часов - самостоятельный критерии ОПП
        """
        if self.sex in ('male', 'female'):
            out = "RBW adult urinary output:\n"
            out += " * x0.5={:.0f} ml/h, {:.0f} ml/24h (target >0.5 ml/kg/h)\n".format(0.5 * self.weight, 0.5 * self.weight * 24)
            out += " * x1  ={:.0f} ml/h, {:.0f} ml/24h".format(self.weight, self.weight * 24)
        if self.sex == 'paed':
            # Not lower than 1 ml/kg/h in paed [Курек 2013 122, 129]
            out = "RBW paed urinary output:\n"
            out += " * x1  ={:3.0f} ml/h, {:.0f} ml/24h (target >1 ml/kg/h).\n".format(self.weight, self.weight * 24)
            out += " * x3.5={:3.0f} ml/h, {:.0f} ml/24h much higher in infants (up to 3.5 ml/kg/h)".format(3.5 * self.weight, 3.5 * self.weight * 24)
        return out

    def medication(self):
        if not self.is_init():
            return "Medication not initialized"
        else:
            return "\n".join(["* " + str(d) for d in self.drug_list])

    def body_mass_ideal(self, sex, height):
        """Evaluate ideal body weight (IBW) for all ages.

        Check https://en.wikipedia.org/wiki/Human_body_weight#Ideal_body_weight

        Понятие идеальной массы тела было введено во время изучения клиренса лекарственных средств,
        так как клиренс ЛС больше кореллирует с идеальной, чем с реальной массой тела.
        Ideal weight for minute volume calculation taken from Hamilton G5 documentation
            1. Formulas for adult male/female taken from Hamilton G5 Ventilator - Operators manual ru v2.6x 2017-02-24 page 197
            2. Precalculated tables 4-1, 4-2 to check formulas was taken from RAPHAEL-ops-manual-ru-624150.02 2015-09-24
            3. Traub-Kichen formula for paed taken directly from publications, not from hamilton docs

        Определение должной массы тела (ДМТ) [посдеж 2014, страница 211]:
            self.weight_ideal = 50 +   0.91   (height * 100 - 152.4);   # Для мужчин
            self.weight_ideal = 45.5 + 0.91 (height * 100 - 152.4);   # Для женщин
            Упрощенный вариант расчета для обоих полов: self.weight_ideal = height – 100
        """
        if sex == 'male':  # Adult male, negative value with height <97 cm
            # Как в таблице 4-1 руководства Hamilton, взятых от Pennsylvania Medical Center
            weight_ideal = 0.9079 * height * 100 - 88.022  # kg
        elif sex == 'female':  # Adult female, negative value with height <101 cm
            # Как в таблице 4-1 руководства Hamilton, взятых от Pennsylvania Medical Center
            weight_ideal = 0.9049 * height * 100 - 92.006  # kg
        elif sex == 'paed':
            if not 0.74 <= height <= 1.524:  # Ranges from paper
                self.comment.append("WARNING: paed IBW estimation accurate only for height 0.74-1.524 m.\n".format(height))
            # Traub-Kichen formula. [Am J Hosp Pharm. 1983 Jan;40(1):107-10](https://www.ncbi.nlm.nih.gov/pubmed/6823980)
            # For children over 74 cm and aged 1 to 17 years.
            weight_ideal = 2.396 * math.exp(0.01863 * height * 100)
        return weight_ideal


def body_mass_index(height, weight):
    """Body mass index and description.

    NB! Normal ranges in children differ from adults.

    :param float height: meters
    :param float weight: kilograms

    http://apps.who.int/bmi/index.jsp?introPage=intro_3.html
    """
    bmi = weight / height ** 2

    # For adults
    if bmi < 18.5:
        descr = "Underweight: "
        if bmi < 16:
            descr += "Severe thinness"
        elif 16 <= bmi < 17:
            descr += "Moderate thinness"
        elif 17 <= bmi:
            descr += "Mild thinness"
    elif 18.5 <= bmi < 25:
        descr = "Normal weight"
    elif 25 <= bmi < 30:
        descr = "Overweight, pre-obese"
    elif bmi >= 30:
        descr = "Obese "
        if bmi < 35:
            descr += "I"
        elif 35 <= bmi < 40:
            descr += "II"
        elif bmi >= 40:
            descr += "III"
    return bmi, descr


def body_surface_area(height, weight):
    """Human body surface area (Du Bois formula).

    BSA = (W ** 0.425 * H ** 0.725) * 0.007184

    :param float height: Patient height, meters
    :param float weight: Real body mass, kg
    :return:
        m2, square meters
    :rtype: float

    body_surface_area(1.86, 70)
    >>> 1.932

    References
    ----------
    [1] https://en.wikipedia.org/wiki/Body_surface_area
    [2] DuBois D, DuBois EF. A formula to estimate the approximate surface area if height and weight be known. Arch Intern Medicine. 1916; 17:863-71.
    [3] http://www-users.med.cornell.edu/~spon/picu/calc/bsacalc.htm
    """
    return 0.007184 * weight ** 0.425 * (height * 100) ** 0.725


def bmr_harris_benedict(height, weight, sex, age):
    """Basal metabolic rate, revised Harris-Benedict equation (1984).

    Examples
    --------

    >>> bmr_harris_benedict(168, 59, 'female', 55)
    1275.4799999999998

    References
    ----------
    [1] https://en.wikipedia.org/wiki/Basal_metabolic_rate
    [2] Roza AM, Shizgal HM (1984). "The Harris Benedict equation reevaluated:
        resting energy requirements and the body cell mass" (PDF).
        The American Journal of Clinical Nutrition. 40 (1): 168–182.

    :param float height: Height, meters
    :param float weight: Weight, kg
    :param str sex: Choose 'male', 'female'.
    :param float age: Age, years
    :return: 
        BMR, kcal/24h
    :rtype:
        float
    """
    if sex == 'male':
        bmr = 13.397 * weight + 4.799 * height * 100 - 5.677 * age + 88.362
    elif sex == 'female':
        bmr = 9.247 * weight + 3.098 * height * 100 - 4.330 * age + 447.593
    elif sex == 'paed':
        raise ValueError("Harris-Benedict equation BMR calculation for paed not supported")
    return bmr


def bmr_mifflin(height, weight, sex, age):
    """Basal metabolic rate, Mifflin St Jeor Equation (1990).

    Considered as more accurate than revised Harris-Benedict equation.

    Examples
    --------

    >>> bmr_mifflin(168, 59, 'female', 55)
    1204.0

    References
    ----------
    [1] https://en.wikipedia.org/wiki/Basal_metabolic_rate
    [2] Mifflin MD, St Jeor ST, Hill LA, Scott BJ, Daugherty SA, Koh YO (1990).
        "A new predictive equation for resting energy expenditure in healthy
        individuals". 
        The American Journal of Clinical Nutrition. 51 (2): 241–247. 

    :param float height: Height, meters
    :param float weight: Weight, kg
    :param str sex: Choose 'male', 'female'.
    :param float age: Age, years
    :return: 
        BMR, kcal/24h
    :rtype:
        float
    """
    bmr = 10 * weight + 6.25 * height * 100 - 5 * age
    if sex == 'male':
        bmr += 5
    elif sex == 'female':
        bmr -= 161
    elif sex == 'paed':
        raise ValueError("Mufflin BMR calculation for paed not supported")
    return bmr


def mean_arterial_pressure(SysP, DiasP):
    """Расчёт Среднего АД (mean arterial pressure, MAP)

    :param float SysP: Systolic pressure, mmHg
    :param float DyasP: Diastolic pressure, mmHg
    :return:
        Mean arterial pressure, mmHg
    :rtype: float

    >>> mean_arterial_pressure(120, 87)
    >>> 98.0  # (120 + 2 * 87) / 3
    """
    # return (SysP - DiasP) / 3 + DiasP  # Just different algebra
    return (SysP + 2 * DiasP) / 3


def parcland_volume(weight, burned_surface):
    """Calculate Ringer's lactate solution volume to support burned patient.

    Formula used to calculate volume of crystalloids (Ringer's lactate) to
    compensate fluid loss in burned patients in first 24 hours.
    Рассчитанный объём добавляется к жидкости поддержания у педиатрических пациентов [4].

    Increase volume if urinary output <0.5 ml/kg/h). Don't use potassium solutions!

    Examples
    --------

    V = 4 * m * A%
    V = 4 x 75 kg x 20% = 6000 ml


    References
    ----------

    [1] https://en.wikipedia.org/wiki/Parkland_formula
    [2] Клинические случаи в анестезиологии А.П. Рид, Дж. Каплан 1995 г, с 309
    [3] https://www.remm.nlm.gov/burns.htm
    [4] В.В. Курек, А.Е. Кулагин «Анестезия и интенсивная терапия у детей» изд. третье 2013, с 418

    :param float weight: Real body mass (not ideal), kg
    :param float burned_surface: Percent (not fraction) of body surface area
        affected by burns of SECOND degree and worse.
        See 'Wallace rule of nines' for area estimation
        При ожоге > 50% поверхности тела вводят то же количество как для 50 %.
        Т.е. этот параметр не может быть больше 50.
    :return:
        Total volume for 24 hours after burn incident, ml.
        The first half of this amount is delivered within 8 hours from
        the burn incident (not from time of admission to ED), and the
        remaining fluid is delivered in the next 16 hours.
    :rtype: float
    """
    # Or 5000 ml/m2 of burned area?
    if burned_surface > 50:
        burned_surface = 50
    print("Warning: burn area set to 50 %")
    volume_ml = 4 * weight * burned_surface
    print("Patient {} kg with burns {} % of body surface area: deliver {} ml of lactated Ringer's within 24 hours".format(
        weight, burned_surface, volume_ml))
    print("{0:.0f} ml within first 8 hours\n{0:.0f} ml within next 16 hours".format(volume_ml / 2.))

    return volume_ml


def fluid_req_holidaysegar_mod(rbm):
    """Расчёт суточной потребности в жидкости.

    Looks like Holliday-Segar method, but modified for infants with body weight <3 kg.

    References
    ----------
    The maintenance need for water in parenteral fluid therapy, Pediatrics 1957. Holliday Segar
    Курек 2013, стр. 121 или 418. По идее, дложен соответствовать таблице с 121, но для >20 кг это не так.

    :param float rbm: Real body mass, kg
    """
    if rbm < 2:  # Kurek modification?
        return 150 * rbm
    elif 2 <= rbm < 10:  # 100 ml/kg for the 1st 10 kg of wt
        return 100 * rbm
    elif 10 <= rbm < 20:  # 50 ml/kg for the 2nd 10 kg of wt
        return 1000 + 50 * (rbm - 10)
    else:  # 20 kg and up
        return 1500 + 20 * (rbm - 20)


def wetflag(age=None, weight=None):
    """Fast and not very precise formulas for calculations in children.

    https://www.resus.org.uk/faqs/faqs-paediatric-life-support/

    EPALS course uses the simple acronym W E T Fl A G for children over the age of 1 year and up to 10 years old. This equates to:

    Example for a 2 year old child:
    W  = (2 + 4) x 2 = 12 kg
    E  = 12 x 4 = 48 J
    T  = 2/4 +4 = 4.5 mm ID tracheal tube uncuffed
    Fl = 20 mL x 12 kg = 240 mL 0.9% saline
    A  = 10 micrograms x 12 kg = 120 micrograms 1:10,000 = 1.2 mL
    G  = 2 mL x 12 kg = 24 mL 10% Dextrose

    Whilst this is not evidence based, it provides a simple, easy to remember framework in a stressful situation reducing the risk or error.

    June 2016

    :param float age: years, 1-10
    :param float weight: kg, jus a fallback now
    """
    if not any((age, weight)):
        raise ValueError("Specify children age or weight")
    if weight:  # Don't want to add age field now
        age = weight / 2 - 4
    if not 1 <= age <= 10:
        return "WETFlAG: Age must be in range 1-10 years"

    W = (age + 4) * 2   # Weight, kg
    E = 4 * W  # Energy, Joules. Mono or bifasic?
    T = age / 4 + 4  # Tube (endotracheal), ID mm (uncuffed)
    Fl = 20 * W  # Fluids (bolus), ml of isotonic fluid (caution in some cases)
    A = 10 * W  # Adrenaline 10 mcg/kg (1:10000 solution = 0.1 mL/kg)
    G = 2 * W # 2 mL/kg Glucose 10 %
    info = """\
WETFlAG report for {} yo, weight {} kg paed:
    Energy for defib {:.0f} J
    Tube {:.1f} mm
    Fluid bolus {:.0f} ml of isotonic fluid
    Adrenaline {:.0f} mcg
    Glucosae 10 % {:.0f} ml""".format(age, W, E, T, Fl, A, G)
    return info


if __name__ == '__main__':
    # HModel = HumanModel()
    # HModel.sex = male_thin['sex']
    # HModel.height = male_thin['height']
    # HModel.use_ibw = True
    # HModel.weight = male_thin['weight']
    # print(HModel)
    # print(HModel.medication())
    print(bmr_harris_benedict(168/100, 59, 'female', 55))
    print(bmr_mifflin(168/100, 59, 'female', 55))
