#!/usr/bin/env python

import doctest

from heval import abg, drugs, electrolytes, human, nutrition

DOCTESTS = (abg, drugs, electrolytes, human, nutrition)


def load_tests(loader, tests, ignore):
    tests.addTests([doctest.DocTestSuite(t) for t in DOCTESTS])
    return tests
