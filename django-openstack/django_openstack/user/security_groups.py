# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2011 Fourth Paradigm Development, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Views for managing Nova instances.
"""
import logging

from django import http
from django import template
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import validators
from django import shortcuts
from django.shortcuts import redirect, render_to_response
from django.utils.translation import ugettext as _

from django_openstack import api
from django_openstack import forms
import openstackx.api.exceptions as api_exceptions
from django_openstack.urls import get_topbar_name


topbar = get_topbar_name(__file__)
SECURITY_GROUPS = r'^(?P<tenant_id>[^/]+)/security_groups/(?P<security_group_id>[^/]+)/%s$'

urlpatterns = patterns(__name__,
    url(r'^(?P<tenant_id>[^/]+)/security_groups/$', 'index', name=topbar + '/security_groups'),
    url(r'^(?P<tenant_id>[^/]+)/security_groups/create$', 'create', name=topbar + '/security_groups_create'),
    url(SECURITY_GROUPS % 'edit_rules', 'edit_rules', name=topbar + '/security_groups_edit_rules'),
)

LOG = logging.getLogger('django_openstack.dash.views.security_groups')


class CreateGroup(forms.SelfHandlingForm):
    name = forms.CharField(validators=[validators.validate_slug])
    description = forms.CharField()
    tenant_id = forms.CharField(widget=forms.HiddenInput())
    def handle(self, request, data):
        try:
            LOG.info('Add security_group: "%s"' % data)

            security_group = api.security_group_create(request,
                                                       data['name'],
                                                       data['description'])
            messages.info(request, 'Successfully created security_group: %s' \
                                    % data['name'])
        except api_exceptions.ApiException, e:
            LOG.error("ApiException in CreateGroup", exc_info=True)
            messages.error(request, 'Error creating security group: %s' % e.message)
        return shortcuts.redirect(topbar + '/security_groups', data['tenant_id'])


class DeleteGroup(forms.SelfHandlingForm):
    tenant_id = forms.CharField(widget=forms.HiddenInput())
    security_group_id = forms.CharField(widget=forms.HiddenInput())
    def handle(self, request, data):
        try:
            LOG.info('Delete security_group: "%s"' % data)

            security_group = api.security_group_delete(request, data['security_group_id'])
            messages.info(request, 'Successfully deleted security_group: %s' \
                                    % data['security_group_id'])
        except api_exceptions.ApiException, e:
            LOG.error("ApiException in DeleteGroup", exc_info=True)
            messages.error(request, 'Error deleting security group: %s' % e.message)
        return shortcuts.redirect(topbar + '/security_groups', data['tenant_id'])


class AddRule(forms.SelfHandlingForm):
    ip_protocol = forms.ChoiceField(choices=[('tcp', 'tcp'), ('udp', 'udp'), ('icmp', 'icmp')])
    from_port = forms.IntegerField()
    to_port = forms.IntegerField()
    cidr = forms.CharField()
# group_id = forms.CharField()

    security_group_id = forms.CharField(widget=forms.HiddenInput())
    tenant_id = forms.CharField(widget=forms.HiddenInput())

    def handle(self, request, data):
        tenant_id = data['tenant_id']
        try:
            LOG.info('Add security_group_rule: "%s"' % data)

            security_group = api.security_group_rule_create(request,
                                                     data['security_group_id'],
                                                     data['ip_protocol'],
                                                     data['from_port'],
                                                     data['to_port'],
                                                     data['cidr'])
            messages.info(request, 'Successfully added rule: %s' \
                                    % security_group.id)
        except api_exceptions.ApiException, e:
            LOG.error("ApiException in AddRule", exc_info=True)
            messages.error(request, 'Error adding rule security group: %s' % e.message)
        return shortcuts.redirect(request.build_absolute_uri())


class DeleteRule(forms.SelfHandlingForm):
    security_group_rule_id = forms.CharField(widget=forms.HiddenInput())
    security_group_id = forms.CharField(widget=forms.HiddenInput())
    tenant_id = forms.CharField(widget=forms.HiddenInput())
    def handle(self, request, data):
        security_group_rule_id = data['security_group_rule_id']
        tenant_id = data['tenant_id']
        try:
            LOG.info('Delete security_group_rule: "%s"' % data)

            security_group = api.security_group_rule_delete(
                                                request,
                                                security_group_rule_id)
            messages.info(request, 'Successfully deleted rule: %s' \
                                    % security_group_rule_id)
        except api_exceptions.ApiException, e:
            LOG.error("ApiException in DeleteRule", exc_info=True)
            messages.error(request, 'Error authorizing security group: %s' % e.message)
        return shortcuts.redirect(request.build_absolute_uri())


@login_required
def index(request, tenant_id):
    delete_form, handled = DeleteGroup.maybe_handle(request,
                                initial={ 'tenant_id': tenant_id })

    if handled:
        return handled

    try:
        security_groups = api.security_group_list(request)
    except api_exceptions.ApiException, e:
        security_groups = []
        LOG.error("ApiException in security_groups index", exc_info=True)
        messages.error(request, 'Error fetching security_groups: %s' % e.message)

    return shortcuts.render_to_response(topbar + '/security_groups_view.html', {
        'security_groups': security_groups,
        'delete_form': delete_form,
    }, context_instance=template.RequestContext(request))


@login_required
def edit_rules(request, tenant_id, security_group_id):
    add_form, handled = AddRule.maybe_handle(request,
                              initial={ 'tenant_id': tenant_id,
                                        'security_group_id': security_group_id })
    if handled:
        return handled

    delete_form, handled = DeleteRule.maybe_handle(request,
                              initial={ 'tenant_id': tenant_id,
                                        'security_group_id': security_group_id })
    if handled:
        return handled

    try:
        security_group = api.security_group_get(request, security_group_id)
    except api_exceptions.ApiException, e:
        LOG.error("ApiException in security_groups rules edit", exc_info=True)
        messages.error(request, 'Error fetching security_group: %s' % e.message)
        return shortcuts.redirect(topbar + '/security_groups', tenant_id)

    return shortcuts.render_to_response(topbar + '/security_groups_edit_rules.html', {
        'security_group': security_group,
        'delete_form': delete_form,
        'form': add_form,
    }, context_instance=template.RequestContext(request))


@login_required
def create(request, tenant_id):
    form, handled = CreateGroup.maybe_handle(request,
                                initial={ 'tenant_id': tenant_id })
    if handled:
        return handled

    return shortcuts.render_to_response(topbar + '/security_group_create.html', {
        'form': form,
    }, context_instance=template.RequestContext(request))
