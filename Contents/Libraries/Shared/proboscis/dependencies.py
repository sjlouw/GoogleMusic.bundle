# Copyright (c) 2011 Rackspace
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""Dynamically selected dependencies for Proboscis.

If Nose is installed, Proboscis will use it. Otherwise Proboscis will use the
default unittest framework, in order to function in IronPython and Jython. It
also supports Python 2.5 in order to work with Jython.

"""
try:
    from nose.plugins.skip import SkipTest as ExternalSkipTest
    from nose.core import TestProgram
    from nose.core import TextTestResult
    from nose.core import TextTestRunner

    use_nose = True

    def skip_test(test_self, message):
        raise SkipTest(message)

except ImportError:
    import unittest
    from unittest import TextTestRunner

    use_nose = False

    # In 2.7 unittest.TestCase has a skipTest method.
    def skip_test(test_self, message):
        try:
            test_self.skipTest(message)
        except AttributeError:  # For versions prior to 2.5.
            raise AssertionError("SKIPPED:%s" % message)
    class TestProgram(unittest.TestProgram):

        def __init__(self, suite, config=None, *args, **kwargs):
            self.suite_arg = suite

            class StubLoader(object):
                def loadTestsFromModule(*args, **kwargs):
                    return self.suite_arg

            self.test = suite
            if 'testLoader' not in kwargs or kwargs['testLoader'] is None:
                kwargs['testLoader'] = StubLoader()
            super(TestProgram, self).__init__(*args, **kwargs)

        def createTests(self):
            self.test = self.suite_arg

    class TextTestResult(unittest._TextTestResult):
        def __init__(self, stream, descriptions, verbosity, config=None,
                     errorClasses=None):
            super(TextTestResult, self).__init__(stream, descriptions,
                                                 verbosity);

    class ExternalSkipTest(Exception):
        def __init__(self, message):
            super(ExternalSkipTest, self).__init__(self, message)
            self.message = message

        def __str__(self):
            return self.message


# Doing it this way so I won't change Nose's pydoc.
class SkipTest(ExternalSkipTest):
    """
    Raise this to skip a test.
    If Nose is available its SkipTest is used.
    Otherwise Proboscis creates its own which class that calls
    unittest.TestCase.skipTest. If that method isn't available (anything under
    2.7) then skipping does not work and test errors are presented.
    """
    pass

