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

import logging

from django import template
from django import shortcuts
from django.contrib import messages
from django.conf.urls.defaults import *
from django.conf import settings
from django.views.decorators import vary

from openstack_dashboard import api
from openstack_dashboard.plugins import auth
from openstack_dashboard import forms
import openstackx
from openstackx.api import exceptions as api_exceptions
from openstack_dashboard.plugins import get_topbar_name


topbar = get_topbar_name(__file__)
urlpatterns = patterns(__name__,
    url(r'login/$', 'login', name=topbar + '/login'),
    url(r'logout/$', 'logout', name=topbar + '/logout'),
    url(r'switch/(?P<tenant_id>[^/]+)/$', 'switch_tenants', name=topbar + '/switch'),
    url(r'$', 'splash', name=topbar + '/splash'),
)
LOG = logging.getLogger(__name__)

def display_error(request, msg):
    LOG.error(msg, exc_info=True)
    messages.error(request, msg)


def handle_login(request, username, password, tenant):
    try:
        token = api.token_create(request, tenant, username, password)
        info = api.token_info(request, token)
        if auth.Roles.needs_tenant(info['roles']):
            if not tenant:
                for tenant_obj in api.token_list_tenants(request, token.id):
                    if not tenant_obj.enabled:
                        continue
                    try:
                        tenant = tenant_obj.id
                        token = api.token_create(request, tenant, username, password)
                        info = api.token_info(request, token)
                    except openstackx.api.exceptions.Unauthorized:
                       continue
                    break
                if not tenant:
                    display_error(request, 'No tenants/projects for user %s' % username)
                    return shortcuts.redirect(topbar + '/splash')
        else:
            info['roles'] -= set(auth.Roles.TENANTED_ROLES)

        request.session['token'] = token.id
        request.session['username'] = username
        request.session['password'] = password
        request.session['tenant'] = tenant
        request.session['roles'] = info['roles']
        request.session['serviceCatalog'] = token.serviceCatalog
        LOG.info('Login form for user "%s" on tenant "%s". Service Catalog data:\n%s' %
                 (username, tenant, token.serviceCatalog))

        return shortcuts.redirect(auth.Roles.get_default_page(info['roles']))

    except api_exceptions.Unauthorized as e:
        display_error(request, 'Error authenticating: %s' % e.message)
        return shortcuts.redirect(topbar + '/splash')
    except api_exceptions.ApiException as e:
        display_error(request, 'Error authenticating with keystone: %s' % e.message)
        return shortcuts.redirect(topbar + '/splash')


class Login(forms.SelfHandlingForm):
    username = forms.CharField(max_length="20", label="User Name")
    password = forms.CharField(max_length="20", label="Password",
                               widget=forms.PasswordInput(render_value=False))

    def handle(self, request, data):
        return handle_login(request, data['username'], data['password'], None)


def login(request):
    if request.user and request.user.is_authenticated():
        return shortcuts.redirect(auth.Roles.get_default_page(request.user.roles))

    form, handled = Login.maybe_handle(request)
    if handled:
        return handled

    return shortcuts.render_to_response(topbar + '/splash.html', {
        'form': form,
    }, context_instance=template.RequestContext(request))


def switch_tenants(request, tenant_id):
    try:
        return handle_login(request, request.session['username'], request.session['password'], tenant_id)
    except KeyError:
        return shortcuts.redirect(topbar + '/splash')


def logout(request):
    request.session.clear()
    return shortcuts.redirect(topbar + '/splash')


@vary.vary_on_cookie
def splash(request):
    return login(request)
