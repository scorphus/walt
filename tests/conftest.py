#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import os
import pytest


@pytest.fixture(autouse=True, scope="session")
def _shut_logger(session_mocker):
    if os.getenv("SHUT_LOGGER", None):
        return session_mocker.patch("walt.action_runners.logger")


@pytest.fixture
def logger_mock(mocker):
    logger_mock = MagicMock()
    mocker.patch("walt.logger", logger_mock)
    mocker.patch("walt.action_runners.logger", logger_mock)
    mocker.patch("walt.storages.logger", logger_mock)
    return logger_mock


@pytest.fixture
def async_magic_mock():
    def _async_magic_mock():
        ctx_mock = MagicMock()
        ctx_mock.__aenter__.return_value = AsyncMock()
        ctx_mock.__aexit__.return_value = AsyncMock()
        return ctx_mock

    return _async_magic_mock


@pytest.fixture
def resp_text_mock():
    return AsyncMock()


@pytest.fixture
def client_session_get_mock(async_magic_mock, resp_text_mock):
    get_mock = async_magic_mock()
    get_mock.return_value.__aenter__.return_value.text = resp_text_mock
    return get_mock


@pytest.fixture
def client_session_mock(mocker, async_magic_mock, client_session_get_mock):
    client_session_mock = async_magic_mock()
    client_session_mock.return_value.__aenter__.return_value.get = client_session_get_mock
    mocker.patch("walt.action_runners.aiohttp.ClientSession", client_session_mock)
    return client_session_mock


@pytest.fixture
def kafka_producer_mock(mocker):
    return mocker.patch("walt.action_runners.aiokafka.AIOKafkaProducer", return_value=AsyncMock())


@pytest.fixture
def kafka_consumer_mock(mocker):
    return mocker.patch("walt.action_runners.aiokafka.AIOKafkaConsumer", return_value=AsyncMock())
