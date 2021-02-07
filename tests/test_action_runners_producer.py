#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

from aiohttp.client_exceptions import ClientOSError
from tests.base import ActionRunnerBaseTester
from unittest.mock import ANY
from unittest.mock import AsyncMock
from unittest.mock import call
from unittest.mock import MagicMock
from walt import result
from walt.action_runners import Producer

import aiohttp
import aiokafka
import asyncio
import contextlib
import pytest
import re


def test_producer_inits_with_a_cfg_arg():
    cfg_mock = MagicMock()
    producer = Producer(cfg_mock)
    assert producer._headers == {"User-Agent": cfg_mock["user_agent"], **cfg_mock["headers"]}
    assert producer._interval == cfg_mock["interval"]
    assert producer._concurrent == cfg_mock["concurrent"]
    assert producer._timeout == cfg_mock["timeout"]
    assert producer._session is None
    assert producer._kafka_uri == cfg_mock["kafka"]["uri"]
    assert producer._kafka_topic == cfg_mock["kafka"]["topic"]
    assert producer._kafka_producer is None


@pytest.fixture
def producer(mocker):
    mocker.patch.object(Producer, "_ssl_arguments", new_callable=lambda: {})
    producer = Producer(MagicMock())
    producer._interval = 1
    producer._timeout = 1
    return producer


def test_compile_url_patterns_copies_url_map(producer):
    url_map_mock = MagicMock()
    producer._compile_url_patterns(url_map_mock)
    url_map_mock.copy.assert_called_once_with()


def test_compile_url_patterns_compiles_no_empty_url_map(producer):
    assert producer._compile_url_patterns({}) == {}


def test_compile_url_patterns_compiles_no_empty_pattern(producer):
    url_map = {"wow-url.doge": "", "much-web.doge": ""}
    assert producer._compile_url_patterns(url_map) == url_map


def test_compile_url_patterns_compiles_patterns(producer):
    url_map = {"wow-url.doge": "many-pat+ern", "much-web.doge": "(very-regular)*"}
    new_url_map = producer._compile_url_patterns(url_map)
    assert len(new_url_map) == len(url_map)
    assert new_url_map != url_map


def test_compile_url_patterns_nullifies_erroneous_patterns(producer, logger_mock):
    url_map = {"wow-url.doge": "(many-error", "much-web.doge": "*very-failure"}
    expected = {"wow-url.doge": None, "much-web.doge": None}
    new_url_map = producer._compile_url_patterns(url_map)
    assert len(new_url_map) == len(url_map)
    assert new_url_map == expected
    assert logger_mock.error.call_count == len(url_map)


@pytest.mark.asyncio
async def test_run_action_does_nothing_when_no_urls(producer, logger_mock):
    producer._url_map = {}
    await producer._run_action()
    logger_mock.warning.assert_called_once()


@pytest.mark.asyncio
async def test_run_action_starts_a_client_session_with_headers(
    producer, client_session_mock, kafka_producer_mock
):
    producer._process_urls = AsyncMock()
    await producer._run_action()
    client_session_mock.assert_called_once_with(headers=producer._headers)


@pytest.mark.asyncio
async def test_run_action_starts_kafka_producer(
    producer, client_session_mock, kafka_producer_mock
):
    producer._process_urls = AsyncMock()
    await producer._run_action()
    kafka_producer_mock.assert_called_once_with(
        bootstrap_servers=producer._kafka_uri,
        request_timeout_ms=producer._timeout * 1000,
        retry_backoff_ms=producer._interval * 1000,
    )
    kafka_producer_mock.return_value.start.assert_called_once_with()


@pytest.mark.asyncio
async def test_start_kafka_producer_retries_with_backoff(producer, kafka_producer_mock, mocker):
    sleep_mocker = mocker.patch("walt.action_runners.asyncio.sleep", AsyncMock())
    failures = 3
    side_effect = [aiokafka.errors.KafkaConnectionError] * failures + [AsyncMock()]
    kafka_producer_mock.return_value.start.side_effect = side_effect
    await producer._start_kafka_producer()
    kafka_producer_mock.return_value.start.call_count == failures
    sleep_mocker.assert_has_calls([call(1), call(2), call(4)])


@pytest.mark.asyncio
async def test_start_kafka_producer_logs_exception(
    producer, kafka_producer_mock, logger_mock, mocker
):
    mocker.patch("walt.action_runners.asyncio.sleep", AsyncMock())
    side_effect = [aiokafka.errors.KafkaConnectionError, AsyncMock]
    kafka_producer_mock.return_value.start.side_effect = side_effect
    await producer._start_kafka_producer()
    logger_mock.exception.assert_called_with("Failed to start Kafka Producer!")


@pytest.fixture
def producer_process(producer):
    producer._create_urls_queue = MagicMock(return_value=AsyncMock())
    producer._create_task = MagicMock()
    return producer


@pytest.mark.asyncio
@pytest.mark.parametrize("concurrent", [1, 5, 10])
async def test_process_urls_creates_concurrent_worker_tasks(
    concurrent, producer_process, kafka_producer_mock
):
    producer_process._concurrent = concurrent
    await producer_process._process_urls()
    assert producer_process._create_task.call_count == concurrent
    for i in range(concurrent):
        producer_process._create_task.assert_any_call(
            producer_process._worker, (f"producer-{i+1}", ANY)
        )


