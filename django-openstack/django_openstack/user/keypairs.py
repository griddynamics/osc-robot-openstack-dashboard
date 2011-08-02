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
from django_openstack.urls import get_panel_name


panel = get_panel_name(__file__)
KEYPAIRS = r'^(?P<tenant_id>[^/]+)/keypairs/%s$'

urlpatterns = patterns(__name__,
    url(r'^(?P<tenant_id>[^/]+)/keypairs/$', 'index', name=panel + '/keypairs'),
    url(KEYPAIRS % 'create', 'create', name=panel + '/keypairs_create'),
)

LOG = logging.getLogger(__name__)


class DeleteKeypair(forms.SelfHandlingForm):
    keypair_id = forms.CharField(widget=forms.HiddenInput())

    def handle(self, request, data):
        try:
            LOG.info('Deleting keypair "%s"' % data['keypair_id'])
            keypair = api.keypair_delete(request, data['keypair_id'])
            messages.info(request, 'Successfully deleted keypair: %s' \
                                    % data['keypair_id'])
        except api_exceptions.ApiException, e:
            LOG.error("ApiException in DeleteKeypair", exc_info=True)
            messages.error(request, 'Error deleting keypair: %s' % e.message)
        return shortcuts.redirect(request.build_absolute_uri())


class CreateKeypair(forms.SelfHandlingForm):

    name = forms.CharField(max_length="20", label="Keypair Name",
                 validators=[validators.RegexValidator('\w+')])

    @classmethod
    def maybe_handle(cls, request, *args, **kwargs):
        LOG.error(request)
        LOG.error("name %s" % cls.__name__)
        if cls.__name__ != request.POST.get('method'):
            return cls(*args, **kwargs), None
        try:
            if request.FILES:
                form = cls(request.POST, request.FILES, *args, 
                 **kwargs)
            else:
                form = cls(request.POST, *args, **kwargs)
            if not form.is_valid():
                return form, None
            data = form.clean()
            return form, form.handle(request, data)
        except Exception as e:
            LOG.error('Nonspecific error while handling form', 
             exc_info=True)
            messages.error(request, 'Unexpected error: %s' % e.
             message)
            return form, None

    def handle(self, request, data):
       # raise Exception("handle called")
        try:
            LOG.info('Creating keypair "%s"' % data['name'])
            keypair = api.keypair_create(request, data['name'])
            response = http.HttpResponse(mimetype='application/binary')
            response['Content-Disposition'] = \
                'attachment; filename=%s.pem' % \
                keypair.key_name
            response.write(keypair.private_key)
            return response
        except api_exceptions.ApiException, e:
            LOG.error("ApiException in CreateKeyPair", exc_info=True)
            messages.error(request, 'Error Creating Keypair: %s' % e.message)
            return shortcuts.redirect(request.build_absolute_uri())


@login_required
def index(request, tenant_id):
    delete_form, handled = DeleteKeypair.maybe_handle(request)

    if handled:
        return handled

    try:
        keypairs = api.keypair_list(request)
    except api_exceptions.ApiException, e:
        keypairs = []
        LOG.error("ApiException in keypair index", exc_info=True)
        messages.error(request, 'Error fetching keypairs: %s' % e.message)

    return shortcuts.render_to_response(panel + '/keypair_view.html', {
        'keypairs': keypairs,
        'delete_form': delete_form,
    }, context_instance=template.RequestContext(request))


@login_required
def create(request, tenant_id):
    form, handled = CreateKeypair.maybe_handle(request)
    #raise Exception("create called" +( handled if handled else " <empty>"))
    if handled:
        return handled

    return shortcuts.render_to_response(panel + '/keypair_create.html', {
        'create_form': form,
    }, context_instance=template.RequestContext(request))