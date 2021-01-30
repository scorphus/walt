#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

from walt.main import hello

import pytest


@pytest.mark.parametrize("cfg", [None, {}, {"foo": "bar"}])
def test_hello(cfg, capsys):
    hello(cfg)
    captured = capsys.readouterr()
    assert "Hello from walt!" in captured.out
    assert f"Config is: {cfg}" in captured.out
