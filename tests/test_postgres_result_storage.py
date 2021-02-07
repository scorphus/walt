#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

from unittest.mock import AsyncMock
from walt import queries
from walt import result
from walt.storages import PostgresResultStorage

import pytest


@pytest.fixture
def psycopg2_mock(mocker):
    return mocker.patch("walt.storages.psycopg2")


@pytest.fixture
def conn_mock(psycopg2_mock):
    return psycopg2_mock.connect.return_value.__enter__.return_value


@pytest.fixture
def execute_mock(conn_mock):
    return conn_mock.cursor.return_value.__enter__.return_value.execute


@pytest.fixture
def init_args():
    return {
        "host": "much-host",
        "port": 5432,
        "user": "wow-user",
        "password": "very-password",
        "dbname": "many-dbname",
    }


@pytest.fixture
def pg_res_storage(init_args):
    return PostgresResultStorage(*init_args.values())


@pytest.fixture
def dsn_with_dbname(init_args):
    return " ".join(f"{k}={v}" for k, v in init_args.items())


@pytest.fixture
def dsn(dsn_with_dbname):
    return dsn_with_dbname.rsplit(maxsplit=1)[0]


def test_create_database_calls_connect(pg_res_storage, psycopg2_mock, dsn):
    pg_res_storage.create_database()
    assert psycopg2_mock.connect.call_count == 1
    psycopg2_mock.connect.assert_any_call(dsn)


def test_create_database_sets_isolation_level(pg_res_storage, conn_mock):
    pg_res_storage.create_database()
    assert conn_mock.set_isolation_level.call_count == 1


def test_create_database_creates_database(pg_res_storage, init_args, execute_mock, mocker):
    sql_mock = mocker.patch("walt.storages.sql")
    sql_mock.SQL.side_effect = sql_mock.Identifier.side_effect = str
    pg_res_storage.create_database()
    execute_mock.assert_any_call(f"CREATE DATABASE {init_args['dbname']}")


def test_create_methods_create_cursor(pg_res_storage, conn_mock):
    pg_res_storage.create_database()
    assert conn_mock.cursor.call_count == 1
    pg_res_storage.create_tables()
    assert conn_mock.cursor.call_count == 2


def test_create_tables_creates_tables(pg_res_storage, execute_mock):
    pg_res_storage.create_tables()
    execute_mock.assert_any_call(queries.CREATE_TABLES_SQL)


def test_create_tables_calls_connect(pg_res_storage, psycopg2_mock, dsn_with_dbname):
    pg_res_storage.create_tables()
    assert psycopg2_mock.connect.call_count == 1
    psycopg2_mock.connect.assert_any_call(dsn_with_dbname)


def test_drop_database_calls_connect(pg_res_storage, psycopg2_mock, dsn):
    pg_res_storage.drop_database()
    assert psycopg2_mock.connect.call_count == 1
    psycopg2_mock.connect.assert_any_call(dsn)


def test_drop_database_sets_isolation_level(pg_res_storage, conn_mock):
    pg_res_storage.drop_database()
    assert conn_mock.set_isolation_level.call_count == 1


def test_drop_database_drops_database(pg_res_storage, init_args, execute_mock, mocker):
    sql_mock = mocker.patch("walt.storages.sql")
    sql_mock.SQL.side_effect = sql_mock.Identifier.side_effect = str
    pg_res_storage.drop_database()
    execute_mock.assert_any_call(f"DROP DATABASE {init_args['dbname']}")


def test_drop_tables_calls_connect(pg_res_storage, psycopg2_mock, dsn_with_dbname):
    pg_res_storage.drop_tables()
    assert psycopg2_mock.connect.call_count == 1
    psycopg2_mock.connect.assert_any_call(dsn_with_dbname)


def test_drop_tables_drops_tables(pg_res_storage, execute_mock):
    pg_res_storage.drop_tables()
    execute_mock.assert_any_call(queries.DROP_TABLES_SQL)


def test_drop_methods_creates_cursor(pg_res_storage, conn_mock):
    pg_res_storage.drop_tables()
    assert conn_mock.cursor.call_count == 1
    pg_res_storage.drop_database()
    assert conn_mock.cursor.call_count == 2


@pytest.fixture
def create_pool_mock(mocker):
    return mocker.patch("walt.storages.aiopg.create_pool", AsyncMock())


@pytest.fixture
def pool_mock(create_pool_mock, async_magic_mock):
    pool_mock = async_magic_mock()
    create_pool_mock.return_value = pool_mock
    return pool_mock


@pytest.fixture
def aiopg_conn_mock(pool_mock, async_magic_mock):
    aiopg_conn_mock = async_magic_mock()
    pool_mock.acquire.return_value.__aenter__.return_value = aiopg_conn_mock
    return aiopg_conn_mock


@pytest.fixture
def cursor_mock(aiopg_conn_mock, async_magic_mock):
    cursor_mock = async_magic_mock()
    cursor_mock.execute = AsyncMock()
    aiopg_conn_mock.cursor.return_value.__aenter__.return_value = cursor_mock
    return cursor_mock


@pytest.fixture
def result_result():
    return result.Result(
        result.ResultType.RESULT, "wow.result", 0.359, 200, result.Pattern.NO_PATTERN
    )


@pytest.fixture
def error_result():
    return result.Result(result.ResultType.ERROR, "very.error")


@pytest.mark.asyncio
async def test_connect_creates_a_pool(pg_res_storage, init_args, create_pool_mock):
    dsn_with_dbname = " ".join(f"{k}={v}" for k, v in init_args.items())
    await pg_res_storage.connect()
    create_pool_mock.assert_awaited_once_with(dsn_with_dbname)


@pytest.mark.asyncio
async def test_save_inserts_result_result(pg_res_storage, result_result, cursor_mock):
    await pg_res_storage.connect()
    await pg_res_storage.save(result_result)
    cursor_mock.execute.assert_awaited_once_with(
        queries.RESULT_INSERT_SQL, result_result.as_dict()
    )


@pytest.mark.asyncio
async def test_save_inserts_error_result(pg_res_storage, error_result, cursor_mock):
    await pg_res_storage.connect()
    await pg_res_storage.save(error_result)
    cursor_mock.execute.assert_awaited_once_with(queries.ERROR_INSERT_SQL, error_result.as_dict())


@pytest.mark.asyncio
async def test_save_logs_exception_when_not_connected(pg_res_storage, logger_mock):
    await pg_res_storage.save(None)
    logger_mock.exception.called_once()
