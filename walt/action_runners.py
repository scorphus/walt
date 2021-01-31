#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

from walt import logger

import asyncio
import signal


class ActionRunnerBase:
    """ActionRunnerBase is a base class for action runners"""

    def __init__(self):
        self._loop = asyncio.get_event_loop()
        self._tasks = []
        for signum in (signal.SIGINT, signal.SIGTERM):
            self._loop.add_signal_handler(signum, self._sigint_handler)
        self._counter, self._counter_lock = 0, asyncio.Lock()

    def _sigint_handler(self):
        logger.info("Stopping %s", self.__class__.__name__)
        self._shutdown()

    def _shutdown(self):
        logger.debug("Stopping %s tasks", len(self._tasks))
        for t in self._tasks:
            t.cancel()
        if not self._tasks:
            logger.debug("Stopping remaining tasks")
            for t in asyncio.all_tasks():
                t.cancel()

    def run(self):
        """run runs the action until completion"""
        try:
            self._loop.run_until_complete(self._run_action())
        except asyncio.CancelledError:
            logger.info("%s finished", self.__class__.__name__)

    def _create_task(self, task, args=None, kwargs=None):
        """_create_task creates the async `task` with arguments `args` and
        keyword arguments `kwargs`"""
        args = args if args is not None else []
        kwargs = kwargs if kwargs is not None else {}
        self._tasks.append(asyncio.create_task(task(*args, **kwargs)))

    async def _run_action(self):
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _incr_counter(self):
        logger.debug("Incrementing counter")
        async with self._counter_lock:
            self._counter += 1
