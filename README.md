Heval — a human evaluator. Calculate what your human crave!

The program describes an human being, small or grown. It takes basic anthropometric values (sex, height), blood test values and calculates BMI, BSA, IBW, fluid, respiratory and energy demands, urinary output, some drugs dosage and speed etc.

* Minimal user input
* Some unknown values (like weight) can be estimated using others (height)
* No need to input same data into multiple forms
* No "Calculate" button - when Heval will know enough about your human, it will push back evaluated data immediately
* Every calculation referenced and explained in source code, so one can reproduce it

Heval gives help to those who can accept it. You have to be familiar with english medical culture (abbreviations, scales etc) or, at least, be able to read. Russian translations known to be ambiguous and too broad.

Heval is an experimental software. Whatever it calculates, it's *your* decisions will made life of your human longer or shorter. I have no responsibility for your collateral damage.

An web or Android application is planned, but implementation deferred until calculations being tested and I'll get some feedback.


## Installation

`build.bat` creates *pyinstaller* standalone Windows executable (one 'exe' file).

Install in with pip:

    $ pip install https://github.com/radioxoma/heval/archive/master.zip

Run development version:

    $ git clone https://github.com/radioxoma/heval.git
    $ cd heval
    $ python -m heval
