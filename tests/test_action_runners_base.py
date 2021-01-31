#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

from unittest.mock import AsyncMock
from walt.action_runners import ActionRunnerBase

import asyncio
import os
import pytest
import signal


class ActionRunnerBaseTester(ActionRunnerBase):
    async def _run_action(self):
        for task in self.tasks:
            try:
                self._create_task(*task)
            except TypeError:
                self._create_task(task)
        await super()._run_action()

    def register_tasks(self, tasks):
        self.tasks = tasks


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


def test_action_runner_finishes_on_tasks_cancellation(action_runner, mocker):
    async def side_effect():
        for task in asyncio.all_tasks():
            task.cancel()
        await asyncio.sleep(1e3)

    logger_mock = mocker.patch("walt.action_runners.logger")
    task = AsyncMock(side_effect=side_effect)
    action_runner.register_tasks([task])
    action_runner.run()
    logger_mock.info.assert_called_once()
