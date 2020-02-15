# -*- coding: utf-8 -*-
"""Nutriflex 48/150 lipid https://www.rlsnet.ru/tn_index_id_36361.htm

    рН 5,0-6,0
    Метаболический ацидоз
    Гиперосмолярность
    ОПП?

Дети с 14 лет и взрослые
Дети с 2 до 5 лет (начинать с половинной дозы)
------------------------
Максимальная суточная доза 40 мл/кг массы тела, что соответствует:
аминокислоты 1,54 г/кг/сутки
глюкоза      4,8  г/кг/сутки
жиры         1,6  г/кг/сутки

Дети с 5 до 14 лет
------------------
Максимальная суточная доза 25 мл/кг массы тела, что соответствует:
аминокислоты 0,96 г/кг/сутки
глюкоза      3,0  г/кг/сутки
жиры         1,0  г/кг/сутки

Скорость повышать в первые 30 минут
Не более 40 ккал/кг массы тела/сутки (исключение - ожоговые)

Максимальная скорость инфузии - 2,0 мл/кг массы тела/ч, что соответствует
аминокислоты 0,08 г/кг/ч
глюкоза      0,24 г/кг/ч
жиры         0,08 г/кг/ч
"""
parenteral_nutriflex_48_150 = {
    'name': "Nutriflex 48/150 lipid 1000, 1250, 1875, 2500 ml",
    'type': 'parenteral',
    'c_prt': 0.0384,        # g/ml proteins
    'c_lip': 0.04,          # g/ml lipids
    'c_glu': 0.12,          # g/ml glucose
    'c_kcal': 1.012,        # kcal/ml total calories including proteins
    'c_kcal_noprot': 0.86,  # kcal/ml nonprotein calories
    'max_24h_volume': 40,   # ml/kg/24h
    'max_1h_rate': 2,       # ml/kg/h rate limit (by glucose for this drug)
    'osmolality': 1540,     # mOsm/kg Central vena only
    'has_vitamins': False,
    'comment': "Ratio 1:1:3",
}


"""Kabiven peripheral https://www.rlsnet.ru/tn_index_id_30269.htm

У пациентов с умеренным или тяжелым катаболическим стрессом
    потребность в аминокислотах составляет 1–2 г/кг/сут
    что примерно соответствует потребности в азоте 0,15–0,3 г/кг/сут.
    Потребность в энергии составляет 30–50 ккал/кг/сут.

У пациентов без катаболического стресса 
    потребность в аминокислотах составляет 0,7–1 г/кг/сут,
    что примерно равно потребности в азоте 0,1–0,15 г/кг/сут.
    Потребность в энергии составляет 20–30 ккал/кг/сут.
    Это соответствует 27–40 мл/кг/сут препарата.


Максимальная суточная доза для взрослых — 40 мл/кг/сут (один большой мешок 2400 мл для пациента массой 64 кг ОШИБКА-60 кг)
    поступление 0,96 г/кг/сут аминокислот (0,16 г/кг/сут азота)
    25 ккал/кг/сут небелковой энергии
    2,7 г/кг/сут глюкозы
    1,4 г/кг/сут липидов

Инфузию детям (от 2 до 10 лет) следует начинать с низких доз — 14–28 мл/кг/сут что соответствует суточному поступлению
    аминокислот 0,34–0,67 г/кг
    глюкозы 0,95–1,9 г/кг
    липидов 0,49–0,98 г/кг
затем дозу следует увеличивать на 10–15 мл/кг/сут, максимально — до 40 мл/кг/сут. У детей старше 10 лет применяют такие же дозы, как и у взрослых.

Максимальная скорость абстрактная:
    аминокислот 0,1  g/kg/h
    глюкозы     0,25 g/kg/h
    липидов     0,15 g/kg/h

Скорость инфузии препарата Кабивен периферический не должна превышать 3,7 мл/кг/ч:
    аминокислот 0,09 g/kg/h
    глюкозы     0,25 g/kg/h <- limit
    липидов     0,13 g/kg/h
"""
parenteral_kabiven_perif = {
    'name': "Kabiven peripheral 1440, 1920, 2400 ml",
    'type': 'parenteral',
    'c_prt': 0.0235,         # g/ml
    'c_lip': 0.0354,         # g/ml
    'c_glu': 0.0675,         # g/ml
    'c_kcal': 0.7,           # kcal/ml total, including proteins
    'c_kcal_noprot': 0.625,  # kcal/ml without proteins
    'max_24h_volume': 40,    # ml/kg/24h
    'max_1h_rate': 3.7,      # ml/kg/h rate limit (by glucose for this drug
    'osmolality': 830,       # mOsm/kg Periferal or central vein
    'has_vitamins': False,
    'comment': "Ratio 1:1.5:3",
}


