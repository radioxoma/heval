## Heval — a human evaluator. Calculate what your human crave!

The program describes an human being, small or grown. It takes basic anthropometric values (sex, height) and calculates [BMI](https://en.wikipedia.org/wiki/Body_mass_index), [BSA](https://en.wikipedia.org/wiki/Body_surface_area), [IBW](https://en.wikipedia.org/wiki/Human_body_weight#Ideal_body_weight), [fluid](https://en.wikipedia.org/wiki/Fluid_replacement), respiratory and [energy](https://en.wikipedia.org/wiki/Basal_metabolic_rate) demands, urinary output, some drugs dosage and more. Heval also incorporates sophisticated [ABG interpreter](https://en.wikipedia.org/wiki/Acid%E2%80%93base_homeostasis). **See [screenshots](https://github.com/radioxoma/heval#screenshots).**

Main features:

* Minimal user input — unknown values estimated automatically whenever possible (e.g. weight by height)
* Only measurable parameters — no need to speak with a human of interest or it's congeners
* No "Calculate" button — evaluated data changes immediately with your input
* Every calculation referenced and explained in source code, so everyone can reproduce it
* It's got electrolytes


### Human body

> Tip: Get yourself a ruler, not all humans are able to talk.

* Just enter sex and height
* No input field for a human age, even for children, because of it poor prediction power. Incorporated [Broselow-Luten color zones](https://en.wikipedia.org/wiki/Broselow_tape) and weight-by-height formulas at your service


### Arterial blood gas & Electrolytes

> Tip: You can test Heval's ability to interpret ABG with [case studies](https://web.archive.org/web/20170818090331/http://fitsweb.uchc.edu/student/selectives/TimurGraham/Case_1.html). Some books provide case studies with invalid data (see below).

* Enter pH and pCO2 for overall acid-base status assessment
* Use electrolytes panel to assess hidden processes of metabolic acidosis ([anion gap](https://en.wikipedia.org/wiki/Anion_gap), [delta-gap](https://en.wikipedia.org/wiki/Delta_ratio)) and general electrolyte disturbances
* Sex and weight used only for dosage calculations, not for ABG diagnostics itself

Please use a real patient's data: all electrolytes interconnected by electroneutrality law, Henderson-Hasselbalch equation. So even if you enter values in reference range, calculations can produce a broken result, especially anion gap (e.g. `149 - (101 + 24) = 24` which is >16 mEq/L!).
**Some imagined case studies from books aren't designed well and will fail too.**



## Disclaimer
Heval is an experimental software. Whatever it calculates, it's *your* decisions will affect your human's live longevity. I have no responsibility for your collateral damage.

An web or Android application is planned, but implementation deferred until calculations being tested and I'll get some feedback.

| Function | Status | Comment |
| --- | --- | --- |
| Human body: anthropometry | **Good** | Straightforward implementation. Broselow for children. Small issues with IBW |
| Human body: respiration | **Good** | Use as start ventilator settings for adults and children |
| Human body: energy & electrolytes | Limited | Generic approximation for healthy human. Real demands are unpredictably dependent on body fat/muscle, fever, sepsis, burns etc |
| Human body: fluid demand | Limited | Generic approximation for healthy human. Pathologic [fluid loss](https://en.wikipedia.org/wiki/Volume_contraction) must be taken into account |
| Human body: urinary output | **Good** | Adults and children, though eGFR estimation may be necessary |
| Human body: drug dosage | Medium | Verified, but limited drug list |
| ABG: anion gap | **Good** | Excellent prediction, but please USE REAL DATA |
| ABG: Electrolytes replacement | Garbage | Multiple calculation methods in books, no one applicable in real world. Exact depletion/excess estimation is impossible. High/low warnings still usable though. |
| ABG: pH correction | Limited | Dubious benefit. Lack of theory. Not all pH range covered. |
| eGFR | **Good** | Straightforward implementation |



## Installation [![semver](https://img.shields.io/github/v/release/radioxoma/heval)](https://github.com/radioxoma/heval/releases/latest/) [![semver](https://img.shields.io/github/release-date/radioxoma/heval)](https://github.com/radioxoma/heval/releases/latest/) [![Build Status](https://travis-ci.org/radioxoma/heval.svg?branch=master)](https://travis-ci.org/radioxoma/heval)

### Windows

Download *exe* file from the [releases page](https://github.com/radioxoma/heval/releases/latest/). Just run it — installation is not required.

Builds are compatible with Windows XP SP3 32 bit and based on python 3.4.4 (see `build.bat`). Latest development version can be installed with `pip install https://github.com/radioxoma/heval/archive/master.zip`.

### Mac OS X

Download *dmg* file (Apple Disk Image with 64-bit *Heval.app*) from the [releases page](https://github.com/radioxoma/heval/releases/latest/). Application unsigned, so warning will appear. You can disable it with `xattr -dr com.apple.quarantine "Heval.app"`.

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

![2019-11-29_heval_human_body](https://user-images.githubusercontent.com/4701641/69869967-632a6e00-12bf-11ea-932d-3dcc9e21936d.png)
![2019-11-29_heval_abg](https://user-images.githubusercontent.com/4701641/69870313-8dc8f680-12c0-11ea-9bef-58f9d2ab32a7.png)
