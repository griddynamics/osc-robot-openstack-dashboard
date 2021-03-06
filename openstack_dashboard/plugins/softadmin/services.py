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
import os
import subprocess
import sys
import urlparse

from django.contrib import messages

from openstack_dashboard import api
from openstack_dashboard import forms
from openstackx.api import exceptions as api_exceptions
from openstack_dashboard.plugins import get_topbar_name


topbar = get_topbar_name(__file__)
urlpatterns = patterns(__name__,
#    url(r'^$', 'index', name=topbar),
    url(r'^services/$', 'index', name=topbar + '/services'),
)

LOG = logging.getLogger(__name__)


class ToggleService(forms.SelfHandlingForm):
    service = forms.CharField(required=False)
    name = forms.CharField(required=False)

    def handle(self, request, data):
        try:
            service = api.service_get(request, data['service'])
            api.service_update(request,
                               data['service'],
                               not service.disabled)
            if service.disabled:
                messages.info(request, "Service '%s' has been enabled"
                                        % data['name'])
            else:
                messages.info(request, "Service '%s' has been disabled"
                                        % data['name'])
        except api_exceptions.ApiException, e:
            LOG.error('ApiException while toggling service %s' %
                      data['service'], exc_info=True)
            messages.error(request, "Unable to update service '%s': %s"
                                     % data['name'], e.message)

        return redirect(request.build_absolute_uri())


@login_required
def index(request):
    for f in (ToggleService,):
        _, handled = f.maybe_handle(request)
        if handled:
            return handled

    services = []
    try:
        services = api.service_list(request)
    except api_exceptions.ApiException, e:
        LOG.error('ApiException fetching service list', exc_info=True)
        messages.error(request, 'Unable to get service info: %s' % e.message)

    other_services = []

    for k, v in request.session['serviceCatalog'].iteritems():
        v = v[0]
        try:
            # TODO(mgius): This silences curl, but there's probably
            # a better solution than using curl to begin with
            subprocess.check_call(['curl', '-m', '1', v['internalURL']],
                                  stdout=open(os.devnull, 'w'),
                                  stderr=open(os.devnull, 'w'))
            up = True
        except:
            up = False
        hostname = urlparse.urlparse(v['internalURL']).hostname
        row = {'type': k, 'internalURL': v['internalURL'], 'host': hostname,
               'region': v['region'], 'up': up }
        other_services.append(row)

    services = sorted(services, key=lambda svc: (svc.type +
                                                 svc.host))
    other_services = sorted(other_services, key=lambda svc: (svc['type'] +
                                                             svc['host']))

    return render_to_response(topbar + '/service_view.html', {
        'services': services,
        'service_toggle_enabled_form': ToggleService,
        'other_services': other_services,
    }, context_instance = template.RequestContext(request))
