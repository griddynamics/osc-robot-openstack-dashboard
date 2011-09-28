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

from openstack_dashboard import api 
from openstack_dashboard.plugins import auth
from openstack_dashboard import forms
from openstackx.api import exceptions as api_exceptions
from openstack_dashboard.plugins import get_topbar_name


topbar = get_topbar_name(__file__)
TENANTS = r'^tenants/(?P<tenant_id>[^/]+)/%s$'
urlpatterns = patterns(__name__,
    url(r'^$', 'index', name=topbar),
    url(r'^tenants/$', 'index', name=topbar + '/tenants'),
    url(r'^tenants/create$', 'create', name=topbar + '/tenant_create'),
    url(TENANTS % 'update', 'update', name=topbar + '/tenant_update'),
    url(TENANTS % 'users', 'users', name=topbar + '/tenant_users'),
    url(TENANTS % 'quotas', 'quotas', name=topbar + '/tenant_quotas'),
)
LOG = logging.getLogger(__name__)


class AddUser(forms.SelfHandlingForm):
    user = forms.CharField()
    tenant = forms.CharField()

    def handle(self, request, data):
        try:
            api.account_api(request).role_refs.add_for_tenant_user(data['tenant'],
                data['user'], auth.Roles.PROJECT_ADMIN)
            messages.success(request,
                             '%s was successfully added to admins of %s.'
                             % (data['user'], data['tenant']))
        except api_exceptions.ApiException, e:
            messages.error(request, 'Unable to create user association: %s' %
                           (e.message))
        return redirect(request.build_absolute_uri())

    
class RemoveUser(forms.SelfHandlingForm):
    user = forms.CharField()
    tenant = forms.CharField()

    def handle(self, request, data):
        try:
            api.account_api(request).role_refs.delete_for_tenant_user(data['tenant'],
                    data['user'], auth.Roles.PROJECT_ADMIN)
            messages.success(request,
                             '%s was successfully removed from admins of %s.'
                             % (data['user'], data['tenant']))
        except api_exceptions.ApiException, e:
            messages.error(request, 'Unable to create tenant: %s' %
                           (e.message))
        return redirect(request.build_absolute_uri())


class CreateTenant(forms.SelfHandlingForm):
    id = forms.SlugField(label="ID (name)")
    description = forms.CharField(widget=forms.widgets.Textarea(), label="Description")
    enabled = forms.BooleanField(label="Enabled", required=False, initial=True)

    def handle(self, request, data):
        try:
            LOG.info('Creating tenant with id "%s"' % data['id'])
            api.tenant_create(request,
                              data['id'],
                              data['description'],
                              data['enabled'])
            api.tenant_append_endpoints(request, 
                                        data['id'], 
                                        settings.OPENSTACK_ENDPOINT_TEMPLATES)
            messages.success(request,
                             '%s was successfully created.'
                             % data['id'])
        except api_exceptions.ApiException, e:
            LOG.error('ApiException while creating tenant\n'
                      'Id: "%s", Description: "%s", Enabled "%s"' %
                      (data['id'], data['description'], data['enabled']),
                      exc_info=True)
            messages.error(request, 'Unable to create tenant: %s' %
                           (e.message))
        return redirect(topbar + '/tenants')


class UpdateTenant(forms.SelfHandlingForm):
    id = forms.CharField(label="ID (name)", widget=forms.TextInput(attrs={'readonly':'readonly'}))
    description = forms.CharField(widget=forms.widgets.Textarea(), label="Description")
    enabled = forms.BooleanField(label="Enabled", required=False)

    def handle(self, request, data):
        try:
            LOG.info('Updating tenant with id "%s"' % data['id'])
            api.tenant_update(request,
                              data['id'],
                              data['description'],
                              data['enabled'])
            messages.success(request,
                             '%s was successfully updated.'
                             % data['id'])
        except api_exceptions.ApiException, e:
            LOG.error('ApiException while updating tenant\n'
                      'Id: "%s", Description: "%s", Enabled "%s"' %
                      (data['id'], data['description'], data['enabled']),
                      exc_info=True)
            messages.error(request, 'Unable to update tenant: %s' % e.message)
        return redirect(topbar + '/tenants')


class DeleteTenantForm(forms.SelfHandlingForm):
    tenant = forms.CharField(required=True)
    scrub = forms.BooleanField(required=False, initial=False)

    def handle(self, request, data):
        tenant_id = data['tenant']
        scrub = data['scrub']
        LOG.info('Deleting project with id "%s"' % tenant_id)
        api.tenant_delete(request, tenant_id)
        # TODO(nsokolov): delete project too
        if scrub:
            try:
                api.project_scrub(request, tenant_id)
            except AttributeError:
                LOG.debug(_('your openstackx library does not support project_scrub'))
        messages.info(request, '%s was successfully deleted.'
                                % tenant_id)

        return redirect(request.build_absolute_uri())


