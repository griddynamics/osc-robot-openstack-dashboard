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

from django import shortcuts
from django import template
from django import http
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.shortcuts import redirect
from django.utils.translation import ugettext as _

import datetime
import json
import logging

from django.contrib import messages

from django_openstack import api
from django_openstack import auth
from django_openstack import forms
from django_openstack.user import instances as dash_instances
from openstackx.api import exceptions as api_exceptions
from django_openstack.urls import get_topbar_name

topbar = get_topbar_name(__file__)
USERS = r'^users/(?P<user_id>[^/]+)/%s$'

urlpatterns = patterns(__name__,
    url(r'^$', 'index', name=topbar),
    url(r'^users/$', 'index', name=topbar + '/users'),
    url(USERS % 'update', 'update', name=topbar + '/users_update'),
    url(r'^users/create$', 'create', name=topbar + '/users_create'),
)
LOG = logging.getLogger(__name__)

class UserForm(forms.SelfHandlingForm):
    id = forms.CharField(label="ID (username)")
    email = forms.CharField(label="Email", required=False)
    password = forms.CharField(label="Password", widget=forms.PasswordInput(render_value=False), required=False)

    def __init__(self, *args, **kwargs):
        if 'user_id' in kwargs:
            self.user_id = kwargs.pop('user_id')
        super(UserForm, self).__init__(*args, **kwargs)

    def handle(self, request, data):
        if request.session.has_key('victim_user_global_roles'):
            self.victim_user_global_roles = request.session['victim_user_global_roles']
            del request.session['victim_user_global_roles']
        else:
            self.victim_user_global_roles = set()
        if self.is_valid():
            self._handle(request, data)
            if self.updated:
                messages.success(request,
                                 'Updated %s for %s.'
                                 % (', '.join(self.updated), self.user_id))
            return redirect(topbar + '/users')
        else:
            # TODO add better error management
            messages.error(request, 'Unable to update user,\
                                    please try again.')

            return render_to_response(
            topbar + '/user_update.html',{
                'self': self,
                'user_id': self.user_id,
            }, context_instance = template.RequestContext(request))

    def _handle(self, request, data):
        self.user = self.clean()
        self.updated = []
        self.user_id = self.user['id']
        try:
            api.user_get(request, self.user_id)
        except api_exceptions.ApiException:  # user does not exist, creating...
            LOG.info('Creating user with id "%s"' % self.user['id'])
            try:
                api.user_create(request,
                                self.user['id'],
                                self.user['email'],
                                self.user['password'],
                                None,
                                True)
                messages.success(request,
                                 '%s was successfully created.'
                                 % self.user['id'])
                return redirect(topbar + '/users')
            except api_exceptions.ApiException, e:
                LOG.error('ApiException while creating user\n'
                          'id: "%s", email: "%s"' %
                          (self.user['id'], self.user['email']),
                          exc_info=True)
                messages.error(request,
                                 'Error creating user: %s'
                                 % e.message)
            return redirect(topbar + '/users')
        else:  # edit user
            if self.user['email']:
                self.updated.append('email')
                api.user_update_email(request, self.user['id'], self.user['email'])
            if self.user['password']:
                self.updated.append('password')
                api.user_update_password(request, self.user['id'], self.user['password'])
            return redirect(topbar + '/users')



class UserEditAdminForm(UserForm):
    is_softadmin = forms.BooleanField(label="Software Admin", required=False, initial=False) 
    is_hardadmin = forms.BooleanField(label="Hardware Admin", required=False, initial=False)

    def _handle(self, request, data):
        super(UserEditAdminForm, self)._handle(request, data)
        for admin_role in [auth.Roles.SOFTWARE_ADMIN, auth.Roles.HARDWARE_ADMIN]: # edit user
            field_name = 'is_' + admin_role
            if self.user.has_key(field_name) and self.user[field_name] != (admin_role in self.victim_user_global_roles):
                if self.user[field_name]:
                    api.account_api(request).role_refs. \
                        add_for_tenant_user(None, self.user['id'], admin_role)
                    self.updated.append(field_name)
                elif self.user['id'] != request.user.username:
                    api.account_api(request).role_refs. \
                        delete_for_tenant_user(None, self.user['id'], admin_role)
                    self.updated.append(field_name)


def get_user_form(request):
    return UserEditAdminForm if "hardadmin" in request.user.roles else UserForm


class UserDeleteForm(forms.SelfHandlingForm):
    user = forms.CharField(required=True)

    def handle(self, request, data):
        user_id = data['user']
        LOG.info('Deleting user with id "%s"' % user_id)
        api.user_delete(request, user_id)
        messages.info(request, '%s was successfully deleted.'
                                % user_id)
            
        return redirect(request.build_absolute_uri())


class UserEnableDisableForm(forms.SelfHandlingForm):
    id = forms.CharField(label="ID (username)", widget=forms.HiddenInput())
    enabled = forms.ChoiceField(label="enabled", widget=forms.HiddenInput(),
                                choices=[[c, c]
                                         for c in ("disable", "enable")])

    def handle(self, request, data):
        user_id = data['id']
        enabled = data['enabled'] == "enable"

        try:
            api.user_update_enabled(request, user_id, enabled)
            messages.info(request, "User %s %s" %
                                   (user_id,
                                    "enabled" if enabled else "disabled"))
        except api_exceptions.ApiException:
            messages.error(request, "Unable to %s user %s" %
                                    ("enable" if enabled else "disable",
                                     user_id))

        return redirect(request.build_absolute_uri())


@login_required
def index(request):
    for f in (UserDeleteForm, UserEnableDisableForm):
        _, handled = f.maybe_handle(request)
        if handled:
            return handled

    users = []
    try:
        users = api.user_list(request)
    except api_exceptions.ApiException, e:
        messages.error(request, 'Unable to list users: %s' %
                                 e.message)
   
    user_delete_form = UserDeleteForm()
    user_enable_disable_form = UserEnableDisableForm()
    
    return shortcuts.render_to_response(topbar + '/user_view.html', {
        'users': users,
        'user_delete_form': user_delete_form,
        'user_enable_disable_form': user_enable_disable_form,
    }, context_instance=template.RequestContext(request))


@login_required
def update(request, user_id):
    for form in (get_user_form(request),):
        _, handle = form.maybe_handle(request, user_id=user_id)
        if handle:
            return handle
    u = api.user_get(request, user_id)
    request.session['victim_user_global_roles'] = u.global_roles
    try:
        # FIXME
        email = u.email
    except AttributeError:
        email = '<none>'
    form = get_user_form(request)(user_id=user_id, initial={'id': user_id,
                             'email': email,
                             'is_hardadmin': "hardadmin" in u.global_roles,
                             'is_softadmin': "softadmin" in u.global_roles})
    return render_to_response(
    topbar + '/user_update.html',{
        'form': form,
        'user_id': user_id,
    }, context_instance = template.RequestContext(request))

@login_required
def create(request):
    for form in (get_user_form(request),):
        _, handle = form.maybe_handle(request)
        if handle:
            return handle
    form = get_user_form(request)()
    return render_to_response(
    topbar + '/user_create.html',{
        'form': form,
    }, context_instance = template.RequestContext(request))
