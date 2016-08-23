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

"""Creates TestCases from a list of TestEntries.

This module mainly exists to translate Proboscis classes and concepts into the
unittest equivalents.

"""

import os
import pydoc
import types
import unittest
import sys

from collections import deque
from functools import wraps

from proboscis import compatability
from proboscis import dependencies
from proboscis import SkipTest
from proboscis.sorting import TestGraph
from proboscis.core import TestMethodClassEntry
from proboscis.decorators import DEFAULT_REGISTRY

# This is here so Proboscis own test harness can change it while still calling
# TestProgram normally. Its how the examples are tested.
OVERRIDE_DEFAULT_STREAM = None


class TestPlan(object):
    """Grabs information from the TestRegistry and creates a test plan."""

    def __init__(self, groups, test_entries, factories):
        test_cases = self.create_cases(test_entries, factories)
        graph = TestGraph(groups, test_entries, test_cases)
        self.tests = graph.sort()

    @staticmethod
    def create_from_registry(registry):
        """Returns a sorted TestPlan from a TestRegistry instance."""
        return TestPlan(registry.groups, registry.tests, registry.factories)

    @staticmethod
    def create_cases_from_instance(factory, instance):
        if isinstance(instance, type):
            raise RuntimeError("Factory %s returned type %s (rather than an "
                "instance), which is not allowed." % (factory, instance))
        if isinstance(instance, types.MethodType):
            home = compatability.get_method_function(instance)
        elif isinstance(instance, types.FunctionType):
            home = instance
        else:
            home = type(instance)
        if issubclass(home, unittest.TestCase):
            raise RuntimeError("Factory %s returned a unittest.TestCase "
                "instance %s, which is not legal.")
        try:
            entry = home._proboscis_entry_
        except AttributeError:
            raise RuntimeError("Factory method %s returned an instance %s "
                "which was not tagged as a Proboscis TestEntry." %
                (factory, instance))
        entry.mark_as_used_by_factory()  # Don't iterate this since a
                                         # function is creating it.
        if entry.is_child:
            raise RuntimeError("Function %s, which exists as a bound method "
                "in a decorated class may not be returned from a factory." %
                instance)
        # There is potentially an issue in that a different Registry might
        # register an entry, and we could then read that in with a factory.
        # Later the entry would not be found in the dictionary of entries.
        if isinstance(instance, types.MethodType):
            try:
                state = TestMethodState(instance.im_self)
            except AttributeError:
                raise RuntimeError("Only bound methods may be returned from "
                    "factories. %s is not bound." % instance)
        else:
            state = TestMethodState(entry, instance)
        return TestPlan._create_test_cases_for_entry(entry, state)

    @staticmethod
    def create_cases(test_entries, factories):
        tests = []
        entries = {}
        for factory in factories:
            list = factory()
            for item in list:
                cases = TestPlan.create_cases_from_instance(factory, item)
                tests += cases
        for entry in test_entries:
            if not entry.is_child and not entry.used_by_factory:
                test_cases = TestPlan._create_test_cases_for_entry(entry)
                entries[entry] = test_cases
                tests += test_cases
        return tests

    @staticmethod
    def _create_test_cases_for_entry(entry, state=None):
        """Processes a test case entry."""
        if not hasattr(entry, 'children'):  # function or unittest.TestCase
            return [TestCase(entry)]
        state = state or TestMethodState(entry)
        cases = []
        for child_entry in entry.children:
            case = TestCase(child_entry, state=state)
            cases.append(case)
        return cases

    def create_test_suite(self, config, loader):
        """Transforms the plan into a Nose test suite."""
        creator = TestSuiteCreator(loader)
        if dependencies.use_nose:
            from nose.suite import ContextSuiteFactory
            suite = ContextSuiteFactory(config)([])
        else:
            suite = unittest.TestSuite()
        for case in self.tests:
            if case.entry.info.enabled and case.entry.home is not None:
                tests = creator.loadTestsFromTestEntry(case)
                for test in tests:
                    suite.addTest(test)
        return suite

    def filter(self, group_names=None, classes=None, functions=None):
        """Whittles down test list to those matching criteria."""
        test_homes = []
        classes = classes or []
        functions = functions or []
        for cls in classes:
            test_homes.append(cls)
        for function in functions:
            test_homes.append(function)
        group_names = group_names or []
        filtered_list = []
        while self.tests:
            case = self.tests.pop()
            if case.entry.contains(group_names, test_homes):
                filtered_list.append(case)
                # Add any groups this depends on so they will run as well.
                for group_name in case.entry.info.depends_on_groups:
                    if not group_name in group_names:
                        group_names.append(group_name)
                for test_home in case.entry.info.depends_on:
                    if not test_home in test_homes:
                        test_homes.append(test_home)
        self.tests = list(reversed(filtered_list))


