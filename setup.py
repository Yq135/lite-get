#!/usr/bin/env python3

PROJ_NAME = 'lite-get'
PACKAGE_NAME = 'lite_get'

import importlib.machinery
import importlib.util


def load_source(modname, filename):
    loader = importlib.machinery.SourceFileLoader(modname, filename)
    spec = importlib.util.spec_from_file_location(modname, filename, loader=loader)
    module = importlib.util.module_from_spec(spec)
    # The module is always executed and not cached in sys.modules.
    # Uncomment the following line to cache the module.
    # sys.modules[module.__name__] = module
    loader.exec_module(module)
    return module


import os

here = os.path.abspath(os.path.dirname(__file__))
try:
    README = open(os.path.join(here, 'README.rst'), encoding='utf-8').read()
except:
    README = ""

VERSION = load_source('version', os.path.join(here, 'src/%s/version.py' % PACKAGE_NAME)).__version__

from setuptools import setup, find_packages

setup(
    name=PROJ_NAME,
    version=VERSION,

    author='kairon57',

    packages=find_packages('src'),
    package_dir={'': 'src'},

    test_suite='tests',

    platforms='any',
    zip_safe=True,
    include_package_data=True,

    entry_points={
        'console_scripts': [
            "lite-get = lite_get.__main__:main"
        ],
    },
)