class UpdateQuotas(forms.SelfHandlingForm):
    tenant_id = forms.CharField(label="ID (name)", widget=forms.TextInput(attrs={'readonly':'readonly'}))
    metadata_items = forms.CharField(label="Metadata Items")
    injected_files = forms.CharField(label="Injected Files")
    injected_file_content_bytes = forms.CharField(label="Injected File Content Bytes")
    cores = forms.CharField(label="VCPUs")
    instances = forms.CharField(label="Instances")
    volumes = forms.CharField(label="Volumes")
    gigabytes = forms.CharField(label="Gigabytes")
    ram = forms.CharField(label="RAM (in MB)")
    floating_ips = forms.CharField(label="Floating IPs")

    def handle(self, request, data):
        try:
            api.admin_api(request).quota_sets.update(data['tenant_id'],
                          metadata_items=data['metadata_items'],
                          injected_file_content_bytes=
                          data['injected_file_content_bytes'],
                          volumes=data['volumes'],
                          gigabytes=data['gigabytes'],
                          ram=int(data['ram']) * 100,
                          floating_ips=data['floating_ips'],
                          instances=data['instances'],
                          injected_files=data['injected_files'],
                          cores=data['cores'],
            )
            messages.success(request,
                             'Quotas for %s were successfully updated.'
                             % data['tenant_id'])
        except api_exceptions.ApiException, e:
            messages.error(request, 'Unable to update quotas: %s' % e.message)
        return redirect(topbar + '/tenants')


@login_required
def index(request):
    for f in (DeleteTenantForm,):
        _, handled = f.maybe_handle(request)
        if handled:
            return handled

    tenants = []
    try:
        tenants = api.tenant_list(request)
    except api_exceptions.ApiException, e:
        LOG.error('ApiException while getting tenant list', exc_info=True)
        messages.error(request, 'Unable to get tenant info: %s' % e.message)

    tenant_delete_form = DeleteTenantForm()

    tenants.sort(key=lambda x: x.id, reverse=True)
    return render_to_response(topbar + '/tenant_view.html',{
        'tenants': tenants,
        'tenant_delete_form': tenant_delete_form,
    }, context_instance = template.RequestContext(request))


@login_required
def create(request):
    form, handled = CreateTenant.maybe_handle(request)
    if handled:
        return handled

    return render_to_response(
    topbar + '/tenant_create.html',{
        'form': form,
    }, context_instance = template.RequestContext(request))


@login_required
def update(request, tenant_id):
    form, handled = UpdateTenant.maybe_handle(request)
    if handled:
        return handled

    if request.method == 'GET':
        try:
            tenant = api.tenant_get(request, tenant_id)
            form = UpdateTenant(initial={'id': tenant.id,
                                         'description': tenant.description,
                                         'enabled': tenant.enabled})
        except api_exceptions.ApiException, e:
            LOG.error('Error fetching tenant with id "%s"' % tenant_id,
                      exc_info=True)
            messages.error(request, 'Unable to update tenant: %s' % e.message)
            return redirect(topbar + '/tenants')

    return render_to_response(
    topbar + '/tenant_update.html',{
        'form': form,
    }, context_instance = template.RequestContext(request))


@login_required
def users(request, tenant_id):
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
    new_user_ids = set([u.id for u in all_users if auth.Roles.needs_tenant(api.User(u).global_roles)]) - set([u['id'] for u in users])
    users = [user for user in users if auth.Roles.PROJECT_ADMIN in user["tenantRoles"]]
    return render_to_response(
    topbar + '/tenant_users.html',{
        'add_user_form': add_user_form,
        'remove_user_form': remove_user_form,
        'tenant_id': tenant_id,
        'users': users,
        'new_users': new_user_ids,
    }, context_instance = template.RequestContext(request))


@login_required
def quotas(request, tenant_id):
    for f in (UpdateQuotas,):
        _, handled = f.maybe_handle(request)
        if handled:
            return handled

    quotas = api.admin_api(request).quota_sets.get(tenant_id)
    quota_set = {
        'tenant_id': quotas.id,
        'metadata_items': quotas.metadata_items,
        'injected_file_content_bytes': quotas.injected_file_content_bytes,
        'volumes': quotas.volumes,
        'gigabytes': quotas.gigabytes,
        'ram': int(quotas.ram) / 100,
        'floating_ips': quotas.floating_ips,
        'instances': quotas.instances,
        'injected_files': quotas.injected_files,
        'cores': quotas.cores,
    }
    form = UpdateQuotas(initial=quota_set)

    return render_to_response(
    topbar + '/tenant_quotas.html',{
        'form': form,
        'tenant_id': tenant_id,
        'quotas': quotas,
    }, context_instance = template.RequestContext(request))
