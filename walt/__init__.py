#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

"""walt - Website Availability Monitor"""

import asyncio
import functools
import logging


__version__ = "0.1.0"

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter(
        "%(asctime)s %(levelname)s [%(filename)s:%(funcName)s:%(lineno)d] %(message)s"
    )
)
logger.addHandler(handler)


def async_backoff(backoff=1, msg=None):
    if not isinstance(backoff, int) or isinstance(backoff, float):
        raise ValueError("backoff is expected to be numeric")

    def decorator(f):
        nonlocal msg
        if not msg:
            msg = f"{f.__name__} failed!"

        @functools.wraps(f)
        async def wrapper(*args, **kwargs):
            round_backoff = backoff
            while True:
                try:
                    return await f(*args, **kwargs)
                except Exception:
                    logger.exception(msg)
                await asyncio.sleep(round_backoff)
                round_backoff = min(backoff * 8, round_backoff * 2)

        return wrapper

    return decorator
