#!/usr/bin/env python
# -*- coding: utf-8 -*-
try:
    from setuptools import setup
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup

setup(
    name='litesimple',
    version='0.1.0',
    description='Simple python ORM micro-framework for sqlite3',
    author='Jonatan Nilsson',
    license='WTFPL-2',
    author_email='jonatan@nilsson.is',
    url='https://github.com/TheThing/litesimple',
    long_description=open('readme.md', 'r').read(),
    py_modules=['litesimple'],
    scripts=['litesimple.py'],
    requires=[],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Plugins',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Database',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries',
    ],
)