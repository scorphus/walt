#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

"""main contains the `walt` entry point along with main actions"""

import logging
import os
import sys

from walt import config
from walt import logger
from walt.action_runners import Consumer
from walt.action_runners import Producer
from walt.argparser import ActionArgParser
from walt.argparser import action
from walt.result import ResultSerde
from walt.storages import PostgresResultStorage


def walt():  # pragma: no cover
    """Entry point for command line tool ``walt``.

    :Usage:

    .. code-block:: text

        $ walt [-c config.toml] <action>
        $ walt -c config.toml produce  # to start a producer

    """
    set_verbosity(ActionArgParser.args.verbose)
    if ActionArgParser.args.help:
        ActionArgParser.print_help()
    elif ActionArgParser.args.version:
        ActionArgParser.print_version()
    elif ActionArgParser.args.action:
        if not ActionArgParser.requires_config:
            ActionArgParser.run_action()
        elif not ActionArgParser.args.config:
            logger.fatal("Cannot proceed with no config file")
            sys.exit(1)
        else:
            cfg = config.load(ActionArgParser.args.config)
            config.override_from(cfg, os.environ)
            set_verbosity(level_name=cfg.get("log_level"))
            ActionArgParser.run_action(cfg)
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
def create_database(cfg):
    storage = PostgresResultStorage(**cfg["postgres"])
    storage.create_database()


@action
def create_tables(cfg):
    storage = PostgresResultStorage(**cfg["postgres"])
    storage.create_tables()


@action
def drop_database(cfg):
    storage = PostgresResultStorage(**cfg["postgres"])
    storage.drop_database()


@action
def drop_tables(cfg):
    storage = PostgresResultStorage(**cfg["postgres"])
    storage.drop_tables()


@action
def produce(cfg):
    producer = Producer(cfg)
    producer.run()


@action
def consume(cfg):
    storage = PostgresResultStorage(**cfg["postgres"])
    consumer = Consumer(cfg, storage, ResultSerde)
    consumer.run()
