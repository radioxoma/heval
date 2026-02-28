"""Calculations based on human height and weight.

Author: Eugene Dvoretsky

Function parameters tends to be in International System of Units.
"""

from __future__ import annotations

import math
import textwrap
import warnings
from dataclasses import dataclass

from heval import abg, nutrition
from heval.common import HumanSex


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


@dataclass
class HumanModel:
    """Must set 'sex' and 'height' to make it work. See `is_init()`.

    Note that 'use_ibw == False' by default.
    """

    body_sex: HumanSex
    body_height: float  # Human height in meters
    body_age: float | None = None  # Human age in years
    body_temp: float = 36.6  # Celsius

    # Represents an human blood ABG status
    blood_abg_pH: float | None = None
    blood_abg_pCO2: float | None = None  # kPa

    blood_abg_cK: float | None = None  # mmol/L
    blood_abg_cNa: float | None = None  # mmol/L
    blood_abg_cCl: float | None = None  # mmol/L

    blood_abg_ctAlb: float | None = None  # g/dL albumin
    blood_abg_cGlu: float | None = None  # mmol/L
    blood_abg_ctHb: float | None = None  # g/dl, haemoglobin
    blood_abg_ctBun: float | None = None  # May be for osmolarity in future

    def __init__(self):
        self.debug = False
        self._weight: float | None = None
        self._use_ibw: bool = False
        self._weight_ideal_method: str = ""
        self.comment = dict()  # For warnings
        self.nutrition = nutrition.HumanNutritionModel(self)

    @property
    def body_weight(self) -> float:
        """Return human body weight, kg.

        Must calculate weight, without it class is useless.
        return RBW, then IBW
        return IBW, then RBW if 'use_ibw = True'
        """
        if self._use_ibw:
            return self.body_weight_ideal
        else:
            return self._weight or self.body_weight_ideal

    @body_weight.setter
    def body_weight(self, value: float):
        """Human body weight, kg."""
        self._weight = value

    @property
    def body_use_ibw(self):
        return self._use_ibw

    @body_use_ibw.setter
    def body_use_ibw(self, value: bool):
        """Set flag to use calculated IBW instead real weight.

        Args:
            value: Use or not IBW, bool
        """
        self._use_ibw = value

    @property
    def body_weight_ideal(self) -> float:
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
        if self.body_sex in (HumanSex.male, HumanSex.female):
            self._weight_ideal_method = "Hamilton"
            return ibw_hamilton(self.body_sex, self.body_height)

        if 0.74 <= self.body_height <= 1.524:
            self._weight_ideal_method = "Traub-Kichen 1983"
            return ibw_traub_kichen(self.body_height)
        elif 0.468 <= self.body_height < 0.74:
            # Broselow tape range. Temporary and only for low height
            self._weight_ideal_method = "Broselow"
            return ibw_broselow(self.body_height)
        else:
            self._weight_ideal_method = "Default for neonates"
            return 3.3  # Default for all neonates

    @property
    def body_bmi(self):
        """Body mass index."""
        return body_mass_index(self.body_height, self.body_weight)

    @property
    def body_bsa(self):
        """Body surface area, m2, square meters."""
        return body_surface_area_dubois(
            height=self.body_height, weight=self.body_weight
        )

    @property
    def body_total_blood_volume(self):
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
        return 70 / math.sqrt(self.body_bmi / 22) * self.body_weight

    @property
    def blood_abg_sbe(self):
        return abg.calculate_cbase(self.blood_abg_pH, self.blood_abg_pCO2)

    @property
    def blood_abg_hco3p(self):
        return abg.calculate_hco3p(self.blood_abg_pH, self.blood_abg_pCO2)

    @property
    def blood_abg_anion_gapk(self):
        """Anion gap (K+), usually not used."""
        if self.blood_abg_cK is not None:
            return abg.calculate_anion_gap(
                Na=self.blood_abg_cNa,
                Cl=self.blood_abg_cCl,
                HCO3act=self.blood_abg_hco3p,
                K=self.blood_abg_cK,
                albumin=self.blood_abg_ctAlb,
            )
        else:
            raise ValueError("No potassium specified")

    @property
    def blood_abg_anion_gap(self):
        """Calculate anion gap without potassium. Preferred method."""
        return abg.calculate_anion_gap(
            Na=self.blood_abg_cNa,
            Cl=self.blood_abg_cCl,
            HCO3act=self.blood_abg_hco3p,
            albumin=self.blood_abg_ctAlb,
        )

    @property
    def blood_abg_sid_abbr(self):
        """Strong ion difference."""
        return abg.calculate_sid_abbr(
            self.blood_abg_cNa, self.blood_abg_cCl, self.blood_abg_ctAlb
        )

    @property
    def blood_abg_osmolarity(self):
        return abg.calculate_osmolarity(self.blood_abg_cNa, self.blood_abg_cGlu)

    @property
    def blood_abg_hct_calc(self):
        """Haematocrit."""
        return abg.calculate_hct(self.blood_abg_ctHb * 10 / abg.M_Hb)

    def is_init(self) -> bool:
        """Is class got all necessary data for calculations."""
        return None not in (self.body_height, self.body_sex)

    def _info_in_body(self) -> str:
        info = f"{self.body_sex.name.title()} {self.body_height * 100:.0f}/{self.body_weight:.0f}:"
        info += f" IBW {self.body_weight_ideal:.1f} kg [{self._weight_ideal_method}],"
        if self.body_sex in (HumanSex.male, HumanSex.female):
            info += f" BMI {self.body_bmi:.1f} ({bmi_describe(self.body_bmi)}),"
        else:
            # Adult normal ranges cannot be applied to children
            info += f" BMI {self.body_bmi:.1f},"

        info += f" BSA {self.body_bsa:.3f} m².\n"

        # Value 70 ml/kg used in cardiopulmonary bypass. It valid for humans
        # older than 3 month. ml/kg ratio more in neonates and underweight
        info += "Total blood volume {:.0f} ml (70 ml/kg) or {:.0f} ml (weight indexed by Lemmens). ".format(
            self.body_weight * 70, self.body_total_blood_volume
        )
        info += f"Transfusion of one pRBC dose will increase Hb by {estimate_prbc_transfusion_response(self.body_weight):+.2f} g/dL."

        if self.body_sex == HumanSex.child:
            try:
                br_code, br_age, br_weight = get_broselow_code(self.body_height)
                info += f"\nBROSELOW TAPE: {br_code.upper()}, {br_age.lower()}, ~{br_weight:.1f} kg.\n"
            except ValueError:
                pass
            info += f"\n{mnemonic_wetflag(weight=self.body_weight)}"
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
        if self.body_use_ibw:
            weight_type = "IBW"
            weight_chosen = self.body_weight_ideal
        else:
            weight_type = "RBW"
            weight_chosen = self.body_weight

        # Dead space https://www.openanesthesia.org/aba_respiratory_function_-_dead_space
        VDaw = 2.2 * weight_chosen
        Tv_min = 2 * VDaw  # ml Lowest reasonable tidal volume
        tv_mul_min = 6
        tv_mul_max = 8
        info = ""
        mv = normal_minute_ventilation(weight_chosen)
        Vd = mv * weight_chosen  # l/min
        info += "{} respiration parameters for {} {:.1f} kg [Hamilton ASV]\n".format(
            weight_type, self.body_sex.name, weight_chosen
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
        if self.body_sex in (HumanSex.male, HumanSex.female):
            info += " * RBW fluids demand {:.0f}-{:.0f} ml/24h (30-35 ml/kg/24h) [ПосДеж]\n".format(
                30 * self.body_weight, 35 * self.body_weight
            )

        hs_fluid = fluid_holidaysegar_mod(self.body_weight)
        info += " * RBW fluids demand {:.0f} ml/24h or {:.0f} ml/h [Holliday-Segar]\n".format(
            hs_fluid, hs_fluid / 24
        )

        if self.body_height is not None:
            info += " * BSA fluids demand {:.0f} ml/24h (1750 ml/m²)".format(
                body_surface_area_dubois(
                    height=self.body_height, weight=self.body_weight
                )
                * 1750
            )  # All ages

        # Variable perspiration losses, which is not included in physiologic demand
        # persp_ros = 10 * self.weight + 500 * (self.body_temp - 36.6)
        # info += "\nRBW Perspiration: {:.0f} ml/24h [Расенок]".format(persp_ros)

        # Перспирационные потери – 5-7 мл/кг/сут на каждый градус выше 37°С [Пособие дежуранта 2014, стр. 230]
        # Точная оценка перспирационных потерь невозможна. Формула из "Пособия дежуранта" примерно соответствует [таблице 1.6 Рябов 1994, с 31 (Condon R.E. 1975)]
        if self.body_temp > 37:
            deg = self.body_temp - 37
            info += "\n + perspiration fluid loss {:.0f}-{:.0f} ml/24h (5-7 ml/kg/24h for each °C above 37°C)".format(
                5 * self.body_weight * deg, 7 * self.body_weight * deg
            )
        return info

    def _info_in_food(self) -> str:
        """Daily electrolytes demand."""
        info = ""
        if self.body_sex in (HumanSex.male, HumanSex.female):
            info += "Daily nutrition requirements for adults [ПосДеж]:\n"
            info += " * Protein {:3.0f}-{:3.0f} g/24h (1.2-1.5 g/kg/24h)\n".format(
                1.2 * self.body_weight_ideal, 1.5 * self.body_weight_ideal
            )
            info += " * Fat     {:3.0f}-{:3.0f} g/24h (1.0-1.5 g/kg/24h) (30-40% of total energy req.)\n".format(
                1.0 * self.body_weight_ideal, 1.5 * self.body_weight_ideal
            )
            info += " * Glucose {:3.0f}-{:3.0f} g/24h (4.0-5.0 g/kg/24h) (60-70% of total energy req.)\n".format(
                4.0 * self.body_weight_ideal, 5.0 * self.body_weight_ideal
            )

            info += "Electrolytes daily requirements:\n"
            info += " * Na⁺\t{:3.0f} mmol/24h [~1.00 mmol/kg/24h]\n".format(
                self.body_weight
            )
            info += " * K⁺\t{:3.0f} mmol/24h [~1.00 mmol/kg/24h]\n".format(
                self.body_weight
            )

            # Parenteral (33% of enteral) 120 mg, 5 mmol/24h [Kostuch, p 49]
            info += f" * Mg²⁺\t{self.body_weight * 0.04:3.1f} mmol/24h [~0.04 mmol/kg/24h]\n"
            # Parenteral (25% of enteral) 200 mg/24h, 5 mmol/24h [Kostuch, p 49]
            info += (
                f" * Ca²⁺\t{self.body_weight * 0.11:3.1f} mmol/24h [~0.11 mmol/kg/24h]"
            )
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
        if self.body_sex in (HumanSex.male, HumanSex.female):
            # 25-30 kcal/kg/24h IBW? ESPEN Guidelines on Enteral Nutrition: Intensive care https://doi.org/10.1016/j.clnu.2018.08.037
            if self.body_age:
                info += "Resting energy expenditure for healthy adults:\n"
                info += " * {:.0f} kcal/24h [Harris-Benedict, revised 1984] \n".format(
                    ree_harris_benedict_revised(
                        self.body_height, self.body_weight, self.body_sex, self.body_age
                    )
                )
                info += " * {:.0f} kcal/24h [Mifflin 1990]\n".format(
                    ree_mifflin(
                        self.body_height, self.body_weight, self.body_sex, self.body_age
                    )
                )
            else:
                info += "Enter age to calculate REE\n"
            info += (
                " * {:.0f}-{:.0f} kcal/24h (25-30 kcal/kg/24h IBW) [ESPEN 2019]".format(
                    25 * self.body_weight_ideal, 30 * self.body_weight_ideal
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
        info = ""
        if self.body_sex in (HumanSex.male, HumanSex.female):
            info += "RBW adult urinary output:\n"
            info += (
                " * x0.5={:2.0f} ml/h, {:4.0f} ml/24h (target >0.5 ml/kg/h)\n".format(
                    0.5 * self.body_weight, 0.5 * self.body_weight * 24
                )
            )
            info += " * x1.0={:2.0f} ml/h, {:4.0f} ml/24h".format(
                self.body_weight, self.body_weight * 24
            )
        if self.body_sex == HumanSex.child:
            # Not lower than 1 ml/kg/h in children [Курек 2013 122, 129]
            info += "RBW child urinary output:\n"
            info += " * x1  ={:3.0f} ml/h, {:.0f} ml/24h (target >1 ml/kg/h).\n".format(
                self.body_weight, self.body_weight * 24
            )
            info += " * x3.5={:3.0f} ml/h, {:.0f} ml/24h much higher in infants (up to 3.5 ml/kg/h)".format(
                3.5 * self.body_weight, 3.5 * self.body_weight * 24
            )
        return info

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
        info = ""
        if self.blood_abg_cNa is None or self.blood_abg_cGlu is None:
            return info

        info = "Osmolarity is "
        if self.blood_abg_osmolarity > abg.norm_mOsm[1]:
            info += "high"
        elif self.blood_abg_osmolarity < abg.norm_mOsm[0]:
            info += "low"
        else:
            info += "ok"
        info += f" {self.blood_abg_osmolarity:.0f} ({abg.norm_mOsm[0]:.0f}-{abg.norm_mOsm[1]:.0f} mOsm/L)"

        # Hyperosmolarity flags
        # if self.osmolarity >=282: # mOsm/kg
        #     info += " vasopressin released"
        if self.blood_abg_osmolarity > 290:  # mOsm/kg
            # plasma thirst point reached
            info += ", human is thirsty (>290 mOsm/kg)"
        if self.blood_abg_osmolarity > 320:  # mOsm/kg
            # >320 mOsm/kg Acute kidney injury cause https://www.ncbi.nlm.nih.gov/pubmed/9387687
            info += ", acute kidney injury risk (>320 mOsm/kg)"
        if self.blood_abg_osmolarity > 330:  # mOsm/kg
            # >330 mOsm/kg hyperosmolar hyperglycemic coma https://www.ncbi.nlm.nih.gov/pubmed/9387687
            info += ", coma (>330 mOsm/kg)"

        # Implies cNa, pCO2 available
        if self.blood_abg_pH is None or self.blood_abg_pCO2 is None:
            return info

        # SBE>-18.4 - same as (pH>7.3 and hco3p>15 mEq/L) https://emedicine.medscape.com/article/1914705-overview
        if all(
            (
                self.blood_abg_osmolarity > 320,
                self.blood_abg_cGlu > 30,
                self.blood_abg_sbe > -18.4,
            )
        ):
            # https://www.aafp.org/afp/2005/0501/p1723.html
            # IV insulin drip and crystalloids
            info += " Diabetes mellitus type 2 with hyperosmolar hyperglycemic state? Check for HAGMA and ketonuria to exclude DKA. Look for infection or another underlying illness that caused the hyperglycemic crisis."
        return info

    def describe_abg(self) -> str:
        """Describe pH and pCO2 - an old implementation considered stable."""
        info = ""
        if self.blood_abg_pH is not None and self.blood_abg_pCO2 is not None:
            info += textwrap.dedent(
                f"""\
                pCO2    {self.blood_abg_pCO2:2.1f} kPa
                HCO3(P) {self.blood_abg_hco3p:2.1f} mmol/L
                Conclusion: {abg.abg_approach_stable(self.blood_abg_pH, self.blood_abg_pCO2)[0]}\n"""
            )
            if self.debug:
                info += "\n-- Manual compensatory response check --------------\n"
                # info += "Abg Ryabov:\n{}\n".format(textwrap.indent(abg_approach_ryabov(self.pH, self.pCO2), '  '))
                info += abg.abg_approach_research(
                    self.blood_abg_pH, self.blood_abg_pCO2
                )
        return info

    def describe_anion_gap(self):
        if None in (
            self.blood_abg_pH,
            self.blood_abg_pCO2,
            self.blood_abg_cNa,
            self.blood_abg_cCl,
            self.blood_abg_ctAlb,
        ):
            return "pH, pCO2, cNa, cCl, albumin required"
        info = "-- Anion gap ---------------------------------------\n"
        desc = f"{self.blood_abg_anion_gap:.1f} ({abg.norm_gap[0]:.0f}-{abg.norm_gap[1]:.0f} mEq/L)"
        if (
            abg.abg_approach_stable(self.blood_abg_pH, self.blood_abg_pCO2)[1]
            == "metabolic_acidosis"
        ):
            if abg.norm_gap[1] < self.blood_abg_anion_gap:
                # Since AG elevated, calculate delta ratio to test for coexistent NAGMA or metabolic alkalosis
                info += f"HAGMA {desc} (KULT?), "
                info += abg.calculate_anion_gap_delta(
                    self.blood_abg_anion_gap, self.blood_abg_hco3p
                )
            elif self.blood_abg_anion_gap < abg.norm_gap[0]:
                info += f"Low AG {desc} - hypoalbuminemia or low Na⁺?"
            else:
                # Hypocorticism [Henessy 2018, с 113 (Clinical case 23)]
                info += f"NAGMA {desc}. Diarrhea or renal tubular acidosis?"
        else:
            if abg.norm_gap[1] < self.blood_abg_anion_gap:
                info += f"Unexpected high AG {desc} without main metabolic acidosis; "
                # Can catch COPD or concurrent metabolic alkalosis here
                info += abg.calculate_anion_gap_delta(
                    self.blood_abg_anion_gap, self.blood_abg_hco3p
                )
            elif self.blood_abg_anion_gap < abg.norm_gap[0]:
                info += f"Unexpected low AG {desc}. Starved patient with low albumin? Check your input and enter ctAlb if known."
            else:
                info += f"AG is ok {desc}"

        if self.debug:
            """Strong ion difference.

            Sometimes Na and Cl don't changes simultaneously.
            Try distinguish Na-Cl balance in case high/low osmolarity.
            Should help to choose better fluid for correction.
            """
            SIDabbr_norm = (-5, 5)  # Arbitrary threshold
            ref_str = f"{self.blood_abg_sid_abbr:.1f} ({SIDabbr_norm[0]:.0f}-{SIDabbr_norm[1]:.0f} mEq/L)"
            info += "\nSIDabbr [Na⁺-Cl⁻-38] "
            if self.blood_abg_sid_abbr > SIDabbr_norm[1]:
                info += f"is alkalotic {ref_str}, relative Na⁺ excess"
            elif self.blood_abg_sid_abbr < SIDabbr_norm[0]:
                info += f"is acidotic {ref_str}, relative Cl⁻ excess"
            else:
                info += f"is ok {ref_str}"
            info += f", BDE gap {self.blood_abg_sbe - self.blood_abg_sid_abbr:.01f} mEq/L"  # Lactate?
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
        if None in (self.blood_abg_pH, self.blood_abg_pCO2):
            return ""
        NaHCO3_threshold = -15  # was -9 mEq/L
        info = ""
        if self.blood_abg_sbe > abg.norm_sbe[1]:
            # FIXME: can be high if chloride is low. Calculate SID?
            # https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2856150
            # https://en.wikipedia.org/wiki/Contraction_alkalosis
            # Acetazolamide https://en.wikipedia.org/wiki/Carbonic_anhydrase_inhibitor
            info += f"SBE is high {self.blood_abg_sbe:.1f} ({abg.norm_sbe[0]:.0f}-{abg.norm_sbe[1]:.0f} mEq/L). Low Cl⁻, hypoalbuminemia? NaHCO₃ overdose?"
        elif self.blood_abg_sbe < abg.norm_sbe[0]:
            if self.blood_abg_sbe <= NaHCO3_threshold:
                info += f"SBE is drastically low {self.blood_abg_sbe:.1f} ({abg.norm_sbe[0]:.0f}-{abg.norm_sbe[1]:.0f} mEq/L), consider NaHCO₃ in AKI patients to reach target pH 7.3:\n"
                info += "  * Fast ACLS tip (all ages): load dose 1 mmol/kg, then 0.5 mmol/kg every 10 min [Курек 2013, 273]\n"
                # info += "NaHCO3 {:.0f} mmol during 30-60 minutes\n".format(0.5 * (24 - self.hco3p) * self.parent.weight)  # Doesn't looks accurate, won't use it [Курек 2013, с 47]
                NaHCO3_mmol = -0.3 * self.blood_abg_sbe * self.body_weight  # mmol/L
                NaHCO3_mmol_24h = self.body_weight * 5  # mmol/L
                NaHCO3_g = NaHCO3_mmol / 1000 * abg.M_NaHCO3  # gram
                NaHCO3_g_24h = NaHCO3_mmol_24h / 1000 * abg.M_NaHCO3
                # Курек 273, Рябов 73 for children and adult
                info += f"  * NaHCO₃ {NaHCO3_mmol:.0f} mmol (-0.3*SBE/kg) during 30-60 min, daily dose {NaHCO3_mmol_24h:.0f} mmol/24h (5 mmol/kg/24h):\n"
                # info += "  * NaHCO₃ {:.0f} mmol (-(SBE - 8)/kg/4)\n".format(
                #     -(self.sbe - 8) * self.parent.weight / 4, NaHCO3_mmol_24h)  # Плохой 152
                for dilution in (4, 8.4):
                    NaHCO3_ml = NaHCO3_g / dilution * 100
                    NaHCO3_ml_24h = NaHCO3_g_24h / dilution * 100
                    info += f"    * NaHCO3 {dilution:.1f}% {NaHCO3_ml:.0f} ml, daily dose {NaHCO3_ml_24h:.0f} ml/24h\n"
                if self.debug:
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
                info += f"SBE is low {self.blood_abg_sbe:.1f} ({abg.norm_sbe[0]:.0f}-{abg.norm_sbe[1]:.0f} mEq/L), but NaHCO₃ won't improve outcome when BE > {NaHCO3_threshold:.0f} mEq/L"
        else:
            info += f"SBE is ok {self.blood_abg_sbe:.1f} ({abg.norm_sbe[0]:.0f}-{abg.norm_sbe[1]:.0f} mEq/L)"
        return info

    def describe_electrolytes(self):
        if None in (
            self.body_weight,
            self.blood_abg_cK,
            self.blood_abg_cNa,
            self.blood_abg_cCl,
            self.blood_abg_cGlu,
        ):
            return ""
        info = [
            "-- Electrolyte and osmolar abnormalities -----------",
            self.describe_osmolarity(),
            electrolyte_K(self.body_weight, self.blood_abg_cK),
            electrolyte_Na(
                self.body_weight, self.blood_abg_cNa, self.blood_abg_cGlu, self.debug
            ),
            electrolyte_Cl(self.blood_abg_cCl),
        ]

        return "\n".join(info) + "\n"

    def describe_glucose(self):
        """Assess glucose level.

        https://en.wikipedia.org/wiki/Renal_threshold
        https://en.wikipedia.org/wiki/Glycosuria
        """
        info = ""
        if self.body_weight is None or self.blood_abg_cGlu is None:
            return info
        if self.blood_abg_cGlu > abg.norm_cGlu[1]:
            if self.blood_abg_cGlu <= abg.norm_cGlu_target[1]:
                info += f"cGlu is above ideal {self.blood_abg_cGlu:.1f} (target {abg.norm_cGlu_target[0]:.1f}-{abg.norm_cGlu_target[1]:.1f} mmol/L), but acceptable"
            else:
                info += f"Hyperglycemia {self.blood_abg_cGlu:.1f} (target {abg.norm_cGlu_target[0]:.1f}-{abg.norm_cGlu_target[1]:.1f} mmol/L) causes glycosuria with osmotic diuresis"
                if self.blood_abg_cGlu <= 20:  # Arbitrary threshold
                    info += f", consider insulin {insulin_by_glucose(self.blood_abg_cGlu):.0f} IU subcut for adult"
                else:
                    info += f", refer to DKE/HHS protocol (HAGMA and urine ketone), start fluid and I/V insulin {self.body_weight * 0.1:.1f} IU/h (0.1 IU/kg/h)"

        elif self.blood_abg_cGlu < abg.norm_cGlu[0]:
            if self.blood_abg_cGlu > 3:  # Hypoglycemia <3.3 mmol/L for pregnant?
                info += f"cGlu is below ideal {self.blood_abg_cGlu:.1f} (target {abg.norm_cGlu_target[0]:.1f}-{abg.norm_cGlu_target[1]:.1f} mmol/L), repeat blood work, don't miss hypoglycemic state"
            else:
                info += "Severe hypoglycemia, IMMEDIATELY INJECT BOLUS GLUCOSE 10 % 2.5 mL/kg:\n"
                # https://litfl.com/glucose/
                # For all ages: dextrose 10% bolus 2.5 mL/kg (0.25 g/kg) [mistake Курек, с 302]
                info += solution_glucose(
                    0.25 * self.body_weight,
                    self.body_weight,
                    add_insuline=False,
                )
                # High lactate + refractory low cGlu marks liver failure: expect death in 24-48 hours
                info += "Check cGlu after 20 min, repeat bolus and use continuous infusion, if refractory. In case of sepsis, liver failure may be the cause."

        else:
            info += f"cGlu is ok {self.blood_abg_cGlu:.1f} ({abg.norm_cGlu[0]:.1f}-{abg.norm_cGlu[1]:.1f} mmol/L)"
        return info

    def describe_albumin(self):
        """Albumin as nutrition marker in adults."""
        if self.blood_abg_ctAlb is None:
            return ""
        ctalb_range = f"{self.blood_abg_ctAlb:0.1f} ({abg.norm_ctAlb[0]}-{abg.norm_ctAlb[1]} g/dL)"
        if abg.norm_ctAlb[1] < self.blood_abg_ctAlb:
            info = f"ctAlb is high {ctalb_range}. Dehydration?"
        elif abg.norm_ctAlb[0] <= self.blood_abg_ctAlb <= abg.norm_ctAlb[1]:
            info = f"ctAlb is ok {ctalb_range}"
        elif 3 <= self.blood_abg_ctAlb < abg.norm_ctAlb[0]:
            info = f"ctAlb is low: mild hypoalbuminemia {ctalb_range}"
        elif 2.5 <= self.blood_abg_ctAlb < 3:
            info = f"ctAlb is low: medium hypoalbuminemia {ctalb_range}"
        elif self.blood_abg_ctAlb < 2.5:
            info = f"ctAlb is low: severe hypoalbuminemia {ctalb_range}. Expect oncotic edema"
        return info

    def describe_hb(self):
        """Describe Hb and hct_calc.

        References
        ----------
        [1] https://en.wikipedia.org/wiki/Hematocrit#cite_ref-3
        [2] https://www.healthcare.uiowa.edu/path_handbook/appendix/heme/pediatric_normals.html
        """
        info = ""
        if (
            self.body_weight is None
            or self.body_sex is None
            or self.blood_abg_ctHb is None
        ):
            return info
        # Top hct value for free water deficit calculation.
        if self.body_sex == HumanSex.male:
            hb_norm = abg.hb_norm_male
            hct_norm = abg.hct_norm_male
        elif self.body_sex == HumanSex.female:
            hb_norm = abg.hb_norm_female
            hct_norm = abg.hct_norm_female
        elif self.body_sex == HumanSex.child:
            hb_norm = abg.hb_norm_child
            hct_norm = abg.hct_norm_child
        hct_target = hct_norm[0] + (hct_norm[1] - hct_norm[0]) / 2  # Mean
        vol_def = volume_deficit_hct(
            self.body_weight, self.blood_abg_hct_calc, hct_target
        )

        desc_hb = f"{self.blood_abg_ctHb:.1f} ({hb_norm[0]:.1f}-{hb_norm[1]:.1f} g/dl)"
        desc_hct = (
            f"{self.blood_abg_hct_calc:.3f} ({hct_norm[0]:.3f}-{hct_norm[1]:.3f})"
        )
        info = ""
        if self.blood_abg_ctHb < 7:  # Generic threshold
            info += f"Hb is low {desc_hb}, consider transfusion. "
        else:
            info += f"Hb {desc_hb}. "

        if self.blood_abg_hct_calc > hct_norm[1]:
            info += f"Hct is high {desc_hct}"
        elif self.blood_abg_hct_calc < hct_norm[0]:
            info += f"Hct is low {desc_hct}"
        else:
            info += f"Hct is ok {desc_hct}"

        if self.blood_abg_hct_calc > hct_target + 0.01:  # Age-independent threshold
            info += f", free water deficit {vol_def:.0f} ml (limitations: valid if no anemia, osmolarity and Na⁺ are more specific)."

        if self.body_sex == HumanSex.child:
            info += " \nNote that normal Hb and Hct values in children greatly dependent from age."
        return info

    def describe_body(self) -> str:
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

    def describe_blood_abg(self) -> str:
        info = ""
        info += "Basic ABG assessment\n"
        info += "====================\n"
        info += "{}\n".format(self.describe_abg())
        info += "{}\n\n\n".format(self.describe_sbe())

        info += "Complex electrolyte assessment\n"
        info += "==============================\n"
        info += "{}\n\n".format(self.describe_anion_gap())
        info += "{}\n".format(self.describe_electrolytes())

        info += "{}\n\n".format(self.describe_glucose())
        info += "{}\n\n".format(self.describe_albumin())
        info += "{}\n".format(self.describe_hb())
        return info


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
    info = ""
    if bmi < 18.5:
        info += "underweight: "
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
        Tuple of color code, approx age, approx weight (kg).
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


###


def solution_glucose(
    glu_mass: float, body_weight: float, add_insuline: bool = True
) -> str:
    """Glucose and insulin solution calculation.

    Probably such glucose/insulin ratio can be used for both nutrition
    and as hyperkalemia bolus.

    * 1 ЕД на 3-5 г сухой глюкозы, скорость инфузии <= 0.5 г/кг/ч чтобы избежать глюкозурии [Мартов, Карманный справочник врача; RLSNET, Крылов Нейрореаниматология] (Ins 0.33-0.2 UI/г)
    * 1 ЕД на 4 г сухой глюкозы (если глюкозурия, то добавить инсулин или снизить скорость введения) [Курек, с 143; калькулятор BBraun; другие источники]
        * 0.25 IU/g

    Args:
        glu_mass: glucose mass, grams
        body_weight: patient body weight, kg
        add_insuline: Set False if bolus intended for hypoglycemic state
    """
    glu_mol = glu_mass / abg.M_C6H12O6  # mmol/L
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


def solution_kcl4(salt_mmol: float) -> float:
    """Convert mmol of KCl to volume of saline solution.

    Args:
        salt_mmol: KCl, amount of substance, mmol

    Returns:
        KCl 4 % ml solution, ml
    """
    return salt_mmol / 1000 * abg.M_KCl / 4 * 100


def solution_normal_saline(salt_mmol: float, hours: float | None = None) -> str:
    """Convert mmol of NaCl to volume of saline solution (several dilutions).

    Administration rate limiting:
        By ml/min for bolus
        By ml/h for continuous
        By mmol/h of sodioum

    NaCl 0.9%, 0.15385 mmol/ml
    NaCl 3%  , 0.51282 mmol/ml
    NaCl 10% , 1.70940 mmol/ml

    Args:
        salt_mmol: Amount of substance (NaCl or single ion equivalent), mmol
        hours: Replacement time. If given, return flow speed, otherwise just volume
    Returns:
        Info string
    """
    info = ""
    for dilution in (0.9, 3, 5, 10):
        conc = 1000 * (dilution / 100) / abg.M_NaCl  # mmol/ml
        vol = salt_mmol / conc  # ml
        if hours is None:
            info += f" * NaCl {dilution:>4.1f}% {vol:>4.0f} ml"
        else:
            info += f" * NaCl {dilution:>4.1f}% {vol / hours:>4.0f} ml/h"
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
        info += f"replace it with D5 at rate {water_deficit / Na_shift_hours:.1f} ml/h during {Na_shift_hours:.0f} hours.\n"
    elif Na_serum < Na_target:
        # Classic hyponatremia formula
        Na_deficit = total_body_water * (Na_target - Na_serum)  # mmol
        info += f"Na⁺ deficit is {Na_deficit:.0f} mmol, which equals to:\n"
        info += solution_normal_saline(Na_deficit)
        info += f"Replace Na⁺ at rate {Na_shift_rate:.1f} mmol/L/h during {Na_shift_hours:.0f} hours:\n"
        info += solution_normal_saline(Na_deficit, Na_shift_hours)
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
        {"name": "NaHCO3 4%       (Na⁺ 476 mmol/L)", "K_inf": 0, "Na_inf": 476},
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


def electrolyte_K(weight: float, K_serum: float) -> str:
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
    if K_serum > abg.norm_K[1]:
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
    elif K_serum < abg.norm_K[0]:
        if K_serum < K_low:
            info += f"K⁺ is dangerously low (<{K_low:.1f} mmol/L). Often associated with low Mg²⁺ (should be at least 1 mmol/L) and low Cl⁻.\n"
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
        info += (
            f"K⁺ is ok {K_serum:.1f} ({abg.norm_K[0]:.1f}-{abg.norm_K[1]:.1f} mmol/L)]"
        )
    return info


def electrolyte_Na(
    weight: float, Na_serum: float, cGlu: float, verbose: bool = True
) -> str:
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
    desc = f"{Na_serum:.0f} ({abg.norm_Na[0]:.0f}-{abg.norm_Na[1]:.0f} mmol/L)"
    if Na_serum > abg.norm_Na[1]:
        info += (
            f"Na⁺ is high {desc}, check osmolarity. Give enteral water if possible. "
        )
        info += f"Warning: Na⁺ decrement faster than {Na_shift_rate:.1f} mmol/L/h can cause cerebral edema.\n"
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
    elif Na_serum < abg.norm_Na[0]:
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


def correct_Na_hyperosmolar(cNa: float, cGlu: float) -> float:
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
    cGlu_mgdl = cGlu * abg.M_C6H12O6 / 10
    # Na_shift = (cGlu_mgdl - 100) / 100 * 1.6  # Katz, 1973
    Na_shift = (cGlu_mgdl - 100) / 100 * 2.4  # Hillier, 1999
    return cNa + Na_shift


def volume_deficit_hct(weight: float, hct: float, hct_target: float = 0.4) -> float:
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

    Args:
        weight: Real body weight, kg
        hct: Hematocrit fraction, e.g 0.5
        hct_target: Target hematocrit fraction, default 0.4 for both men
            and women. May be 0.407–0.503 for men and 0.361-0.443 for women.

    Returns:
        Volume deficiency, ml
    """
    return (1 - hct_target / hct) * 0.2 * weight * 1000


def electrolyte_Cl(Cl_serum: float) -> str:
    """Assess blood serum chloride level.

    Args:
        Cl_serum: mmol/L
    """
    info = ""
    Cl_low, Cl_high = abg.norm_Cl[0], abg.norm_Cl[1]
    if Cl_serum > Cl_high:
        info += f"Cl⁻ is high {Cl_serum:.0f} (>{Cl_high} mmol/L), excessive NaCl infusion or dehydration (check osmolarity)."
    elif Cl_serum < Cl_low:
        # KCl replacement?
        info += (
            f"Cl⁻ is low {Cl_serum:.0f} (<{Cl_low} mmol/L). Vomiting? Diuretics abuse?"
        )
    else:
        info += f"Cl⁻ is ok {Cl_serum:.0f} ({abg.norm_Cl[0]:.0f}-{abg.norm_Cl[1]:.0f} mmol/L)"
    return info


def egfr_mdrd(
    sex: HumanSex, cCrea: float, age: float, black_skin: bool = False
) -> float:
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
    >>> from heval import common
    >>> egfr_mdrd(common.HumanSex.male, 74.4, 27)
    109.36590492087734
    >>> egfr_mdrd(common.HumanSex.female, 100, 80, True)
    55.98942027449337

    Args:
        sex: Choose 'male', 'female'.
        cCrea: Serum creatinine (IDMS-calibrated), μmol/L
        age: Human age, years
        black_skin: True for people with black skin (african american)

    Returns:
        eGFR, mL/min/1.73 m2
    """
    # Original equation from 1999 (non IDMS)
    # egfr = 186 * (cCrea / m_Crea) ** -1.154 * age ** -0.203

    # Revised equation from 2005, to accommodate for standardization of
    # creatinine assays over isotope dilution mass spectrometry (IDMS) SRM 967.
    # Equation being used by Radiometer devices
    egfr = 175 * (cCrea / abg.M_Crea) ** -1.154 * age**-0.203
    if sex == HumanSex.female:
        egfr *= 0.742
    elif sex == HumanSex.child:
        raise ValueError("MDRD eGFR for children not supported")
    if black_skin:
        egfr *= 1.210
    return egfr


def egfr_ckd_epi(
    sex: HumanSex, cCrea: float, age: float, black_skin: bool = False
) -> float:
    """Estimated glomerular filtration rate (CKD-EPI 2009 formula).

    For patients >18 years. Appears as more accurate than MDRD, especially
    when actual GFR is greater than 60 mL/min per 1.73 m2.
    Cahexy, limb amputation will reduce creatinine production, so eGFR
    will look better than it is.

    References
    ----------
    [1] A new equation to estimate glomerular filtration rate. Ann Intern Med. 2009;150(9):604-12.
    [2] https://en.wikipedia.org/wiki/Renal_function#Glomerular_filtration_rate

    Args:
        sex: Choose 'male', 'female'.
        cCrea: Serum creatinine (IDMS-calibrated), μmol/L
        age: Human age, years
        black_skin: True for people with black skin (african american)

    Returns:
        eGFR, mL/min/1.73 m2
    """
    cCrea /= abg.M_Crea  # to mg/dl
    if sex == HumanSex.male:
        if cCrea <= 0.9:
            egfr = 141 * (cCrea / 0.9) ** -0.411 * 0.993**age
        else:
            egfr = 141 * (cCrea / 0.9) ** -1.209 * 0.993**age
    elif sex == HumanSex.female:
        if cCrea <= 0.7:
            egfr = 141 * (cCrea / 0.7) ** -0.329 * 0.993**age * 1.018
        else:
            egfr = 141 * (cCrea / 0.7) ** -1.209 * 0.993**age * 1.018
    elif sex == HumanSex.child:
        raise ValueError("CKD-EPI eGFR for children not supported")

    if black_skin:
        egfr *= 1.159
    return egfr


def egfr_schwartz(cCrea: float, height: float) -> float:
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

    Args:
        cCrea: Serum creatinine (IDMS-calibrated), μmol/L
        height: Children height, meters

    Returns:
        eGFR, mL/min/1.73 m2.
    """
    cCrea /= abg.M_Crea  # to mg/dl
    # k = 0.33  # First year of life, pre-term infants
    # k = 0.45  # First year of life, full-term infants
    # k = 0.55  # 1-12 years
    k = 0.413  # 1 to 16 years. Updated in 2009
    return k * height * 100 / cCrea


def gfr_describe(gfr: float) -> str:
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


def insulin_by_glucose(cGlu: float) -> float:
    """Monoinsulin subcutaneous dose for a given serum glycemia level.

    Insulin sesnitivity at morning lower, then at evening.

    References
    ----------
    [1] Oleskevitch uses target 5 mmol/L: `(cGlu - 5) * 2`
    [2] Lipman, T. Let's abandon urine fractionals in TPN. Nutrition Support Services. 4:38-40, 1984.

    Args:
        cGlu: Serum glucose mmol/L
    Returns:
        Insulin dose in IU. Returns zero if cGlu < 10 or cGlu > 25.
    """
    # cGlu mg/dl * 0.0555 = mmol/L
    # 0.55 = (100 / daily_iu) may be considered as sensetivity to ins
    target = 7  # Tagget glycemia, mmol/L
    if cGlu < 10 or 25 < cGlu:
        return 0
    else:
        return (cGlu - target) / 0.55