class TestCase(object):
    """Represents an instance of a TestEntry.

    This class is also used to store status information, such as the dependent
    TestEntry objects (discovered when this test is sorted) and any failure
    in the dependencies of this test (used to raise SkipTest if needed).

    There may be multiple TestCase instances for each TestEntry instance.

    """
    def __init__(self, entry, state=None):
        self.entry = entry
        self.dependents = []  # This is populated when we sort the tests.
        self.dependency_failure = None
        self.state = state

    def check_dependencies(self, test_self):
        """If a dependency has failed, SkipTest is raised."""
        if self.dependency_failure is not None and \
           self.dependency_failure != self and not self.entry.info.always_run:
            home = self.dependency_failure.entry.home
            dependencies.skip_test(test_self, "Failure in %s" % home)

    def fail_test(self, dependency_failure=None):
        """Called when this entry fails to notify dependents."""
        if not dependency_failure:
            dependency_failure = self
        if not self.dependency_failure:  # Do NOT overwrite the first cause
            self.dependency_failure = dependency_failure
            for dependent in self.dependents:
                if dependent.critical:
                    dependent.case.fail_test(
                        dependency_failure=dependency_failure)

    def write_doc(self, file):
        file.write(str(self.entry.home) + "\n")
        doc = pydoc.getdoc(self.entry.home)
        if doc:
            file.write(doc + "\n")
        for field in str(self.entry.info).split(', '):
            file.write("\t" + field + "\n")

    def __repr__(self):
        return "TestCase(" + repr(self.entry.home) + ", " + \
               repr(self.entry.info) + ", " + object.__repr__(self) + ")"

    def __str__(self):
        return "Home = " + str(self.entry.home) + ", Info(" + \
               str(self.entry.info) + ")"


class TestResultListener():
    """Implements methods of TestResult to be informed of test failures."""

    def __init__(self, chain_to_cls):
        self.chain_to_cls = chain_to_cls

    def addError(self, test, err):
        self.onError(test)
        self.chain_to_cls.addError(self, test, err)

    def addFailure(self, test, err):
        self.onError(test)
        self.chain_to_cls.addFailure(self, test, err)

    def onError(self, test):
        """Notify a test entry and its dependents of failure."""
        if dependencies.use_nose:
            root = test.test
        else:
            root = test
        if hasattr(root, "__proboscis_case__"):
            case = root.__proboscis_case__
            case.fail_test()



class TestResult(TestResultListener, dependencies.TextTestResult):
    """Adds Proboscis skip on dependency failure functionality.

    Extends either Nose or unittest's TextTestResult class.
    If a program needs to use its own TestResult class it must inherit from
    this class and call "onError" at the start of both the addError and
    addFailure functions, passing the "test" parameter, to keep
    Proboscis's skip on depdendency failure functionality.

    """

    # I had issues extending TextTestResult directly so resorted to this.

    def __init__(self, *args, **kwargs):
        TestResultListener.__init__(self, dependencies.TextTestResult)
        dependencies.TextTestResult.__init__(self, *args, **kwargs)


def test_runner_cls(wrapped_cls, cls_name):
    """Creates a test runner class which uses Proboscis TestResult."""
    new_dict = wrapped_cls.__dict__.copy()

    if dependencies.use_nose:
        def cb_make_result(self):
            return TestResult(self.stream, self.descriptions, self.verbosity,
                              self.config)
    else:
        def cb_make_result(self):
            return TestResult(self.stream, self.descriptions, self.verbosity)
    new_dict["_makeResult"] = cb_make_result
    return type(cls_name, (wrapped_cls,), new_dict)


def skippable_func(test_case, func):
    """Gives free functions a Nose independent way of skipping a test.

    The unittest module TestCase class has a skipTest method, but to run it you
    need access to the TestCase class. This wraps the runTest method of the
    underlying unittest.TestCase subclass to invoke the skipTest method if it
    catches the SkipTest exception.

    """
    s_func = None
    if dependencies.use_nose:
        s_func = func
    else:
        @wraps(func)
        def skip_capture_func():
            st = compatability.capture_exception(func, SkipTest)
            if st is not None:
                dependencies.skip_test(test_case, st.message)
        s_func = skip_capture_func

    @wraps(s_func)
    def testng_method_mistake_capture_func():
        compatability.capture_type_error(s_func)

    return testng_method_mistake_capture_func


