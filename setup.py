#!/usr/bin/python
# coding: utf-8
#
# Copyright (C) 2018 Kristian Sloth Lauszus. All rights reserved.
#
# Contact information
# -------------------
# Kristian Sloth Lauszus
# Web      :  http://www.lauszus.com
# e-mail   :  lauszus@gmail.com

import re
from setuptools import setup, find_packages

with open('python_can_viewer/__init__.py', 'r') as f:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        f.read(), re.MULTILINE).group(1)

with open('README.md', 'r') as f:
    long_description = f.read()

tests_require = [
    'future',
    'mock',
    'pytest',
    'pytest-runner',
    'coverage',
    'codecov',
]

extras_require = {
    'test': tests_require,
}

setup(
    name='Python CAN Viewer',
    url='https://github.com/Lauszus/python_can_viewer',
    description='A simple CAN viewer terminal application written in Python',
    long_description=long_description,
    long_description_content_type='text/markdown',
    version=version,
    packages=find_packages(),
    author='Kristian Sloth Lauszus',
    author_email='lauszus@gmail.com',
    license='GPLv2',
    include_package_data=True,
    zip_safe=False,
    python_requires='>=2.7',
    install_requires=['python-can>=2.0.0', 'six', 'typing', 'windows-curses;platform_system=="Windows"'],
    extras_require=extras_require,
    tests_require=tests_require,
    classifiers=(
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: OS Independent',
    ),
)
