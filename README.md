## Heval: the Human EVALuator

> Calculate what your human crave online https://radioxoma.github.io/heval/

Heval is an advanced medical calculator and decision support system for [intensive care units](https://en.wikipedia.org/wiki/Intensive_care_medicine).
It is available as a web app, a desktop app, and a Python package for integration with existing medical information systems.

Heval aims to achieve an ambitious goal: unifying multiple calculations within a single robust human model.

When the model properties are populated with anthropometric and laboratory data, it derives additional human features (calculated properties) and executes a comprehensive rule set of validation and diagnostic checks.
Found issues are represented as broad _text report_ and set of _flags_.
The _flag_ is a short distinct warning with a reason, description, color coded severity and action required.

Main features:

* Minimal user input — unknown values estimated automatically whenever possible (e.g. [weight by height](https://en.wikipedia.org/wiki/Human_body_weight#Ideal_body_weight))
* Only measurable parameters — no need to speak with a human of interest, no opinion controversy
* No "Calculate" button — evaluated data changes immediately with your input
* Every calculation referenced and explained in source code, so everyone can reproduce it
* Python package can be integrated into medical information system
* It's got electrolytes

## Usage

There are overwhelming amount of model properties, but filling them all is not required. Only _sex_ and _height_ are mandatory.

### Body

> Tip: Get yourself a [ruler](https://en.wikipedia.org/wiki/Tape_measure) or [Broselow tape](https://en.wikipedia.org/wiki/Broselow_tape), not all humans are able to talk.

**Just enter *sex* and *height***. That's it! Ideal body weight is used by default - uncheck <dfn>Use IBW</dfn> and enter real body weight if known. Age, even for children, is not mandatory because it has poor prediction power.

* Anthropometry. [IBW](https://en.wikipedia.org/wiki/Human_body_weight#Ideal_body_weight), [BMI](https://en.wikipedia.org/wiki/Body_mass_index), [BSA](https://en.wikipedia.org/wiki/Body_surface_area), blood volume. Broselow-Luten color zones for children.
* Respiratory. Use as start ventilator settings for adults and children.
* Nutrition
  * Generic approximation for healthy human. Real demands are unpredictably dependent on body fat/muscle compound, fever, sepsis, burns etc. [REE](https://en.wikipedia.org/wiki/Resting_metabolic_rate) formulas has been taken from original papers, so your lovely Harris-Benedict equation don't have dubious correction coefficients, leading to irreproducible result.
  * Based on [ESPEN](https://www.espen.org/) 25-30 kcal/kg recommendation and nitrogen balance. Use [indirect calorimetry](https://en.wikipedia.org/wiki/Indirect_calorimetry) if you need a real tool.
* [Fluid](https://en.wikipedia.org/wiki/Fluid_replacement) demands. Generic approximation for healthy human. Pathologic [fluid loss](https://en.wikipedia.org/wiki/Volume_contraction) must be taken into account
* Urinary output, dialysis dose. Simple ml/kg/h approach for adults and children, though eGFR estimation may be necessary

### Laboratory

#### Arterial blood gas (ABG) test

> Tip: You can test Heval's ability to interpret ABG with [case studies](https://web.archive.org/web/20170818090331/http://fitsweb.uchc.edu/student/selectives/TimurGraham/Case_1.html). Some books provide case studies with invalid data (see below).

[ABG test](https://en.wikipedia.org/wiki/Arterial_blood_gas_test) reveals main and mixed acidosis-alkalosis, suggests urgent correction measures and infusion therapy. Prefer arterial blood sample, but venous will work too.

1. Enter **pH** and **pCO<sub>2</sub>** for simplest acid-base status assessment.
   * pH correction. Papers deny benefit from [iv bicarbonate](https://en.wikipedia.org/wiki/Intravenous_sodium_bicarbonate) if BE &gt;-15 mEq/L. Mortality decrease is possible in AKI patients. No validated formula found.
2. Enter Na<sup>+</sup>, **Cl<sup>-</sup>**, **K<sup>+</sup>** to reveal hidden processes (via [anion gap](https://en.wikipedia.org/wiki/Anion_gap), [delta-gap](https://en.wikipedia.org/wiki/Delta_ratio)) and general electrolyte disturbances
   * Algorithm is able to detect mixed acid-base disorders, vomiting etc
   * Excellent prediction, but please USE REAL DATA
   * Hi-low electrolytes correction strategies (sex and weight used only for dosage calculations, not for ABG diagnostics itself). Exact depletion/excess estimation is impossible due to multiple body compartments. High/low warnings still usable though.
     * K<sup>+</sup> — no reliable model, use daily requirement and standard iv replacement rate for hypokalemia.
     * Na<sup>+</sup> — Adrogue and classic one compartment model.
     * Cl<sup>-</sup> — no model at all. Multiple calculation methods in books, few applicable in real world.
   * Tips for emergency cases
3. Enter **albumin** and **glucose** for complex cases
   * If there are metabolic acidosis and patient is starved, enter albumin for anion gap correction
   * [DKE](https://en.wikipedia.org/wiki/Diabetic_ketoacidosis)/[HHS](https://en.wikipedia.org/wiki/Hyperosmolar_hyperglycemic_state) detection
   * [Hyperosmolar pseudohyponatremia](https://en.wikipedia.org/wiki/Hyponatremia#False_hyponatremia) estimation
   * Na and glucose used for serum osmolarity estimation

#### Transfusions

> Warning: Blood management is a serious deal and anyone involved must be trained and certified.

Enter Hb, PLT, Fib, INR to estimate overall recommendations and transfusion dose for a stable patient without continuous bleeding. Heval will point at obvious issues, but normal lab values of routine coagulation tests won't reveal impact of modern drugs (anti-Xa, antiplatelet) and have nothing to do with surgeon hands curvature.

#### Other properties

Human model has many other properties, but filling them manually may not worth time spent. They exist for completeness and medical information system integration.

* [eGFR](https://en.wikipedia.org/wiki/Glomerular_filtration_rate) Cockcroft-Gault, CKD-EPI 2021 for adults, Schwartz revised 2009 for children.

## Validation

Please use a real patient's data: all electrolytes interconnected by electroneutrality law, Henderson-Hasselbalch equation. So even if you enter values in reference range, calculations can produce a broken result, especially anion gap (e.g. `149 - (101 + 24) = 24` which is &gt;16 mEq/L!).
**Some imagined case studies from books aren't designed well and will fail too.**

## Disclaimer

Heval is an experimental software. Whatever it calculates, it's *your* decisions will affect your human's live longevity. I have no responsibility for your collateral damage.

## Installation [![semver](https://img.shields.io/github/v/release/radioxoma/heval)](https://github.com/radioxoma/heval/releases/latest/) [![semver](https://img.shields.io/github/release-date/radioxoma/heval)](https://github.com/radioxoma/heval/releases/latest/)

Since 2026 development switched towards web app. Desktop app is obsolete.

<details>

### Windows

Download *exe* file from the [releases page](https://github.com/radioxoma/heval/releases/latest/). Just run it — installation is not required.

* [v0.1.5](https://github.com/radioxoma/heval/releases/tag/v0.1.5) is last compatible with Windows XP SP3 x86 and python 3.4.3.
* Latest version can be installed with `pip install https://github.com/radioxoma/heval/archive/main.zip`.

### Mac OS X

Download *dmg* file (Apple Disk Image with 64-bit *Heval.app*) from the [releases page](https://github.com/radioxoma/heval/releases/latest/). Unpack *Heval.app* from *dmg*. Application unsigned, so warning "*macOS cannot verify the developer of 'Heval'*" will appear if you try to run it. You can overcome this in one of two ways:

* Press <kbd>Control</kbd> and simultaneously click on unpacked *Heval.app*. Click *Open* in appeared context menu. Click *Open* in appeared window
* Run in terminal `xattr -dr com.apple.quarantine "Heval.app"`. Now "Heval" can be run by click


### Linux

> Tip: Archlinux [AUR](https://wiki.archlinux.org/index.php/Arch_User_Repository) package [`heval-git`](https://aur.archlinux.org/packages/heval-git/) available.

Heval is written in python and uses tkinter for GUI.

 $ sudo apt install git python3-tk # Debian / Ubuntu
 $ sudo pacman -S git python tk # Archlinux

 $ git clone https://github.com/radioxoma/heval.git
 $ cd heval
 $ pip install .
 $ python -m heval # Run code directly

Instead of executing `python -m heval` it's possible to double-click 'heval.desktop'.
</details>

## Desktop app screenshots

![2023-04-02_17-39-38](https://user-images.githubusercontent.com/4701641/229360354-9b64cf87-eee7-415f-b536-650ed7f0294b.png)
![2023-04-02_17-46-04](https://user-images.githubusercontent.com/4701641/229360360-f9b12a49-7ffa-4bd9-b309-e4b94f00e57c.png)
