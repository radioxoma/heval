#!/usr/bin/env python

import unittest
import doctest
from heval import abg, drugs, electrolytes, human

DOCTESTS = (abg, drugs, electrolytes, human)


def suite():
    suite = unittest.TestSuite()
    suite.addTests([doctest.DocTestSuite(t) for t in DOCTESTS])
    return suite


runner = unittest.TextTestRunner(verbosity=2)
runner.run(suite())
