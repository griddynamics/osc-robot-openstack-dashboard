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
from django.conf import settings
from django.contrib import messages
from django.utils.importlib import import_module
import django.views.i18n

from openstack_dashboard.plugins import topbars


LOG = logging.getLogger(__name__)


urlpatterns = patterns('',
    url(r'^$', 'openstack_dashboard.plugins.auth.views.splash', name='splash'),
)


class PluginsMiddleware(object):
    MIDDLEWARE_CLASSES = ()

    def __init__(self):
        self._request_middleware = []
        self._view_middleware = []
        self._template_response_middleware = []
        self._response_middleware = []
        self._exception_middleware = []
        print "classes %s" %(PluginsMiddleware.MIDDLEWARE_CLASSES,)
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
        print "qqq:::::::::::"
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


class FeaturesMiddleware(object):
    FEATURES = set()

    def process_request(self, request):
        request.__class__.features = FeaturesMiddleware.FEATURES


for pattern_file in glob(os.path.dirname(os.path.abspath(__file__)) + "/*/*.py"):
    topbar = os.path.basename(os.path.dirname(pattern_file))
    sidebar = os.path.basename(pattern_file)[:-3]
    topbars.append(topbar)
    sidebar_module_name = "openstack_dashboard.plugins." + topbar
    if sidebar != "__init__":
        sidebar_module_name += "." + sidebar
    try:
        sidebar_module = import_module(sidebar_module_name)
    except ImportError, e:
        LOG.exception("cannot load %s" % sidebar_module_name)
        continue
    LOG.info("loaded plugin %s" % sidebar_module_name)
    try:
        sidebar_module.urlpatterns
    except AttributeError:
        pass
    else:
        urlpatterns += patterns('', url(r'^' + topbar + '/', include(sidebar_module_name)))
        LOG.info("loaded urlpatterns from %s" % sidebar_module_name)
    try:
        sidebar_module.MIDDLEWARE_CLASSES
    except AttributeError:
        pass
    else:
        for mw_classname in sidebar_module.MIDDLEWARE_CLASSES:
            PluginsMiddleware.MIDDLEWARE_CLASSES += (sidebar_module_name + "." + mw_classname,)
        LOG.info("loaded middleware %s.%s" % (sidebar_module_name, mw_classname))
    try:
        sidebar_module.FEATURES
    except AttributeError:
        pass
    else:
        FeaturesMiddleware.FEATURES.update(sidebar_module.FEATURES)
        LOG.info("loaded features %s from %s" % (list(sidebar_module.FEATURES), sidebar_module_name))

print urlpatterns
