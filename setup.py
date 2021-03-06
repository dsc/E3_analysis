#!/usr/bin/python
# -*- coding: utf-8 -*-

from distutils.core import setup

with open('README.md') as file:
    long_description = file.read()

__version__ = '0.1.1'

setup(
    name='wmf_user_metrics',
    version=__version__,
    long_description=long_description,
    description='Data Analysis for Wikipedia User data.',
    url='http://www.github.com/rfaulkner/E3_analysis',
    author="Wikimedia Foundation",
    author_email="e3-team@lists.wikimedia.org",
    packages=['src.etl',
              'src.metrics',
              'src.utils',
              'config'],
    install_requires=[
        'numpy == 1.6.2',
        'Flask == 0.9',
        'python-dateutil >= 2.1',
        # MySQLdb is not in PyPi
    ],
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    data_files=[('readme', ['README.md'])]
)
