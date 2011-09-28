# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2011 Nebula, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


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

