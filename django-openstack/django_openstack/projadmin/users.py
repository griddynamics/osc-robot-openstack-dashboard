# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 Grid Dynamics Consulting Services, Inc.
# All rights reserved.
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

from django import template
from django import http
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.shortcuts import redirect
from django.utils.translation import ugettext as _

import logging

from django.contrib import messages

from django_openstack import api
from django_openstack import auth
from django_openstack import forms
from django_openstack.user import instances as dash_instances
from openstackx.api import exceptions as api_exceptions
from django_openstack.urls import get_topbar_name


topbar = get_topbar_name(__file__)
USERS = r'^users/(?P<tenant_id>[^/]+)/%s$'
urlpatterns = patterns(__name__,
    url(r'^users/$', 'users', name=topbar + '/users'),
)
LOG = logging.getLogger(__name__)


class AddUser(forms.SelfHandlingForm):
    user = forms.CharField()
    tenant = forms.CharField()

    def handle(self, request, data):
        try:
            api.account_api(request).role_refs.add_for_tenant_user(data['tenant'],
                    data['user'], auth.Roles.DEFAULT)
            messages.success(request,
                             '%s was successfully added to %s.'
                             % (data['user'], data['tenant']))
        except api_exceptions.ApiException, e:
            messages.error(request, 'Unable to create user association: %s' %
                           (e.message))
        return redirect(topbar + '/users')

class RemoveUser(forms.SelfHandlingForm):
    user = forms.CharField()
    tenant = forms.CharField()

    def handle(self, request, data):
        try:
            api.account_api(request).role_refs.delete_for_tenant_user(data['tenant'],
                    data['user'], auth.Roles.DEFAULT)
            messages.success(request,
                             '%s was successfully removed from %s.'
                             % (data['user'], data['tenant']))
        except api_exceptions.ApiException, e:
            messages.error(request, 'Unable to create tenant: %s' %
                           (e.message))
        return redirect(topbar + '/users')


@login_required
def users(request):
    tenant_id = request.user.tenant
    for f in (AddUser, RemoveUser,):
        _, handled = f.maybe_handle(request)
        if handled:
            return handled
#    form, handled = UpdateTenant.maybe_handle(request)
#    if handled:
#        return handled
    add_user_form = AddUser()
    remove_user_form = RemoveUser()

    users = api.account_api(request).users.get_for_tenant(tenant_id).values
    all_users = api.account_api(request).users.list()
    new_user_ids = set([u.id for u in all_users]) - set([u['id'] for u in users])
    users = [user for user in users if auth.Roles.DEFAULT in user["tenantRoles"]]
    return render_to_response(
    topbar + '/project_users.html',{
        'add_user_form': add_user_form,
        'remove_user_form': remove_user_form,
        'tenant_id': tenant_id,
        'users': users,
        'new_users': new_user_ids,
    }, context_instance = template.RequestContext(request))

