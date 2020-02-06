#!/usr/bin/env python

import doctest
from heval import abg, drugs, electrolytes, human

DOCTESTS = (abg, drugs, electrolytes, human)


def load_tests(loader, tests, ignore):
    tests.addTests([doctest.DocTestSuite(t) for t in DOCTESTS])
    return tests
