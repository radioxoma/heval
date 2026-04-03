#!/usr/bin/env python

"""Heval web interface (static website).

PyCharm `RMB > Show Interpreter Paths`, Add pyscript stubs:
https://github.com/pyscript/pyscript-stubs/tree/main/src/pyscript-stubs
"""

from pyscript import Event, web, when, window  # ty: ignore[unresolved-import]

import heval
from heval import abg, common, human

human_model = human.HumanModel()
human_model_changed = Event()
event_change = window.Event.new("change")  # Dummy object to generate events

input_list = (
    ("body_use_ibw", f"Use {common.A.ibw}", True),
    ("verbose", "", False),
    ("body_height", "m", 1.77),
    ("body_weight", "kg", 75),
    ("body_age", "years", 40),
    ("body_temp", "°C", 36.6),
    ("blood_abg_pH", "", abg.norm_pH_mean),
    ("blood_abg_pCO2", "mmHg", abg.norm_pCO2mmHg_mean),
    ("blood_abg_pO2", "mmHg", abg.norm_pO2mmHg_mean),
    ("blood_abg_FiO2", "", abg.norm_FiO2),
    ("blood_abg_cK", "mmol/L", abg.norm_K_mean),
    ("blood_abg_cNa", "mmol/L", abg.norm_Na_mean),
    ("blood_abg_cCl", "mmol/L", abg.norm_Cl_mean),
    ("blood_abg_cGlu", "mmol/L", abg.norm_cGlu_mean),
    ("blood_bchem_albumin", "g/L", abg.norm_ctAlb_mean),
    ("blood_bchem_urea", "mmol/L", abg.norm_urea),
    ("blood_abg_cCrea", "μmol/L", abg.norm_cCrea),
    ("blood_bchem_ctBil", "μmol/L", abg.norm_ctBil),
    ("blood_bchem_ctBilIndir", "μmol/L", abg.norm_ctBilIndir),
    ("blood_cbc_hb", "g/L", abg.norm_hb_mean),
    ("blood_cbc_plt", "10⁹/L", abg.norm_plt_mean),
    ("blood_cbc_mcv", "fL", abg.norm_mcv_mean),
    ("blood_cbc_ret_fraq", "%", abg.norm_ret_fraq_mean),
    ("blood_coag_fib", "g/L", abg.norm_fib_mean),
    ("blood_coag_inr", "", abg.norm_inr_mean),
    ("blood_coag_ddimer", "ng/ml", abg.norm_ddimer_mean),
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
        human_model,
        event.target.id,
        common.HumanSex[web.page["body_sex"].value.upper()],
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
        if event.target.id in ("blood_abg_pCO2", "blood_abg_pO2"):
            setattr(human_model, event.target.id, float(event.target.value) * abg.kPa)
        else:
            setattr(human_model, event.target.id, float(event.target.value))
        human_model_changed.trigger(None)
    elif event.target.type == "checkbox":
        print(
            f"{event.target.type} changed by event: {event.target.id}={event.target.checked}"
        )
        setattr(human_model, event.target.id, event.target.checked)
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
    for prop, _unit, val in input_list:
        target = web.page[prop]
        if target.type == "number":
            target.value = val
        elif target.type == "checkbox":
            target.checked = val
        target.dispatchEvent(event_change)
    human_model_changed.trigger(None)


set_input_defaults()


@when(human_model_changed)
def eval_model():
    human_model.init()
    web.page["output_flags"].innerHTML = human_model.flags.render()
    web.page["output_body"].innerHTML = human_model.eval_body()
    web.page["output_labs"].innerHTML = human_model.eval_labs()


web.page["output_body"].innerText = "🟢 Ready"
web.page["output_labs"].innerText = "🟢 Ready"
web.page["output_help"].innerHTML = heval.__doc__
web.page["output_help"].append(web.p(heval.DISCLAIMER))