enteral_nutricomp_standard = {
    'name': "Nutricomp standard 500, 1000 ml",
    'type': 'enteral',
    'c_prt': 3.8 / 100,     # g/ml proteins
    'c_lip': 3.3 / 100,     # g/ml lipids
    'c_glu':  14 / 100,     # g/ml glucose
    'water': 0.84,          # H2O/ml
    'c_kcal': 1,            # kcal/ml total calories including proteins
#     'c_kcal_noprot': 0,     # kcal/ml nonprotein calories
    'max_1h_rate': 0,
    'osmolality': 240,      # mOsm/kg
    'has_vitamins': True,
    'comment': "Caloric P:F:C - 15:30:55:0; 1500-2000 ml per day",
}


enteral_nutricomp_energy = {
    'name': "Nutricomp energy 500, 1000 ml",
    'type': 'enteral',
    'c_prt': 6.0 / 100,     # g/ml proteins
    'c_lip': 5 / 100,       # g/ml lipids
    'c_glu': 20 / 100,      # g/ml glucose
    'water': 0.76,          # H2O/ml
    'c_kcal': 1.5,          # kcal/ml total calories including proteins
#     'c_kcal_noprot': 0,     # kcal/ml nonprotein calories
    'max_1h_rate': None,
    'osmolality': 495,      # mOsm/kg
    'has_vitamins': True,
    'comment': "Caloric P:F:C - 20:30:50:0; 1000–1500 ml per day",
}

# https://pharmland.by/product/nutrition/enterolin-500-ml-i-1000-ml.html
enteral_enterolin_vanilla = {
    'name': "Enterolin vanilla or Enterolin fiber 500, 1000 ml",
    'type': 'enteral',
    'c_prt': 4 / 100,     # g/ml proteins
    'c_lip': 3.8 / 100,     # g/ml lipids
    'c_glu':  12 / 100,     # g/ml glucose
    'water': None,          # H2O/ml
    'c_kcal': 1,            # kcal/ml total calories including proteins
#     'c_kcal_noprot': 0,     # kcal/ml nonprotein calories
    'max_1h_rate': None,
    'osmolality': 330,      # mOsm/kg
    'has_vitamins': True,
    'comment': "1500-2000 ml per day",
}

enteral_enterolin_caloric = {
    'name': "Enterolin caloric cherry 500, 1000 ml",
    'type': 'enteral',
    'c_prt': 7.5 / 100,     # g/ml proteins
    'c_lip': 5.6 / 100,     # g/ml lipids
    'c_glu': 17.5 / 100,     # g/ml glucose
    'water': None,          # H2O/ml
    'c_kcal': 1.5,            # kcal/ml total calories including proteins
#     'c_kcal_noprot': 0,     # kcal/ml nonprotein calories
    'max_1h_rate': None,
    'osmolality': 420,      # mOsm/kg
    'has_vitamins': True,
    'comment': "",
}


