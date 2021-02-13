#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

import asyncio
import contextlib
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import call

import aiokafka
import pytest

from tests.base import ActionRunnerBaseTester
from walt import result
from walt.action_runners import Consumer


def test_consumer_inits_with_a_cfg_and_storage_args():
    cfg_mock = MagicMock()
    consumer = Consumer(cfg_mock, AsyncMock(), result.ResultSerde)
    assert consumer._interval == cfg_mock["interval"]
    assert consumer._timeout == cfg_mock["timeout"]
    assert consumer._kafka_uri == cfg_mock["kafka"]["uri"]
    assert consumer._kafka_topic == cfg_mock["kafka"]["topic"]
    assert consumer._kafka_consumer is None


@pytest.fixture
def consumer(mocker):
    mocker.patch.object(Consumer, "_ssl_arguments", new_callable=lambda: {})
    consumer = Consumer(MagicMock(), AsyncMock(), result.ResultSerde)
    consumer._interval = 1
    consumer._timeout = 1
    return consumer


@pytest.mark.asyncio
async def test_start_kafka_consumer_retries_with_backoff(consumer, kafka_consumer_mock, mocker):
    sleep_mocker = mocker.patch("walt.action_runners.asyncio.sleep", AsyncMock())
    failures = 3
    side_effect = [aiokafka.errors.KafkaConnectionError] * failures + [AsyncMock()]
    kafka_consumer_mock.return_value.start.side_effect = side_effect
    await consumer._start_kafka_consumer()
    kafka_consumer_mock.return_value.start.call_count == failures
    sleep_mocker.assert_has_calls([call(1), call(2), call(4)])


@pytest.mark.asyncio
async def test_run_action_connects_storage(consumer, kafka_consumer_mock):
    consumer._process_urls = AsyncMock()
    await consumer._run_action()
    consumer._storage.connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_action_starts_kafka_consumer(consumer, kafka_consumer_mock):
    consumer._process_urls = AsyncMock()
    await consumer._run_action()
    kafka_consumer_mock.assert_called_once_with(
        consumer._kafka_topic,
        bootstrap_servers=consumer._kafka_uri,
        request_timeout_ms=consumer._timeout * 1000,
        retry_backoff_ms=consumer._interval * 1000,
    )
    kafka_consumer_mock.return_value.start.assert_called_once_with()


@pytest.mark.asyncio
async def test_start_kafka_consumer_logs_exception(
    consumer, kafka_consumer_mock, logger_mock, mocker
):
    mocker.patch("walt.action_runners.asyncio.sleep", AsyncMock())
    side_effect = [aiokafka.errors.KafkaConnectionError, AsyncMock]
    kafka_consumer_mock.return_value.start.side_effect = side_effect
    await consumer._start_kafka_consumer()
    logger_mock.exception.assert_called_with("Failed to start Kafka Consumer!")


class ConsumerTester(ActionRunnerBaseTester, Consumer):
    def run(self):
        with contextlib.suppress(KeyboardInterrupt):
            super().run()


@pytest.fixture
def consumer_auto_cancel(mocker):
    async def side_effect(consumer):
        attempts = 0
        while True:
            await asyncio.sleep(1e-3)
            attempts += 1
            if consumer._counter > 9 or attempts > 10:
                break
        for task in asyncio.all_tasks():
            task.cancel()

    mocker.patch.object(Consumer, "_ssl_arguments", new_callable=lambda: {})
    consumer = ConsumerTester(MagicMock(), AsyncMock(), result.ResultSerde)
    consumer.register_tasks([(AsyncMock(side_effect=side_effect), (consumer,))])
    consumer._interval = 1
    consumer._timeout = 1
    return consumer


def test_consumer_consume_one_message(consumer_auto_cancel, kafka_consumer_mock):
    msg_value = b"1\nwow.web\n0.359\n200\n2\n719"
    msg = MagicMock(value=msg_value)
    kafka_consumer_mock.return_value.__aiter__.return_value = [msg]
    consumer_auto_cancel.run()
    expected_result = result.ResultSerde.from_bytes(msg_value)
    consumer_auto_cancel._storage.save.assert_called_once_with(expected_result)


def test_consumer_consume_messages(consumer_auto_cancel, kafka_consumer_mock):
    total_messages = 10
    msg_value = b"1\nwow.web\n0.359\n200\n2\n719"
    msg = MagicMock(value=msg_value)
    kafka_consumer_mock.return_value.__aiter__.return_value = [msg] * total_messages
    consumer_auto_cancel.run()
    assert consumer_auto_cancel._storage.save.call_count == total_messages
    expected_result = result.ResultSerde.from_bytes(msg_value)
    consumer_auto_cancel._storage.save.assert_any_call(expected_result)
