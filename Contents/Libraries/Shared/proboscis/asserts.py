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

"""Assert functions with a parameter order of actual_value, expected_value.

This module contains many stand-ins for functions in Nose.tools. It is also
a clone of TestNG's Assert class with the static methods changed to functions,
and the term "equals" changed to simply "equal" to be more Pythonic.

There are also a few original assertions methods and the class Check.

This module should be preferred when Nose is not always available.

"""


import sys
import traceback

from proboscis import compatability

ASSERTION_ERROR=AssertionError
# Setting this causes stack traces shown by unittest and nose to stop before
# this moudle. It feels dirty but modifying the traceback is even worse.
__unittest = True


def assert_equal(actual, expected, message=None):
    """Asserts that the two values are equal.

    :param actual: The actual value.
    :param expected: The expected value.
    :param message: A message to show in the event of a failure.
    """
    #TODO: assert equal with dictionaries, arrays, etc
    if actual == expected:
        return
    if not message:
        try:
            message = "%s != %s" % (actual, expected)
        except Exception:
            message = "The actual value did not equal the expected one."
    raise ASSERTION_ERROR(message)


def assert_false(condition, message=None):
    """Asserts that the given condition is false.

    :param condition: Must be true.
    :param message: A message to show in the event of failure.
    """
    if condition:
        if not message:
            message = "Condition was True."
        raise ASSERTION_ERROR(message)


def assert_is(actual, expected, message=None):
    """Asserts that the two variables share the same identity.

    :param actual: A variable which has the actual identity.
    :param expected: The variable which has the expected variable.
    :param message: A message to show in the event of failure.

    """
    #TODO: assert equal with dictionaries, arrays, etc
    if actual is expected:
        return
    if not message:
        try:
            message = "%s is not %s" % (actual, expected)
        except Exception:
            message = "The actual value is not the expected one."
    raise ASSERTION_ERROR(message)


def assert_is_none(value, message=None):
    """Asserts that the given value is None.

    :param value: The value which is tested for nothingness.
    :param message: A message to show in the event of failure.
    """
    #TODO: assert equal with dictionaries, arrays, etc
    if value is None:
        return
    if not message:
        try:
            message = "%s is not None" % value
        except Exception:
            message = "The value is not None."
    raise ASSERTION_ERROR(message)


def assert_is_not(actual, expected, message=None):
    """Asserts that the two variables has different identities.

    :param actual: A variable which has the actual identity.
    :param expected: A variable which has the expected identity.
    :param message: The assertion message if the variables share an identity.
    """
    #TODO: assert equal with dictionaries, arrays, etc
    if actual is not expected:
        return
    if not message:
        try:
            message = "%s is %s" % (actual, expected)
        except Exception:
            message = "The actual value is the expected one."
    raise ASSERTION_ERROR(message)


def assert_is_not_none(value, message=None):
    """Asserts that a value is anything other than None.

    :param value: A variable which is expected to be anything other than None.
    :param message: The assertion message if the variable is None.
    """
    #TODO: assert equal with dictionaries, arrays, etc
    if value is not None:
        return
    if not message:
        message = "The value is None."
    raise ASSERTION_ERROR(message)

def assert_not_equal(actual, expected, message=None):
    """Asserts that the two values are not equal.

    :param actual: The actual value.
    :param expected: The expected value.
    :param message: The assertion message if the variables are equal.
    """
    if (actual != expected) and not (actual == expected):
        return
    if not message:
        try:
            message = "%s == %s" % (actual, expected)
        except Exception:
            message = "The actual value equalled the expected one."
    raise ASSERTION_ERROR(message)


def assert_true(condition, message=None):
    """Asserts that the given value is True.

    :param condition: A value that must be True.
    :param message: The assertion message if the value is not True.
    """
    if not condition:
        if not message:
            message = "Condition was False."
        raise ASSERTION_ERROR(message)


def assert_raises(exception_type, function, *args, **kwargs):
    """Calls function and fails the test if an exception is not raised.

    Unlike nose.Tool's assert_raises or TestCase.assertRaises the given
    exception type must match the exactly: if the raised exception is a
    subclass the test will fail. For example, it fails if the exception_type
    param is "Exception" but "RuntimeException" is raised. To be less demanding
    use assert_raises_instance.

    :param exception_type: The exact type of exception to be raised.
    :param function: The function to call, followed by its arguments.

    """
    actual_exception = compatability.capture_exception(
        lambda : function(*args, **kwargs),
        exception_type)
    if actual_exception is None:
        fail("Expected an exception of type %s to be raised." % exception_type)
    elif type(actual_exception) != exception_type:
        _a, _b, tb = sys.exc_info()
        info = traceback.format_list(traceback.extract_tb(tb))
        fail("Expected a raised exception of type %s, but found type %s. "
            "%s" % (exception_type, type(actual_exception), info))
    return actual_exception


def assert_raises_instance(exception_type, function, *args, **kwargs):
    """Calls function and fails the test if an exception is not raised.

    The exception thrown must only be an instance of the given type. This means
    if "Exception" is expected but "RuntimeException" is raised the test will
    still pass. For a stricter function see assert_raises.

    :param exception_type: The expected exception type.
    :param function: The function to call, followed by its arguments.

    """
    actual_exception = compatability.capture_exception(
        lambda : function(*args, **kwargs),
        exception_type)
    if actual_exception is None:
        fail("Expected an exception of type %s to be raised." % exception_type)


def fail(message):
    """Fails a test.

    :param message: The message to display.

    Unlike the other functions in this module the message argument is required.

    """
    if not message:
        message = "Test failure."
    raise ASSERTION_ERROR(message)


from proboscis.check import Check

__all__ = [
    'assert_equal',
    'assert_false',
    'assert_is',
    'assert_is_none',
    'assert_is_not',
    'assert_is_not_none',
    'assert_not_equal',
    'assert_true',
    'assert_raises',
    'assert_raises_instance',
    'fail',
]
