"""Calculations based on human height and weight.

Author: Eugene Dvoretsky

Function parameters tends to be in International System of Units.
"""

from __future__ import annotations

import copy
import math
import textwrap
import warnings
from enum import IntEnum
from itertools import chain

from heval import drugs, electrolytes, nutrition


class HumanSex(IntEnum):
    """Human body constitution based on sex.

    Male/female integers comply EMIAS database and belarusian sick leave documents.
    """

    male = 1
    female = 2
    child = 3  # For <12 years old


class HumanBodyModel:
    """Must set 'sex' and 'height' to make it work. See `is_init()`.

    Note that 'use_ibw == False' by default.
    """

    def __init__(self):
        self.debug = False
        self._int_prop = ("height", "age", "weight", "body_temp")
        self._txt_prop = ("sex", "comment")
        self._sex = None
        self._height = None
        self._age = None

        self.weight = None
        self._use_ibw = False
        self._weight_ideal_valid = False
        self._weight_ideal_method = ""
        self.weight_ideal = None  # Changes only at sex/weight change

        self.blood = electrolytes.HumanBloodModel(self)
        self.drugs = drugs.HumanDrugsModel(self)
        self.nutrition = nutrition.HumanNutritionModel(self)
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

    @property
    def sex(self):
        return self._sex

    @sex.setter
    def sex(self, value):
        """Set HumanSex."""
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
        """Set 'use_ibw = True' to return 'weight_ideal' instead 'weight'."""
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

    @property
    def use_ibw(self):
        return self._use_ibw

    @use_ibw.setter
    def use_ibw(self, value):
        """Set flag to use calculated IBW instead real weight.

        :param bool value: Use or not IBW, bool
        """
        self._use_ibw = value

    def _set_weight_ideal(self) -> None:
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
        # misuse of explicitly invalid IBW e.g. in respiratory calculations
        self._weight_ideal_valid = True
        if self.sex in (HumanSex.male, HumanSex.female):
            self._weight_ideal_method = "Hamilton"
            self.weight_ideal = ibw_hamilton(self.sex, self.height)
        elif self.sex == HumanSex.child:
            # Broselow tape range. Temporary and only for low height
            if 0.468 <= self.height < 0.74:
                self._weight_ideal_method = "Broselow"
                self.weight_ideal = ibw_broselow(self.height)
            elif 0.74 <= self.height <= 1.524:
                self._weight_ideal_method = "Traub-Kichen 1983"
                self.weight_ideal = ibw_traub_kichen(self.height)
            else:
                warnings.warn("IBW cannot be calculated for children with this height")
                self._weight_ideal_valid = False

    @property
    def bmi(self):
        """Body mass index."""
        return body_mass_index(self.height, self.weight)

    @property
    def bsa(self):
        """Body surface area, m2, square meters."""
        return body_surface_area_dubois(height=self.height, weight=self.weight)

    @property
    def age(self):
        return self._age

    @age.setter
    def age(self, value):
        """Human age in years."""
        self._age = value

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

        According to review, all children (though neonates has been stated
        as 80–90 ml/kg early) has the same mean blood volume 70 ml/kg RBW.
        [Dr K Morris et all, 2005 https://adc.bmj.com/content/90/7/724]

        :return: Total blood volume, ml
        """
        return 70 / math.sqrt(self.bmi / 22) * self.weight

    def is_init(self) -> bool:
        """Is class got all necessary data for calculations."""
        return all((self.height, self.weight, self.sex))

    def describe(self) -> str:
        info = ""
        if not self.is_init():
            return "Empty human model (set sex, height, weight)"
        info += "{}\n".format(self._info_in_body())
        info += "\n-- Respiration ---------------------------------\n"
        info += "{}\n".format(self._info_in_respiration())
        info += "\n-- Fluids --------------------------------------\n"
        info += "{}\n".format(self._info_in_fluids())
        info += "\n-- Metabolic -----------------------------------\n"
        info += "{}\n".format(self._info_in_energy())
        if self.debug:
            info += "\n{}\n".format(self._info_in_food())
        # Estimate also CO2 production?
        info += "\n-- Diuresis ------------------------------------\n"
        info += f"{self._info_out_fluids()}\n"
        if self.comment:
            info += f"\nComments:\n{self.comment}\n"
        return info

    def _info_in_body(self) -> str:
        info = f"{self.sex.name.title()} {self.height * 100:.0f}/{self.weight:.0f}:"
        if self._weight_ideal_valid:
            info += f" IBW {self.weight_ideal:.1f} kg [{self._weight_ideal_method}],"
        else:
            info += " IBW can't be calculated for this height, enter weight manually."

        if self.sex in (HumanSex.male, HumanSex.female):
            info += f" BMI {self.bmi:.1f} ({bmi_describe(self.bmi)}),"
        else:
            # Adult normal ranges cannot be applied to children
            info += f" BMI {self.bmi:.1f},"

        info += f" BSA {self.bsa:.3f} m².\n"

        # Value 70 ml/kg used in cardiopulmonary bypass. It valid for humans
        # older than 3 month. ml/kg ratio more in neonates and underweight
        info += "Total blood volume {:.0f} ml (70 ml/kg) or {:.0f} ml (weight indexed by Lemmens). ".format(
            self.weight * 70, self.total_blood_volume
        )
        info += f"Transfusion of one pRBC dose will increase Hb by {estimate_prbc_transfusion_response(self.weight):+.2f} g/dL."

        if self.sex == HumanSex.child:
            try:
                br_code, br_age, br_weight = get_broselow_code(self.height)
                info += f"\nBROSELOW TAPE: {br_code.upper()}, {br_age.lower()}, ~{br_weight:.1f} kg.\n"
            except ValueError:
                pass
            info += f"\n{mnemonic_wetflag(weight=self.weight)}"
        return info

    def _info_in_respiration(self) -> str:
        """Calulate optimal Tidal Volume for given patient (any gas mixture).

        IBW - ideal body weight
        RBW - real body weight

        Главное - рассчитать безопасный дыхательный объём (TV) при
            * повреждённых лёгких 6-8 ml/kg (ARDSNET, normal volume ventilation)
            * при здоровых лёгких 8.5 ml/kg (Drager documentation, типичная вентиляция во время ОЭТН)
        Если при вентиляции с таким рассчитанным TV Ppeak >35 (если пациент не поддыхивает и не кашляет)
        и Pplato > 30 (даже если поддыхивает), то TV уменьшается [видео Owning Oxylog].
            Target Pplato <30 cmH2O
            RR <=35/min

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

        def normal_minute_ventilation(ibw: float) -> float:
            """Calculate normal minute ventilation for humans with IBW >=3 kg.

            Calculation accomplished according to ASV ventilation mode from
            Hamilton G5 Ventilator - Operators manual en v2.6x 2016-03-07 p 451 or C-11

            Examples:
                mv, l/kg * ibw, kg = Vd, l/min
                0.2 l/kg * 15 kg = 3 l/min

            Args:
                ibw: Ideal body mass for given adult or child >=3 kg.

            Returns:
                l/kg/min
            """
            # Approximation to Hamilton graph
            if ibw < 3:
                print("WARNING: MV calculation for child <3 kg is not supported")
                minute_volume = 0.0
            elif 3 <= ibw < 5:
                minute_volume = 0.3
            elif 5 <= ibw < 15:
                minute_volume = 0.3 - 0.1 / 10 * (ibw - 5)
            elif 15 <= ibw < 30:
                minute_volume = 0.2 - 0.1 / 15 * (ibw - 15)
            else:  # >= 30:
                minute_volume = 0.1
            return minute_volume

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
        tv_mul_min = 6
        tv_mul_max = 8
        info = ""
        mv = normal_minute_ventilation(weight_chosen)
        Vd = mv * weight_chosen  # l/min
        info += "{} respiration parameters for {} {:.1f} kg [Hamilton ASV]\n".format(
            weight_type, self.sex.name, weight_chosen
        )
        info += f"MV x{mv:.2f} L/kg/min={Vd:.3f} L/min. "
        info += f"VDaw is {VDaw:.0f} ml, so TV must be >{Tv_min:.0f} ml\n"
        info += " * TV x{:.1f}={:3.0f} ml, RR {:.0f}/min\n".format(
            tv_mul_min,
            weight_chosen * tv_mul_min,
            Vd * 1000 / (weight_chosen * tv_mul_min),
        )
        info += " * TV x{:.1f}={:3.0f} ml, RR {:.0f}/min".format(
            tv_mul_max,
            weight_chosen * tv_mul_max,
            Vd * 1000 / (weight_chosen * tv_mul_max),
        )
        return info

    def _info_in_fluids(self) -> str:
        # Normal physiologic demand
        info = ""
        if self.sex in (HumanSex.male, HumanSex.female):
            info += " * RBW fluids demand {:.0f}-{:.0f} ml/24h (30-35 ml/kg/24h) [ПосДеж]\n".format(
                30 * self.weight, 35 * self.weight
            )

        hs_fluid = fluid_holidaysegar_mod(self.weight)
        info += " * RBW fluids demand {:.0f} ml/24h or {:.0f} ml/h [Holliday-Segar]\n".format(
            hs_fluid, hs_fluid / 24
        )

        info += " * BSA fluids demand {:.0f} ml/24h (1750 ml/m²)".format(
            body_surface_area_dubois(height=self.height, weight=self.weight) * 1750
        )  # All ages

        # Variable perspiration losses, which is not included in physiologic demand
        # persp_ros = 10 * self.weight + 500 * (self.body_temp - 36.6)
        # info += "\nRBW Perspiration: {:.0f} ml/24h [Расенок]".format(persp_ros)

        # Перспирационные потери – 5-7 мл/кг/сут на каждый градус выше 37°С [Пособие дежуранта 2014, стр. 230]
        # Точная оценка перспирационных потерь невозможна. Формула из "Пособия дежуранта" примерно соответствует [таблице 1.6 Рябов 1994, с 31 (Condon R.E. 1975)]
        if self.body_temp > 37:
            deg = self.body_temp - 37
            info += "\n + perspiration fluid loss {:.0f}-{:.0f} ml/24h (5-7 ml/kg/24h for each °C above 37°C)".format(
                5 * self.weight * deg, 7 * self.weight * deg
            )
        return info

    def _info_in_food(self) -> str:
        """Daily electrolytes demand."""
        info = ""
        if self.sex in (HumanSex.male, HumanSex.female):
            info += "Daily nutrition requirements for adults [ПосДеж]:\n"
            info += " * Protein {:3.0f}-{:3.0f} g/24h (1.2-1.5 g/kg/24h)\n".format(
                1.2 * self.weight_ideal, 1.5 * self.weight_ideal
            )
            info += " * Fat     {:3.0f}-{:3.0f} g/24h (1.0-1.5 g/kg/24h) (30-40% of total energy req.)\n".format(
                1.0 * self.weight_ideal, 1.5 * self.weight_ideal
            )
            info += " * Glucose {:3.0f}-{:3.0f} g/24h (4.0-5.0 g/kg/24h) (60-70% of total energy req.)\n".format(
                4.0 * self.weight_ideal, 5.0 * self.weight_ideal
            )

            info += "Electrolytes daily requirements:\n"
            info += " * Na⁺\t{:3.0f} mmol/24h [~1.00 mmol/kg/24h]\n".format(self.weight)
            info += " * K⁺\t{:3.0f} mmol/24h [~1.00 mmol/kg/24h]\n".format(self.weight)

            # Parenteral (33% of enteral) 120 mg, 5 mmol/24h [Kostuch, p 49]
            info += f" * Mg²⁺\t{self.weight * 0.04:3.1f} mmol/24h [~0.04 mmol/kg/24h]\n"
            # Parenteral (25% of enteral) 200 mg/24h, 5 mmol/24h [Kostuch, p 49]
            info += f" * Ca²⁺\t{self.weight * 0.11:3.1f} mmol/24h [~0.11 mmol/kg/24h]"
            return info
        else:
            return "Electrolytes demand calculation for children not implemented. Refer to [Курек 2013, с 130]"

    def _info_in_energy(self) -> str:
        """Attempt to calculate energy requirements for an human.

        There are ESPEN and ASPEN recommendations. See:
            * ESPEN guideline: Clinical nutrition in surgery
                https://www.espen.org/files/ESPEN-guideline_Clinical-nutrition-in-surgery.pdf
            * ESPEN guideline on clinical nutrition in the intensive care unit
                https://www.espen.org/files/ESPEN-Guidelines/ESPEN_guideline-on-clinical-nutrition-in-the-intensive-care-unit.pdf

        Взрослый мужчина
        1. Минимальная_ дневная потребность в глюкозе 2 г/кг в сутки
        2. Дневная потребность в аминокислотах 0,7 г/кг в сутки
        3. Суточная потребность в энергии составляет 24-30 ккал/кг [тесты БелМАПО]
        4. Суточная потребность в жирах 2 г/кг в сутки

        Толстым рассчитывать на идеальный, истощённым на реальный [РМАНПО]

        Top administraion limit
        -----------------------
        * Administration of more than 1.5 g/kg/24h exceeds the body's ability to
        incorporate protein and does little to restore nitrogen balance.
        Healthy person requires approximately 0.8 grams of protein/kg/day)
        https://www.surgicalcriticalcare.net/Resources/nitrogen.php
        * Липиды <=0.2 г/кг/час независимо от возраста [Курек 2013], 0.15 г/кг/час [РМАНПО]
        * Углеводы <=5-6 г/кг/24h если выше, то риск жирового гепатоза [РМАНПО]
            Glycosuria

        Нейрореаниматология: практическое руководство 2017
        --------------------------------------------------
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
          * 25-30 kcal/kg/24h [ESPEN 2009]

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
        info = ""
        if self.sex in (HumanSex.male, HumanSex.female):
            # 25-30 kcal/kg/24h IBW? ESPEN Guidelines on Enteral Nutrition: Intensive care https://doi.org/10.1016/j.clnu.2018.08.037
            if self.age:
                info += "Resting energy expenditure for healthy adults:\n"
                info += " * {:.0f} kcal/24h [Harris-Benedict, revised 1984] \n".format(
                    ree_harris_benedict_revised(
                        self.height, self.weight, self.sex, self.age
                    )
                )
                info += " * {:.0f} kcal/24h [Mifflin 1990]\n".format(
                    ree_mifflin(self.height, self.weight, self.sex, self.age)
                )
            else:
                info += "Enter age to calculate REE\n"
            info += (
                " * {:.0f}-{:.0f} kcal/24h (25-30 kcal/kg/24h IBW) [ESPEN 2019]".format(
                    25 * self.weight_ideal, 30 * self.weight_ideal
                )
            )
        else:
            # Looks like child needs more then 25 kcal/kg/24h (up to 100?) [Курек p. 163]
            # стартовые дозы глюкозы [Курек с 143]
            info += "Energy calculations for children not implemented. Refer to [Курек АиИТ у детей 3-е изд. 2013, стр. 137]"
        return info

    def _info_out_fluids(self) -> str:
        """Minimal required urinary output 0.5-1 ml/kg/h.

        У детей диурез значительно выше, у новорождённых 2.5 ml/kg/h.
        Выделение мочи <0.5 мл/кг/ч >6 часов - самостоятельный критерии ОПП
        """
        if self.sex in (HumanSex.male, HumanSex.female):
            info = "RBW adult urinary output:\n"
            info += (
                " * x0.5={:2.0f} ml/h, {:4.0f} ml/24h (target >0.5 ml/kg/h)\n".format(
                    0.5 * self.weight, 0.5 * self.weight * 24
                )
            )
            info += " * x1.0={:2.0f} ml/h, {:4.0f} ml/24h".format(
                self.weight, self.weight * 24
            )
        if self.sex == HumanSex.child:
            # Not lower than 1 ml/kg/h in children [Курек 2013 122, 129]
            info = "RBW child urinary output:\n"
            info += " * x1  ={:3.0f} ml/h, {:.0f} ml/24h (target >1 ml/kg/h).\n".format(
                self.weight, self.weight * 24
            )
            info += " * x3.5={:3.0f} ml/h, {:.0f} ml/24h much higher in infants (up to 3.5 ml/kg/h)".format(
                3.5 * self.weight, 3.5 * self.weight * 24
            )
        return info

    def describe_drugs(self) -> str:
        info = [
            "-- Drugs ---------------------------------------",
            "Pressors:",
            self.drugs.describe_pressors(),
            "Anesthesiology:",
            self.drugs.describe_anesthesiology(),
        ]
        return "\n".join(info) + "\n"


def body_mass_index(height: float, weight: float) -> float:
    """Body mass index and description.

    NB! Normal ranges in children differ from adults.

    http://apps.who.int/bmi/index.jsp?introPage=intro_3.html

    :param float height: meters
    :param float weight: kilograms
    :return: Body Mass Index
    :rtype: float
    """
    assert height < 10  # Fall if height in centimeters
    return weight / height**2


def bmi_describe(bmi: float) -> str:
    """Describe Body Mass Index for adults.

    :param float bmi: Body Mass Index.
    :return: Opinion
    :rtype: str
    """
    if bmi < 18.5:
        info = "underweight: "
        if bmi < 16:
            info += "severe thinness"
        elif 16 <= bmi < 17:
            info += "moderate thinness"
        elif 17 <= bmi:
            info += "mild thinness"
    elif 18.5 <= bmi < 25:
        info = "normal weight"
    elif 25 <= bmi < 30:
        info = "overweight, pre-obese"
    elif bmi >= 30:
        info = "obese "
        if bmi < 35:
            info += "I"
        elif 35 <= bmi < 40:
            info += "II"
        elif bmi >= 40:
            info += "III"
    return info


def body_surface_area_dubois(height: float, weight: float) -> float:
    """Human body surface area (Du Bois formula).

    Suitable for newborn, adult, fat.

    BSA = (W ** 0.425 * H ** 0.725) * 0.007184

    References
    ----------
    [1] https://en.wikipedia.org/wiki/Body_surface_area
    [2] DuBois D, DuBois EF. A formula to estimate the approximate surface area if height and weight be known. Arch Intern Medicine. 1916; 17:863-71.
    [3] http://www-users.med.cornell.edu/~spon/picu/calc/bsacalc.htm

    Examples
    --------
    >>> body_surface_area_dubois(1.86, 70)
    1.931656390627583

    :param float height: Patient height, meters
    :param float weight: Real body mass, kg
    :return:
        m2, square meters
    :rtype: float
    """
    return 0.007184 * weight**0.425 * (height * 100) ** 0.725


def get_broselow_code(height: float) -> tuple[str, str, float]:
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

    Args:
        height: Child height in meters.

    Returns:
        Typle of color code, approx age, approx weight (kg).
    """
    height *= 100
    if 46.8 <= height < 51.9:
        return "Grey", "Newborn", 3.0
    elif 51.9 <= height < 55.0:
        return "Grey", "Newborn", 4.0
    elif 55.0 <= height < 59.2:
        return "Grey", "2 months", 5.0
    elif 59.2 <= height < 66.9:
        return "Pink", "4 months", 6.5  # 6-7
    elif 66.9 <= height < 74.2:
        return "Red", "8 months", 8.5  # 8-9
    elif 74.2 <= height < 83.8:
        return "Purple", "1 year", 10.5  # 10-11
    elif 83.8 <= height < 95.4:
        return "Yellow", "2 years", 13.0  # 12-14
    elif 95.4 <= height < 108.3:
        return "White", "4 years", 16.5  # 15-18
    elif 108.3 <= height < 121.5:
        return "Blue", "6 years", 21.0  # 19-23
    elif 121.5 <= height < 130.7:
        return "Orange", "8 years", 26.5  # 24-29
    elif 130.7 <= height <= 143.3:
        return "Green", "10 years", 33.0  # 30-36
    else:
        raise ValueError("Out of Broselow height range")


def ibw_broselow(height: float) -> float:
    """Calculate ideal body weight by height (Broselow).

    Args:
        height: Child height in meters.

    Returns:
        Ideal body weight, approx weight (kg).
    """
    return get_broselow_code(height)[2]


def ibw_traub_kichen(height: float) -> float:
    """Calculate ideal body weight by height (child 0.74-1.524 m).

    Can predict IBW for children aged 1 to 17 years and height 0.74-1.524 m

    Traub-Kichen's formula. [Am J Hosp Pharm. 1983 Jan;40(1):107-10](
    https://www.ncbi.nlm.nih.gov/pubmed/6823980)

    Derived in 1983 in the USA from data from more than 20,000 children
    in the National Centre for Health Statistics database.
    The formula was intended to estimate the 50th centile of weight-for-height
    which the developers regarded as an approximation of ideal body weight.
    Underestimates total body weight.
    For children over 0.74-1.524 m and aged 1 to 17 years.

    :param float height: meters, valid range is 0.74 < height < 1.524 (5 ft)
    :return: Ideal children body weight in kg
    :rtype: float
    """
    if not 0.74 <= height <= 1.524:
        warnings.warn(
            f"Warning: ibw_traub_kichen height must be in 0.74-1.524 m, not {height}"
        )
    # return 2.396 * 1.0188 ** (height * 100)  # First variant
    return 2.396 * math.exp(0.01863 * height * 100)  # Second variant


def ibw_hamilton(sex: HumanSex, height: float) -> float:
    """Calculate ideal body weight by height (0.3-2.5 m) for adult and pediatric patients.

    Reverse-engineered Hamilton implementation. Main principles:
      * Three height ranges

    Known issues:
    1. Not suitable for neonatal patients - use real body weight
    2. Formula <=70 cm doesn't looks good. May be Broselow is better.
    3. Joint between formulas has a notch around 127 cm for females
        and no notch for males

    References:
        Traub SL. Am J Hosp Pharm 1980 (pediatric patients):

            height ≤ 70 cm       IBW = 0.125 * height - 0.75
            70 < height ≤ 128    IBW = (0.0037 * height - 0.4018) * height + 18.62

        Hamilton manual, table 4-1. Adopted from Pennsylvania Medical Center.
        Same line as ARDSNET predicted body weight.

            height ≥ 129
                Male             IBW = 0.9079 * height - 88.022
                Female           IBW = 0.9049 * height - 92.006

    Examples:
        >>> ibw_hamilton(HumanSex.male, 0.6)
        6.75
        >>> ibw_hamilton(HumanSex.male, 1.0)
        15.440000000000001
        >>> ibw_hamilton(HumanSex.male, 1.5)
        48.163
        >>> ibw_hamilton(HumanSex.female, 1.5)
        43.72900000000001

    Args:
        sex: male, female. For height <129 doesn't matter which.
        height: Height (0.3-2.5 m), meters.

    Returns:
        Ideal body weight, kg

    """
    height *= 100  # to cm
    if height <= 70:
        return 0.125 * height - 0.75
    elif 70 < height < 129:
        # Missing parentheses in Hamilton manual
        return (0.0037 * height - 0.4018) * height + 18.62
    else:  # height >= 129:  # This switch fits only for males. Notch for females
        # Looks like Devine formula from ARDSNET
        # Devine BJ.Gentamicin therapy.Drug Intell Clin Pharm. 1974;8: 650–655.
        if sex == HumanSex.male:
            # 50 + 0.91 * (height - 152.4)  # ARDSNET formula
            # Adult male, negative value with height <97 cm
            return 0.9079 * height - 88.022
        elif sex == HumanSex.female:
            # 45.5 + 0.91 * (height - 152.4)  # ARDSNET formula
            # Adult female, negative value with height <101 cm
            return 0.9049 * height - 92.006
        else:
            raise NotImplementedError("IBW calculation in children not implemented")


def ree_harris_benedict_revised(
    height: float, weight: float, sex: HumanSex, age: float
) -> float:
    """Resting energy expenditure, revised Harris-Benedict equation (revised 1984).

    References
    ----------
    [1] https://en.wikipedia.org/wiki/Basal_metabolic_rate
    [2] Roza AM, Shizgal HM (1984). "The Harris Benedict equation reevaluated:
        resting energy requirements and the body cell mass" (PDF).
        The American Journal of Clinical Nutrition. 40 (1): 168–182.
    [3] https://www.omnicalculator.com/health/bmr

    Examples
    --------
    >>> ree_harris_benedict_revised(1.68, 59, HumanSex.male, 55)
    1372.7820000000002
    >>> ree_harris_benedict_revised(1.68, 59, HumanSex.female, 55)
    1275.4799999999998

    :param float height: Height, meters
    :param float weight: Weight, kg
    :param human.HumanSex sex: Choose HumanSex.male, HumanSex.female
    :param float age: Age, years
    :return: Resting energy expenditure, kcal/24h
    :rtype: float
    """
    if sex == HumanSex.male:
        return 13.397 * weight + 4.799 * height * 100 - 5.677 * age + 88.362
    elif sex == HumanSex.female:
        return 9.247 * weight + 3.098 * height * 100 - 4.330 * age + 447.593
    else:
        raise ValueError(
            "Harris-Benedict equation REE calculation for children not supported"
        )


def ree_mifflin(height: float, weight: float, sex: HumanSex, age: float) -> float:
    """Resting energy expenditure in healthy individuals, Mifflin St Jeor Equation (1990).

    Considered as more accurate than revised Harris-Benedict equation.

    References
    ----------
    [1] https://en.wikipedia.org/wiki/Basal_metabolic_rate
    [2] Mifflin MD, St Jeor ST, Hill LA, Scott BJ, Daugherty SA, Koh YO (1990).
        "A new predictive equation for resting energy expenditure in healthy
        individuals".
        The American Journal of Clinical Nutrition. 51 (2): 241–247.
    [3] https://www.omnicalculator.com/health/bmr

    Examples
    --------
    >>> ree_mifflin(1.68, 59, HumanSex.male, 55)
    1373.81
    >>> ree_mifflin(1.68, 59, HumanSex.female, 55)
    1207.81

    :param float height: Height, meters
    :param float weight: Weight, kg
    :param human.HumanSex sex: Choose HumanSex.male, HumanSex.female
    :param float age: Age, years
    :return:
        REE, kcal/24h
    :rtype:
        float
    """
    # ree = 10 * weight + 6.25 * height * 100 - 5 * age  # Simplifyed
    ree = 9.99 * weight + 6.25 * height * 100 - 4.92 * age  # From paper
    if sex == HumanSex.male:
        ree += 5
    elif sex == HumanSex.female:
        ree -= 161
    elif sex == HumanSex.child:
        raise ValueError("Mufflin REE calculation for children not supported")
    return ree


def mean_arterial_pressure(SysP: float, DiasP: float) -> float:
    """Calculate mean arterial pressure (MAP).

    Examples
    --------
    >>> mean_arterial_pressure(120, 87)
    98.0

    :param float SysP: Systolic pressure, mmHg
    :param float DiasP: Diastolic pressure, mmHg
    :return:
        Mean arterial pressure, mmHg
    :rtype: float
    """
    # (120 + 2 * 87) / 3
    # return (SysP - DiasP) / 3 + DiasP  # Just different algebra
    return (SysP + 2 * DiasP) / 3


def fluid_parcland(weight: float, burned_surface: float) -> float:
    """Calculate Ringer's lactate solution volume to support burned patient.

    Formula used to calculate volume of crystalloids (Ringer's lactate) to
    compensate fluid loss in burned patients in first 24 hours.
    Рассчитанный объём добавляется к жидкости поддержания у педиатрических пациентов [4].

    Increase volume if urinary output <0.5 ml/kg/h). Don't use potassium solutions!

    References
    ----------
    [1] https://en.wikipedia.org/wiki/Parkland_formula
    [2] Клинические случаи в анестезиологии А.П. Рид, Дж. Каплан 1995 г, с 309
    [3] https://www.remm.nlm.gov/burns.htm
    [4] В.В. Курек, А.Е. Кулагин «Анестезия и интенсивная терапия у детей» изд. третье 2013, с 418

    Examples
    --------
    V = 4 * m * A%
    V = 4 x 75 kg x 20% = 6000 ml

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
    print(
        "Patient {} kg with burns {} % of body surface area: deliver {} ml of lactated Ringer's within 24 hours".format(
            weight, burned_surface, volume_ml
        )
    )
    print(
        f"{volume_ml / 2.0:.0f} ml within first 8 hours\n{volume_ml / 2.0:.0f} ml within next 16 hours"
    )
    return volume_ml


def fluid_holidaysegar_mod(rbw: float) -> float:
    """Daily fluid requirement for children.

    Looks like Holliday-Segar method, but modified for premature infants
    with body weight <3 kg.

    References:
        [1] The maintenance need for water in parenteral fluid therapy, Pediatrics 1957. Holliday Segar
            https://www.ncbi.nlm.nih.gov/pubmed/13431307

        [2] Курек 2013, стр. 121 или 418. По идее, дложен соответствовать
        таблице с 121, но для >20 кг это не так.

    Examples:
        >>> fluid_holidaysegar_mod(1)
        150
        >>> fluid_holidaysegar_mod(5)
        500
        >>> fluid_holidaysegar_mod(15)
        1250
        >>> fluid_holidaysegar_mod(30)
        1700
        >>> fluid_holidaysegar_mod(90)
        2900

    Args:
        rbw: Real body mass, kg

    Returns:
        24 hour fluid demand.
    """
    if rbw < 2:  # Kurek modification?
        return 150 * rbw
    elif 2 <= rbw < 10:  # 100 ml/kg for the 1st 10 kg of wt
        return 100 * rbw
    elif 10 <= rbw < 20:  # 50 ml/kg for the 2nd 10 kg of wt
        return 1000 + 50 * (rbw - 10)
    else:  # 20 kg and up
        return 1500 + 20 * (rbw - 20)


def mnemonic_wetflag(age: float | None = None, weight: float | None = None) -> str:
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
    :param float weight: kg, just a fallback now
    """
    if weight:  # Don't want to add age field now
        age = weight / 2 - 4
    if age is None:
        raise ValueError("Specify children's age or weight")
    if not 1 <= age <= 10:
        return "WETFLAG: Age must be in range 1-10 years"

    w = (age + 4) * 2  # Weight, kg
    e = 4 * w  # Energy, Joules. Mono or bifasic?
    t = age / 4 + 4  # Tube (endotracheal), ID mm (uncuffed)
    fl = 20 * w  # Fluids (bolus), ml of isotonic fluid (caution in some cases)
    a = 10 * w  # Adrenaline 10 mcg/kg (1:10000 solution = 0.1 mL/kg)
    g = 2 * w  # 2 mL/kg Glucose 10 %
    return textwrap.dedent(
        f"""\
        WETFLAG tip for {age:.1f} yo:
          Weight           {w:>4.1f} kg  = (age + 4) * 2
          Energy for defib {e:>4.0f} J   = 4 J/kg
          Tube             {t:>4.1f} mm  = age / 4 + 4
          Fluid bolus      {fl:>4.0f} ml  = 20 ml/kg of isotonic fluid
          Adrenaline       {a:>4.0f} mcg = 10 mcg/kg
          Glucose 10 %     {g:>4.0f} ml  = 2 mL/kg"""
    )


def total_blood_volume_nadler(sex: HumanSex, height: float, weight: float) -> float:
    """Calculate total blood volume (TBV) for adult by Nadler 1962 formula.

    This formula is widely known and popular.

    Plasma volume (PV) can be derived with hematocrit (hct) value:

        PV = TBV * (1 – hct)

    References:
        [1] Nadler SB, Hidalgo JH, Bloch T. Prediction of blood volume in normal human adults. Surgery. 1962 Feb;51(2):224-32.

    Args:
        height: Human height, meters
        weight: Human weight, kg
        sex: Choose HumanSex.male, HumanSex.female

    Returns:
        Total blood volume, ml
    """
    # Same as http://apheresisnurses.org/apheresis-calculators
    if sex == HumanSex.male:
        return ((0.3669 * height**3) + (0.03219 * weight) + 0.6041) * 1000
    elif sex == HumanSex.female:
        return ((0.3561 * height**3) + (0.03308 * weight) + 0.1833) * 1000
    else:
        raise ValueError("Nadler formula isn't applicable to children")


def transfusion_prbc_target(
    weight: float, target_hb_increment: float = 1, prbc_hct: float = 0.6
) -> float:
    """Estimate needed pRBC transfusion volume to reach target Hb.

    Applicable to adult and children.

    Dose response:
      * In an average adult (70 kg): one pRBC unit increases Hgb by 1 g/dL (Hct by 2–3%) [1]
      * Infant: 10-15 ml/kg to achieve the same response

    References:
        [1] Calculating the required transfusion volume in children, 2007
            https://www.ncbi.nlm.nih.gov/pubmed/17302766
            * 10 mL/kg gives an increment of 2 g/dL
            * Hb estimation 1 hour after transfusion is the same as 7 hours after transfusion.
        [2] Ness PM, Kruskall MS. Principles of red blood cell transfusion. In: Hoffman K, editor.
            Hematology: basic principles and practice. 4th ed. Orlando, FL: Churchill Livingstone; 2005.
        [3] https://www.sciencedirect.com/topics/biochemistry-genetics-and-molecular-biology/hemoglobin-blood-level
            One RBC unit:
              * 300 ml, prbc_hct 0.7, so rbc_volume = 300 * 0.7
              * 200 mg of iron
        [4] https://www.omnicalculator.com/health/pediatric-transfusion

    Examples:
        >>> transfusion_prbc_target(70)
        350.0

    Args:
        weight: Real body weight, kg
        target_hb_increment: Desired Hb increment, g/dL
        prbc_hct: Haematocrit of pRBC dose, fraction

    Returns:
        Required pRBC volume to reach target Hb, ml
    """
    return weight * target_hb_increment * 3 / prbc_hct


def estimate_prbc_transfusion_response(
    real_body_weight: float, prbc_volume: float = 350, prbc_hct: float = 0.6
) -> float:
    """Estimate Hb increase after one pRBC dose transfusion.

    Applicable to adult and children.

    References:
        See function `hb_prbc_dose` for complete reference.

        [1] https://www.ncbi.nlm.nih.gov/pubmed/17302766
            10 mL/kg gives an increment of 2 g/dL

    Examples:
        >>> estimate_prbc_transfusion_response(70, 10 * 70)
        2.0
        >>> estimate_prbc_transfusion_response(real_body_weight=70)
        1.0

    Args:
        real_body_weight: Real body weight, kg
        prbc_volume: Volume of one pRBC package, ml
        prbc_hct: Haematocrit of pRBC dose, fraction. Value is

    Returns:
        Expected Hb increase, g/dL
    """
    return prbc_volume / (real_body_weight * 3 / prbc_hct)


def estimate_prbc_transfusion_volume(
    real_body_weight: float, hb: float, target_hb: float = 75
) -> float:
    """Estimate required RBC volume to reach target recipient Hb level.

    For 0-16 years old, based on recipient Hb.

    Examples:
        >>> estimate_prbc_transfusion_volume(real_body_weight=70, hb=70, target_hb=75)
        168.0
        >>> estimate_prbc_transfusion_volume(70, 65)
        336.0
        >>> estimate_prbc_transfusion_volume(70, 50)
        840.0
        >>> estimate_prbc_transfusion_volume(90, 30)
        1944.0

    Args:
        real_body_weight: recipient real body weight, kg
        hb: Recipient hemoglobin, g/L
        target_hb: Target recipient hemoglobin, g/L

    Returns:
        Estimated pRBC volume (formula valid for pRBC HCT 0.64-0.72), ml

    References:
        Dr K Morris et all, 2005 https://adc.bmj.com/content/90/7/724

        Old unvalidated formula (for reference)
        donor_rbc_vol = real_body_weight * (target_hb - hb) / donor_rbc_hb
        donor_rbc_vol = 3 × real_body_weight * (target_hb - hb)
    """
    # return 1.6 * real_body_weight * (target_hct - hct)
    return 4.8 * real_body_weight * (target_hb - hb) / 10


def check_anemia(hb: float, mcv: float) -> str:
    """Check for anemia and guess it's cause.

    Args:
        hb: Hemoglobin, g/L
        mcv: Mean corpuscular volume, fL


    References
    ----------
    Universal anemia threshold is <110 g/L, based on [WHO VMNIS 2011]:
        * Minimal Hb registered in humans during lifetime (at age 6 months - 5 years)
        * Minimal Hb in pregnant women
        * Simpler to implement, than thresholds for each sex, age,
            condition (120 for females, 130 males, etc)


    https://medvisor.ru/services/kalkulyator-anemii/
    MCV low
        Ferritin coefficient
            Normal/high
                Total iron binding capacity
                    High/Normal -> Plumbum; Perform Hemoglobin electrophoresis for abnormal Hb like Sickle cell disease B-thalassemia); bone marrow smear (e.g. sideroblastic anemia)
                    Low -> Anemia of Chronic Disease (ACD)
            Low -> Iron deficiency

    MCV high
        B9 low -> Folate deficiency anemia
        B12 low
             Schilling test for intrinsic factor
                Low -> B12 deficiency;
                Normal -> Gastrointestinal condition;
        Both normal -> Liver; Drug induced anemia; Reticulocytosis.

    MCV normal
        Reticulocyte
            High -> blood loss; hemolysis; platelet sequestration in spleen;
            Low
                LEY, PLT
                    Low -> Myelodysplastic syndrome; Aplastic anemia; Leukemia.
                    Normal/High -> Chronic infection; Malignancy; Chronic kidney disease.
    """
    msg = ""
    if hb >= 110:
        return msg

    # Normal MCV range 80-100 fL
    if mcv < 80:  # As low as 60-70
        # MCHC hypochromic
        msg = f"""<abbr title="MCV {mcv:.0f} fL: Fe deficiency, chronic disease, thalassemia. Check Fe, ferritin, total iron binding capacity">Microcytic</abbr> anemia"""
    elif 100 < mcv:  # Up to 150
        msg = f"""<abbr title="MCV {mcv:.0f} fL: B12 and/or B9 (folic acid) deficiency or gastrointestinal condition; chronic alcohol abuse (check AST)">Macrocytic</abbr> anemia"""
    else:
        # Reticulocytes aren't measured routinely as it requires
        # manual blood count or expensive analyzer
        msg = f"""<abbr title="Normal MCV {mcv:.0f} fL: blood loss, hemolysis, chronic disease (suppressed production, B2, B6 deficiency).\n\nCheck reticulocyte count: it raises in 12-24 hours after hemorrhage and stays low if problem in the bone marrow.">Normocytic</abbr> anemia"""
    return msg


# https://news.tut.by/society/311809.html
# Average Belorussian male in 2008 >=18 years old
male_generic_by = {
    "height": 1.77,
    "weight": 69.0,
    "sex": HumanSex.male,
    "body_temp": 36.6,
}

# Average Belorussian female in 2008 >=18 years old
female_generic_by = {
    "height": 1.65,
    "weight": 56.0,
    "sex": HumanSex.female,
    "body_temp": 36.6,
}

female_overweight_by = {
    "height": 1.62,
    "weight": 72.0,
    "sex": HumanSex.female,
    "body_temp": 36.6,
}

male_thin = {  # Me
    "height": 1.86,
    "weight": 55.0,
    "sex": HumanSex.male,
    "body_temp": 36.6,
}

child = {  # 3 year old kid
    "height": 0.95,
    "weight": 16.5,
    "sex": HumanSex.child,
    "body_temp": 36.6,
}

newborn = {"height": 0.5, "weight": 3.6, "sex": HumanSex.child, "body_temp": 36.6}
