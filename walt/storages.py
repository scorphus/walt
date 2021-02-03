#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

from psycopg2 import sql
from walt import logger
from walt.queries import CREATE_TABLES_SQL
from walt.queries import DROP_TABLES_SQL

import psycopg2


class ConsoleResultWriter:
    @staticmethod
    async def save(result):
        print(f"Got a result: {result}")


class PostgresResultStorage:
    """PostgresResultStorage manages the database and Result tables"""

    def __init__(self, host, port, user, password, dbname):
        self._dbname = dbname
        self._dsn = f"host={host} port={port} user={user} password={password}"

    def setup_database(self):
        """setup_database creates the database and its tables"""
        with psycopg2.connect(self._dsn) as conn, conn.cursor() as cur:
            logger.info("Creating database %s", self._dbname)
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(self._dbname)))
        with psycopg2.connect(f"{self._dsn} dbname={self._dbname}") as conn, conn.cursor() as cur:
            logger.info("Creating tables on %s", self._dbname)
            cur.execute(CREATE_TABLES_SQL)

    def teardown_database(self):
        """teardown_database drops the database and its tables"""
        with psycopg2.connect(f"{self._dsn} dbname={self._dbname}") as conn, conn.cursor() as cur:
            logger.info("Dropping tables from %s", self._dbname)
            cur.execute(DROP_TABLES_SQL)
        with psycopg2.connect(self._dsn) as conn, conn.cursor() as cur:
            logger.info("Dropping database %s", self._dbname)
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cur.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(self._dbname)))
