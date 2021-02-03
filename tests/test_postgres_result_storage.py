#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

from walt.queries import CREATE_TABLES_SQL
from walt.queries import DROP_TABLES_SQL
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


def test_setup_database_calls_connect(pg_res_storage, psycopg2_mock, init_args):
    dsn_with_dbname = " ".join(f"{k}={v}" for k, v in init_args.items())
    dsn, _ = dsn_with_dbname.rsplit(maxsplit=1)
    pg_res_storage.setup_database()
    assert psycopg2_mock.connect.call_count == 2
    psycopg2_mock.connect.assert_any_call(dsn)
    psycopg2_mock.connect.assert_any_call(dsn_with_dbname)


def test_setup_database_creates_cursor(pg_res_storage, conn_mock):
    pg_res_storage.setup_database()
    assert conn_mock.cursor.call_count == 2


def test_setup_database_sets_isolation_level(pg_res_storage, conn_mock):
    pg_res_storage.setup_database()
    assert conn_mock.set_isolation_level.call_count == 1


def test_setup_database_creates_database(pg_res_storage, init_args, execute_mock, mocker):
    sql_mock = mocker.patch("walt.storages.sql")
    sql_mock.SQL.side_effect = sql_mock.Identifier.side_effect = str
    pg_res_storage.setup_database()
    execute_mock.assert_any_call(f"CREATE DATABASE {init_args['dbname']}")


def test_setup_database_creates_tables(pg_res_storage, execute_mock):
    pg_res_storage.setup_database()
    execute_mock.assert_any_call(CREATE_TABLES_SQL)


def test_teardown_database_calls_connect(pg_res_storage, psycopg2_mock, init_args):
    dsn_with_dbname = " ".join(f"{k}={v}" for k, v in init_args.items())
    dsn, _ = dsn_with_dbname.rsplit(maxsplit=1)
    pg_res_storage.teardown_database()
    assert psycopg2_mock.connect.call_count == 2
    psycopg2_mock.connect.assert_any_call(dsn)
    psycopg2_mock.connect.assert_any_call(dsn_with_dbname)


def test_teardown_database_creates_cursor(pg_res_storage, conn_mock):
    pg_res_storage.teardown_database()
    assert conn_mock.cursor.call_count == 2


def test_teardown_database_sets_isolation_level(pg_res_storage, conn_mock):
    pg_res_storage.teardown_database()
    assert conn_mock.set_isolation_level.call_count == 1


def test_teardown_database_drops_tables(pg_res_storage, execute_mock):
    pg_res_storage.teardown_database()
    execute_mock.assert_any_call(DROP_TABLES_SQL)


def test_teardown_database_drops_database(pg_res_storage, init_args, execute_mock, mocker):
    sql_mock = mocker.patch("walt.storages.sql")
    sql_mock.SQL.side_effect = sql_mock.Identifier.side_effect = str
    pg_res_storage.teardown_database()
    execute_mock.assert_any_call(f"DROP DATABASE {init_args['dbname']}")
