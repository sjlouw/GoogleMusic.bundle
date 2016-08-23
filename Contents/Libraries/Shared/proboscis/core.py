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
"""Contains Proboscis-centric concepts."""


import inspect
import types
import unittest


from proboscis import compatability

class ProboscisTestMethodClassNotDecorated(Exception):
    """

    This denotes a very common error that seems somewhat unavoidable due to
    the fact it isn't possible to know if a method is bound or not in Python
    when you decorate it.

    """

    def __init__(self):
        super(Exception, self).__init__(self,
            "Proboscis attempted to run what looks like a bound method "
            "requiring a self argument as a free-standing function. Did you "
            "forget to put a @test decorator on the method's class?")


class TestGroup(object):
    """Represents a group of tests.

    Think of test groups as tags on a blog.  A test case may belong to multiple
    groups, and one group may have multiple test cases.

    """
    def __init__(self, name):
        self.name = name
        self.entries = []

    def add_entry(self, entry):
        """Adds a TestEntry to this group."""
        self.entries.append(entry)


def transform_depends_on_target(target):
    if isinstance(target, types.MethodType):
        return compatability.get_method_function(target)
    else:
        return target


class TestEntryInfo:
    """Represents metadata attached to some kind of test code."""

    def __init__(self,
                 groups=None,
                 depends_on=None,
                 depends_on_classes=None,
                 depends_on_groups=None,
                 enabled=None,
                 always_run=False,
                 runs_after_groups=None,
                 runs_after=None,
                 run_before_class=False,
                 run_after_class=False):
        groups = groups or []
        depends_on_list = depends_on or []
        depends_on_classes = depends_on_classes or []
        depends_on_groups = depends_on_groups or []
        runs_after = runs_after or []
        runs_after_groups = runs_after_groups or []
        self.groups = groups
        self.depends_on = set(transform_depends_on_target(target)
                              for target in depends_on_list)
        for cls in depends_on_classes:
            self.depends_on.add(cls)
        self.runs_after_groups = runs_after_groups
        self.depends_on_groups = depends_on_groups
        self.enabled_was_specified = enabled is not None
        if enabled is None:
            enabled = True
        self.enabled = enabled
        self.always_run = always_run
        self.inherit_groups = False
        self.before_class = run_before_class
        self.after_class = run_after_class
        self.runs_after = set(transform_depends_on_target(target)
                              for target in runs_after)

        if run_before_class and run_after_class:
            raise RuntimeError("It is illegal to set 'before_class' and "
                               "'after_class' to True.")

    def inherit(self, parent_entry):
        """The main use case is a method inheriting from a class decorator.

        Returns the groups this entry was added to.

        """
        added_groups = []
        for group in parent_entry.groups:
            if group not in self.groups:
                self.groups.append(group)
                added_groups.append(group)
        for item in parent_entry.depends_on_groups:
            if item not in self.depends_on_groups:
                self.depends_on_groups.append(item)
        for item in parent_entry.depends_on:
            if item not in self.depends_on:
                self.depends_on.add(item)
        for item in parent_entry.runs_after:
            if item not in self.runs_after:
                self.runs_after.add(item)
        for item in parent_entry.runs_after_groups:
            if item not in self.runs_after_groups:
                self.runs_after_groups.append(item)
        if parent_entry.enabled_was_specified and \
            not self.enabled_was_specified:
            self.enabled = parent_entry.enabled
        if parent_entry.always_run:
            self.always_run = True
        return added_groups

    def __repr__(self):
        return "TestEntryInfo(groups=" + str(self.groups) + \
               ", depends_on=" + str(self.depends_on) + \
               ", depends_on_groups=" + str(self.depends_on_groups) + \
               ", enabled=" + str(self.enabled) + \
               ", runs_after=" + str(self.runs_after) + ")"

    def __str__(self):
        return "groups = [" + ",".join(self.groups) + ']' \
               ", enabled = " + str(self.enabled) + \
               ", depends_on_groups = " + str(self.depends_on_groups) + \
               ", depends_on = " + str(self.depends_on) + \
               ", runs_after = " + str(self.runs_after)


