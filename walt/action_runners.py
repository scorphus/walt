#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

from walt import async_backoff
from walt import logger
from walt import result

import aiohttp
import aiokafka
import asyncio
import re
import signal
import time


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


class Producer(ActionRunnerBase):
    """Producer produces website verification result into a Kafka topic"""

    def __init__(self, cfg):
        super().__init__()
        self._headers = {"User-Agent": cfg["user_agent"], **cfg["headers"]}
        self._url_map = self._compile_url_patterns(cfg["url_map"])
        self._interval = cfg["interval"]
        self._concurrent = cfg["concurrent"]
        self._timeout = cfg["timeout"]
        self._session = None
        self._kafka_uri = cfg["kafka"]["uri"]
        self._kafka_topic = cfg["kafka"]["topic"]
        self._kafka_producer = None

    def _compile_url_patterns(self, url_map):
        """_compile_url_patterns compiles all regexp patterns skipping those
        empty or erroneous"""
        new_url_map = url_map.copy()
        for url, regexp in url_map.items():
            if not regexp:
                continue
            try:
                new_url_map[url] = re.compile(regexp)
            except re.error as err:
                logger.error("Failed to compile regexp pattern `%s`: %s", regexp, err)
                new_url_map[url] = None
        return new_url_map

    async def _run_action(self):
        """_run_action starts a kafka producer, creates a client session and
        starts processing the URLs"""
        if not self._url_map:
            logger.warning("No URLs to check!")
            return
        logger.info("Starting %s", self.__class__.__name__)
        await self._start_kafka_producer()
        async with aiohttp.ClientSession(headers=self._headers) as session:
            self._session = session
            await self._process_urls()
        logger.debug("Waiting until all worker tasks are cancelled")
        logger.info("Produced %d results", self._counter)
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.debug("Stopping Kafka producer")
        await self._kafka_producer.stop()

    @async_backoff(msg="Failed to start Kafka Producer!")
    async def _start_kafka_producer(self):
        logger.debug("Starting Kafka Producer")
        self._kafka_producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=self._kafka_uri,
            request_timeout_ms=self._timeout * 1000,
            retry_backoff_ms=self._interval * 1000,
        )
        await self._kafka_producer.start()

    async def _process_urls(self):
        """_process_urls creates worker tasks to check the URLs"""
        logger.info("Checking %d URLs", len(self._url_map))
        urls = self._create_urls_queue()
        for i in range(self._concurrent):
            self._create_task(self._worker, (f"producer-{i+1}", urls))
        logger.debug("Checking URLs")
        await urls.join()

    def _create_urls_queue(self):
        urls = asyncio.Queue()
        for url in self._url_map:
            urls.put_nowait(url)
        if len(self._url_map) == 1:
            # prevents `urls` from being exhausted when checking a single URL:
            urls.put_nowait(list(self._url_map)[0])
        return urls

    async def _worker(self, name, urls):
        logger.debug("Starting %s", name)
        try:
            await self._check_urls(name, urls)
        except asyncio.CancelledError:
            for _ in range(urls.qsize()):
                urls.task_done()
            raise
        except Exception:
            logger.exception("%s failed!", name)
        finally:
            logger.debug("Stopping %s worker", name)

    async def _check_urls(self, name, urls):
        """_check_urls takes a URL, checks it and sends the result"""
        while True:
            url = await urls.get()
            logger.info("Checking %s", url)
            logger.debug("%s is checking %s", name, url)
            res = await self._session_get(url)
            res_bytes = str(res).encode()
            logger.debug("%s is sending result %s", name, res_bytes)
            await self._kafka_send(res_bytes)
            urls.task_done()
            urls.put_nowait(url)
            await self._incr_counter()
            logger.debug("%s is going to sleep", name)
            await asyncio.sleep(self._interval)

    async def _session_get(self, url):
        """_session_get fetches a URL and generates a verification result"""
        try:
            start = time.monotonic()
            async with self._session.get(url, timeout=self._timeout) as resp:
                pattern = await self._check_pattern(url, resp)
                spent = time.monotonic() - start
                return result.Result(result.ResultType.RESULT, url, spent, resp.status, pattern)
        except aiohttp.ClientError as err:
            logger.error("ClientError (%s): %s", err.__class__.__name__, url)
            return result.Result(result.ResultType.CLIENT_ERROR, url)
        except asyncio.TimeoutError:
            logger.error("Timeout: %s", url)
            return result.Result(result.ResultType.TIMEOUT_ERROR, url)
        except Exception:
            logger.exception("Failed to fetch %s", url)
            return result.Result(result.ResultType.ERROR, url)

    async def _check_pattern(self, url, resp):
        regexp = self._url_map[url]
        if not regexp:
            return result.Pattern.NO_PATTERN
        text = await resp.text()
        if regexp.search(text, re.MULTILINE):
            return result.Pattern.FOUND
        return result.Pattern.NOT_FOUND

    async def _kafka_send(self, msg):
        try:
            await self._kafka_producer.send(self._kafka_topic, msg)
        except Exception:
            logger.exception("Failed to send {msg} to {self._kafka_topic}!")


class Consumer(ActionRunnerBase):
    """Consumer consumes data from a Kafka topic, runs it through a deserializer
    and delivers it to a data storage"""

    def __init__(self, cfg, storage, serde):
        super().__init__()
        self._interval = cfg["interval"]
        self._timeout = cfg["timeout"]
        self._kafka_uri = cfg["kafka"]["uri"]
        self._kafka_topic = cfg["kafka"]["topic"]
        self._kafka_consumer = None
        self._storage = storage
        self._serde = serde

    async def _run_action(self):
        logger.info("Starting %s", self.__class__.__name__)
        await self._start_kafka_consumer()
        logger.info("Consuming results")
        try:
            async for msg in self._kafka_consumer:
                logger.info("Consumed a message with value: %s", msg.value)
                value = self._serde.from_bytes(msg.value)
                await self._storage.save(value)
                await self._incr_counter()
        finally:
            logger.debug("Stopping Kafka consumer")
            await self._kafka_consumer.stop()
            logger.info("Consumed %d messages", self._counter)

    @async_backoff(msg="Failed to start Kafka Consumer!")
    async def _start_kafka_consumer(self):
        logger.debug("Starting Kafka Consumer")
        self._kafka_consumer = aiokafka.AIOKafkaConsumer(
            self._kafka_topic,
            bootstrap_servers=self._kafka_uri,
            request_timeout_ms=self._timeout * 1000,
            retry_backoff_ms=self._interval * 1000,
        )
        await self._kafka_consumer.start()
