## Heval: the human evaluator. Calculate what your human crave!

> Heval is available as a web app https://radioxoma.github.io/heval/

Heval is a medical calculator for [intensive care unit](https://en.wikipedia.org/wiki/Intensive_care_medicine). Main features:

* Minimal user input — unknown values estimated automatically whenever possible (e.g. weight by height)
* Only measurable parameters — no need to speak with a human of interest
* No "Calculate" button — evaluated data changes immediately with your input
* Every calculation referenced and explained in source code, so everyone can reproduce it
* Python package can be integrated into medical information system
* It's got electrolytes

## Usage

From just *sex* and *height* it evaluates [IBW](https://en.wikipedia.org/wiki/Human_body_weight#Ideal_body_weight), [BSA](https://en.wikipedia.org/wiki/Body_surface_area), [fluid](https://en.wikipedia.org/wiki/Fluid_replacement), nutrition and respiratory demands, urinary output, dialysis dose and more. [ABG interpreter](https://en.wikipedia.org/wiki/Acid%E2%80%93base_homeostasis) reveals hidden processes, suggests urgent correction measures and infusion therapy. There are overwhelming amount of spinboxes, but filling them all is not required.

### Human body

> Tip: Get yourself a [ruler](https://en.wikipedia.org/wiki/Tape_measure), not all humans are able to talk.

**Just enter *sex* and *height***. That's it! Age, even for children, is not mandatory because it has poor prediction power. Incorporated [Broselow-Luten color zones](https://en.wikipedia.org/wiki/Broselow_tape) and [weight-by-height](https://en.wikipedia.org/wiki/Human_body_weight#Ideal_body_weight) formulas at your service.

### Laboratory

> Tip: You can test Heval's ability to interpret ABG with [case studies](https://web.archive.org/web/20170818090331/http://fitsweb.uchc.edu/student/selectives/TimurGraham/Case_1.html). Some books provide case studies with invalid data (see below).

Requires some bloodwork to be done. Take [arterial blood gas](https://en.wikipedia.org/wiki/Arterial_blood_gas_test) sample whenever possible.
1. Enter pH and pCO<sub>2</sub> for simplest acid-base status assessment
2. Enter electrolytes to reveal hidden processes ([anion gap](https://en.wikipedia.org/wiki/Anion_gap), [delta-gap](https://en.wikipedia.org/wiki/Delta_ratio)) and general electrolyte disturbances
    * Algorithm able to detect mixed acid-base disorders, vomiting etc
    * Hi-low electrolytes correction strategies
    * Tips for emergency cases
    * Sex and weight used only for dosage calculations, not for ABG diagnostics itself
3. Enter optional data for complex cases
    * Albumin, if there is metabolic acidosis - for anion gap correction
    * [DKE](https://en.wikipedia.org/wiki/Diabetic_ketoacidosis)/[HHS](https://en.wikipedia.org/wiki/Hyperosmolar_hyperglycemic_state)
    * [Hyperosmolar pseudohyponatremia](https://en.wikipedia.org/wiki/Hyponatremia#False_hyponatremia) estimation

## Validation

Please use a real patient's data: all electrolytes interconnected by electroneutrality law, Henderson-Hasselbalch equation. So even if you enter values in reference range, calculations can produce a broken result, especially anion gap (e.g. `149 - (101 + 24) = 24` which is >16 mEq/L!).
**Some imagined case studies from books aren't designed well and will fail too.**

## Disclaimer
Heval is an experimental software. Whatever it calculates, it's *your* decisions will affect your human's live longevity. I have no responsibility for your collateral damage.

> Key: Garbage -> Limited -> Medium -> Good -> Excellent

| Function                                                         | Status    | Comment                                                                                                                                                                                                                                                                                                                                                                                                 |
|------------------------------------------------------------------|-----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Human body: anthropometry                                        | **Good**  | Straightforward implementation. Broselow for children.                                                                                                                                                                                                                                                                                                                                                  |
| Human body: respiration                                          | **Good**  | Use as start ventilator settings for adults and children                                                                                                                                                                                                                                                                                                                                                |
| Human body: energy & electrolytes                                | Limited   | Generic approximation for healthy human. Real demands are unpredictably dependent on body fat/muscle compound, fever, sepsis, burns etc. [REE](https://en.wikipedia.org/wiki/Resting_metabolic_rate) formulas has been taken from original papers, so your lovely Harris-Benedict equation don't have dubious correction coefficients, leading to irreproducible result.                                |
| Human body: fluid demand                                         | Limited   | Generic approximation for healthy human. Pathologic [fluid loss](https://en.wikipedia.org/wiki/Volume_contraction) must be taken into account                                                                                                                                                                                                                                                           |
| Human body: urinary output                                       | **Good**  | Simple ml/kg/h approach for adults and children, though eGFR estimation may be necessary                                                                                                                                                                                                                                                                                                                |
| Nutrition                                                        | Limited   | Enteral and parenteral. Based on [ESPEN](https://www.espen.org/) 25-30 kcal/kg recommendation and nitrogen balance. Use [indirect calorimetry](https://en.wikipedia.org/wiki/Indirect_calorimetry) if you need a real tool.                                                                                                                                                                             |
| ABG: pH correction                                               | Limited   | Recent papers deny benefit from [iv bicarbonate](https://en.wikipedia.org/wiki/Intravenous_sodium_bicarbonate) if BE <-15 mEq/L. Mortality decrease is possible in AKI patients. No validated formula found.                                                                                                                                                                                            |
| ABG: anion gap                                                   | **Good**  | Excellent prediction, but please **USE REAL DATA**                                                                                                                                                                                                                                                                                                                                                      |
| ABG: Electrolytes replacement                                    | Limited   | Exact depletion/excess estimation is impossible due to multiple body compartments. High/low warnings still usable though. K<sup>+</sup> — no reliable model, use daily requirement and standard iv replacement rate for hypokalemia. Na<sup>+</sup> — Adrogue and classic one compartment model. Cl<sup>-</sup> — no model at all. Multiple calculation methods in books, few applicable in real world. |
| [eGFR](https://en.wikipedia.org/wiki/Glomerular_filtration_rate) | **Good**  | Straightforward implementation. Cockcroft-Gault, CKD-EPI 2021 for adults, Schwartz revised 2009 for children.                                                                                                                                                                                                                                                                                           |


## Installation [![semver](https://img.shields.io/github/v/release/radioxoma/heval)](https://github.com/radioxoma/heval/releases/latest/) [![semver](https://img.shields.io/github/release-date/radioxoma/heval)](https://github.com/radioxoma/heval/releases/latest/)

Since 2026 development switched towards web app. Desktop app is obsolete.

<details>

### Windows

Download *exe* file from the [releases page](https://github.com/radioxoma/heval/releases/latest/). Just run it — installation is not required.

* [v0.1.5](https://github.com/radioxoma/heval/releases/tag/v0.1.5) is last compatible with Windows XP SP3 x86 and python 3.4.3.
* Latest version can be installed with `pip install https://github.com/radioxoma/heval/archive/main.zip`.

### Mac OS X

Download *dmg* file (Apple Disk Image with 64-bit *Heval.app*) from the [releases page](https://github.com/radioxoma/heval/releases/latest/). Unpack *Heval.app* from *dmg*. Application unsigned, so warning "*macOS cannot verify the developer of "Heval"*" will appear if you try to run it. You can overcome this in one of two ways:

* Press <kbd>Control</kbd> and simultaneously click on unpacked *Heval.app*. Click *Open* in appeared context menu. Click *Open* in appeared window
* Run in terminal `xattr -dr com.apple.quarantine "Heval.app"`. Now "Heval" can be run by click


### Linux

> Tip: Archlinux [AUR](https://wiki.archlinux.org/index.php/Arch_User_Repository) package [`heval-git`](https://aur.archlinux.org/packages/heval-git/) available.

Heval is written in python and uses tkinter for GUI.

    $ sudo apt install git python3-tk  # Debian / Ubuntu
    $ sudo pacman -S git python tk  # Archlinux

    $ git clone https://github.com/radioxoma/heval.git
    $ cd heval
    $ pip install .
    $ python -m heval  # Run code directly

Instead of executing `python -m heval` it's possible to double-click 'heval.desktop'.
</details>

## Desktop app screenshots

![2023-04-02_17-39-38](https://user-images.githubusercontent.com/4701641/229360354-9b64cf87-eee7-415f-b536-650ed7f0294b.png)
![2023-04-02_17-46-04](https://user-images.githubusercontent.com/4701641/229360360-f9b12a49-7ffa-4bd9-b309-e4b94f00e57c.png)
