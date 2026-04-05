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
    (human.HumanModel.body_height.attr, "m", 1.77),
    (human.HumanModel.body_weight.attr, "kg", 75),
    (human.HumanModel.body_age.attr, "years", 40),
    (human.HumanModel.body_temp.attr, "°C", 36.6),
    (
        human.HumanModel.blood_abg_pH.attr,
        common.LabTypeMapper.blood_abg_pH.ref.unit,
        common.LabTypeMapper.blood_abg_pH.ref.default,
    ),
    (
        human.HumanModel.blood_abg_pCO2.attr,
        common.LabTypeMapper.blood_abg_pCO2.ref.unit,
        common.LabTypeMapper.blood_abg_pCO2.ref.default,
    ),
    (
        human.HumanModel.blood_abg_pO2.attr,
        common.LabTypeMapper.blood_abg_pO2.ref.unit,
        common.LabTypeMapper.blood_abg_pO2.ref.default,
    ),
    (
        human.HumanModel.blood_abg_FiO2.attr,
        common.LabTypeMapper.blood_abg_FiO2.ref.unit,
        common.LabTypeMapper.blood_abg_FiO2.ref.default,
    ),
    (
        human.HumanModel.blood_abg_cK.attr,
        common.LabTypeMapper.blood_abg_cK.ref.unit,
        common.LabTypeMapper.blood_abg_cK.ref.default,
    ),
    (
        human.HumanModel.blood_abg_cNa.attr,
        common.LabTypeMapper.blood_abg_cNa.ref.unit,
        common.LabTypeMapper.blood_abg_cNa.ref.default,
    ),
    (
        human.HumanModel.blood_abg_cCl.attr,
        common.LabTypeMapper.blood_abg_cCl.ref.unit,
        common.LabTypeMapper.blood_abg_cCl.ref.default,
    ),
    (
        human.HumanModel.blood_abg_cGlu.attr,
        common.LabTypeMapper.blood_abg_cGlu.ref.unit,
        common.LabTypeMapper.blood_abg_cGlu.ref.default,
    ),
    (
        human.HumanModel.blood_bchem_albumin.attr,
        common.LabTypeMapper.blood_bchem_albumin.ref.unit,
        common.LabTypeMapper.blood_bchem_albumin.ref.default,
    ),
    (
        human.HumanModel.blood_bchem_urea.attr,
        common.LabTypeMapper.blood_bchem_urea.ref.unit,
        common.LabTypeMapper.blood_bchem_urea.ref.default,
    ),
    (
        human.HumanModel.blood_abg_cCrea.attr,
        common.LabTypeMapper.blood_abg_cCrea.ref.unit,
        common.LabTypeMapper.blood_abg_cCrea.ref.default,
    ),
    (
        human.HumanModel.blood_abg_ctBil.attr,
        common.LabTypeMapper.blood_abg_ctBil.ref.unit,
        common.LabTypeMapper.blood_abg_ctBil.ref.default,
    ),
    (
        human.HumanModel.blood_bchem_ctBilIndir.attr,
        common.LabTypeMapper.blood_bchem_ctBilIndir.ref.unit,
        common.LabTypeMapper.blood_bchem_ctBilIndir.ref.default,
    ),
    (
        human.HumanModel.blood_cbc_hb.attr,
        common.LabTypeMapper.blood_cbc_hb.ref.unit,
        common.LabTypeMapper.blood_cbc_hb.ref.default,
    ),
    (
        human.HumanModel.blood_cbc_plt.attr,
        common.LabTypeMapper.blood_cbc_plt.ref.unit,
        common.LabTypeMapper.blood_cbc_plt.ref.default,
    ),
    (
        human.HumanModel.blood_cbc_mcv.attr,
        common.LabTypeMapper.blood_cbc_mcv.ref.unit,
        common.LabTypeMapper.blood_cbc_mcv.ref.default,
    ),
    (
        human.HumanModel.blood_cbc_retFraq.attr,
        common.LabTypeMapper.blood_cbc_retFraq.ref.unit,
        common.LabTypeMapper.blood_cbc_retFraq.ref.default,
    ),
    (
        human.HumanModel.blood_coag_fib.attr,
        common.LabTypeMapper.blood_coag_fib.ref.unit,
        common.LabTypeMapper.blood_coag_fib.ref.default,
    ),
    (
        human.HumanModel.blood_coag_inr.attr,
        common.LabTypeMapper.blood_coag_inr.ref.unit,
        common.LabTypeMapper.blood_coag_inr.ref.default,
    ),
    (
        human.HumanModel.blood_coag_ddimer.attr,
        common.LabTypeMapper.blood_coag_ddimer.ref.unit,
        common.LabTypeMapper.blood_coag_ddimer.ref.default,
    ),
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
