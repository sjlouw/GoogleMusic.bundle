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

"""Extension for Nose to facilitate higher level testing.

Changes how tests are discovered by forcing them to use a common decorator
which contains useful metadata such as whether or not they have dependencies
on other tests.  This allows larger processes or stories to be modelled and
run as tests.  Much of this functionality was "inspired" by TestNG.

"""



from proboscis.core import ProboscisTestMethodClassNotDecorated
from proboscis.dependencies import SkipTest
from proboscis.case import TestPlan
from proboscis.case import TestProgram
from proboscis.core import TestRegistry
from proboscis.decorators import after_class
from proboscis.decorators import before_class
from proboscis.decorators import factory
from proboscis.decorators import register
from proboscis.decorators import test
from proboscis.case import TestResult
