# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2011 Fourth Paradigm Development, Inc.
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

from django.conf.urls.defaults import *
from django.conf import settings
import os
from glob import glob


def get_topbar_name(file_name):
    return os.path.basename(os.path.dirname(os.path.abspath(file_name)))


urlpatterns = []

for pattern_file in glob(os.path.dirname(os.path.abspath(__file__)) + "/*/*.py"):
    topbar = os.path.basename(os.path.dirname(pattern_file))
    sidebar = os.path.basename(pattern_file)[:-3]
    if sidebar == "__init__":
        continue
    sidebar_module_name = "django_openstack" + "." + topbar + "." + sidebar
    try:
        sidebar_module = __import__(sidebar_module_name, fromlist="django_openstack." + topbar)
        sidebar_module.urlpatterns
    except (ImportError, AttributeError):
        continue
    urlpatterns += patterns('', url(r'^' + topbar + '/', include(sidebar_module_name)))