class FunctionTest(unittest.FunctionTestCase):
    """Wraps a single function as a test runnable by unittest / nose."""

    def __init__(self, test_case):
        func = test_case.entry.home
        _old_setup = None
        if hasattr(func, 'setup'):  # Don't destroy nose-style setup
            _old_setup = func.setup
        def cb_check(cb_self=None):
            test_case.check_dependencies(self)
            if _old_setup is not None:
                _old_setup()
        self.__proboscis_case__ = test_case
        sfunc = skippable_func(self, func)
        unittest.FunctionTestCase.__init__(self, testFunc=sfunc, setUp=cb_check)


class TestMethodState(object):
    """Manages a test class instance used by one or more test methods."""

    def __init__(self, entry, instance=None):
        self.entry = entry
        # This would be a simple "isinstance" but due to the reloading mania
        # needed for Proboscis's documentation tests it has to be a bit
        # weirder.
        if not str(type(self.entry)) == str(TestMethodClassEntry):
            raise RuntimeError("%s is not a TestMethodClassEntry but is a %s."
                               % (self.entry, type(self.entry)))
        self.instance = instance

    def get_state(self):
        if not self.instance:
            self.instance = self.entry.home()
        return self.instance


class MethodTest(unittest.FunctionTestCase):
    """Wraps a method as a test runnable by unittest."""

    def __init__(self, test_case):
        assert test_case.state is not None
        #TODO: Figure out how to attach calls to BeforeMethod and BeforeClass,
        #      AfterMethod and AfterClass. It should be easy enough to
        #      just find them using the TestEntry parent off test_case Entrty.
        def cb_check(cb_self=None):
            test_case.check_dependencies(self)
        @wraps(test_case.entry.home)
        def func(self=None):  # Called by FunctionTestCase
            func = test_case.entry.home
            func(test_case.state.get_state())
        self.__proboscis_case__ = test_case
        sfunc = skippable_func(self, func)
        unittest.FunctionTestCase.__init__(self, testFunc=sfunc, setUp=cb_check)


def decorate_class(setUp_method=None, tearDown_method=None):
    """Inserts method calls in the setUp / tearDown methods of a class."""
    def return_method(cls):
        """Returns decorated class."""
        new_dict = cls.__dict__.copy()
        if setUp_method:
            if hasattr(cls, "setUp"):
                @wraps(setUp_method)
                def _setUp(self):
                    setUp_method(self)
                    cls.setUp(self)
            else:
                @wraps(setUp_method)
                def _setUp(self):
                    setUp_method(self)
            new_dict["setUp"] = _setUp
        if tearDown_method:
            if hasattr(cls, "tearDown"):
                @wraps(tearDown_method)
                def _tearDown(self):
                    tearDown_method(self)
                    cls.setUp(self)
            else:
                @wraps(tearDown_method)
                def _tearDown(self):
                    tearDown_method(self)
            new_dict["tearDown"] = _tearDown
        return type(cls.__name__, (cls,), new_dict)
    return return_method


class TestSuiteCreator(object):
    """Turns Proboscis test cases into elements to be run by unittest."""

    def __init__(self, loader):
        self.loader = loader

    def loadTestsFromTestEntry(self, test_case):
        """Wraps a test class in magic so it will skip on dependency failures.

        Decorates the testEntry class's setUp method to raise SkipTest if
        tests this test was dependent on failed or had errors.

        """
        home = test_case.entry.home
        if home is None:
            return []
        if isinstance(home, type):
            return self.wrap_unittest_test_case_class(test_case)
        if isinstance(home, types.FunctionType):
            if home._proboscis_entry_.is_child:
                return self.wrap_method(test_case)
            else:
                return self.wrap_function(test_case)
        raise RuntimeError("Unknown test type:" + str(type(home)))

    def wrap_function(self, test_case):
        return [FunctionTest(test_case)]

    def wrap_method(self, test_case):
        return [MethodTest(test_case)]

    def wrap_unittest_test_case_class(self, test_case):
        original_cls = test_case.entry.home
        def cb_check(cb_self):
            test_case.check_dependencies(cb_self)
        testCaseClass = decorate_class(setUp_method=cb_check)(original_cls)
        testCaseNames = self.loader.getTestCaseNames(testCaseClass)
        if not testCaseNames and hasattr(testCaseClass, 'runTest'):
            testCaseNames = ['runTest']
        suite = []
        if issubclass(original_cls, unittest.TestCase):
            for name in testCaseNames:
                test_instance = testCaseClass(name)
                setattr(test_instance, "__proboscis_case__", test_case)
                suite.append(test_instance)
        return suite


