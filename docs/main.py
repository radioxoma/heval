#!/usr/bin/env python

"""
https://radioxoma.github.io/sandbox
"""

from pyscript import web, when, Event
import heval.common
import heval.human


human = heval.human.HumanModel()
human_model_changed = Event()


@when("change", "#sel_body_sex")
def set_model_sex():
    human.body_sex = heval.common.HumanSex[web.page["sel_body_sex"].value.upper()]
    human_model_changed.trigger(None)


@when("change", "#sbx_body_height")
def set_model_height():
    human.body_height = float(web.page["sbx_body_height"].value)
    human_model_changed.trigger(None)


@when("click", "#btn_body_reset")
def set_input_defaults():
    web.page["sel_body_sex"].value = heval.common.HumanSex.MALE.name.lower()
    set_model_sex()
    web.page["sbx_body_height"].value = 1.86
    set_model_height()


set_input_defaults()


@when("click", "#btn_body_set")
@when(human_model_changed)
def eval_model():
    human.init()
    web.page["output"].innerHTML = human.eval_body()


web.page["output"].innerText = "Ready"
