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
Views for managing Nova images.
"""

import datetime
import logging
import re

from django import http
from django import template
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render_to_response
from django.utils.translation import ugettext as _
from django import shortcuts

from openstack_dashboard import api
from openstack_dashboard import forms
from openstackx.api import exceptions as api_exceptions
from glance.common import exception as glance_exception
from openstack_dashboard.plugins import get_topbar_name


topbar = get_topbar_name(__file__)
IMAGES = r'^(?P<tenant_id>[^/]+)/images/(?P<image_id>[^/]+)/%s$'

urlpatterns = patterns(__name__,
    url(r'^(?P<tenant_id>[^/]+)/images/$', 'index', name=topbar + '/images'),
    url(IMAGES % 'launch', 'launch', name=topbar + '/images_launch'),
)

LOG = logging.getLogger(__name__)

class LaunchForm(forms.SelfHandlingForm):
    name = forms.SlugField(max_length=80, label="Server Name")
    image_id = forms.CharField(widget=forms.HiddenInput())
    tenant_id = forms.CharField(widget=forms.HiddenInput())
    user_data = forms.CharField(widget=forms.Textarea,
                                label="User Data",
                                required=False)

    # make the dropdown populate when the form is loaded not when django is
    # started
    def __init__(self, *args, **kwargs):
        super(LaunchForm, self).__init__(*args, **kwargs)
        flavorlist = kwargs.get('initial', {}).get('flavorlist', [])
        self.fields['flavor'] = forms.ChoiceField(
                choices=flavorlist,
                label="Flavor",
                help_text="Size of Image to launch")

        keynamelist = kwargs.get('initial', {}).get('keynamelist', [])
        self.fields['key_name'] = forms.ChoiceField(choices=keynamelist,
                label="Key Name",
                required=False,
                help_text="Which keypair to use for authentication")

        securitygrouplist = kwargs.get('initial', {}).get('securitygrouplist', [])
        self.fields['security_groups'] = forms.MultipleChoiceField(choices=securitygrouplist,
                label='Security Groups',
                required=True,
                initial=['default'],
                widget=forms.SelectMultiple(attrs={'class': 'chzn-select',
                                                   'style': "min-width: 200px"}),
                help_text="Launch instance in these Security Groups")

        # setting self.fields.keyOrder seems to break validation,
        # so ordering fields manually
        field_list = (
            'name',
            'user_data',
            'flavor',
            'key_name')
        for field in field_list[::-1]:
            self.fields.insert(0, field, self.fields.pop(field))


    def handle(self, request, data):
        image_id = data['image_id']
        tenant_id = data['tenant_id']
        try:
            image = api.image_get(request, image_id)
            flavor = api.flavor_get(request, data['flavor'])
            api.server_create(request,
                              data['name'],
                              image,
                              flavor,
                              data.get('key_name'),
                              data.get('user_data'),
                              data.get('security_groups'))

            msg = 'Instance was successfully launched'
            LOG.info(msg)
            messages.success(request, msg)
            return redirect(topbar + '/instances', tenant_id)

        except api_exceptions.ApiException, e:
            LOG.error('ApiException while creating instances of image "%s"' %
                      image_id, exc_info=True)
            messages.error(request,
                           'Unable to launch instance: %s' % e.message)


@login_required
def index(request, tenant_id):
    tenant = {}

    try:
        tenant = api.token_get_tenant(request, request.user.tenant)
    except api_exceptions.ApiException, e:
        messages.error(request, "Unable to retrienve tenant info\
                                 from keystone: %s" % e.message)

    all_images = []
    try:
        all_images = api.image_list_detailed(request)
        if not all_images:
            messages.info(request, "There are currently no images.")
    except glance_exception.ClientConnectionError, e:
        LOG.error("Error connecting to glance", exc_info=True)
        messages.error(request, "Error connecting to glance: %s" % str(e))
    except glance_exception.Error, e:
        LOG.error("Error retrieving image list", exc_info=True)
        messages.error(request, "Error retrieving image list: %s" % str(e))

    images = [im for im in all_images
              if im['container_format'] not in ['aki', 'ari']]

    return render_to_response(topbar + '/image_view.html', {
        'tenant': tenant,
        'images': images,
    }, context_instance=template.RequestContext(request))


@login_required
def launch(request, tenant_id, image_id):
    def flavorlist():
        try:
            fl = api.flavor_list(request)

            # TODO add vcpu count to flavors
            sel = [(f.id, '%s (%svcpu / %sGB Disk / %sMB Ram )' %
                   (f.name, f.vcpus, f.disk, f.ram)) for f in fl]
            return sorted(sel)
        except api_exceptions.ApiException:
            LOG.error('Unable to retrieve list of instance types',
                      exc_info=True)
            return [(1, 'm1.tiny')]

    def keynamelist():
        try:
            fl = api.keypair_list(request)
            sel = [(f.key_name, f.key_name) for f in fl]
            return sel
        except api_exceptions.ApiException:
            LOG.error('Unable to retrieve list of keypairs', exc_info=True)
            return []

    def securitygrouplist():
        try:
            fl = api.security_group_list(request)
            sel = [(f.name, f.name) for f in fl]
            return sel
        except api_exceptions.ApiException:
            LOG.error('Unable to retrieve list of security groups', exc_info=True)
            return []

    # TODO(mgius): Any reason why these can't be after the launchform logic?
    # If The form is valid, we've just wasted these two api calls
    image = api.image_get(request, image_id)
    tenant = api.token_get_tenant(request, request.user.tenant)
    quotas = api.tenant_quota_get(request, request.user.tenant)
    try:
        quotas.ram = int(quotas.ram)/100
    except Exception, e:
        messages.error(request, 'Error parsing quota  for %s: %s' %
                                 (image_id, e.message))
        return redirect(topbar + '/instances', tenant_id)

    form, handled = LaunchForm.maybe_handle(
            request, initial={'flavorlist': flavorlist(),
                              'keynamelist': keynamelist(),
                              'securitygrouplist': securitygrouplist(),
                              'image_id': image_id,
                              'tenant_id': tenant_id})
    if handled:
        return handled

    return render_to_response(topbar + '/image_launch.html', {
        'tenant': tenant,
        'image': image,
        'form': form,
        'quotas': quotas,
    }, context_instance=template.RequestContext(request))
