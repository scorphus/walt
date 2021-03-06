#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

"""queries collects all queries used by walt"""

DROP_TABLES_SQL = """
DROP TABLE IF EXISTS result;
DROP TYPE IF EXISTS pattern_type;
DROP TABLE IF EXISTS error;
DROP TYPE IF EXISTS error_type;
"""

CREATE_TABLES_SQL = """
CREATE TYPE pattern_type AS ENUM ('FOUND', 'NO_PATTERN', 'NOT_FOUND', 'IRRELEVANT');

CREATE TABLE IF NOT EXISTS result (
    result_id INT GENERATED ALWAYS AS IDENTITY,
    url VARCHAR NOT NULL,
    response_time decimal not null,
    status_code int not null,
    pattern pattern_type not null,
    timestamp timestamptz
);

CREATE INDEX result_url_index ON result(url ASC NULLS LAST);

CREATE TYPE error_type AS ENUM ('CLIENT_ERROR', 'TIMEOUT_ERROR', 'ERROR');

CREATE TABLE IF NOT EXISTS error (
    error_id INT GENERATED ALWAYS AS IDENTITY,
    url VARCHAR NOT NULL,
    error error_type not null,
    timestamp timestamptz
);

CREATE INDEX error_url_index ON error(url ASC NULLS LAST);
"""

RESULT_INSERT_SQL = """
INSERT INTO result (url, response_time, status_code, pattern, timestamp) VALUES (
    %(url)s, %(response_time)s, %(status_code)s, %(pattern)s,
    TIMESTAMP 'epoch' + %(utc_timestamp_ms)s * INTERVAL '1 millisecond'
);
"""

ERROR_INSERT_SQL = """
INSERT INTO error (url, error, timestamp) VALUES (
    %(url)s, %(result_type)s,
    TIMESTAMP 'epoch' + %(utc_timestamp_ms)s * INTERVAL '1 millisecond'
);
"""