class HumanNutritionModel(object):
    def __init__(self, human_model):
        super(HumanNutritionModel, self).__init__()
        self.human_model = human_model
        self.fluid_multipler = 30  # ml/kg RBW
        self.kcal_multipler = 25  # ml/kg RBW
        self.uurea = None  # Total urine urea, mmol
        # self.protein_24h = 1.5 * self.human_model.weight

    @property
    def fluid_24h(self):
        return self.fluid_multipler * self.human_model.weight

    @property
    def fluid_1h(self):
        return self.fluid_24h / 24

    @property
    def kcal_24h(self):
        return self.kcal_multipler * self.human_model.weight

    @property
    def uurea_prot_24h(self):
        return nitrogen_balance(self.uurea)

    @property
    def uures_prot_g_kg_24h(self):
        return self.uurea_prot_24h / self.human_model.weight

    def describe_nutrition(self, by_protein=False):
        """Trying to find a compromise between fluids, electrolytes and energy.
        """

        info = "Generic approximation by body mass\n==================================\n"
        info += "Start point:\n * Fluid demand {:.0f} ml/24h (35 ml/kg/24h)\n * Energy demand {:.0f} kcal/24h (25 kcal/kg/24h)\n\n".format(self.fluid_24h, self.kcal_24h)

        # Total enteral nutrition
        info += "Enteral nutrition\n-----------------\n"
        if self.human_model.debug:
            info += "Always prefer enteral nutrition. Enteral mixtures contains proteins, fat, glucose. Plus vitamins and electrolytes - all that human craves. For an adult give 1500-2000 kcal, add water to meet daily requirements and call it a day.\n"
        NForm = NutritionFormula(enteral_nutricomp_standard, self)
        info += "{}\n".format(str(NForm))
        if by_protein:
            full_enteral_nutrition = NForm.dose_by_protein(self.kcal_24h)
        else:
            full_enteral_nutrition = NForm.dose_by_kcal(self.kcal_24h)
        full_enteral_fluid = self.fluid_24h - full_enteral_nutrition
        info += "Give {:.0f} ml + water {:.0f} ml. ".format(full_enteral_nutrition, full_enteral_fluid)
        # full_enteral_nutrition and self.fluid_24h in ml, so they reduce each other
        info += "Resulting osmolality is {:.1f} mOsm/kg".format(
            (full_enteral_nutrition * NForm.osmolality) / self.fluid_24h)
        info += "{}\n".format(NForm.describe_dose(full_enteral_nutrition))

        # Total parenteral nutrition
        info += "Total parenteral nutrition\n--------------------------\n"
        if self.human_model.debug:
            info += "Parenteral mixtures contains proteins, fat, glucose and minimal electrolytes to not strain the vein. Add vitamins, fluid, electrolytes to meet daily requirement (total parenteral nutrition criteria).\n"
        NForm = NutritionFormula(parenteral_nutriflex_48_150, self)
        info += "{}\n".format(str(NForm))
        if by_protein:
            full_parenteral_nutrition = NForm.dose_by_protein(self.kcal_24h)
        else:
            full_parenteral_nutrition = NForm.dose_by_kcal(self.kcal_24h)
        full_parenteral_fluid = self.fluid_24h - full_parenteral_nutrition
        info += "Give {:.0f} ml + isotonic fluid {:.0f} ml\n".format(full_parenteral_nutrition, full_parenteral_fluid)
        info += "{}\n".format(NForm.describe_dose(full_parenteral_nutrition))
        info += "Maximal {}\n".format(NForm.describe_dose(NForm.dose_max_kcal()))

        # Mixed parenteral with enteral
        info += "Partial periferal + enteral nutrition\n-------------------------------------\n"
        if self.human_model.debug:
            info += "Using periferal vein is possible for <900 mOsm/kg mixtures, but needs simultanious enteral feeding to meet daily requirement.\n"
        NForm = NutritionFormula(parenteral_kabiven_perif, self)
        info += "{}\n".format(str(NForm))
        if by_protein:
            full_parenteral_nutrition = NForm.dose_by_protein(self.kcal_24h)
        else:
            full_parenteral_nutrition = NForm.dose_by_kcal(self.kcal_24h)
        full_parenteral_fluid = self.fluid_24h - full_parenteral_nutrition
        info += "Give {:.0f} ml + isotonic fluid {:.0f} ml. No need to give a water?\n".format(full_parenteral_nutrition, full_parenteral_fluid)
        info += "{}\n".format(NForm.describe_dose(full_parenteral_nutrition))
        info += "Maximal {}\n".format(NForm.describe_dose(NForm.dose_max_kcal()))
        if self.kcal_24h > NForm.dose_max_kcal():
            info += "Add enteral"
        return info

    def describe_nitrogen_balance(self):
        return nitrogen_balance(self.uurea, text=True)


