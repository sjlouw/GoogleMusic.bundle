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

"""Decorators useful to the tests."""

from functools import wraps

from proboscis.asserts import assert_raises_instance
from proboscis import compatability
from proboscis.core import TestRegistry


DEFAULT_REGISTRY = TestRegistry()


def expect_exception(exception_type):
    """Decorates a test method to show it expects an exception to be raised."""
    def return_method(method):
        @wraps(method)
        def new_method(*args, **kwargs):
            assert_raises_instance(exception_type, method, *args, **kwargs)
        return new_method
    return return_method


class TimeoutError(RuntimeError):
    """Thrown when a method has exceeded the time allowed."""
    pass


def time_out(time):
    """Raises TimeoutError if the decorated method does not finish in time."""
    if not compatability.supports_time_out():
        raise ImportError("time_out not supported for this version of Python.")
    import signal

    def cb_timeout(signum, frame):
        raise TimeoutError("Time out after waiting " + str(time) + " seconds.")

    def return_method(func):
        """Turns function into decorated function."""
        @wraps(func)
        def new_method(*kargs, **kwargs):
            previous_handler = signal.signal(signal.SIGALRM, cb_timeout)
            try:
                signal.alarm(time)
                return func(*kargs, **kwargs)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, previous_handler)
        return new_method
    return return_method


def register(**kwargs):
    """Registers a test in proboscis's default registry.

    :param home: The target class or function.

    This also allows all of the parameters used by the @test decorator.

    This function works differently than a decorator as it allows the class or
    function which is being registered to appear in the same call as all of the
    options.

    Its designed to make it easier to register class or functions with
    Proboscis after they're defined.

    """
    DEFAULT_REGISTRY.register(**kwargs)


def test(home=None, **kwargs):
    """Decorates a test class or function to cause Proboscis to run it.

    The behavior differs depending the target:

        - If put on a stand-alone function, the function will run by itself.

        - If put on a class inheriting unittest.TestCase, then the class will
          run just like a normal unittest class by using the method names and
          instantiate a new instance of the class for each test method.

        - If the class does not inherit from unittest.TestCase, the class will
          be instantiated once and this instance will be passed to each method
          decorated with @test (this increases encapsulation over using class
          fields as the instance can not be accessed outside of its methods).

          Note that due to how decorators work its impossible to know if a
          function is or is not part of a class; thus if a class method is
          decorated with test but its class is not then
          ProboscisTestMethodNotDecorated will be raised.

    :param groups: A list of strings representing the groups this test method
                   or class belongs to. By default this is an empty list.
    :param depends_on: A list of test functions or classes which must run
                       before this test. By default this is an empty list.
    :param depends_on_groups: A list of strings each naming a group that must
                              run before this test. By default this is an empty
                              list.
    :param enabled: By default, true. If set to false this test will not run.
    :param always_run: If true this test will run even if the tests listed in
                       depends_on or depends_on_groups have failed.
    """
    if home:
        return DEFAULT_REGISTRY.register(home, **kwargs)
    else:
        def cb_method(home_2):
            return DEFAULT_REGISTRY.register(home_2, **kwargs)
        return cb_method


def before_class(home=None, **kwargs):
    """Like @test but indicates this should run before other class methods.

    All of the arguments sent to @test work with this decorator as well.

    """
    kwargs.update({'run_before_class':True})
    return test(home=home, **kwargs)


def after_class(home=None, **kwargs):
    """Like @test but indicates this should run after other class methods.

    All of the arguments sent to @test work with this decorator as well.

    This will be skipped if a class method test fails;
    set always_run if that is not desired. See `issue #5
    <https://github.com/rackspace/python-proboscis/issues/5>`__.

    """
    kwargs.update({'run_after_class':True})
    return test(home=home, **kwargs)


def factory(func=None, **kwargs):
    """Decorates a function which returns new instances of Test classes."""
    if func:
        return DEFAULT_REGISTRY.register_factory(func)
    else:
        raise ValueError("Arguments not supported on factories.")

