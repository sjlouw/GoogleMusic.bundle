# Copyright (c) 2012 Rackspace
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

"""Like asserts, but does not raise an exception until the end of a block."""

import traceback
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_is
from proboscis.asserts import assert_is_not
from proboscis.asserts import assert_is_not_none
from proboscis.asserts import assert_false
from proboscis.asserts import assert_true
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_raises_instance
from proboscis.asserts import assert_is_none
from proboscis.asserts import ASSERTION_ERROR
from proboscis.compatability import capture_exception
from proboscis.compatability import raise_with_traceback
from proboscis.asserts import fail


def get_stack_trace_of_caller(level_up):
    """Gets the stack trace at the point of the caller."""
    level_up += 1
    st = traceback.extract_stack()
    caller_index = len(st) - level_up
    if caller_index < 0:
        caller_index = 0
    new_st = st[0:caller_index]
    return new_st


class Check(object):
    """Used to test and record multiple failing asserts in a single function.

    Usually its best to write numerous small methods with a single assert in
    each one, but sometimes this ideal isn't possible and multiple asserts
    must be made in the same function.

    In some cases, such as when all properties of a returned object are being
    interrogated, these asserts do not depend on each other and having the test
    stop after the first one can be a bother if the task was run on a CI
    server or somewhere else.

    This class solves that by saving any assert failures and raising one giant
    assert at the end of a with block.

    To use it, write something like:

    .. code-block:: python

        some_obj = ...
        with Check() as check:
            check.equal(some_obj.a, "A")
            check.equal(some_obj.b, "B")
            check.equal(some_obj.c, "C")

    At the end of the with block if any checks failed one assertion will be
    raised containing inside it the stack traces for each assertion.

    If instances are not used in a with block any failed assert will
    raise instantly.
    """

    def __init__(self):
        self.messages = []
        self.odd = True
        self.protected = False

    def _add_exception(self, _type, value, tb):
        """Takes an exception, and adds it as a string."""
        if self.odd:
            prefix = "* "
        else:
            prefix = "- "
        start = "Check failure! Traceback:"
        middle = prefix.join(traceback.format_list(tb))
        end = '\n'.join(traceback.format_exception_only(_type, value))
        msg = '\n'.join([start, middle, end])
        self.messages.append(msg)
        self.odd = not self.odd

    def _run_assertion(self, assert_func, *args, **kwargs):
        """
        Runs an assertion method, but catches any failure and adds it as a
        string to the messages list.
        """
        if self.protected:
            def func():
                assert_func(*args, **kwargs)
            ae = capture_exception(func, ASSERTION_ERROR)
            if ae is not None:
                st = get_stack_trace_of_caller(2)
                self._add_exception(ASSERTION_ERROR, ae, st)
        else:
            assert_func(*args, **kwargs)

    def __enter__(self):
        self.protected = True
        return self

    def __exit__(self, _type, value, tb):
        self.protected = False
        if len(self.messages) == 0:
            final_message = None
        else:
            final_message = '\n'.join(self.messages)
        if _type is not None:  # An error occurred
            if len(self.messages) == 0:
                raise_with_traceback(_type, value, tb)
            self._add_exception(_type, value, traceback.extract_tb(tb))
        if len(self.messages) != 0:
            final_message = '\n'.join(self.messages)
            raise ASSERTION_ERROR(final_message)


def add_assert_method(name, func):
    def f(self, *args, **kwargs):
        self._run_assertion(func, *args, **kwargs)
    f.__doc__ = "Identical to %s." % func.__name__
    setattr(Check, name, f)

add_assert_method("equal", assert_equal)
add_assert_method("not_equal", assert_not_equal)
add_assert_method("false", assert_false)
add_assert_method("true", assert_true)
add_assert_method("is_same", assert_is)
add_assert_method("is_none", assert_is_none)
add_assert_method("is_not", assert_is_not)
add_assert_method("is_not_none", assert_is_not_none)
add_assert_method("raises", assert_raises)
add_assert_method("raises_instance", assert_raises_instance)
add_assert_method("fail", fail)
