# -*- coding: utf-8 -*-
"""
Calculations based on human height and weight.

Author: Eugene Dvoretsky

Function parameters tends to be in International System of Units.
"""

import math
import copy
from itertools import chain
from heval import abg
from heval import drugs


# https://news.tut.by/society/311809.html
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

child = {  # 3 year old kid
    'height': 0.95,
    'weight': 16.5,
    'sex': 'child',
    'body_temp': 36.6
}

newborn = {
    'height': 0.5,
    'weight': 3.6,
    'sex': 'child',
    'body_temp': 36.6
}


class HumanBodyModel(object):
    def __init__(self):
        self.debug = False
        self._int_prop = ('height', 'age', 'weight', 'body_temp')
        self._txt_prop = ('sex', 'comment')
        self._sex = None
        self._height = None
        self._age = None

        self.weight = None
        self._use_ibw = False
        self._weight_ideal_valid = False
        self._weight_ideal_method = ""
        self.weight_ideal = None  # Changes only at sex/weight change

        self.blood = abg.HumanBloodModel(self)
        self.drugs = drugs.HumanDrugsModel(self)
        self.body_temp = 36.6
        self.comment = dict()  # For warnings

    def __str__(self):
        int_prop = {}
        for attr in chain(self._int_prop, self._txt_prop):
            int_prop[attr] = getattr(self, attr)
        return "HumanBody: {}".format(str(int_prop))

    def populate(self, properties):
        """Populate model from data structure.

        :param dict properties: Dictionary with model properties to set.
            Key names must be equal to class properties names.
        :return:
            Not applied properties (including nested models)
        :rtype: dict
        """
        prop = copy.deepcopy(properties)  # Avoid changing passed object
        for item in self._int_prop:
            if item in prop:
                setattr(self, item, float(prop.pop(item)))
        for item in self._txt_prop:
            if item in prop:
                setattr(self, item, prop.pop(item))

        # Push the rest of the dict deeper
        self.blood.populate(prop)
        return prop

    def describe_body(self):
        if not self.is_init():
            return "Empty human model (set sex, height, weight)"
        info = ""
        if self.sex == 'child':
            try:
                br_code, br_age, br_weight = get_broselow_code(self.height)
                info += "BROSELOW TAPE: {}, {}, ~{:.1f} kg.\n".format(
                    br_code.upper(), br_age.lower(), br_weight)
            except ValueError:
                pass

        info += "{} {:.0f}/{:.0f}:".format(self.sex.capitalize(), self.height * 100, self.weight)

        if self._weight_ideal_valid:
            info += " IBW {:.1f} kg [{}],".format(self.weight_ideal, self._weight_ideal_method)
        else:
            info += " IBW can't be calculated for this height, enter weight manually."
        bmi_idx, bmi_comment = body_mass_index(height=self.height, weight=self.weight)

        if self.sex in ('male', 'female'):
            info += " BMI {:.1f} ({}),".format(bmi_idx, bmi_comment.lower())
        else:
            # Adult normal ranges cannot be applied to children
            info += " BMI {:.1f},".format(bmi_idx)

        info += " BSA {:.3f} m².\n".format(self.bsa)

        # Value 70 ml/kg used in cardiopulmonary bypass. It valid for humans
        # older than 3 month. ml/kg ratio more in neonates and underweight
        info += "Total blood volume {:.0f} ml (70 ml/kg) or weight indexed {:.0f} ml [Lemmens].\n".format(
            self.weight * 70, self.total_blood_volume)

        # if self.sex == 'child':
        #     info += "{}\n".format(wetflag(weight=self.weight))
        info += "\n--- IN -----------------------------------------\n"
        info += "{}\n".format(self._info_in_respiration())
        info += "\n{}".format(self._info_in_fluids())
        info += "\n{}\n".format(self._info_in_electrolytes())
        info += "\n{}\n".format(self._info_in_energy())
        info += "\n--- OUT ----------------------------------------\n"  # Also CO2, feces
        info += "{}\n".format(self._info_out_fluids())
        if self.comment:
            info += "\nComments:\n{}\n".format(self.comment)
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
        """One from: 'male', 'female', 'child'."""
        self._sex = value
        if all((self.height, self.sex)):  # optimization
            self._set_weight_ideal()

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        """Human height in meters."""
        self._height = value
        if all((self.height, self.sex)):  # optimization
            self._set_weight_ideal()

    @property
    def weight(self):
        if self._use_ibw:
            return self.weight_ideal
        else:
            return self._weight

    @weight.setter
    def weight(self, value):
        """Human weight in kilograms.

        You always can set real body weight, but not get it.
        Never use 'self._weight' directly beyond setter/getter code.
        """
        self._weight = value

    def _set_weight_ideal(self):
        """Evaluate ideal body weight (IBW) for all ages.

          * https://en.wikipedia.org/wiki/Human_body_weight#Ideal_body_weight
          * https://en.wikipedia.org/wiki/Birth_weight
          * https://en.wikipedia.org/wiki/Growth_chart

        По росту и весу рассчитывается: BMI, BSA, идеальный вес.

        IBW is used for calculation of:
            * Metabolic needs: kcal/24h
                Курек 341
                При ожогах Курек 425-426
            * Respiratory volumes: TV, MV, dead space
            * Some drug dosage

        Real body weight is used for:
            * BMI, BSA
            * In children?
            * Потребность в воде и электролитах?
                Курек 418
                + Перспирация ИВЛ/без ИВЛ?
            * Urine output
            * Some drug dosage

        Unknown RBW or IBW:
            * Blood pressure, heart rate.

        Понятие идеальной массы тела было введено во время изучения клиренса
        лекарственных средств, так как клиренс ЛС больше кореллирует с
        идеальной, чем с реальной массой тела.
        Ideal weight for minute volume calculation taken from Hamilton G5 documentation
            1. Formulas for adult male/female taken from Hamilton G5 Ventilator - Operators manual ru v2.6x 2017-02-24 page 197
            2. Precalculated tables 4-1, 4-2 to check formulas was taken from RAPHAEL-ops-manual-ru-624150.02 2015-09-24
            3. Traub-Kichen formula for children taken directly from publications, not from Hamilton docs

        Определение должной массы тела (ДМТ) [посдеж 2014, страница 211]:
            self.weight_ideal = 50 +   0.91   (height * 100 - 152.4);   # Для мужчин
            self.weight_ideal = 45.5 + 0.91 (height * 100 - 152.4);   # Для женщин
            Упрощенный вариант расчета для обоих полов: self.weight_ideal = height – 100
        """
        # IBW estimation formulas cover not all ranges. This flag helps prevent
        # misuse of explicitly invalid IBW in e.g. respirarory calculations
        self._weight_ideal_valid = True
        if self.sex == 'male':  # Adult male, negative value with height <97 cm
            # Как в таблице 4-1 руководства Hamilton, взятых от Pennsylvania Medical Center
            self.weight_ideal = 0.9079 * self.height * 100 - 88.022  # kg
            self._weight_ideal_method = "Hamilton"
        elif self.sex == 'female':  # Adult female, negative value with height <101 cm
            # Hamilton manual, table 4-1. Hamilton adopted from Pennsylvania Medical Center
            self.weight_ideal = 0.9049 * self.height * 100 - 92.006  # kg
            self._weight_ideal_method = "Hamilton"
        elif self.sex == 'child':
            # Brocelow tape range. Temporary and only for lowest height
            if 0.468 <= self.height < 0.74:
                # print("WARNING: Braselow IBW for range 0.468-0.74 m")
                self._weight_ideal_method = "Broselow"
                self.weight_ideal = get_broselow_code(self.height)[2]
            elif 0.74 <= self.height <= 1.524:
                # Traub-Kichen 1983 can predict IBW for children aged 1 to 17 years
                # and height 0.74-1.524 m
                # [Am J Hosp Pharm. 1983 Jan;40(1):107-10](https://www.ncbi.nlm.nih.gov/pubmed/6823980)
                self._weight_ideal_method = "Traub-Kichen 1983"
                self.weight_ideal = 2.396 * math.exp(0.01863 * self.height * 100)
            else:
                print("WARNING: IBW cannot be calculated for children with this height")
                self._weight_ideal_valid = False

    @property
    def bsa(self):
        """Body surface area, m2, square meters."""
        return body_surface_area(height=self.height, weight=self.weight)

    @property
    def total_blood_volume(self):
        """Calculate total blood volume (TBV) by Lemmens-Bernstein-Brodsky.

        Considered as more accurate, than Nadler 1962 method.

        [1] Lemmens HJ, Bernstein DP, Brodsky JB. Estimating blood volume in obese and morbidly obese patients. Obes Surg. 2006 Jun;16(6):773-6.
            https://www.ncbi.nlm.nih.gov/pubmed/16756741
        [2] https://www.ncbi.nlm.nih.gov/books/NBK526077/

        Blood volume Human 77 ml/kg [https://en.wikipedia.org/wiki/Blood_volume]
        Курек, Кулагин Анестезия и ИТ у детей, 2009 с 621; Курек 2013 231

        [Feldschuh, J., & Enson, Y. (1977). Prediction of the normal blood volume. Relation of blood volume to body habitus. Circulation, 56(4), 605–612. doi:10.1161/01.cir.56.4.605]:
           * Blood volume to body mass ration in doesn't remain constant even in one individual during one month
           * Thin man has higher TBV (95-105 ml/kg) than fat (45 ml/kg)
           * Men: 72.6 ml/kg, 2566 ml/m2; women: 66.3 ml/kg, 2245 ml/m2

        :return: Total blood volume, ml
        """
        bmi = self.weight / self.height ** 2
        return 70 / math.sqrt(bmi / 22) * self.weight

    @property
    def age(self):
        return self._age

    @age.setter
    def age(self, value):
        """Human age in years."""
        self._age = value

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


        Dead space is 2.2 ml/kg IBW for both adults and children, so TV _must_ be
        double of 2.2 ml/kg [Hamilton p.455; Курек 2013 стр. 63]

        По дыхательным объёмам у детей TV одинаковый, F у новорождённых больше, MV разный.
        [Курек 2013 стр. 63, 71]
        """
        def normal_minute_ventilation(ibw):
            """Calculate normal minute ventilation for humans with IBW >=3 kg.

            Calculation accomplished according to ASV ventilation mode from
            Hamilton G5 Ventilator - Operators manual en v2.6x 2016-03-07 p 451 or C-11

            Example
            mv, l/kg * ibw, kg = Vd, l/min
            0.2 l/kg * 15 kg = 3 l/min

            :param float ibw: Ideal body mass for given adult or child >=3 kg.
            :return: l/kg/min
            """
            # Approximation to Hamilton graph
            if ibw < 3:
                print("WARNING: MV calculation for child <3 kg is not supported")
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

        # Use RBW for neonates:
        #    * I don't know how to calculate IBW for neonates
        #    * Neonate's weight must be known in advance
        #    * They RBW must be near IBW
        if self._weight_ideal_valid:
            weight_type = "IBW"
            weight_chosen = self.weight_ideal
        else:
            weight_type = "RBW"
            weight_chosen = self.weight

        # Dead space https://www.openanesthesia.org/aba_respiratory_function_-_dead_space
        VDaw = 2.2 * weight_chosen
        Tv_min = 2 * VDaw  # ml Lowest reasonable tidal volume
        info = ""
        mv = normal_minute_ventilation(weight_chosen)
        Vd = mv * weight_chosen  # l/min
        info += "{} respiration for {} {:.1f} kg [Hamilton ASV]\n".format(weight_type, self.sex, weight_chosen)
        info += "MV x{:.2f} L/kg/min={:.3f} L/min. ".format(mv, Vd)
        info += "VDaw is {:.0f} ml, so TV must be >{:.0f} ml\n".format(VDaw, Tv_min)
        info += " * TV x6.5={:.0f} ml, RR {:.0f}/min\n".format(weight_chosen * 6.5, Vd * 1000 / (weight_chosen * 6.5))
        info += " * TV x8.5={:.0f} ml, RR {:.0f}/min".format(weight_chosen * 8.5, Vd * 1000 / (weight_chosen * 8.5))
        return info

    def _info_in_fluids(self):
        # Панкреатит жидкость 50-70 мл/кг/сут, [Пособие дежуранта 2014, стр. 259]
        info = ""
        info = "BSA all ages fluids demand {:.0f} ml/24h [1750 ml/m²]\n".format(body_surface_area(height=self.height, weight=self.weight) * 1750)
        if self.sex in ('male', 'female'):
            h2o_min = 30 * self.weight
            h2o_max = 35 * self.weight
            info += "RBW adult fluids demand {:.0f}-{:.0f} ml/24h (30-35 ml/kg/24h) [ПосДеж]\n".format(h2o_min, h2o_max)
            # [2.0 ml/kg/min Курек 2013 с 127]
            info += "Bolus {:.0f} ml (20-30 ml/kg) at max speed {:.0f} ml/h (120 ml/kg/h) [Курек]".format(self.weight * 25, 2 * 60 * self.weight)
            # Видимо к жидкости потребления нужно добавлять перспирационные потери
            # persp_ros = 10 * self.weight + 500 * (self.body_temp - 36.6)
            # info += "\nRBW Perspiration: {:.0f} ml/24h [Расенок]".format(persp_ros)

            # Перспирационные потери – 5-7 мл/кг/сут на каждый градус выше 37°С [Пособие дежуранта 2014, стр. 230]
            # Точная оценка перспирационных потерь невозможна. Формула из "Пособия дежуранта" примерно соответствует [таблице 1.6 Рябов 1994, с 31 (Condon R.E. 1975)]
            if self.body_temp > 37:
                deg = self.body_temp - 37
                info += "\n + perspiration fluid loss {:.0f}-{:.0f} ml/24h (5-7 ml/kg/24h for each °C above 37°C)".format(
                    5 * self.weight * deg,
                    7 * self.weight * deg)
        elif self.sex == 'child':
            """
            Infusion volume = ЖП + текущие потери

            * ФП рассчитывается по формуле Валлачи `100 - (3 х возраст в годах) = ml/kg/24h`
            * Холидей и Сигар (https://meduniver.com/Medical/nefrologia/raschet_poddergivaiuchei_infuzionnoi_terapii.html).
            """
            hs_fluid = fluid_req_holidaysegar_mod(self.weight)
            info += "RBW child fluids demand {:.0f} ml/24h or {:.0f} ml/h [Holliday-Segar]\n".format(hs_fluid, hs_fluid / 24)
            # Max speed [1.2 ml/kg/min Курек 2013 с 127]
            info += "Bolus {:.0f} ml (20-30 ml/kg) at max speed {:.0f} ml/h (72 ml/kg/h) [Курек]".format(self.weight * 25, 1.2 * 60 * self.weight)
            """
            Тестовый болюс при низком давлении у детей 20 мл/кг?
            [IV Fluids in Children](https://www.ncbi.nlm.nih.gov/books/NBK349484/)
                * fluids, calculated on the basis of insensible losses within the range 300–400 ml/m2/24 hours plus urinary output
                * Т.е. количество утилизированный на метаболические нужды воды + диурез + перспирация + другие потери
            """
        return info

    def _info_in_electrolytes(self):
        """Daily electrolytes demand.
        """
        info = ""
        if self.sex in ('male', 'female'):
            info += "\nElectrolytes daily requirements:\n"
            info += " * Na⁺\t{:3.0f} mmol/24h [~1.00 mmol/kg/24h]\n".format(self.weight)
            info += " * K⁺\t{:3.0f} mmol/24h [~1.00 mmol/kg/24h]\n".format(self.weight)
            info += " * Mg²⁺\t{:3.1f} mmol/24h [~0.04 mmol/kg/24h]\n".format(self.weight * 0.04)
            info += " * Ca²⁺\t{:3.1f} mmol/24h [~0.11 mmol/kg/24h]".format(self.weight * 0.11)
            return info
        else:
            return "Electrolytes calculation for children not implemented. Refer to [Курек 2013, с 130]"

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

        Administration of more than 1.5 g/kg/24h exceeds the body's ability to
        incorporate protein and does little to restore nitrogen balance.
        Healthy person requires approximately 0.8 grams of protein/kg/day)
        https://www.surgicalcriticalcare.net/Resources/nitrogen.php
        """
        info = ''
        if self.sex in ('male', 'female'):
            info += "Daily nutrition requirements for adults [ПосДеж]:\n"
            info += " * Protein {:3.0f}-{:3.0f} g/24h (1.2-1.5 g/kg/24h)\n".format(1.2 * self.weight_ideal, 1.5 * self.weight_ideal)
            info += " * Fat     {:3.0f}-{:3.0f} g/24h (1.0-1.5 g/kg/24h) (30-40% of total energy req.)\n".format(1.0 * self.weight_ideal, 1.5 * self.weight_ideal)
            info += " * Glucose {:3.0f}-{:3.0f} g/24h (4.0-5.0 g/kg/24h) (60-70% of total energy req.)\n".format(4.0 * self.weight_ideal, 5.0 * self.weight_ideal)
            if self.age:
                info += "Basal metabolic rate for healthy adults:\n"
                info += " * {:.0f} kcal/24h ({} kcal/kg/24h IBW) [ПосДеж]:\n".format(25 * self.weight_ideal, 25)
                info += " * {:.0f} kcal/24h Harris-Benedict (revised 1984) \n".format(bmr_harris_benedict(self.height, self.weight, self.sex, self.age))
                info += " * {:.0f} kcal/24h Mifflin (1990)\n".format(bmr_mifflin(self.height, self.weight, self.sex, self.age))
            else:
                info += "Enter age to calculate BMR"
        else:
            # Looks like child needs more then 25 kcal/kg/24h (up to 100?) [Курек p. 163]
            # стартовые дозы глюкозы [Курек с 143]
            info += "Energy calculations for children not implemented. Reref to [Курек АиИТ у детей 3-е изд. 2013, стр. 137]"
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
        if self.sex == 'child':
            # Not lower than 1 ml/kg/h in children [Курек 2013 122, 129]
            out = "RBW child urinary output:\n"
            out += " * x1  ={:3.0f} ml/h, {:.0f} ml/24h (target >1 ml/kg/h).\n".format(self.weight, self.weight * 24)
            out += " * x3.5={:3.0f} ml/h, {:.0f} ml/24h much higher in infants (up to 3.5 ml/kg/h)".format(3.5 * self.weight, 3.5 * self.weight * 24)
        return out

    def describe_drugs(self):
        info = "--- Drugs --------------------------------------"
        info += "\nPressors:\n"
        info += "{}\n".format(self.drugs.describe_pressors())
        info += "Anesthesiology:\n"
        info += "{}\n".format(self.drugs.describe_anesthesiology())
        return info


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

    Sutable for newborn, adult, fat.

    BSA = (W ** 0.425 * H ** 0.725) * 0.007184

    :param float height: Patient height, meters
    :param float weight: Real body mass, kg
    :return:
        m2, square meters
    :rtype: float

    >>> body_surface_area(1.86, 70)
    1.931656390627583

    References
    ----------
    [1] https://en.wikipedia.org/wiki/Body_surface_area
    [2] DuBois D, DuBois EF. A formula to estimate the approximate surface area if height and weight be known. Arch Intern Medicine. 1916; 17:863-71.
    [3] http://www-users.med.cornell.edu/~spon/picu/calc/bsacalc.htm
    """
    return 0.007184 * weight ** 0.425 * (height * 100) ** 0.725


def bmr_harris_benedict(height, weight, sex, age):
    """Basal metabolic rate, revised Harris-Benedict equation (revised 1984).

    Examples
    --------

    >>> bmr_harris_benedict(1.68, 59, 'male', 55)
    1372.7820000000002
    >>> bmr_harris_benedict(1.68, 59, 'female', 55)
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
    elif sex == 'child':
        raise ValueError("Harris-Benedict equation BMR calculation for children not supported")
    return bmr


def bmr_mifflin(height, weight, sex, age):
    """Resting energy expenditure in healthy individuals, Mifflin
    St Jeor Equation (1990).

    Considered as more accurate than revised Harris-Benedict equation.

    Examples
    --------

    >>> bmr_mifflin(1.68, 59, 'male', 55)
    1373.81
    >>> bmr_mifflin(1.68, 59, 'female', 55)
    1207.81

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
    # ree = 10 * weight + 6.25 * height * 100 - 5 * age  # Simplifyed
    ree = 9.99 * weight + 6.25 * height * 100 - 4.92 * age  # From paper
    if sex == 'male':
        ree += 5
    elif sex == 'female':
        ree -= 161
    elif sex == 'child':
        raise ValueError("Mufflin ree calculation for children not supported")
    return ree


def mean_arterial_pressure(SysP, DiasP):
    """Расчёт Среднего АД (mean arterial pressure, MAP)

    :param float SysP: Systolic pressure, mmHg
    :param float DyasP: Diastolic pressure, mmHg
    :return:
        Mean arterial pressure, mmHg
    :rtype: float

    >>> mean_arterial_pressure(120, 87)
    98.0
    """
    # (120 + 2 * 87) / 3
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
    """Daily fluid requirement for children.

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

    EPALS course uses the simple acronym W E T Fl A G for children over
    the age of 1 year and up to 10 years old. This equates to:

    Example for a 2 year old child:
    W  = (2 + 4) x 2 = 12 kg
    E  = 12 x 4 = 48 J
    T  = 2/4 +4 = 4.5 mm ID tracheal tube uncuffed
    Fl = 20 mL x 12 kg = 240 mL 0.9% saline
    A  = 10 micrograms x 12 kg = 120 micrograms 1:10,000 = 1.2 mL
    G  = 2 mL x 12 kg = 24 mL 10% Dextrose

    Whilst this is not evidence based, it provides a simple, easy to remember
    framework in a stressful situation reducing the risk or error.

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
    G = 2 * W  # 2 mL/kg Glucose 10 %
    info = """\
WETFlAG report for {} yo, weight {} kg child:
    Energy for defib {:.0f} J
    Tube {:.1f} mm
    Fluid bolus {:.0f} ml of isotonic fluid
    Adrenaline {:.0f} mcg
    Glucosae 10 % {:.0f} ml""".format(age, W, E, T, Fl, A, G)
    return info


def get_broselow_code(height):
    """Get Brocelow-Luten color zone by height.

    Broselow tape https://www.ncbi.nlm.nih.gov/pubmed/3377285
    How to use Broselow tape https://www.jems.com/2019/04/29/a-tale-of-two-tapes-broselow-luten-tapes-2011-vs-2017/

    Kinder-sicher T.O Zugck (numbers taken from this tape) https://kindersicher.biz
    Each color zone estimates the 50th percentile weight for length
    Color   Age,     Height,      Ideal body weight
    Grey    Newborn  46.8- 51.9,   3    kg
    Grey    Newborn  51.9- 55.0,   4    kg
    Grey     2 mos   55.0- 59.2,   5    kg
    Pink     4 mos   59.2- 66.9,   6- 7 kg (13-15 lbs)
    Red      8 mos   66.9- 74.2,   8- 9 kg (17-20 lbs)
    Purple   1 yr    74.2- 83.8,  10-11 kg (22-24 lbs)
    Yellow   2 yr    83.8- 95.4,  12-14 kg (26-30 lbs)
    White    4 yr    95.4-108.3,  15-18 kg (33-40 lbs)
    Blue     6 yr   108.3-121.5,  19-23 kg (42-50 lbs)
    Orange   8 yr   121.5-130.7,  24-29 kg (53-64 lbs)
    Green   10 yr   130.7-143.3,  30-36 kg (66-80 lbs)


    An remark
    ---------
    I don't think that estimating child weight by age is a good idea.
    "Weight-by-height" approach declared as more accurate and objective.
    But unfortunately I'm not able to find decent calculations
    "weight-by-height", although it definitely exists:
      * https://www.researchgate.net/post/Is_there_a_formula_for_calculating_weight_for_height_and_height_for_age_z_scores
      * https://www.who.int/childgrowth/
      * http://www.who.int/childgrowth/standards/Technical_report.pdf
    So I have to use Broselow height ranges and it's weight percentiles for now.

    The accuracy of emergency weight estimation systems:
        * https://www.ncbi.nlm.nih.gov/pubmed/28936627
        * https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6223606/
    Real body weight estimation (not IBW!)
        * PW10 70.9%, PW20 95.3% Mercy Tape method
        * PW10 78.0%, PW20 96.6% PAWPER tape http://www.wjem.com.cn/default/articlef/index/id/674
        * PW10 69.8%, PW20 87.1% parental estimates
        * PW10 55.6%, PW20 81.2% https://en.wikipedia.org/wiki/Broselow_tape
        * Age-based estimates achieved a very low accuracy - use length-based

    Parameters
    ----------
    :param float height: Child height in meters.
    :return: Color code, approx age, approx weight (kg).
    :rtype: typle
    """
    height *= 100
    if 46.8 <= height < 51.9:
        return "Grey", "Newborn", 3
    elif 51.9 <= height < 55.0:
        return "Grey", "Newborn", 4
    elif 55.0 <= height < 59.2:
        return "Grey", "2 months", 5
    elif 59.2 <= height < 66.9:
        return "Pink", "4 months", 6.5  # 6-7
    elif 66.9 <= height < 74.2:
        return "Red", "8 months", 8.5  # 8-9
    elif 74.2 <= height < 83.8:
        return "Purple", "1 year", 10.5  # 10-11
    elif 83.8 <= height < 95.4:
        return "Yellow", "2 years", 13  # 12-14
    elif 95.4 <= height < 108.3:
        return "White", "4 years", 16.5  # 15-18
    elif 108.3 <= height < 121.5:
        return "Blue", "6 years", 21  # 19-23
    elif 121.5 <= height < 130.7:
        return "Orange", "8 years", 26.5  # 24-29
    elif 130.7 <= height <= 143.3:
        return "Green", "10 years", 33  # 30-36
    else:
        raise ValueError("Out of Broselow height range")


def nadler_total_blood_volume(sex, height, weight):
    """Calculate total blood volume (TBV) for adult by Nadler 1962 formula.

    This formula is widely known and popular.

    Plasma volume (PV) can be derived with hematocrit (hct) value:

        PV = TBV * (1 – hct)

    Reference
    ---------

    [1] Nadler SB, Hidalgo JH, Bloch T. Prediction of blood volume in normal human adults. Surgery. 1962 Feb;51(2):224-32.

    :param height float: Human height, meters
    :param weight float: Human weight, kg
    :param str sex: Choose 'male', 'female'.
    :return:
        Total blood volume, ml
    :rtype: float
    """
    # Same as http://apheresisnurses.org/apheresis-calculators
    if sex == 'male':
        return ((0.3669 * height ** 3) + (0.03219 * weight) + 0.6041) * 1000
    elif sex == 'female':
        return ((0.3561 * height ** 3) + (0.03308 * weight) + 0.1833) * 1000
    else:
        raise ValueError("Nadler formula isn't applicable to children")
