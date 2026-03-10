#!/usr/bin/env python

"""
Heval web interface (static website).

PyCharm `RMB > Show Interpreter Paths`, Add pyscript stubs:
https://github.com/pyscript/pyscript-stubs/tree/main/src/pyscript-stubs
"""

from pyscript import Event, web, when, window
import heval.common
import heval.human


human = heval.human.HumanModel()
human_model_changed = Event()
event_change = window.Event.new("change")  # Dummy object to generate events


@when("change", "select#body_sex")
def select_changed(event):
    print(f"select_changed {event.target.id} by event")
    setattr(
        human,
        event.target.id,
        heval.common.HumanSex[web.page["body_sex"].value.upper()],
    )
    human_model_changed.trigger(None)


@when("change", "input[type=number]")
def spinbox_changed(event):
    # if event.target.tagName == "INPUT" and event.target.type == "number":
    print(f"spinbox_changed by event: {event.target.id}={event.target.value}")
    setattr(human, event.target.id, float(event.target.value))
    human_model_changed.trigger(None)


@when("click", "#body_reset")
def set_input_defaults():
    print("Reset form")
    # Reset value selector
    web.page["body_sex"].value = web.page["body_sex option:first-of-type"].value
    web.page["body_sex"].dispatchEvent(event_change)
    # Reset spinboxes
    web.page["body_height"].value = 1.77
    for k in web.page.find("input[type=number]"):
        k.dispatchEvent(event_change)
    human_model_changed.trigger(None)


set_input_defaults()


@when(human_model_changed)
def eval_model():
    human.init()
    web.page["output_body"].innerHTML = human.eval_body()
    web.page["output_labs"].innerHTML = human.eval_labs()


web.page["output_body"].innerText = "Ready"
