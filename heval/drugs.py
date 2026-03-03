"""Drug dosage calculator.

Author: Eugene Dvoretsky
"""

from __future__ import annotations

from heval import human, common

press_nor16 = {
    "name": "Nor-16",
    "weight": 16,  # mg
    "volume": 50,  # ml
    "speed_start": 0.1,  # mcg/kg/min
    "speed_max": 3,  # mcg/kg/min. Or 0.1 to 1 mcg/kg/min? https://litfl.com/noradrenaline/
}

press_nor32 = {
    "name": "Nor-32",
    "weight": 32,  # mg
    "volume": 50,  # ml
    "speed_start": 0.1,  # mcg/kg/min
    "speed_max": 3,  # mcg/kg/min. Or 0.1 to 1 mcg/kg/min? https://litfl.com/noradrenaline/
}

press_epi = {
    "name": "Epi-10",
    "weight": 10,  # mg
    "volume": 50,  # ml
    "speed_start": 0.1,  # mcg/kg/min 0.15?
    "speed_max": 3,
}

press_phenylephrine = {
    "name": "Phen50",
    "weight": 50,  # mg
    "volume": 50,  # ml
    "speed_start": 0.1,  # mcg/kg/min
    "speed_max": 3,  # mcg/kg/min
}

press_dopamine = {
    "name": "Dop200",
    "weight": 200,  # mg
    "volume": 50,  # ml
    "speed_start": 5,  # mcg/kg/min
    "speed_max": 20,  # mcg/kg/min
}

press_dobutamine = {
    "name": "Dob250",
    "weight": 250,  # mg
    "volume": 50,  # ml
    "speed_start": 2.5,  # mcg/kg/min
    "speed_max": 25,  # mcg/kg/min
}


class HumanDrugsModel:
    """Human drugs list."""

    def __init__(self, human_body: human.HumanModel):
        super().__init__()
        self.human_body = human_body

        # English names
        self.drug_list = [
            Fentanyl(self.human_body),
            Propofol(self.human_body),
            Suxamethonium(self.human_body),
            Atracurium(self.human_body),
            Pipecuronium(self.human_body),
            Rocuronium(self.human_body),
        ]

    def describe_anesthesiology(self):
        return "\n".join(["* " + str(d) for d in self.drug_list])

    def describe_pressors(self):
        def describe_pressor(pressor, weight):
            """Generate pressor cheatsheet.

            :param tuple pressor: Pressor typle
            :param float weight: Human weight, kg.
            """
            dilution = pressor["weight"] / pressor["volume"]
            out_str = "{} ({:3.0f} mg / {:.0f} ml, {:.2f} mg/ml) rate {:.2f}-{:>5.2f} mсg/kg/min".format(
                pressor["name"],
                pressor["weight"],
                pressor["volume"],
                dilution,
                pressor["speed_start"],
                pressor["speed_max"],
            )

            speed_start_mgh = pressor["speed_start"] / 1000 * weight * 60
            speed_start_mlh = speed_start_mgh / dilution
            speed_max_mgh = pressor["speed_max"] / 1000 * weight * 60
            speed_max_mlh = speed_max_mgh / dilution
            out_str += f" ({speed_start_mgh:>4.1f}-{speed_max_mgh:>5.1f} mg/h, {speed_start_mlh:.1f}-{speed_max_mlh:>4.1f} ml/h)"
            return out_str

        info = list()
        for p in (
            press_nor16,
            press_nor32,
            press_epi,
            press_phenylephrine,
            press_dopamine,
            press_dobutamine,
        ):
            info.append(describe_pressor(p, self.human_body.body_weight))
        return "\n".join(info) + "\n"


class Suxamethonium:
    """According to RUE Belmedpreparaty instruction.

    Dithylin, succinylcholine.
    """

    def __init__(self, human_body: human.HumanModel):
        self.human_body = human_body
        self.name = "Suxamethonium"
        self.concentration = 20  # mg/ml
        # self.volume = 5  # ml
        # For IBW

    def __str__(self):
        # print("%s for intubation %.0f mg (5-10 mins).".format(
        #    self.name, 1.5 * self.human_body.weight))
        info = "{} IBW intubation 5-10 mins relaxation: {:.0f} mg adult, {:.0f} mg child.".format(
            self.name,
            1.5 * self.human_body.body_weight_ideal,
            self.human_body.body_weight_ideal,
        )
        info += f" Max maintenance dose {self.human_body.body_weight_ideal:.0f} mg every 5 mins (all ages)."
        return info


class Propofol:
    """Propofol Fresenius Kabi 1 %."""

    def __init__(self, human_body: human.HumanModel):
        self.human_body = human_body
        self.name = "Propofol"
        self.concentration = 10  # mg/ml
        self.maintenance_dosage = 10  # mg/kg/h
        # Induction in one minute
        # self.volume = 20  # ml
        # For RBW

    def delay(self, bolus=50):
        """Delay in minutes between boluses. Typical bolus is 25-50 mg."""
        per_hour = self.maintenance_dosage * self.human_body.body_weight
        return 60 / (per_hour / bolus)

    def __str__(self):
        info = f"{self.name} induction 20-40 mg every 10 secs, up to {2.5 * self.human_body.body_weight:.0f} mg (2.5 mg/kg for adult & children)."
        info += f" Maintenance 50 mg every {self.delay():.0f} min ({self.maintenance_dosage:.0f} mg/kg/h)."
        return info


