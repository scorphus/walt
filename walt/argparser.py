#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

from argparse import ArgumentParser
from argparse import FileType
from walt import __version__

import inspect
import sys


class PropertyMetaClass(type):
    """PropertyMetaClass provides classes with three "class properties". Since
    Python 3.9, such metaclass is unnecessary as the `classmethod` decorator can
    then wrap other descriptors such as property objects. Check the following
    bug description for more: https://bugs.python.org/issue19072"""

    @property
    def args(self):
        return self._args_property()

    @property
    def parser(self):
        return self._parser_property()

    @property
    def requires_config(self):
        return self._requires_config_property()


class ActionArgParser(metaclass=PropertyMetaClass):
    """ActionArgParser parses arguments for apps composed of a set of actions,
    optionally configured with a configuration file"""

    _args = None
    _parser = None
    _actions = {}
    _req_cfg = False

    @classmethod
    def _args_property(cls):
        if not cls._args:
            cls._args = cls.parser.parse_args()
            cls._req_cfg = cls._actions.get(cls._args.action, (None, cls._req_cfg))[1]
        return cls._args

    @classmethod
    def _parser_property(cls):
        if not cls._parser:
            cls._parser = ArgumentParser(
                prog="walt",
                description="walt - Website Availability Monitor",
                add_help=False,
            )
            cls._parser.add_argument(
                "-c", "--config", type=FileType("r"), help="path to configuration file"
            )
            cls._parser.add_argument(
                "-v", "--verbose", action="store_true", help="activate verbose mode"
            )
            cls._parser.add_argument(
                "-V", "--version", action="store_true", help="display program version"
            )
            cls._parser.add_argument(
                "-h", "--help", action="store_true", help="display this help message"
            )
            if cls._actions:
                cls._parser.add_argument(
                    "action",
                    nargs="?",
                    help="the action to be performed",
                    type=str,
                    choices=cls._actions,
                )
        return cls._parser

    @classmethod
    def _requires_config_property(cls):
        return cls.args and cls._req_cfg

    @classmethod
    def print_help(cls):
        cls.parser.print_help(sys.stderr)

    @classmethod
    def print_usage(cls):
        cls.parser.print_usage(sys.stderr)

    @classmethod
    def print_version(cls):
        sys.stderr.write(f"walt {__version__}")

    @classmethod
    def run_action(cls, *args, **kwargs):
        return cls._actions[cls.args.action][0](*args, **kwargs)

    @staticmethod
    def __new__(cls, f):
        cls._actions[f.__name__] = (f, "cfg" in inspect.getfullargspec(f).args)
        return f


action = ActionArgParser
