#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

import asyncio
import os
import signal
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

from tests.base import ActionRunnerBaseTester
from walt.action_runners import KafkaSSLConnector


@pytest.fixture
def action_runner():
    return ActionRunnerBaseTester()


def test_action_runner_runs_a_single_task(action_runner):
    task = AsyncMock()
    action_runner.register_tasks([task])
    action_runner.run()
    task.assert_awaited_once_with()


def test_action_runner_runs_a_task_with_args(action_runner):
    task = AsyncMock()
    action_runner.register_tasks([(task, ("much", "args"))])
    action_runner.run()
    task.assert_awaited_once_with("much", "args")


def test_action_runner_runs_a_task_with_kwargs(action_runner):
    task = AsyncMock()
    action_runner.register_tasks([(task, (), {"wow": "keyword", "many": "args"})])
    action_runner.run()
    task.assert_awaited_once_with(wow="keyword", many="args")


def test_action_runner_runs_a_task_with_args_and_kwargs(action_runner):
    task = AsyncMock()
    action_runner.register_tasks([(task, ("much", "args"), {"wow": "keyword", "many": "args"})])
    action_runner.run()
    task.assert_awaited_once_with("much", "args", wow="keyword", many="args")


def test_action_runner_runs_concurrent_tasks(action_runner):
    tasks = [AsyncMock() for _ in range(10)]
    action_runner.register_tasks(tasks)
    action_runner.run()
    for task in tasks:
        task.assert_awaited_once_with()


def test_action_runner_supports_counting(action_runner):
    async def side_effect(self):
        await self._incr_counter()

    task = AsyncMock(side_effect=side_effect)
    action_runner.register_tasks([(task, [action_runner])])
    action_runner.run()
    assert action_runner._counter == 1


def test_action_runner_supports_concurrent_counts(action_runner):
    async def side_effect(self):
        await self._incr_counter()

    tasks = [AsyncMock(side_effect=side_effect) for _ in range(10)]
    action_runner.register_tasks(zip(tasks, [[action_runner]] * 10))
    action_runner.run()
    assert action_runner._counter == 10


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_action_runner_finishes_on_signals(signum, action_runner):
    async def side_effect():
        os.kill(os.getpid(), signum)
        await asyncio.sleep(1e3)

    task = AsyncMock(side_effect=side_effect)
    action_runner.register_tasks([task])
    action_runner.run()


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_action_runner_finishes_on_signals_when_no_tasks(signum, action_runner):
    async def side_effect(self):
        self._tasks = []
        os.kill(os.getpid(), signum)
        await asyncio.sleep(1e3)

    task = AsyncMock(side_effect=side_effect)
    action_runner.register_tasks([(task, [action_runner])])
    action_runner.run()


def test_action_runner_finishes_on_tasks_cancellation(action_runner, logger_mock):
    async def side_effect():
        for task in asyncio.all_tasks():
            task.cancel()
        await asyncio.sleep(1e3)

    task = AsyncMock(side_effect=side_effect)
    action_runner.register_tasks([task])
    action_runner.run()
    logger_mock.info.assert_called_once()


@pytest.fixture
def aiokafka_helpers_mock(mocker):
    return mocker.patch("walt.action_runners.aiokafka.helpers")


def test_kafka_ssl_context_connector_returns_dict_with_protocol_and_context(aiokafka_helpers_mock):
    cfg_mock = MagicMock()
    arguments = KafkaSSLConnector(cfg_mock)._ssl_arguments
    assert arguments["security_protocol"] == "SSL"
    assert arguments["ssl_context"] == aiokafka_helpers_mock.create_ssl_context.return_value
    aiokafka_helpers_mock.create_ssl_context.assert_called_once_with(
        cafile=cfg_mock["kafka"]["cafile"],
        certfile=cfg_mock["kafka"]["certfile"],
        keyfile=cfg_mock["kafka"]["keyfile"],
    )


def test_kafka_ssl_context_connector_returns_empty_dict(aiokafka_helpers_mock):
    cfg_kafka = {"cafile": "", "certfile": "", "keyfile": ""}
    assert KafkaSSLConnector({"kafka": cfg_kafka})._ssl_arguments == {}
    aiokafka_helpers_mock.create_ssl_context.assert_not_called()
