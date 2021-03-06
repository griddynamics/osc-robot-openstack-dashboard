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
Views for managing Nova floating ips.
"""
import logging

from django import template
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django import shortcuts
from django.conf.urls.defaults import *

from openstack_dashboard import api
from openstack_dashboard import forms
from novaclient import exceptions as novaclient_exceptions
from openstack_dashboard.plugins import get_topbar_name


topbar = get_topbar_name(__file__)

FLOATING_IPS = r'^(?P<tenant_id>[^/]+)/floating_ips/(?P<ip_id>[^/]+)/%s$'

urlpatterns = patterns(__name__,
    url(r'^(?P<tenant_id>[^/]+)/floating_ips/$', 'index', name=topbar + '/floating_ips'),
    url(FLOATING_IPS % 'associate', 'associate', name=topbar + '/floating_ips/associate'),
    url(FLOATING_IPS % 'disassociate', 'disassociate', name=topbar + '/floating_ips/disassociate'),
)

LOG = logging.getLogger(__name__)


class ReleaseFloatingIp(forms.SelfHandlingForm):
    floating_ip_id = forms.CharField(widget=forms.HiddenInput())

    def handle(self, request, data):
        try:
            LOG.info('Releasing Floating IP "%s"' % data['floating_ip_id'])
            api.tenant_floating_ip_release(request, data['floating_ip_id'])
            messages.info(request, 'Successfully released Floating IP: %s' \
                                    % data['floating_ip_id'])
        except novaclient_exceptions.ClientException, e:
            LOG.error("ClientException in ReleaseFloatingIp", exc_info=True)
            messages.error(request, 'Error releasing Floating IP from tenant: \
%s' % e.message)
        return shortcuts.redirect(request.build_absolute_uri())


class FloatingIpAssociate(forms.SelfHandlingForm):
    floating_ip_id = forms.CharField(widget=forms.HiddenInput())
    floating_ip = forms.CharField(widget=forms.TextInput(
                                            attrs={'readonly': 'readonly'}))
    instance_id = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        super(FloatingIpAssociate, self).__init__(*args, **kwargs)
        instancelist = kwargs.get('initial', {}).get('instances', [])
        self.fields['instance_id'] = forms.ChoiceField(
                choices=instancelist,
                label="Instance")

    def handle(self, request, data):
        try:
            api.server_add_floating_ip(request,
                                       data['instance_id'],
                                       data['floating_ip_id'])
            LOG.info('Associating Floating IP "%s" with Instance "%s"'
                                % (data['floating_ip'], data['instance_id']))
            messages.info(request, 'Successfully associated Floating IP: %s \
with Instance: %s'
                                    % (data['floating_ip'],
                                       data['instance_id']))
        except novaclient_exceptions.ClientException, e:
            LOG.error("ClientException in FloatingIpAssociate", exc_info=True)
            messages.error(request, 'Error associating Floating IP: %s'
                                     % e.message)
        return shortcuts.redirect(topbar + '/floating_ips', request.user.tenant)


class FloatingIpDisassociate(forms.SelfHandlingForm):
    floating_ip_id = forms.CharField(widget=forms.HiddenInput())

    def handle(self, request, data):
        try:
            fip = api.tenant_floating_ip_get(request, data['floating_ip_id'])
            api.server_remove_floating_ip(request, fip.instance_id, fip.id)

            LOG.info('Disassociating Floating IP "%s"'
                      % data['floating_ip_id'])

            messages.info(request, 'Successfully disassociated Floating IP: %s'
                                    % data['floating_ip_id'])
        except novaclient_exceptions.ClientException, e:
            LOG.error("ClientException in FloatingIpAssociate", exc_info=True)
            messages.error(request, 'Error disassociating Floating IP: %s'
                                     % e.message)
        return shortcuts.redirect(topbar + '/floating_ips', request.user.tenant)


class FloatingIpAllocate(forms.SelfHandlingForm):
    tenant_id = forms.CharField(widget=forms.HiddenInput())

    def handle(self, request, data):
        fip = None
        try:
            fip = api.tenant_floating_ip_allocate(request)
            LOG.info('Allocating Floating IP "%s" to tenant "%s"'
                     % (fip.ip, data['tenant_id']))

            messages.success(request, 'Successfully allocated Floating IP "%s"\
to tenant "%s"' % (fip.ip, data['tenant_id']))

        except novaclient_exceptions.ClientException, e:
            LOG.error("ClientException in FloatingIpAllocate", exc_info=True)
            messages.error(request, 'Error allocating Floating IP "%s"\
to tenant "%s": %s' %
                           (fip.ip if fip else "None", data['tenant_id'], e.message))
        return shortcuts.redirect(topbar + '/floating_ips', request.user.tenant)


@login_required
def index(request, tenant_id):
    for f in (ReleaseFloatingIp, FloatingIpDisassociate, FloatingIpAllocate):
        _unused, handled = f.maybe_handle(request)
        if handled:
            return handled
    try:
        floating_ips = api.tenant_floating_ip_list(request)
    except novaclient_exceptions.ClientException, e:
        floating_ips = []
        LOG.error("ClientException in floating ip index", exc_info=True)
        messages.error(request, 'Error fetching floating ips: %s' % e.message)

    return shortcuts.render_to_response(topbar + '/floating_ip_view.html', {
        'allocate_form': FloatingIpAllocate(initial={
                                            'tenant_id': request.user.tenant}),
        'disassociate_form': FloatingIpDisassociate(),
        'floating_ips': floating_ips,
        'release_form': ReleaseFloatingIp(),
    }, context_instance=template.RequestContext(request))


@login_required
def associate(request, tenant_id, ip_id):
    instancelist = [(server.id, 'id: %s, name: %s' %
            (server.id, server.name))
            for server in api.server_list(request)]

    form, handled = FloatingIpAssociate().maybe_handle(request, initial={
                'floating_ip_id': ip_id,
                'floating_ip': api.tenant_floating_ip_get(request, ip_id).ip,
                'instances': instancelist})
    if handled:
        return handled

    return shortcuts.render_to_response(topbar + '/floating_ip_associate.html', {
        'associate_form': form,
    }, context_instance=template.RequestContext(request))


@login_required
def disassociate(request, tenant_id, ip_id):
    form, handled = FloatingIpDisassociate().maybe_handle(request)
    if handled:
        return handled

    return shortcuts.render_to_response(topbar + '/floating_ip_associate.html', {
    }, context_instance=template.RequestContext(request))

