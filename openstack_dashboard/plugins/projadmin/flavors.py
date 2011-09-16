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

from operator import itemgetter

from django import template
from django import http
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.shortcuts import render_to_response
from openstackx.api import exceptions as api_exceptions


from openstack_dashboard import api
from openstack_dashboard import forms
from openstack_dashboard.plugins import get_topbar_name


topbar = get_topbar_name(__file__)
urlpatterns = patterns(__name__,
    url(r'^flavors/$', 'index', name=topbar + '/flavors'),
    url(r'^flavors/create/$', 'create', name=topbar + '/flavors_create'),
)

LOG = logging.getLogger(__name__)


class CreateFlavor(forms.SelfHandlingForm):
    flavorid = forms.IntegerField(label="Flavor ID")
    name = forms.SlugField(max_length="25", label="Name")
    vcpus = forms.IntegerField(label="VCPUs")
    memory_mb = forms.IntegerField(label="Memory MB")
    disk_gb = forms.IntegerField(label="Disk GB")

    def handle(self, request, data):
        api.flavor_create(request,
                          data['name'],
                          int(data['memory_mb']),
                          int(data['vcpus']),
                          int(data['disk_gb']),
                          int(data['flavorid']))
        msg = '%s was successfully added to flavors.' % data['name']
        LOG.info(msg)
        messages.success(request, msg)
        return redirect(topbar + '/flavor')


class DeleteFlavor(forms.SelfHandlingForm):
    flavorid = forms.CharField(required=True)

    def handle(self, request, data):
        try:
            flavor_id = data['flavorid']
            flavor = api.flavor_get(request, flavor_id)
            LOG.info('Deleting flavor with id "%s"' % flavor_id)
            api.flavor_delete(request, flavor_id, False)
            messages.info(request, 'Successfully deleted flavor: %s' %
                          flavor.name)
        except api_exceptions.ApiException, e:
            messages.error(request, 'Unable to delete flavor: %s' %
                                     e.message)
        return redirect(request.build_absolute_uri())

@login_required
def index(request):
    for f in (DeleteFlavor,):
        _, handled = f.maybe_handle(request)
        if handled:
            return handled

    delete_form = DeleteFlavor()

    flavors = []
    try:
        flavors = api.flavor_list(request)
    except api_exceptions.ApiException, e:
        LOG.error('ApiException while fetching usage info', exc_info=True)
        messages.error(request, 'Unable to get usage info: %s' % e.message)

    flavors.sort(key=lambda x: x.id, reverse=True)
    return render_to_response(topbar + '/flavor_view.html',{
        'delete_form': delete_form,
        'flavors': flavors,
    }, context_instance = template.RequestContext(request))


@login_required
def create(request):
    form, handled = CreateFlavor.maybe_handle(request)
    if handled:
        return handled

    global_summary = api.GlobalSummary(request)
    global_summary.service()
    global_summary.avail()
    global_summary.human_readable('disk_size')
    global_summary.human_readable('ram_size')

    return render_to_response(topbar + '/flavor_create.html',{
        'global_summary': global_summary.summary,
        'form': form,
    }, context_instance = template.RequestContext(request))
