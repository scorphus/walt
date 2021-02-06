#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

from walt import main

import pytest


@pytest.fixture
def cfg():
    return {"postgres": {"so": "arg"}}


@pytest.fixture
def pg_res_storage(mocker):
    return mocker.patch("walt.main.PostgresResultStorage")


def test_setup_database(cfg, pg_res_storage):
    main.setup_database(cfg)
    pg_res_storage.assert_called_once_with(so="arg")
    pg_res_storage.return_value.setup_database.assert_called_once_with()


def test_teardown_database(cfg, pg_res_storage):
    main.teardown_database(cfg)
    pg_res_storage.assert_called_once_with(so="arg")
    pg_res_storage.return_value.teardown_database.assert_called_once_with()


def test_produce(cfg, mocker):
    producer = mocker.patch("walt.main.Producer")
    main.produce(cfg)
    producer.assert_called_once_with(cfg)
    producer.return_value.run.assert_called_once_with()


def test_consume(cfg, pg_res_storage, mocker):
    consumer = mocker.patch("walt.main.Consumer")
    serde = mocker.patch("walt.main.ResultSerde")
    main.consume(cfg)
    pg_res_storage.assert_called_once_with(so="arg")
    consumer.assert_called_once_with(cfg, pg_res_storage.return_value, serde)
    consumer.return_value.run.assert_called_once_with()
    assert pg_res_storage.return_value.method_calls == []
