#!/usr/bin/env python3
"""
Script to run all unit tests.
"""
import unittest


if __name__ == "__main__":
    # Discover all tests in the tests directory
    test_suite = unittest.defaultTestLoader.discover('tests')
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(test_suite) 