class NutritionFormula(object):
    def __init__(self, preparation, parent):
        """
        :param dict preparation: Specific dict with an nutrition preparation.
        :param class parent: HumanModel class instance.
        """
        self.parent = parent
        for k, v in preparation.items():
            setattr(self, k, v)

    def __str__(self):
        return self.name

    def estimete_calories(self):
        """Test caloric content.
        """
        prt = 4  # 4.1
        lip = 9
        glu = 4.1  # pure glucose
        # glu = 3.4  # glucose monohydrate
        info = "Estimation of total calories {:.2f} kcal/ml, ".format(self.c_lip * lip + self.c_glu * glu + self.c_prt * prt)
        info += "nonprotein calories {:.2f} kcal/ml. ".format(self.c_lip * lip + self.c_glu * glu)
        if hasattr(self, 'c_kcal_noprot'):
            info += "Manufacturer states: {:.1f} kcal/ml, {:.1f} kcal/ml nonprotein".format(self.c_kcal, self.c_kcal_noprot)
        else:
            info += "Manufacturer states: {:.1f} kcal/ml".format(self.c_kcal)
        return info

    def dose_by_kcal(self, kcal_24h):
        """Dose by non-protein kcal_24h.

        Mathod can returm volume exceeding maximal recommended daily dose.
        """
        return kcal_24h / self.c_kcal

    # def dose_by_kcal_total(self, kcal_24h):
    #     """Dose by non-protein kcal_24h.
    #     """
    #     return kcal_24h / self.c_kcal

    def dose_by_protein(self, protein_24h):
        """Dose by required protein in 24 h.

        Mathod can returm volume exceeding maximal recommended daily dose.

        protein, g
        """
        return protein_24h / self.c_prt

    def dose_max_ml(self):
        """Maximal 24h parenteral nutrition volume, recommended by manufacturer.

        Nutriflex 48/150.
        """
        if self.parent.human_model.sex in ('male', 'female'):  # 2-5 years and adults,
            daily_volume = 40  # Top ml/kg/24h, same as 40 kcal/kg/24h
        elif self.parent.human_model.sex == 'child':  # 5-14 years
            daily_volume = 25  # Top ml/kg/24h
        return self.parent.human_model.weight * daily_volume

    def dose_max_kcal(self):
        """How many kcal provides maximal daily dose.
        """
        return self.dose_max_ml() * self.c_kcal
    
    def describe_dose(self, vol_24h):
        """Info about given volime content.

        :param float vol_24h: Dose, ml
        """
        weight = self.parent.human_model.weight
        kcal_24h = vol_24h * self.c_kcal
        info = ""
        if self.type == 'parenteral':
            rate_1h = vol_24h / 24
            top_rate_1h = self.max_1h_rate * weight
            info += "Daily dose {:.0f} ml/24h ({:.0f} kcal/24h) at rate {:.0f}-{:.0f} ml/h:\n".format(vol_24h, kcal_24h, rate_1h, top_rate_1h)
            info += "  * Proteins {:>5.1f} g/24h ({:>4.2f}-{:>4.2f} g/kg/h)\n".format(self.c_prt * vol_24h, self.c_prt * rate_1h / weight, self.c_prt * top_rate_1h / weight)
            info += "  * Lipids   {:>5.1f} g/24h ({:>4.2f}-{:>4.2f} g/kg/h)\n".format(self.c_lip * vol_24h, self.c_lip * rate_1h / weight, self.c_lip * top_rate_1h / weight)
            info += "  * Glusose  {:>5.1f} g/24h ({:>4.2f}-{:>4.2f} g/kg/h)\n".format(self.c_glu * vol_24h, self.c_glu * rate_1h / weight, self.c_glu * top_rate_1h / weight)
        else:
            info += "Daily dose {:.0f} ml/24h ({:.0f} kcal/24h)\n".format(vol_24h, kcal_24h)
            info += "  * Proteins {:>5.1f} g/24h\n".format(self.c_prt * vol_24h)
            info += "  * Lipids   {:>5.1f} g/24h\n".format(self.c_lip * vol_24h)
            info += "  * Glusose  {:>5.1f} g/24h\n".format(self.c_glu * vol_24h)
        return info


def uun_mgdl2mmoll(gdl):
    """Urine urea nitrogen mg/dL to mmol/L conversion.

    Note that it uses different bolam mass, so it's not an urea converter.

    https://en.wikipedia.org/wiki/Urine_urea_nitrogen
    http://www.scymed.com/en/smnxps/psxfg163_c.htm

    Examples
    --------
    >>> uun_mgdl2mmoll(500)
    178.57142857142858
    """
    return gdl / 2.8  # Urea nitrogen molar mass


def uun_mmoll2mgdl(mmol):
    """Urine urea nitrogen mmol/L to mg/dL conversion.

    Note that it uses different molar mass, so it's not an urea converter.

    https://en.wikipedia.org/wiki/Urine_urea_nitrogen

    Exaxmples
    ---------
    >>> uun_mmoll2mgdl(200)
    560.0
    """
    return mmol * 2.8  # Urea nitrogen molar mass