class TestProgram(dependencies.TestProgram):
    """Use this to run Proboscis.

    Translates the Proboscis test registry into types used by Nose or unittest
    in order to run the program.

    Most arguments to this are simply passed to Nose or unittest's TestProgram
    class.

    For most cases using the default arguments works fine.

    :param registry: The test registry to use. If unset uses the default global
                     registry.
    :param groups: A list of strings representing the groups of tests to run.
                   The list is added to by parsing the argv argument. If unset
                   then all groups are run.
    :param testLoader: The test loader. By default, its unittest.TestLoader.
    :param config: The config passed to Nose or unittest.TestProgram. The
                   config determines things such as plugins or output streams,
                   so it may be necessary to create this for advanced use
                   cases.
    :param plugins: Nose plugins. Similar to config it may be necessary to
                    set this in an advanced setup.
    :param env: By default is os.environ. This is used only by Nose.
    :param testRunner: By default Proboscis uses its own. If this is set
                       however care must be taken to avoid breaking Proboscis's
                       automatic skipping of tests on dependency failures.
                       In particular, _makeResult must return a subclass of
                       proboscis.TestResult which calls
                       proboscis.TestResult.onError at the start of the
                       addFailure and addError methods.
    :param stream: By default this is standard out.
    :param argv: By default this is sys.argv. Proboscis parses this for the
                 --group argument.
    """
    def __init__(self,
                 registry=DEFAULT_REGISTRY,
                 groups=None,
                 testLoader=None,
                 config=None,
                 plugins=None,
                 env=None,
                 testRunner=None,
                 stream=None,
                 argv=None,
                 *args, **kwargs):
        groups = groups or []
        argv = argv or sys.argv
        argv = self.extract_groups_from_argv(argv, groups)
        if "suite" in kwargs:
            raise ValueError("'suite' is not a valid argument, as Proboscis " \
                             "creates the suite.")

        self.__loader = testLoader or unittest.TestLoader()

        if OVERRIDE_DEFAULT_STREAM:
            stream = OVERRIDE_DEFAULT_STREAM

        if env is None:
            env = os.environ
        if dependencies.use_nose and config is None:
            config = self.makeConfig(env, plugins)
            if not stream:
                stream = config.stream

        stream = stream or sys.stdout

        if testRunner is None:
            runner_cls = test_runner_cls(dependencies.TextTestRunner,
                                         "ProboscisTestRunner")
            if dependencies.use_nose:
                testRunner = runner_cls(stream,
                                        verbosity=3,  # config.verbosity,
                                        config=config)
            else:
                testRunner = runner_cls(stream, verbosity=3)

        #registry.sort()
        self.plan = TestPlan.create_from_registry(registry)

        if len(groups) > 0:
            self.plan.filter(group_names=groups)
        self.cases = self.plan.tests
        if "--show-plan" in argv:
            self.__run = self.show_plan
        else:
            self.__suite = self.create_test_suite_from_entries(config,
                                                               self.cases)
            def run():
                if dependencies.use_nose:
                    dependencies.TestProgram.__init__(
                        self,
                        suite=self.__suite,
                        config=config,
                        env=env,
                        plugins=plugins,
                        testLoader=testLoader,  # Pass arg, not what we create
                        testRunner=testRunner,
                        argv=argv,
                        *args, **kwargs
                    )
                else:
                    dependencies.TestProgram.__init__(
                        self,
                        suite=self.__suite,
                        config=config,
                        testLoader=testLoader,  # Pass arg, not what we create
                        testRunner=testRunner,
                        argv=argv,
                        *args, **kwargs
                    )
            self.__run = run

    def create_test_suite_from_entries(self, config, cases):
        """Creates a suite runnable by unittest."""
        return self.plan.create_test_suite(config, self.__loader)

    def extract_groups_from_argv(self, argv, groups):
        """Given argv, records the "--group" options.

        :param argv: A list of arguments, such as sys.argv.
        :param groups: A list of strings for each group to run which is added
                       to.

        Returns a copy of param argv with the --group options removed. This is
        useful if argv needs to be passed to another program such as Nose.

        """
        new_argv = [argv[0]]
        for arg in argv[1:]:
            if arg[:8] == "--group=":
                groups.append(arg[8:])
            else:
                new_argv.append(arg)
        return new_argv

    def run_and_exit(self):
        """Calls unittest or Nose to run all tests.

        unittest will call sys.exit on completion.

        """
        self.__run()

    def show_plan(self):
        """Prints information on test entries and the order they will run."""
        print("   *  *  *  Test Plan  *  *  *")
        for case in self.cases:
            case.write_doc(sys.stdout)

    @property
    def test_suite(self):
        return self.__suite
