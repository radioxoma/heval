## Heval — a human evaluator. Calculate what your human crave!

The program describes an human being, small or grown from position of [intensive care medicine](https://en.wikipedia.org/wiki/Intensive_care_medicine). See [screenshots](https://github.com/radioxoma/heval#screenshots).

From just *sex* and *height* it calculates [BSA](https://en.wikipedia.org/wiki/Body_surface_area), [IBW](https://en.wikipedia.org/wiki/Human_body_weight#Ideal_body_weight), [fluid](https://en.wikipedia.org/wiki/Fluid_replacement), respiratory and [parenteral nutrition](https://en.wikipedia.org/wiki/Parenteral_nutrition) demands, urinary output, some drugs dosage and more.

[ABG interpreter](https://en.wikipedia.org/wiki/Acid%E2%80%93base_homeostasis) reveals hidden processes, suggest urgent correction measures and infusion therapy.

Main features:

* Minimal user input — unknown values estimated automatically whenever possible (e.g. weight by height)
* Only measurable parameters — no need to speak with a human of interest
* No "Calculate" button — evaluated data changes immediately with your input
* Every calculation referenced and explained in source code, so everyone can reproduce it
* It's got electrolytes


### Human body

> Tip: Get yourself a [ruler](https://en.wikipedia.org/wiki/Tape_measure), not all humans are able to talk.

* Just enter sex and height
* No input field for a human age, even for children, because of it poor prediction power. Incorporated [Broselow-Luten color zones](https://en.wikipedia.org/wiki/Broselow_tape) and [weight-by-height](https://en.wikipedia.org/wiki/Human_body_weight#Ideal_body_weight) formulas at your service


### Arterial blood gas & Electrolytes

> Tip: You can test Heval's ability to interpret ABG with [case studies](https://web.archive.org/web/20170818090331/http://fitsweb.uchc.edu/student/selectives/TimurGraham/Case_1.html). Some books provide case studies with invalid data (see below).

1. Enter pH and pCO2 for overall acid-base status assessment
2. Use electrolytes panel to assess hidden processes of metabolic acidosis ([anion gap](https://en.wikipedia.org/wiki/Anion_gap), [delta-gap](https://en.wikipedia.org/wiki/Delta_ratio)) and general electrolyte disturbances
    * Algorithm able to detect vomiting, hypoalbuminemia, [HHS](https://en.wikipedia.org/wiki/Hyperosmolar_hyperglycemic_state)
    * Sex and weight used only for dosage calculations, not for ABG diagnostics itself
3. Adjust optional data for precise calculations in complex cases

Please use a real patient's data: all electrolytes interconnected by electroneutrality law, Henderson-Hasselbalch equation. So even if you enter values in reference range, calculations can produce a broken result, especially anion gap (e.g. `149 - (101 + 24) = 24` which is >16 mEq/L!).
**Some imagined case studies from books aren't designed well and will fail too.**



## Disclaimer
Heval is an experimental software. Whatever it calculates, it's *your* decisions will affect your human's live longevity. I have no responsibility for your collateral damage.

An web or Android application is planned, but implementation deferred until calculations being tested and I'll get some feedback.

> Key: Garbadge > Limited > Meduim > Good > Exellent

| Function | Status | Comment |
| -------- | ------ | ------- |
| Human body: anthropometry | **Good** | Straightforward implementation. Broselow for children. |
| Human body: respiration | **Good** | Use as start ventilator settings for adults and children |
| Human body: energy & electrolytes | Limited | Generic approximation for healthy human. Real demands are unpredictably dependent on body fat/muscle compound, fever, sepsis, burns etc. [REE](https://en.wikipedia.org/wiki/Resting_metabolic_rate) formulas has been taken from original papers, so your lovely Harris-Benedict equation don't have dubious correction coefficients, leading to irreproducible result. |
| Human body: fluid demand | Limited | Generic approximation for healthy human. Pathologic [fluid loss](https://en.wikipedia.org/wiki/Volume_contraction) must be taken into account |
| Human body: urinary output | **Good** | Simple ml/kg/h approach for adults and children, though eGFR estimation may be necessary |
| Human body: drug dosage | Medium | Verified, but limited drug list |
| Nutrition | Limited | Enteral and parenteral. Based on [ESPEN](https://www.espen.org/) 25-30 kcal/kg recommendation and nitrogen balance. Use [indirect calorimetry](https://en.wikipedia.org/wiki/Indirect_calorimetry) if you need a real tool. |
| ABG: pH correction | Limited | Recent papers deny benefit from iv bicarbonate if BE <-15 mEq/L. Some benefit possible in AKI patients. No validated formula found. |
| ABG: anion gap | **Good** | Excellent prediction, but please **USE REAL DATA** |
| ABG: Electrolytes replacement | Limited | Exact depletion/excess estimation is impossible due to multiple body compartments. High/low warnings still usable though. K<sup>+</sup> — no reliable model, use daily requirement and standard iv replacement rate for hypokalemia. Na<sup>+</sup> — Adrogue and classic one compartment model. Cl<sup>-</sup> — no model at all. Multiple calculation methods in books, few applicable in real world. |
| eGFR | **Good** | Straightforward implementation for adults and children |


## Installation [![semver](https://img.shields.io/github/v/release/radioxoma/heval)](https://github.com/radioxoma/heval/releases/latest/) [![semver](https://img.shields.io/github/release-date/radioxoma/heval)](https://github.com/radioxoma/heval/releases/latest/) [![Build Status](https://travis-ci.org/radioxoma/heval.svg?branch=master)](https://travis-ci.org/radioxoma/heval)

### Windows

Download *exe* file from the [releases page](https://github.com/radioxoma/heval/releases/latest/). Just run it — installation is not required.

Builds are compatible with Windows XP SP3 32 bit and based on python 3.4 (see `build.bat`). Latest development version can be installed with `pip install https://github.com/radioxoma/heval/archive/master.zip`.

### Mac OS X

Download *dmg* file (Apple Disk Image with 64-bit *Heval.app*) from the [releases page](https://github.com/radioxoma/heval/releases/latest/). Unpack *Heval.app* from *dmg*. Application unsigned, so warning "*macOS cannot verify the developer of "Heval"*" will appear if you try to run it. You can overcome this in one of two ways:

* Press <kbd>Control</kbd> and simultaneously click on unpacked *Heval.app*. Click *Open* in appeared context menu. Click *Open* in appeared window
* Run in terminal `xattr -dr com.apple.quarantine "Heval.app"`. Now "Heval" can be run by click


### Linux

> Tip: Archlinux [AUR](https://wiki.archlinux.org/index.php/Arch_User_Repository) package [`heval-git`](https://aur.archlinux.org/packages/heval-git/) available.

Heval is written in pure python3 and uses tkinter for GUI. Install dependencies and run python code directly:

    $ sudo apt install git python3-tk  # Debian / Ubuntu
    $ sudo pacman -S git python tk  # Archlinux

    $ git clone https://github.com/radioxoma/heval.git
    $ cd heval
    $ python3 -m heval

Instead of executing `python3 -m heval` it's possible to double-click 'heval.desktop'.


## Screenshots

![2020-02-19_v0 0 10_1](https://user-images.githubusercontent.com/4701641/74849673-0e404600-534a-11ea-83e2-75a03a67a07f.png)
![2020-02-19_v0 0 10_2](https://user-images.githubusercontent.com/4701641/74849686-1304fa00-534a-11ea-9373-7bfd30e39271.png)
![2020-02-19_v0 0 10_3](https://user-images.githubusercontent.com/4701641/74849895-56f7ff00-534a-11ea-94ca-3d6b609b3832.png)