def urea_mmoll2mgdl(mmol):
    """Urea mmol/L to mg/dL conversion.

    Note that it uses different molar mass, so it's not an urea converter.

    https://en.wikipedia.org/wiki/Urine_urea_nitrogen

    Exaxmples
    ---------
    >>> urea_mmoll2mgdl(500)
    3003.0
    """
    return mmol * 6.006  # Urea molar mass


def nitrogen_balance(c_uurea, diuresis=1000, text=False):
    """Calculate daily protein recquirement by daily Urine Urea Nitrogen (BUN) excretion.

    1. Wait 1-2 days before urine urea collection to acieve steady metabolic state
    2. Collect urine for 24 hours and measure it's BUN concentration
    3. Calculate total BUN lost with urine (mol/24h), recalculate it to nitrogen (g/24h)
    4. Add insensituve loss (stool) with empiric constant
    5. Convert to protein requirement g/24h by multiplying by a 6.25 factor

    Not applicable:
        * If diuresis <1000 ml/24h
        * If kidney not excrete BUN (correction method exhists, see [3, 4])

    Urine Urea Nitrogen, higher than intake nitrogen means catabolism.
    Goal is positive balance 3-4 g for growth and repair.
    Must give non-protein caloric substrate along with protein, or protein will be wasted for energy.

    [1] Original paper? https://www.ncbi.nlm.nih.gov/pubmed/98649
    [2] https://en.wikipedia.org/wiki/Nitrogen_balance
    [3] Dickerson R.N. Using nitrogen balance in clinical practice. Hosp. Pharm. 2005;40:1081–1087. doi: 10.1177/001857870504001210.
        https://www.researchgate.net/profile/Roland_Dickerson/publication/237837800_Using_Nitrogen_Balance_in_Clinical_Practice/links/540daa0b0cf2d8daaacc6c84/Using-Nitrogen-Balance-in-Clinical-Practice.pdf
    [4] Нутритивная терапия. Костюченко 2016

    Examples
    --------
    Urea 177 mmol/L (= 10.6 g / 60 * 1000) == Protein requirement 70 * 0.8 g/kg/24h
    print("In healthy 70 kg person: protein requirement {:.1f} g/24h, UUN {:.1f} g/24h, Urea {:.1f} g/24h".format(
        0.8 * 70,
        ((0.8 * 70 / 6.25) - 4),
        ((0.8 * 70 / 6.25) - 4) / 28 * 60))
    print(nitrogen_balance(177, 1000))

    Parameters
    ----------
    :param float c_urea: Urea concentration in 24 hours urine, mmol/L.
        If diuresis not given, total Urea mmol/24h
    :param float diuresis: Total diuresis, ml/24h
    :return float: Protein reqirement per g/24h
    """
    # UUN - Urine Urea Nitrogen
    # M_UUN = (14 + 1 * 2) * 2 + 12  + 16  # 60 g/mol (NH_2)_2 CO
    # M_N_UUN = 14 * 2  # 1 mol of BUN contains 28 grams of nitrogen
    uun = c_uurea / 1000 * diuresis / 1000 * 28  # g/24h

    # Concentrations for urea and urea nitroagen are the same,
    # but they have differemt molar mass
    info = "Protein requirement by 24h urine urea nitrogen\n==============================================\n"
    info += "cUUrea {:.1f} g/L ({:.0f} mg/dL), cUUN {:.0f} mg/dL\n".format(
        urea_mmoll2mgdl(c_uurea) * 0.01,  # g/L
        urea_mmoll2mgdl(c_uurea),
        uun_mmoll2mgdl(c_uurea))

    info += "UUN {:.1f} g/24h".format(uun)
    # if uun > 30:  # Kostuchenko, p 45
    #     uun += 2
    uun += 4  # Add skin and gastrointestinal tract losses
    protein_req = uun * 6.25  # 1 g nitrogen = 6.25 g protein

    info += "{}\n".format(" - protein requirement to maintain zero nitrogen balance {:.1f} g/24h".format(protein_req))
    # info += "{}\n".format("Nonprotein energy requirement {:.0f} kcal/24h (as 150 kcal/g of nitrogen)".format(uun * 150))
    if text:
        return info
    else:
        return protein_req
