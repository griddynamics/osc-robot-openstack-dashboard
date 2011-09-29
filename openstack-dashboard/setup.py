#!/usr/bin/env python
import os
from setuptools import setup, find_packages, findall

setup(
    name = "openstack_dashboard",
    version = "1.0",
    url = 'https://launchpad.net/openstack-dashboard',
    license = 'Apache 2.0',
    description = "Django based reference implementation of a web based management interface for OpenStack.",
#    packages = find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests", "local"]),
    packages = ['dashboard', 'media'],
#    package_data = {'openstack_dashboard':
#                        [s[len('openstack_dashboard/'):] for s in
#                        findall('openstack_dashboard/templates') +
#                        findall('openstack_dashboard/wsgi') +
#                        findall('openstack_dashboard/locale') +
#                        findall('openstack_dashboard/static')],
#                    },
    package_data = {'dashboard':
                        [s[len('dashboard/'):] for s in
                        findall('dashboard/templates') + findall('dashboard/wsgi') + findall('dashboard/locale')],
                       'media': [s[len('media/'):] for s in findall('media')]
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

