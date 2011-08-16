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
from django.core import exceptions
from django.utils.importlib import import_module
from django.contrib import messages
from django import shortcuts
import os
from glob import glob


def get_topbar_name(file_name):
    return os.path.basename(os.path.dirname(os.path.abspath(file_name)))


urlpatterns = []
topbars = []

class PluginsMiddleware(object):
    MIDDLEWARE_CLASSES = ()

    def __init__(self):
        self._request_middleware = []
        self._view_middleware = []
        self._template_response_middleware = []
        self._response_middleware = []
        self._exception_middleware = []

        for middleware_path in PluginsMiddleware.MIDDLEWARE_CLASSES:
            try:
                mw_module, mw_classname = middleware_path.rsplit('.', 1)
            except ValueError:
                raise exceptions.ImproperlyConfigured('%s isn\'t a middleware module' % middleware_path)
            try:
                mod = import_module(mw_module)
            except ImportError, e:
                raise exceptions.ImproperlyConfigured('Error importing middleware %s: "%s"' % (mw_module, e))
            try:
                mw_class = getattr(mod, mw_classname)
            except AttributeError:
                raise exceptions.ImproperlyConfigured('Middleware module "%s" does not define a "%s" class' % (mw_module, mw_classname))
            except ImportError, e:
                continue
            try:
                mw_instance = mw_class()
            except exceptions.MiddlewareNotUsed:
                continue
            if hasattr(mw_instance, 'process_request'):
                self._request_middleware.append(mw_instance.process_request)
            if hasattr(mw_instance, 'process_view'):
                self._view_middleware.append(mw_instance.process_view)
            if hasattr(mw_instance, 'process_template_response'):
                self._template_response_middleware.insert(0, mw_instance.process_template_response)
            if hasattr(mw_instance, 'process_response'):
                self._response_middleware.insert(0, mw_instance.process_response)
            if hasattr(mw_instance, 'process_exception'):
                self._exception_middleware.insert(0, mw_instance.process_exception)

    def process_request(self, request):
        response = None
        for middleware_method in self._request_middleware:
            response = middleware_method(request)
            if response:
                return response

    def process_view(self, request, callback, callback_args, callback_kwargs):
        response = None
        for middleware_method in self._view_middleware:
            response = middleware_method(request, callback, callback_args, callback_kwargs)
            if response:
                return response

    def process_template_response(self, request, response):
        for middleware_method in self._template_response_middleware:
            response = middleware_method(request, response)
        return response

    def process_response(self, request, response):
        for middleware_method in self._response_middleware:
            response = middleware_method(request, response)
        return response

    def process_exception(self, request, exception):
        for middleware_method in self._exception_middleware:
            response = middleware_method(request, e)
            if response:
                return response


class TopbarRoleCheckMiddleware(object):
    def __init__(self):
        if not hasattr(self, "topbar"):
            self.topbar = self.__class__.__module__.split('.')[1]

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
            return shortcuts.redirect("splash")


class FeaturesMiddleware(object):
    FEATURES = set()

    def process_request(self, request):
        request.__class__.features = FeaturesMiddleware.FEATURES


for pattern_file in glob(os.path.dirname(os.path.abspath(__file__)) + "/*/*.py"):
    topbar = os.path.basename(os.path.dirname(pattern_file))
    sidebar = os.path.basename(pattern_file)[:-3]
    topbars.append(topbar)
    if sidebar == "__init__":
        sidebar_module_name = "django_openstack" + "." + topbar
    else:
        sidebar_module_name = "django_openstack" + "." + topbar + "." + sidebar
    try:
        sidebar_module = import_module(sidebar_module_name)
    except ImportError:
        continue
    try:
        sidebar_module.urlpatterns
        urlpatterns += patterns('', url(r'^' + topbar + '/', include(sidebar_module_name)))
    except AttributeError:
        pass
    try:
        for mw_classname in sidebar_module.MIDDLEWARE_CLASSES:
            PluginsMiddleware.MIDDLEWARE_CLASSES += (sidebar_module_name + "." + mw_classname,)
    except AttributeError:
        pass
    try:
        FeaturesMiddleware.FEATURES.update(sidebar_module.FEATURES)
    except AttributeError:
        pass
