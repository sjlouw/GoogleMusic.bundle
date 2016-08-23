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

import inspect
import sys
import types

if sys.version_info >= (2, 6):
    from proboscis.compatability.exceptions_2_6 import capture_exception
    from proboscis.compatability.exceptions_2_6 import capture_type_error
else:
    from proboscis.compatability.exceptions_2_5 import capture_exception
    from proboscis.compatability.exceptions_2_5 import capture_type_error


if sys.version_info >= (3, 0):
    import imp
    reload = imp.reload
    from proboscis.compatability.raise_3_x import raise_with_traceback

    def get_class_methods(cls):
        members = inspect.getmembers(cls, inspect.isfunction)
        return [member[1] for member in members]

    def get_method_function(method):
        return method


else:
    reload = reload
    from proboscis.compatability.raise_2_x import raise_with_traceback

    def get_class_methods(cls):
        members = inspect.getmembers(cls, inspect.ismethod)
        return [member[1] for member in members]

    def get_method_function(method):
        return method.im_func


_IS_JYTHON = "Java" in str(sys.version) or hasattr(sys, 'JYTHON_JAR')

def is_jython():
    return _IS_JYTHON


def supports_time_out():
    if is_jython():
        return False
    try:
        import signal
        return True
    except ImportError:
        return False
