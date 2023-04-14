#!/usr/bin/env python

import doctest
import unittest

from heval import abg, drugs, electrolytes, human, nutrition

modules = (abg, drugs, electrolytes, human, nutrition)


def load_tests(loader: unittest.TestLoader, tests, pattern) -> unittest.TestSuite:
    """Callback to load doctests from modules."""
    tests.addTests([doctest.DocTestSuite(m) for m in modules])
    return tests