class Fentanyl:
    """According to RUE Belmedpreparaty instruction."""

    def __init__(self, human_body: human.HumanModel):
        self.human_body = human_body
        self.name = "Fentanyl"
        self.concentration = 0.05  # mg/ml
        self.maintenance_dosage = 0.0001 * 60  # mg/kg/h
        # 2 ml every 20 mins during one hour == 0.3 mg/hour
        # self.volume =  # ml

    def __str__(self):
        ml_h = (
            self.maintenance_dosage * self.human_body.body_weight / self.concentration
        )
        delay = 2 / (ml_h / 60)  # Delay for 3 ml bolus
        info = f"{self.name} 2 ml (0.1 mg) every {delay:.0f} mins ({ml_h:.1f} ml/h). Children?"
        info += " Typically in adults 2 ml every 20 mins or 6 ml/h."
        return info


class Atracurium:
    """Atracurium besilate (tracrium).

    According to GlaxoSmithKline.

    Eliminated by nonspecific plasma esterases.
    No cumulation, block recovery not dependent from kidney/liver metabolism.
    """

    def __init__(self, human_body: human.HumanModel):
        self.human_body = human_body
        self.name = "Atracurium"
        # self.concentration =   # mg/ml
        # self.maintenance_dosage =   # mg/kg/h
        # self.volume =  # ml
        # 90 seconds before intubation
        # -30 % for isoflurane

    def __str__(self):
        info = "{} load {:.0f}-{:.0f} mg ({:.0f}-{:.0f} mg -30% for isoflurane) for 15-35 mins of full block + 35 extra mins for recovery.".format(
            self.name,
            0.3 * self.human_body.body_weight,
            0.6 * self.human_body.body_weight,
            percent_corr(0.3 * self.human_body.body_weight, -30),
            percent_corr(0.6 * self.human_body.body_weight, -30),
        )
        info += " {:.0f}-{:.0f} mg ({:.0f}-{:.0f} mg -30% for isoflurane) to prolong full block.".format(
            0.1 * self.human_body.body_weight,
            0.2 * self.human_body.body_weight,
            percent_corr(0.1 * self.human_body.body_weight, -30),
            percent_corr(0.2 * self.human_body.body_weight, -30),
        )
        info += " Same dosage for all ages."
        return info


class Pipecuronium:
    """https://www.rlsnet.ru/tn_index_id_358.htm."""

    def __init__(self, human_body: human.HumanModel):
        self.human_body = human_body
        self.name = "Pipecuronium"

    def __str__(self):
        info = ""
        if self.human_body.body_sex in (common.HumanSex.MALE, common.HumanSex.FEMALE):
            info += "{} adult mono intubation {:.2f}-{:.2f} mg for 60-90 min; load after Sux {:.2f} mg for 30-60 min. Maintenance {:.2f}-{:.2f} mg every 30-60 min.".format(
                self.name,
                0.06 * self.human_body.body_weight,
                0.08 * self.human_body.body_weight,
                0.05 * self.human_body.body_weight,
                0.01 * self.human_body.body_weight,
                0.02 * self.human_body.body_weight,
            )
        elif self.human_body.body_sex == common.HumanSex.CHILD:
            info += "{} child 3-12 mos {:.2f} mg (10-44 min), 1-14 yo {:.2f}-{:.2f} mg (18-52 min).".format(
                self.name,
                0.04 * self.human_body.body_weight,
                0.05 * self.human_body.body_weight,
                0.06 * self.human_body.body_weight,
            )
        return info


class Rocuronium:
    """According to http://www.rceth.by/NDfiles/instr/8675_08_13_i.pdf."""

    def __init__(self, human_body: human.HumanModel):
        self.human_body = human_body
        self.name = "Rocuronium"
        self.concentration = 10  # mg/ml
        # self.maintenance_dosage =   # mg/kg/h
        self.volume = 5  # ml
        # 60 seconds before intubation

    def __str__(self):
        info = "{} intubation {:.0f} mg (30-40 mins before <25% recovery). NMT maintenance:\n".format(
            self.name, 0.6 * self.human_body.body_weight
        )
        info += (
            " * bolus: <1h {:.0f} mg; >1h {:.0f}-{:.0f} mg [2-3 TOF, <25%]\n".format(
                self.human_body.body_weight * 0.15,
                self.human_body.body_weight * 0.075,
                self.human_body.body_weight * 0.1,
            )
        )
        info += " * pump: TIVA {:.0f}-{:.0f} mg/h; GA {:.0f}-{:.0f} mg/h [1-2 TOF, <10%]\n".format(
            self.human_body.body_weight * 0.3,
            self.human_body.body_weight * 0.6,
            self.human_body.body_weight * 0.3,
            self.human_body.body_weight * 0.4,
        )
        info += "   Same dosage for all ages."
        return info


def percent_corr(i, corr):
    """Shift value by given percent.

    :param float i: value for transformation
    :param float corr: percent to shift
    :return:
        Shifted value
    :rtype: float
    """
    return i + (i / 100 * corr)