class TestEntry(object):
    """Represents a function, method, or unittest.TestCase and its info."""

    def __init__(self, home, info):
        self.home = home
        self.homes = set([home])
        self.info = info
        self.__method_cls = None
        self.__method = None
        self.__used_by_factory = False
        for dep_list in (self.info.depends_on, self.info.runs_after):
            for dep in dep_list:
                if dep is self.home:
                    raise RuntimeError("TestEntry depends on its own class:" +
                                       str(self))
        for dependency_group in self.info.depends_on_groups:
            for my_group in self.info.groups:
                if my_group == dependency_group:
                    raise RuntimeError("TestEntry depends on a group it " \
                                       "itself belongs to: " + str(self))


    def contains(self, group_names, classes):
        """True if this belongs to any of the given groups or classes."""
        for group_name in group_names:
            if group_name in self.info.groups:
                return True
        for cls in classes:
            if cls == self.home:
                return True
        if hasattr(self, 'parent'):
            return self.parent.contains_shallow(group_names, classes)
        return False

    @property
    def is_child(self):
        """True if this entry nests under a class (is a method)."""
        return self.__method is not None

    def mark_as_child(self, method, cls):
        """Marks this as a child so it won't be iterated as a top-level item.

        Needed for TestMethods. In Python we decorate functions, not methods,
        as the decorator doesn't know if a function is a method until later.
        So we end up storing entries in the Registry's list, but may only
        want to iterate through these from the parent onward. Finding each item
        in the list would be a waste of time, so instead we just mark them
        as such and ignore them during iteration.

        """
        self.__method = method
        self.__method_cls = cls
        self.homes = set([self.home, cls])

    def mark_as_used_by_factory(self):
        """If a Factory returns an instance of a class, the class will not
        also be run by Proboscis the usual way (only factory created instances
        will run).
        """
        self.__used_by_factory = True

    @property
    def method(self):
        """Returns the method represented by this test, if any.

        If this is not None, the underlying function will be the same as 'home'.

        """
        return self.__method

    @property
    def used_by_factory(self):
        """True if instances of this are returned by a @factory."""
        return self.__used_by_factory

    def __repr__(self):
        return "TestEntry(" + repr(self.home) + ", " + \
               repr(self.info) + ", " + object.__repr__(self) + ")"

    def __str__(self):
        return "Home = " + str(self.home) + ", Info(" + str(self.info) + ")"


class TestMethodClassEntry(TestEntry):
    """A special kind of entry which references a class and a list of entries.

    The class is the class which owns the test methods, and the entries are
    the entries for those methods.

    """

    def __init__(self, home, info, children):
        super(TestMethodClassEntry, self).__init__(home, info)
        self.children = children
        for child in self.children:
            child.parent = self

    def contains(self, group_names, classes):
        """True if this belongs to any of the given groups or classes."""
        if self.contains_shallow(group_names, classes):
            return True
        for entry in self.children:
            if entry.contains(group_names, []):
                return True
        return False

    def contains_shallow(self, group_names, classes):
        return super(TestMethodClassEntry, self).contains(group_names, classes)