class ProducerTester(ActionRunnerBaseTester, Producer):
    def run(self):
        with contextlib.suppress(KeyboardInterrupt):
            super().run()


@pytest.fixture
def producer_auto_cancel(mocker):
    async def side_effect(producer):
        attempts = 0
        while True:
            await asyncio.sleep(1e-3)
            attempts += 1
            if producer._counter > 9 or attempts > 10:
                break
        for task in asyncio.all_tasks():
            task.cancel()

    mocker.patch.object(ProducerTester, "_ssl_arguments", new_callable=lambda: {})
    producer = ProducerTester(MagicMock())
    producer.register_tasks([(AsyncMock(side_effect=side_effect), (producer,))])
    producer._interval = 1
    producer._concurrent = 1
    producer._timeout = 1
    producer._url_map = {"very.url": "", "wow.wow.web": ""}
    return producer


def test_producer_sends_messages_successfully(
    producer_auto_cancel, client_session_mock, client_session_get_mock, kafka_producer_mock
):
    client_session_get_mock.return_value.__aenter__.return_value.status = 200
    producer_auto_cancel.run()
    res = result.ResultSerde.from_bytes(producer_auto_cancel._kafka_producer.send.call_args[0][1])
    assert res.result_type is result.ResultType.RESULT
    assert any(res.url == url for url in producer_auto_cancel._url_map)
    assert isinstance(res.response_time, float) and res.response_time > 0
    assert res.status_code == 200
    assert res.pattern == result.Pattern.NO_PATTERN
    assert isinstance(res.utc_timestamp_ms, int) and res.utc_timestamp_ms > 0
    assert producer_auto_cancel._kafka_producer.send.await_count == producer_auto_cancel._counter


@pytest.mark.parametrize(
    "regexp, side_effect, pattern",
    [
        ("", None, result.Pattern.NO_PATTERN),
        (r"\w{,6}", None, result.Pattern.FOUND),
        (r"\w{6,}", None, result.Pattern.NOT_FOUND),
        ("", aiohttp.ClientError, result.Pattern.IRRELEVANT),
        (r".*", aiohttp.ClientError, result.Pattern.IRRELEVANT),
    ],
)
def test_producer_sends_messages_with_pattern_result(
    regexp,
    side_effect,
    pattern,
    producer_auto_cancel,
    client_session_mock,
    client_session_get_mock,
    resp_text_mock,
    kafka_producer_mock,
):
    client_session_get_mock.return_value.__aenter__.return_value.status = 200
    resp_text_mock.return_value = "Such quick fox jumps over the many lazy dog wow"
    client_session_get_mock.side_effect = side_effect
    producer_auto_cancel._url_map = {"such.web": re.compile(regexp) if regexp else None}
    producer_auto_cancel.run()
    res = result.ResultSerde.from_bytes(producer_auto_cancel._kafka_producer.send.call_args[0][1])
    assert res.pattern == pattern
    assert producer_auto_cancel._kafka_producer.send.await_count == producer_auto_cancel._counter


@pytest.mark.parametrize(
    "side_effect, result_type",
    [
        (aiohttp.ClientError, result.ResultType.CLIENT_ERROR),
        (ClientOSError, result.ResultType.CLIENT_ERROR),
        (asyncio.TimeoutError, result.ResultType.TIMEOUT_ERROR),
        (OSError, result.ResultType.ERROR),
        (Exception, result.ResultType.ERROR),
    ],
)
def test_producer_sends_messages_on_client_failure(
    side_effect,
    result_type,
    producer_auto_cancel,
    client_session_mock,
    client_session_get_mock,
    kafka_producer_mock,
):
    client_session_get_mock.side_effect = side_effect
    producer_auto_cancel.run()
    res = result.ResultSerde.from_bytes(producer_auto_cancel._kafka_producer.send.call_args[0][1])
    assert res.result_type is result_type
    assert res.response_time == 0
    assert res.status_code == 0
    assert res.pattern == result.Pattern.IRRELEVANT
    assert producer_auto_cancel._kafka_producer.send.await_count == producer_auto_cancel._counter


@pytest.mark.parametrize(
    "side_effect, logger_func",
    [
        (aiohttp.ClientError, "error"),
        (ClientOSError, "error"),
        (asyncio.TimeoutError, "error"),
        (OSError, "exception"),
        (Exception, "exception"),
    ],
)
def test_producer_logs_on_client_failure(
    side_effect,
    logger_func,
    producer_auto_cancel,
    client_session_mock,
    client_session_get_mock,
    kafka_producer_mock,
    logger_mock,
):
    client_session_get_mock.side_effect = side_effect
    producer_auto_cancel.run()
    getattr(logger_mock, logger_func).assert_called_once()


def test_producer_worker_logs_exception_on_kafka_send_failure(
    producer_auto_cancel, client_session_mock, kafka_producer_mock, logger_mock
):
    kafka_producer_mock.return_value.send = AsyncMock(
        side_effect=aiokafka.errors.KafkaTimeoutError
    )
    producer_auto_cancel.run()
    logger_mock.exception.assert_called_once()
