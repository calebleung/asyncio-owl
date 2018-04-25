#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from setuptools import setup

with open("README.md") as f:
    readme = f.read()

with open(os.path.join(os.path.dirname(__file__), 'requirements.txt')) as f:
    required = f.read().splitlines()

with open(os.path.join(os.path.dirname(__file__), 'test_requirements.txt')) as f:
    test_required = f.read().splitlines() + required

setup(
    name='asyncio_owl',
    version='0.0.1',
    description="An asyncio wrapper for the overwatch league api",
    long_description=readme + '\n',
    url='https://github.com/calebleung/asyncio-owl',
    packages=[
        'asyncio_owl',
    ],
    include_package_data=True,
    install_requires=required,
    license="MIT license",
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
    ],
    test_suite='tests',
    tests_require=test_required,

)
