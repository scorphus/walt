#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>


from walt import config
from walt import logger
from walt.argparser import action
from walt.argparser import ActionArgParser

import logging
import os


def walt():  # pragma: no cover
    """Entry point for command line tool ``walt``.

    :Usage:

    .. code-block:: text

        $ walt [-c config.toml] <action>

    """
    set_verbosity(ActionArgParser.args.verbose)
    if ActionArgParser.args.help:
        ActionArgParser.print_help()
    elif ActionArgParser.args.version:
        ActionArgParser.print_version()
    elif ActionArgParser.args.action:
        if not ActionArgParser.requires_config:
            return ActionArgParser.run_action()
        if not ActionArgParser.args.config:
            logger.fatal("Cannot proceed with no config file")
            exit(1)
        cfg = config.load(ActionArgParser.args.config)
        config.override_from(cfg, os.environ)
        set_verbosity(level_name=cfg.get("log_level"))
        return ActionArgParser.run_action(cfg)
    else:
        ActionArgParser.print_usage()


def set_verbosity(verbose=False, level_name=""):  # pragma: no cover
    level = level_name and getattr(logging, level_name.upper())
    if level:
        logger.setLevel(level)
    elif verbose:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)


@action
def hello(cfg):
    print("Hello from walt!")
    print(f"Config is: {cfg}")