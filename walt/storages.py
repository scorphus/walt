#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

"""storages provides entities responsible for writing a Result to external resources"""

import aiopg
import psycopg2
from psycopg2 import sql

from walt import logger
from walt import queries
from walt.result import ResultType


class PostgresResultStorage:
    """PostgresResultStorage manages the database and Result tables, and inserts
    data into the tables depending on the type of Result"""

    def __init__(self, host, port, user, password, dbname):
        self._dbname = dbname
        self._dsn = f"host={host} port={port} user={user} password={password}"
        self._pool = None

    def create_database(self):
        """create_database creates the database"""
        with psycopg2.connect(self._dsn) as conn, conn.cursor() as cur:
            logger.info("Creating database %s", self._dbname)
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(self._dbname)))

    def create_tables(self):
        """create_tables creates all tables"""
        with psycopg2.connect(f"{self._dsn} dbname={self._dbname}") as conn, conn.cursor() as cur:
            logger.info("Creating tables on %s", self._dbname)
            cur.execute(queries.CREATE_TABLES_SQL)

    def drop_database(self):
        """drop_database drops the database"""
        with psycopg2.connect(self._dsn) as conn, conn.cursor() as cur:
            logger.info("Dropping database %s", self._dbname)
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cur.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(self._dbname)))

    def drop_tables(self):
        """drop_tables drops all tables"""
        with psycopg2.connect(f"{self._dsn} dbname={self._dbname}") as conn, conn.cursor() as cur:
            logger.info("Dropping tables from %s", self._dbname)
            cur.execute(queries.DROP_TABLES_SQL)

    async def connect(self):
        self._pool = await aiopg.create_pool(f"{self._dsn} dbname={self._dbname}")

    async def disconnect(self):
        self._pool.close()
        await self._pool.wait_closed()

    async def save(self, result):
        """save wraps _save and logs exceptions if any"""
        try:
            await self._save(result)
        except Exception:
            logger.exception("Failed to save result %s", repr(str(result)))

    async def _save(self, result):
        """_save inserts one Result according on its type"""
        if not self._pool:
            raise RuntimeError("Not connected. Did you forget to call `connect()`?")
        async with self._pool.acquire() as conn, conn.cursor() as cur:
            logger.info("Saving a result of type %s", result.result_type.name)
            result_dict = result.as_dict()
            if result.result_type is ResultType.RESULT:
                logger.debug("Inserting a result: %s", result_dict)
                await cur.execute(queries.RESULT_INSERT_SQL, result_dict)
            else:
                logger.debug("Inserting an error: %s", result_dict)
                await cur.execute(queries.ERROR_INSERT_SQL, result_dict)
