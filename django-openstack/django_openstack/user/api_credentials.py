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
Views for managing Nova api credentials.
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

from django_openstack import api
from django_openstack import forms
from openstackx.api import exceptions as api_exceptions
from glance.common import exception as glance_exception
from django_openstack.urls import get_topbar_name


topbar = get_topbar_name(__file__)

urlpatterns = patterns(__name__,
    url(r'^(?P<tenant_id>[^/]+)/api_credentials/$', 'index', name=topbar + '/api_credentials'),
    url(r'^(?P<tenant_id>[^/]+)/api_credentials/zipfile$', 'zipfile', name=topbar + '/api_credentials/zipfile'),
)

LOG = logging.getLogger(__name__)

@login_required
def index(request, tenant_id):
    return render_to_response(topbar + '/api_credentials_view.html', {
    }, context_instance=template.RequestContext(request))


@login_required
def zipfile(request, tenant_id):
    try:
        LOG.info("Retrieving zipfile for `%s' user of `%s'project"
                 % (request.user.username, tenant_id))
        zipfile = api.project_zipfile(request, tenant_id)
        response = http.HttpResponse(mimetype='application/binary')
        response['Content-Disposition'] = \
            'attachment; filename=nova_accesskey_%s_%s.zip' % \
            (request.user.username, tenant_id)
        response.write(zipfile)
        return response
    except api_exceptions.ApiException, e:
        LOG.error("ApiException in api_credentials.zipfile", exc_info=True)
        messages.error(request, 'Error Retrieving Zipfile: %s' % e.message)
        return shortcuts.redirect(topbar + '/api_credentials', tenant_id=tenant_id)
