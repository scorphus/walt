#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from enum import auto


EPOCH = datetime(1970, 1, 1)  # timezone-naïve epoch time


class ResultType(Enum):
    """ResultType enumerates all possible types of verification resulta"""

    RESULT = auto()
    CLIENT_ERROR = auto()
    TIMEOUT_ERROR = auto()
    ERROR = auto()


class Pattern(Enum):
    """Pattern enumerates all possible types of regexp patterns results"""

    FOUND = auto()
    NO_PATTERN = auto()
    NOT_FOUND = auto()
    IRRELEVANT = auto()


def utc_now_ms():
    "utc_now_ms returns the current UTC timestamp in milliseconds"
    return round((datetime.utcnow() - EPOCH).total_seconds() * 1e3)


@dataclass
class Result:
    """Result stores website verification results"""

    result_type: ResultType
    url: str
    response_time: float = 0
    status_code: int = 0
    pattern: Pattern = Pattern.IRRELEVANT
    utc_timestamp_ms: int = field(default_factory=utc_now_ms)

    def __repr__(self):
        return (
            f"{self.result_type.value}\n{self.url}\n{self.response_time}"
            f"\n{self.status_code}\n{self.pattern.value}\n{self.utc_timestamp_ms}"
        )

    @staticmethod
    def from_str(result_str):
        try:
            (
                result_type,
                url,
                response_time,
                status_code,
                pattern,
                utc_timestamp_ms,
            ) = result_str.splitlines()
            return Result(
                ResultType(int(result_type)),
                url,
                float(response_time),
                int(status_code),
                Pattern(int(pattern)),
                int(utc_timestamp_ms),
            )
        except ValueError as err:
            raise ValueError(f"{repr(result_str)} is not a valid Result representation: {err}")

    def as_dict(self):
        result = vars(self).copy()
        result["result_type"] = self.result_type.name
        result["pattern"] = self.pattern.name
        return result


class ResultSerde:
    """ResultSerde serializes and deserializes Result into/from bytes"""

    @staticmethod
    def from_bytes(result_bytes):
        return Result.from_str(result_bytes.decode())

    @staticmethod
    def to_bytes(result):
        return str(result.encode())
