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

"""
URL patterns for the OpenStack Dashboard.
"""

import os
import logging
from glob import glob


from django import shortcuts
from django.core import exceptions
from django.conf.urls.defaults import *
from django.conf.urls.static import static
from django.conf import settings
from django.contrib import messages
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.utils.importlib import import_module
from django.views import generic as generic_views
import django.views.i18n


LOG = logging.getLogger(__name__)

topbars = []


def get_topbar_name(file_name):
    return os.path.basename(os.path.dirname(os.path.abspath(file_name)))


class TopbarRoleCheckMiddleware(object):
    def __init__(self):
        if not hasattr(self, "topbar"):
            self.topbar = self.__class__.__module__.split('.')[2]

    def process_request(self, request):
        if "username" not in request.session:
            return
        script_name = settings.SCRIPT_NAME
        if not request.path.startswith(script_name):
            return
        path = request.path[len(script_name) + 1:]
        if not (path == self.topbar or path.startswith(self.topbar + "/")):
            return
        if not (self.roles & set(request.session["roles"])):
            # flush other error messages
            for message in messages.get_messages(request):
                pass
            messages.error(request, 
                           "Access denied for user %s at topbar %s" %
                           (request.session["username"],
                           self.topbar))
            return shortcuts.redirect("auth/splash")
