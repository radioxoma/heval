Heval — a human evaluator. Calculate what your human crave!

### Human body part

The program describes an human being, small or grown. It takes basic anthropometric values (sex, height), blood test values and calculates BMI, BSA, IBW, fluid, respiratory and energy demands, urinary output, some drugs dosage and speed etc.

* Minimal user input
* Some unknown values (like weight) can be estimated using others (height)
* No need to input same data into multiple forms
* No "Calculate" button — when Heval will know enough about your human, it will push back evaluated data immediately
* Every calculation referenced and explained in source code, so one can reproduce it

### Arterial blood gas part

* Enter pH and pCO2 for overall acid-base status assessment
* Use electrolytes panel to assess hidden processes of metabolic acidosis (anion gap, delta-gap) and, of course, electrolyte disturbances
* Sex and weight used for dosage calculations

Heval is an experimental software. Whatever it calculates, it's *your* decisions will made life of your human longer or shorter. I have no responsibility for your collateral damage.

An web or Android application is planned, but implementation deferred until calculations being tested and I'll get some feedback.


## Download

Go to [Releases page](https://github.com/radioxoma/heval/releases/) and download precompiled binary for Windows. Just run it - no installation required.

### Development version

If you have python installed, latest development version can be installed with pip:

    $ pip install https://github.com/radioxoma/heval/archive/master.zip

Run development version:

    $ git clone https://github.com/radioxoma/heval.git
    $ cd heval
    $ python -m heval

`build.bat` creates pyinstaller standalone Windows executable (one 'exe' file).
