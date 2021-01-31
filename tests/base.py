#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

from walt.action_runners import ActionRunnerBase


class ActionRunnerBaseTester(ActionRunnerBase):
    async def _run_action(self):
        tasks = getattr(self, "tasks", [])
        for task in tasks:
            try:
                self._create_task(*task)
            except TypeError:
                self._create_task(task)
        await super()._run_action()

    def register_tasks(self, tasks):
        self.tasks = tasks
