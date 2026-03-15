#!/usr/bin/env python

"""
Heval web interface (static website).

PyCharm `RMB > Show Interpreter Paths`, Add pyscript stubs:
https://github.com/pyscript/pyscript-stubs/tree/main/src/pyscript-stubs
"""

from pyscript import Event, web, when, window
import heval.abg
import heval.common
import heval.human


human = heval.human.HumanModel()
human_model_changed = Event()
event_change = window.Event.new("change")  # Dummy object to generate events

input_list = (
    ("body_use_ibw", """Use <abbr title="Ideal body weight">IBW</abbr>""", True),
    ("body_height", "m", 1.77),
    ("body_weight", "kg", 75),
    ("body_age", "years", 40),
    ("body_temp", "°C", 36.6),
    ("blood_abg_pH", "", 7.4),
    ("blood_abg_pCO2", "mmHg", 40),
    ("blood_abg_cK", "mmol/L", 4),
    ("blood_abg_cNa", "mmol/L", 140),
    ("blood_abg_cCl", "mmol/L", 105),
    ("blood_abg_cGlu", "mmol/L", 5.5),
    ("blood_abg_ctAlb", "g/dL", 4.4),
    ("blood_abg_cCrea", "μmol/L", 75),
    ("blood_bchem_ctBilIndirect", "μmol/L", 10),
    ("blood_cbc_hb", "g/L", 140),
    ("blood_cbc_plt", "10⁹/L", 300),
    ("blood_cbc_mcv", "fL", 90),
    ("blood_cbc_ret", "%", 1),
    ("blood_coag_fib", "g/L", 3),
    ("blood_coag_inr", "", 1),
    ("blood_coag_dDimer", "ng/ml", 300),
)


def gen_ui():
    control: web.Element = web.page["#human_model_form"]
    for prop, unit, val in input_list:
        div = web.div()
        if isinstance(val, bool):  # Subclass of int, so check first
            div.append(web.input_(type="checkbox", id=prop, checked=val))
        elif isinstance(val, int | float):
            # Browser uses 'min', 'max' to calculate input size
            div.append(
                web.input_(type="number", id=prop, min=0, max=999, step=0.1, value=val)
            )
        div.append(" ")
        div.append(
            web.label(f"{prop.split('_')[-1]}{f', {unit}' if unit else ''}", for_=prop)
        )
        control.append(div)


gen_ui()


@when("change", "select#body_sex")
def select_changed(event):
    print(f"select_changed {event.target.id} by event")
    setattr(
        human,
        event.target.id,
        heval.common.HumanSex[web.page["body_sex"].value.upper()],
    )
    human_model_changed.trigger(None)


@when("change", "input")
def input_changed(event):
    """Auto map spinboxes to model properties."""
    # if event.target.tagName == "INPUT" and event.target.type == "number":
    if event.target.type == "number":
        print(
            f"{event.target.type} changed by event: {event.target.id}={event.target.value}"
        )
        if event.target.id == "blood_abg_pCO2":
            setattr(human, event.target.id, float(event.target.value) * heval.abg.kPa)
        else:
            setattr(human, event.target.id, float(event.target.value))
        human_model_changed.trigger(None)
    elif event.target.type == "checkbox":
        print(
            f"{event.target.type} changed by event: {event.target.id}={event.target.checked}"
        )
        setattr(human, event.target.id, event.target.checked)
        human_model_changed.trigger(None)


@when("wheel", "input[type=number]")
def spinbox_scroll(event):
    """Scroll spinboxes with mouse wheel."""
    event.preventDefault()
    if event.deltaY < 0:
        event.target.stepUp()
    else:
        event.target.stepDown()
    event.target.dispatchEvent(event_change)


@when("click", "#body_reset")
def set_input_defaults():
    print("Reset form")
    # Reset value selector
    web.page["body_sex"].value = web.page["body_sex option:first-of-type"].value
    web.page["body_sex"].dispatchEvent(event_change)
    # Reset spinboxes
    for prop, unit, val in input_list:
        web.page[prop].value = val
    for k in web.page.find("input[type=number]"):
        k.dispatchEvent(event_change)
    human_model_changed.trigger(None)


set_input_defaults()


@when(human_model_changed)
def eval_model():
    human.init()
    web.page["output_flags"].innerHTML = human.flags.render()
    web.page["output_body"].innerHTML = human.eval_body()
    web.page["output_labs"].innerHTML = human.eval_labs()


web.page["output_body"].innerText = "🟢 Ready"
web.page["output_labs"].innerText = "🟢 Ready"
