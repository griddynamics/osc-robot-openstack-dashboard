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
import datetime
import logging

from django import http
from django import shortcuts
from django import template
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _

from django_openstack import api
from django_openstack import forms
from django_openstack import utils
import openstack.compute.servers
import openstackx.api.exceptions as api_exceptions
from django_openstack.urls import get_topbar_name


topbar = get_topbar_name(__file__)
INSTANCES = r'^(?P<tenant_id>[^/]+)/instances/(?P<instance_id>[^/]+)/%s$'

urlpatterns = patterns(__name__,
    url(r'^$', 'usage', name=topbar),
    url(r'^overview/$', 'usage', name=topbar + '/overview'),
    url(r'^(?P<tenant_id>[^/]+)/$', 'usage', name=topbar + '/usage'),
    url(r'^(?P<tenant_id>[^/]+)/instances/$', 'index', name=topbar + '/instances'),
    url(r'^(?P<tenant_id>[^/]+)/instances/refresh$', 'refresh', name=topbar + '/instances_refresh'),
    url(INSTANCES % 'console', 'console', name=topbar + '/instances_console'),
    url(INSTANCES % 'update', 'update', name=topbar + '/instances_update'),
)

LOG = logging.getLogger(__name__)

class TerminateInstance(forms.SelfHandlingForm):
    instance = forms.CharField(required=True)

    def handle(self, request, data):
        instance_id = data['instance']
        instance = api.server_get(request, instance_id)

        try:
            api.server_delete(request, instance)
        except api_exceptions.ApiException, e:
            LOG.error('ApiException while terminating instance "%s"' %
                      instance_id, exc_info=True)
            messages.error(request,
                           'Unable to terminate %s: %s' %
                           (instance_id, e.message,))
        else:
            msg = 'Instance %s has been terminated.' % instance_id
            LOG.info(msg)
            messages.success(request, msg)

        return shortcuts.redirect(request.build_absolute_uri())


class RebootInstance(forms.SelfHandlingForm):
    instance = forms.CharField(required=True)

    def handle(self, request, data):
        instance_id = data['instance']
        try:
            server = api.server_reboot(request, instance_id)
            messages.success(request, "Instance rebooting")
        except api_exceptions.ApiException, e:
            LOG.error('ApiException while rebooting instance "%s"' %
                      instance_id, exc_info=True)
            messages.error(request,
                       'Unable to reboot instance: %s' % e.message)

        else:
            msg = 'Instance %s has been rebooted.' % instance_id
            LOG.info(msg)
            messages.success(request, msg)

        return shortcuts.redirect(request.build_absolute_uri())


class UpdateInstance(forms.Form):
    instance = forms.CharField(widget=forms.TextInput(
                               attrs={'readonly':'readonly'}))
    name = forms.CharField(required=True)
    description = forms.CharField(required=False)


@login_required
def index(request, tenant_id):
    for f in (TerminateInstance, RebootInstance):
        _, handled = f.maybe_handle(request)
        if handled:
            return handled
    instances = []
    try:
        instances = api.server_list(request)
    except api_exceptions.ApiException as e:
        LOG.error('Exception in instance index', exc_info=True)
        messages.error(request, 'Unable to get instance list: %s' % e.message)

    # We don't have any way of showing errors for these, so don't bother
    # trying to reuse the forms from above
    terminate_form = TerminateInstance()
    reboot_form = RebootInstance()

    return shortcuts.render_to_response(topbar + '/instance_view.html', {
        'instances': instances,
        'terminate_form': terminate_form,
        'reboot_form': reboot_form,
    }, context_instance=template.RequestContext(request))


@login_required
def refresh(request, tenant_id):
    instances = []
    try:
        instances = api.server_list(request)
    except Exception as e:
        messages.error(request, 'Unable to get instance list: %s' % e.message)

    # We don't have any way of showing errors for these, so don't bother
    # trying to reuse the forms from above
    terminate_form = TerminateInstance()
    reboot_form = RebootInstance()

    return shortcuts.render_to_response(topbar + '/instance_table.html', {
        'instances': instances,
        'terminate_form': terminate_form,
        'reboot_form': reboot_form,
    }, context_instance=template.RequestContext(request))


@login_required
def usage(request, tenant_id=None):
    today = utils.today()
    date_start = datetime.date(today.year, today.month, 1)
    datetime_start = datetime.datetime.combine(date_start, utils.time())
    datetime_end = utils.utcnow()

    show_terminated = request.GET.get('show_terminated', False)

    usage = {}
    if not tenant_id:
        tenant_id = request.user.tenant

    try:
        usage = api.usage_get(request, tenant_id, datetime_start, datetime_end)
    except api_exceptions.ApiException, e:
        LOG.error('ApiException in instance usage', exc_info=True)

        messages.error(request, 'Unable to get usage info: %s' % e.message)

    ram_unit = "MB"
    total_ram = 0
    if hasattr(usage, 'total_active_ram_size'):
        total_ram = usage.total_active_ram_size
        if total_ram > 999:
            ram_unit = "GB"
            total_ram /= float(1024)

    running_instances = []
    terminated_instances = []
    if hasattr(usage, 'instances'):
        now = datetime.datetime.now()
        for i in usage.instances:
            # this is just a way to phrase uptime in a way that is compatible
            # with the 'timesince' filter.  Use of local time intentional
            i['uptime_at'] = now - datetime.timedelta(seconds=i['uptime'])
            if i['ended_at']:
                terminated_instances.append(i)
            else:
                running_instances.append(i)

    instances = running_instances
    if show_terminated:
        instances += terminated_instances

    return shortcuts.render_to_response(topbar + '/usage.html', {
        'usage': usage,
        'ram_unit': ram_unit,
        'total_ram': total_ram,
        'show_terminated': show_terminated,
        'instances': instances
    }, context_instance=template.RequestContext(request))


@login_required
def console(request, tenant_id, instance_id):
    try:
        console = api.console_create(request, instance_id, 'text')
        response = http.HttpResponse(mimetype='text/plain')
        response.write(console.output)
        response.flush()
        return response
    except api_exceptions.ApiException, e:
        LOG.error('ApiException while fetching instance console',
                  exc_info=True)

        messages.error(request,
                   'Unable to get log for instance %s: %s' %
                   (instance_id, e.message))
        return shortcuts.redirect(topbar + '/instances', tenant_id)


@login_required
def update(request, tenant_id, instance_id):
    if request.POST:
        form = UpdateInstance(request.POST)
        if form.is_valid():
            data = form.clean()
            instance_id = data['instance']
            name = data['name']
            description = data.get('description', '')
            try:
                api.server_update(request, instance_id, name, description)
                messages.success(request, "Instance %s updated" % instance_id)
            except api_exceptions.ApiException, e:
                messages.error(request,
                           'Unable to update instance: %s' % e.message)

            return redirect(topbar + '/instances', tenant_id)
    else:
        instance = api.server_get(request, instance_id)
        form = UpdateInstance(initial={'instance': instance_id,
                                       'tenant_id': tenant_id,
                                       'name': instance.name,
                                       'description': instance.attrs['description']})

    return render_to_response(topbar + '/instance_update.html', {
        'instance': instance,
        'form': form,
    }, context_instance=template.RequestContext(request))