class TestRegistry(object):
    """Stores test information.

    All of Proboscis's decorators (@test, @before_class, etc) and the register
    function use a default instance of this class, however its also possible to
    instantiate multiple copies and add tests to them directly.
    """
    def __init__(self):
        self.reset()

    def _change_function_to_method(self, method, cls, cls_info):
        """Add an entry to a method by altering its function entry."""
        function = compatability.get_method_function(method)
        method_entry = function._proboscis_entry_
        method_entry.mark_as_child(method, cls)
        new_groups = method_entry.info.inherit(cls_info)
        for group_name in new_groups:
            group = self.get_group(group_name)
            group.add_entry(method_entry)
        return method_entry

    def ensure_group_exists(self, group_name):
        """Adds the group to the registry if it does not exist.

        :param group_name: The group to create.
        """
        if not group_name in self.groups:
            self.groups[group_name] = TestGroup(group_name)

    def get_group(self, group_name):
        """Returns a TestGroup given its name.

        :param group_name: Group to return.
        """
        self.ensure_group_exists(group_name)
        return self.groups[group_name]

    @staticmethod
    def _mark_home_with_entry(entry):
        """Store the entry inside the function or class it represents.

        This way, non-unittest.TestCase classes can later find information on
        the methods they own, and so that info can be discovered for the
        instances returned by factories.

        """
        if entry.home is not None:
            if hasattr(entry.home, '_proboscis_entry_'):
                # subclasses will get this attribute from their parents.
                # This if statement is necessary because factories may create
                # multiple entries per test method.
                if entry.home._proboscis_entry_.home == entry.home:
                    raise RuntimeError("A test decorator or registration was "
                        "applied twice to the class or function %s." %
                        entry.home)
            # Assign reference so factories can discover it using an instance.
            entry.home._proboscis_entry_ = entry

    def register(self, test_home=None, **kwargs):
        """Registers a bit of code (or nothing) to be run / ordered as a test.

        Registering a test with nothing allows for the creation of groups of
        groups, which can be useful for organization.

        When proboscis.register is called it chains to this method bound to the
        global default registry.

        """
        info = TestEntryInfo(**kwargs)
        if test_home is None:
            return self._register_empty_test_case(info)
        elif isinstance(test_home, types.FunctionType):
            return self._register_func(test_home, info)
        elif issubclass(test_home, unittest.TestCase):
            return self._register_unittest_test_case(test_home, info)
        else:
            return self._register_test_class(test_home, info)

    def register_factory(self, func):
        """Turns a function into a Proboscis test instance factory.

        A factory returns a list of test class instances. Proboscis runs all
        factories at start up and sorts the instances like normal tests.

        :param func: the function to be added.
        """
        self.factories.append(func)

    def _register_empty_test_case(self, info):
        """Registers an 'empty' test."""
        self._register_simple_entry(None, info)
        return None

    def _register_unittest_test_case(self, test_cls, info):
        """Registers a unittest.TestCase."""
        entry = self._register_simple_entry(test_cls, info)
        return entry.home

    def _register_func(self, func, info):
        """Registers a function."""
        entry = self._register_simple_entry(func, info)
        return entry.home

    def _register_entry(self, entry):
        """Adds an entry to this Registry's list and may also create groups."""
        info = entry.info
        for group_name in info.groups:
            group = self.get_group(group_name)
            group.add_entry(entry)
        for group_name in info.depends_on_groups:
            self.ensure_group_exists(group_name)
        if entry.home:
            if not entry.home in self.classes:
                self.classes[entry.home] = []
            self.classes[entry.home].append(entry)
            self._mark_home_with_entry(entry)
        self.tests.append(entry)

    def _register_simple_entry(self, test_home, info):
        """Registers a unitttest style test entry."""
        entry = TestEntry(test_home, info)
        self._register_entry(entry)
        return entry

    def _register_test_class(self, cls, info):
        """Registers the methods within a class."""
        test_entries = []
        methods = compatability.get_class_methods(cls)
        before_class_methods = []
        after_class_methods = []
        for method in methods:
            func = compatability.get_method_function(method)
            if hasattr(func, "_proboscis_entry_"):
                entry = self._change_function_to_method(method, cls, info)
                test_entries.append(entry)
                if entry.info.before_class:
                    before_class_methods.append(entry)
                elif entry.info.after_class:
                    after_class_methods.append(entry)
        for before_entry in before_class_methods:
            for test_entry in test_entries:
                if not test_entry.info.before_class:
                    test_entry.info.depends_on.add(before_entry.home)
        for after_entry in after_class_methods:
            for test_entry in test_entries:
                if not test_entry.info.after_class:
                    after_entry.info.depends_on.add(test_entry.home)
        entry = TestMethodClassEntry(cls, info, test_entries)
        self._register_entry(entry)
        return entry.home

    def reset(self):
        """Wipes the registry."""
        self.tests = []
        self.groups = {}
        self.classes = {}
        self.factories = []
