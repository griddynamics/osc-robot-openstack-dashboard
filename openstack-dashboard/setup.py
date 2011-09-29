#!/usr/bin/env python
import os
from setuptools import setup, find_packages, findall

setup(
    name = "openstack_dashboard",
    version = "1.0",
    url = 'https://launchpad.net/openstack-dashboard',
    license = 'Apache 2.0',
    description = "Django based reference implementation of a web based management interface for OpenStack.",
    packages = find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests", "local"]),
    package_data = {'openstack_dashboard':
                        [s[len('openstack_dashboard/'):] for s in
                        findall('openstack_dashboard/templates') +
                        findall('openstack_dashboard/wsgi') +
                        findall('openstack_dashboard/locale') +
                        findall('openstack_dashboard/static')],
                    },
    data_files = [('/etc/openstack_dashboard/local', findall('local')), ('/var/lib/openstack_dashboard', set())],
    classifiers = [
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ]
)

