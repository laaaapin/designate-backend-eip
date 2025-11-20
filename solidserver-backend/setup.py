#!/usr/bin/env python
"""
Setup script for designate-solidserver-backend
"""

from setuptools import setup, find_packages
import os

# Read long description if available
long_description = ''
if os.path.exists('README.rst'):
    with open('README.rst') as f:
        long_description = f.read()

setup(
    name='designate-solidserver-backend',
    version='1.0.0',
    description='SOLIDserver DNS backend for OpenStack Designate',
    long_description=long_description,
    author='Your Organization',
    author_email='support@example.com',
    url='https://github.com/example/designate-solidserver-backend',
    py_modules=['solidserver_backend'],
    install_requires=[
        'designate>=12.0.0',
        'oslo.log>=4.0.0',
        'oslo.config>=8.0.0',
        'requests>=2.25.0',
    ],
    entry_points={
        'designate.backend': [
            'solidserver = solidserver_backend:SolidServerBackend',
        ],
    },
    classifiers=[
        'Environment :: OpenStack',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
)
