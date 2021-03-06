# Copyright 2015 Confluent Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ducktape.tests.loader import TestLoader, LoaderException

import tests.ducktape_mock

import os
import os.path
import pytest
import re

from mock import Mock


def discover_dir():
    """Return the absolute path to the directory to use with discovery tests."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "loader_test_directory")


def num_tests_in_file(fpath):
    """Count expected number of tests in the file.
    Search for NUM_TESTS = N

    return N if pattern is present else 0
    """
    with open(fpath, 'r') as fd:
        match = re.search(r'^NUM_TESTS\s*=\s*(\d+)', fd.read(), re.MULTILINE)

        if not match:
            return 0
        return int(match.group(1))


def num_tests_in_dir(dpath):
    """Walk through directory subtree and count up expected number of tests that TestLoader should find."""
    assert os.path.exists(dpath)
    assert os.path.isdir(dpath)

    num_tests = 0
    for pwd, dirs, files in os.walk(dpath):
        for f in files:
            file_path = os.path.abspath(os.path.join(pwd, f))
            num_tests += num_tests_in_file(file_path)
    return num_tests


class CheckTestLoader(object):
    def setup_method(self, method):
        self.SESSION_CONTEXT = tests.ducktape_mock.session_context()

    def check_test_loader_with_directory(self):
        """Check discovery on a directory."""
        loader = TestLoader(self.SESSION_CONTEXT, logger=Mock())
        tests = loader.load([discover_dir()])
        assert len(tests) == num_tests_in_dir(discover_dir())

    def check_test_loader_with_file(self):
        """Check discovery on a file. """
        loader = TestLoader(self.SESSION_CONTEXT, logger=Mock())
        module_path = os.path.join(discover_dir(), "test_a.py")

        tests = loader.load([module_path])
        assert len(tests) == num_tests_in_file(module_path)

    def check_test_loader_multiple_files(self):
        loader = TestLoader(self.SESSION_CONTEXT, logger=Mock())
        file_a = os.path.join(discover_dir(), "test_a.py")
        file_b = os.path.join(discover_dir(), "test_b.py")

        tests = loader.load([file_a, file_b])
        assert len(tests) == num_tests_in_file(file_a) + num_tests_in_file(file_b)

    def check_test_loader_with_nonexistent_file(self):
        """Check discovery on a non-existent path should throw LoaderException"""
        with pytest.raises(LoaderException):
            loader = TestLoader(self.SESSION_CONTEXT, logger=Mock())
            tests = loader.load([os.path.join(discover_dir(), "file_that_does_not_exist.py")])

    def check_test_loader_with_class(self):
        """Check test discovery with discover class syntax."""
        loader = TestLoader(self.SESSION_CONTEXT, logger=Mock())
        tests = loader.load([os.path.join(discover_dir(), "test_b.py::TestBB")])
        assert len(tests) == 2

        # Sanity check, test that it discovers two test class & 3 tests if it searches the whole module
        tests = loader.load([os.path.join(discover_dir(), "test_b.py")])
        assert len(tests) == 3

    def check_test_loader_with_injected_args(self):
        """When the --parameters command-line option is used, the loader behaves a little bit differently:

        each test method annotated with @parametrize or @matrix should only expand to a single discovered test,
        and the injected args should be those passed in from command-line.
        """
        parameters = {"x": 1, "y": -1}
        loader = TestLoader(self.SESSION_CONTEXT, logger=Mock(), injected_args=parameters)

        file = os.path.join(discover_dir(), "test_decorated.py")
        tests = loader.load([file])
        assert len(tests) == 4

        for t in tests:
            assert t.injected_args == parameters


def join_parsed_symbol_components(parsed):
    """
    Join together a parsed symbol

    e.g.
        {
            'dir': 'path/to/dir',
            'file': 'test_file.py',
            'cls': 'ClassName',
            'method': 'method'
        },
        ->
        'path/to/dir/test_file.py::ClassName.method'
    """
    symbol = os.path.join(parsed['dir'], parsed['file'])

    if parsed['cls'] or parsed['method']:
        symbol += "::"
        symbol += parsed['cls']
        if parsed['method']:
            symbol += "."
            symbol += parsed['method']

    return symbol


def normalize_ending_slash(dirname):
    if dirname.endswith(os.path.sep):
        dirname = dirname[:-len(os.path.sep)]
    return dirname


class CheckParseSymbol(object):
    def check_parse_discovery_symbol(self):
        """Check that "test discovery symbol" parsing logic works correctly"""
        parsed_symbols = [
            {
                'dir': 'path/to/dir',
                'file': '',
                'cls': '',
                'method': ''
            },
            {
                'dir': 'path/to/dir',
                'file': 'test_file.py',
                'cls': '',
                'method': ''
            },
            {
                'dir': 'path/to/dir',
                'file': 'test_file.py',
                'cls': 'ClassName',
                'method': ''
            },
            {
                'dir': 'path/to/dir',
                'file': 'test_file.py',
                'cls': 'ClassName',
                'method': 'method'
            },
            {
                'dir': 'path/to/dir',
                'file': '',
                'cls': 'ClassName',
                'method': ''
            },
        ]

        loader = TestLoader(tests.ducktape_mock.session_context(), logger=Mock())
        for parsed in parsed_symbols:
            symbol = join_parsed_symbol_components(parsed)

            expected_parsed = (
                normalize_ending_slash(parsed['dir']),
                parsed['file'],
                parsed['cls'],
                parsed['method']
            )

            actually_parsed = loader._parse_discovery_symbol(symbol)
            actually_parsed = (
                normalize_ending_slash(actually_parsed[0]),
                actually_parsed[1],
                actually_parsed[2],
                actually_parsed[3]
            )

            assert actually_parsed == expected_parsed, "%s did not parse as expected" % symbol





