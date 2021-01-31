#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of walt
# https://github.com/scorphus/walt

# Licensed under the BSD-3-Clause license:
# https://opensource.org/licenses/BSD-3-Clause
# Copyright (c) 2021, Pablo S. Blum de Aguiar <scorphus@gmail.com>

from setuptools import find_packages
from setuptools import setup
from walt import __version__

import os


def read(*rnames):
    with open(os.path.join(os.path.dirname(__file__), *rnames)) as f:
        return f.read()


extras_require = {
    "tests": [
        "autopep8",
        "black",
        "coverage",
        "flake8",
        "ipdb",
        "isort",
        "pylint",
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "pytest-mock",
    ],
}

setup(
    name="walt",
    version=__version__,
    url="https://github.com/scorphus/walt",
    license="BSD-3-Clause",
    description="Website Availability Monitor",
    keywords="website availability monitor",
    long_description=read("README.md"),
    classifiers=[
        "License :: OSI Approved :: 3-Clause BSD License License",
        "Programming Language :: Python",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    author="Pablo S. Blum de Aguiar",
    author_email="scorphus@gmail.com",
    packages=find_packages(),
    install_requires=[
        "aiohttp",
        "aiokafka",
        "toml",
    ],
    extras_require=extras_require,
    entry_points={"console_scripts": ["walt = walt.main:walt"]},
    include_package_data=True,
    zip_safe=False,
)
