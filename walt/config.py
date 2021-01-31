#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

from copy import deepcopy
from walt import logger
from walt.argparser import action

import os
import toml


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

CONFIG = {
    "log_level": LOG_LEVEL,
}


def load(config_toml):
    """load returns CONFIG updated with values loaded from a TOML file"""
    cfg = deepcopy(CONFIG)
    if not config_toml:
        return cfg
    file_name = getattr(config_toml, "name", config_toml)
    try:
        logger.info("[config] loading from %s", file_name)
        deep_update(cfg, toml.load(config_toml))
    except Exception as e:
        logger.error("[config] could not load from %s: %s", file_name, e)
    return cfg


def deep_update(cfg, other):
    """deep_update recursively mutates `cfg`, copying items from `other`,
    recursing when both values are dictionaries and overriding otherwise"""
    for key in other.keys():
        if (
            isinstance(other[key], dict)
            and key in cfg
            and isinstance(cfg[key], dict)
            and not key.endswith("_map")
        ):
            deep_update(cfg[key], other[key])
        else:
            cfg[key] = other[key]
    return cfg


def override_from(cfg, recipient, namespace="walt"):
    """override_from iterates over `cfg` and looks for respective keys in
    `recipient`. If a key exists, it's value is overridden on `cfg`"""
    for key, value in cfg.items():
        if key.endswith("_list") or key.endswith("_map"):
            continue
        var_name = namespace + "_" + key
        if isinstance(value, dict):
            cfg[key] = override_from(value, recipient, var_name)
        else:
            cfg[key] = recipient.get(var_name.upper(), value)
    return cfg


@action
def generate_config_sample():
    print(toml.dumps(CONFIG), end="")