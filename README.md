## Heval — a human evaluator. Calculate what your human crave!

The program describes an human being, small or grown. It takes basic anthropometric values (sex, height) and calculates BMI, BSA, IBW, fluid, respiratory and energy demands, urinary output, some drugs dosage and more. Heval also incorporates sophisticated ABG analyzer.

Main features:

* Minimal user input — some unknown values (like weight) can be estimated using others (height)
* Only measurable parameters — no need to speak with a human of interest or it's congeners
* No need to input same data into multiple forms
* No "Calculate" button — when Heval will know enough about your human, it will push back evaluated data immediately
* Every calculation referenced and explained in source code, so everyone can reproduce it
* It's got electrolytes


### Human body

> Tip: Get yourself a ruler, not all humans are able to talk.

* Just enter sex and height
* No input for human age, even for children, because of it poor prediction power. Incorporated Broselow-Luten color zones and weight-by-height formulas at your service


### Arterial blood gas & Electrolytes

> Tip: You can test Heval's ability to interpret ABG with [these case studies](https://web.archive.org/web/20170818090331/http://fitsweb.uchc.edu/student/selectives/TimurGraham/Case_1.html).

* Enter pH and pCO2 for overall acid-base status assessment
* Use electrolytes panel to assess hidden processes of metabolic acidosis (anion gap, delta-gap) and, of course, electrolyte disturbances
* Sex and weight used only for dosage calculations, for not ABG diagnostics


## Disclaimer
Heval is an experimental software. Whatever it calculates, it's *your* decisions will affect your human's live longevity. I have no responsibility for your collateral damage.

An web or Android application is planned, but implementation deferred until calculations being tested and I'll get some feedback.


## Download

You can download Windows build from [releases page](https://github.com/radioxoma/heval/releases/). Just run it — installation is not required. Builds are compatible with Windows XP SP3 32 bit and based on python 3.4.4 (see `build.bat`).

### Development version

Heval is written in pure python and uses tkinter for GUI. If you have python, latest development version can be installed with pip:

    $ pip install https://github.com/radioxoma/heval/archive/master.zip

Run development version:

    $ git clone https://github.com/radioxoma/heval.git
    $ cd heval
    $ python -m heval
