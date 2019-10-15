#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Drug dosage calculator for humans.

Author: Eugene Dvoretsky

Propofol (индукция пока не срубит и поддержка по K мг каждые N минут)
Тиопентал
Кетамин
Фентанил
Dithylin (индукция и поддержка)
Tracrium (индукция и поддержка)

промедол
    Курек 423
налоксон
    детям болюсами по 0.4 мг [Курек 435]
Тахибен - по эффекту
Нитраты - по эффекту
Нимотоп - по эффекту

Адреналин в/в
    Курек 10 мкг/кг с 380.
Mesaton
Допамин
    Курек 419
Маннитол
Гепарин

Питание
    Глюкоза (скорость, количество инсулина у детей и взрослых)
    Инсулин для кетоацидотической комы
    Калийснижающий болюс [Курек 2013 131]

Электролиты? K?
Бикарбонат
    * Курек 47
    * Маневич, Плохой 118 (на BE, вес)

Анальгин для детей?
"""

class Dithylin(object):
    """According to RUE Belmedpreparaty instruction.
    """
    def __init__(self, parent=None):
        self._parent = parent
        self.name = "Dithylin"
        self.concentration = 20  # mg/ml
        # self.volume = 5  # ml
        # На идеальный вес
        # Частота введения поддерживающего болюса

    def __str__(self):
        # print("%s for intubation %.0f mg (5-10 mins)." % (
        #    self.name, 1.5 * self._parent.weight))
        return (
            "%s IBW intubation 5-10 mins relaxation: %.0f mg adult, %.0f mg child." % (
                self.name, 1.5 * self._parent.weight_ideal, 1 * self._parent.weight_ideal) +
            " Max maintenance dose %.0f mg every 5 mins (all ages)." % (
                self._parent.weight_ideal * 1))


class Propofol(object):
    """Propofol Fresenius Kabi 1 %.
    """
    def __init__(self, parent=None):
        self._parent = parent
        self.name = "Propofol"
        self.concentration = 10  # mg/ml
        self.maintenance_dosage = 10  # mg/kg/h
        # Индукция в течение минуты
        # self.volume = 20  # ml
        # На вес
        # Частота введения поддерживающего болюса

    def delay(self, bolus=50):
        """Delay in minutes between boluses. Tupical bolus is 25-50 mg.
        """
        per_hour = self.maintenance_dosage * self._parent.weight
        return 60 / (per_hour / bolus)

    def __str__(self):
        return (
            "%s induction 20-40 mg every 10 secs, up to %.0f mg (2.5 mg/kg for adult & children)." % (self.name, 2.5 * self._parent.weight) +
            " Maintenance 50 mg every %.0f min (%.0f mg/kg/h)." % (self.delay(), self.maintenance_dosage))


class Fentanyl(object):
    """According to RUE Belmedpreparaty instruction.
    """
    def __init__(self, parent=None):
        self._parent = parent
        self.name = "Fentanyl"
        self.concentration = 0.05  # mg/ml
        self.maintenance_dosage = 0.0001 * 60  # mg/kg/h
        # 2 ml every 20 mins during one hour == 0.3 mg/hour
        # self.volume =  # ml

    def __str__(self):
        ml_h = self.maintenance_dosage * self._parent.weight / self.concentration
        delay = 2 / (ml_h / 60)  # Delay for 3 ml bolus
        return (
            "%s 2 ml (0.1 mg) every %.0f mins (%.1f ml/h). Children?" % (self.name, delay, ml_h) +
            " Typically in adults 2 ml every 20 mins or 6 ml/h.")


class Tracrium(object):
    """According to GlaxoSmithKline.

    Метаболизируется неспецефическими эстеразами плазмы. Не кумулирует.
    Скорость снятия блока от метаболизма печени и почек не зависит.
    """
    def __init__(self, parent=None):
        self._parent = parent
        self.name = "Tracrium"
        # self.concentration =   # mg/ml
        # self.maintenance_dosage =   # mg/kg/h
        # self.volume =  # ml
        # 90 seconds before intubation
        # -30 % for isoflurane

    def __str__(self):
        return (
            "%s load %.0f-%.0f mg (%.0f-%.0f mg -30%% for isoflurane) for 15-35 mins of full block + 35 extra mins for recovery." % (
                self.name, 0.3 * self._parent.weight, 0.6 * self._parent.weight,
                percent_corr(0.3 * self._parent.weight, -30),
                percent_corr(0.6 * self._parent.weight, -30)) +
            " %.0f-%.0f mg (%.0f-%.0f mg -30%% for isoflurane) to prolong full block." % (
                0.1 * self._parent.weight, 0.2 * self._parent.weight,
                percent_corr(0.1 * self._parent.weight, -30),
                percent_corr(0.2 * self._parent.weight, -30)) +
            " Same dosage for all ages.")


class Arduan(object):
    """According to GlaxoSmithKline.
    """
    def __init__(self, parent=None):
        self._parent = parent
        self.name = "Arduan"

    def __str__(self):
        self.load_dose = 0.041  # mg/kg
        # info = 
        info = "Arduan load dose {:.1f} mg".format(self._parent.weight * self.load_dose)
        return info


class Esmeron(object):
    """According to http://www.rceth.by/NDfiles/instr/8675_08_13_i.pdf.
    """
    def __init__(self, parent=None):
        self._parent = parent
        self.name = "Esmeron"
        self.concentration = 10  # mg/ml
        # self.maintenance_dosage =   # mg/kg/h
        self.volume = 5  # ml
        # 60 seconds before intubation

    def __str__(self):
        return (
            "%s intubation %.0f mg (30-40 mins before <25%% recovery). NMT maintenance:\n" % (
                self.name, 0.6 * self._parent.weight) +
            " * bolus: <1h %.0f mg; >1h %.0f-%.0f mg [2-3 TOF, <25%%]\n" % (
                self._parent.weight * 0.15,
                self._parent.weight * 0.075, self._parent.weight * 0.1,) +
            " * pump: TIVA %.0f-%.0f mg/h; GA %.0f-%.0f mg/h [1-2 TOF, <10%%]\n" % (
                self._parent.weight * 0.3, self._parent.weight * 0.6,
                self._parent.weight * 0.3, self._parent.weight * 0.4) +
            "   Same dosage for all ages.")


def percent_corr(i, corr):
    """Shift value by given percent.

    :param float i: value for transformation
    :param float corr: percent to shift
    :return:
        Shifted value
    :rtype: float
    """
    return i + (i / 100 * corr)
