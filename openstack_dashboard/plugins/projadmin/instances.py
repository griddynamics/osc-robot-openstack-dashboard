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
from django.utils.translation import ugettext as _

import datetime
import logging

from django.contrib import messages

from openstack_dashboard import api
from openstack_dashboard import forms
from openstack_dashboard.plugins.user import instances as dash_instances
from openstackx.api import exceptions as api_exceptions
from openstack_dashboard.plugins import get_topbar_name


topbar = get_topbar_name(__file__)
INSTANCES = r'^instances/(?P<instance_id>[^/]+)/%s$'
urlpatterns = patterns(__name__,
    url(r'^$', 'usage', name=topbar),
    url(r'^overview/$', 'usage', name=topbar + '/overview'),
    url(r'^usage/(?P<tenant_id>[^/]+)$', 'tenant_usage',
        name=topbar + '/tenant_usage'),
    url(r'^instances/$', 'index', name=topbar + '/instances'),
    url(r'^instances/refresh$', 'refresh', name=topbar + '/instances_refresh'),
    # NOTE(termie): currently just using the 'dash' versions
    #url(INSTANCES % 'console', 'console', name=topbar + '/instances_console'),
    #url(INSTANCES % 'vnc', 'vnc', name=topbar + '/instances_vnc'),
)


TerminateInstance = dash_instances.TerminateInstance
RebootInstance = dash_instances.RebootInstance

LOG = logging.getLogger(__name__)


def _next_month(date_start):
    y = date_start.year + (date_start.month + 1)/13
    m = ((date_start.month + 1)%13)
    if m == 0:
        m = 1
    return datetime.date(y, m, 1)


def _current_month():
    today = datetime.date.today()
    return datetime.date(today.year, today.month,1)


def _get_start_and_end_date(request):
    try:
        date_start = datetime.date(int(request.GET['date_year']), int(request.GET['date_month']), 1)
    except:
        today = datetime.date.today()
        date_start = datetime.date(today.year, today.month,1)

    date_end = _next_month(date_start)
    datetime_start = datetime.datetime.combine(date_start, datetime.time())
    datetime_end = datetime.datetime.combine(date_end, datetime.time())

    if date_end > datetime.date.today():
        datetime_end = datetime.datetime.utcnow()
    return (date_start, date_end, datetime_start, datetime_end)


@login_required
def usage(request):
    (date_start, date_end, datetime_start, datetime_end) = _get_start_and_end_date(request)

    global_summary = api.GlobalSummary(request)
    if date_start > _current_month():
        messages.error(request, 'No data for the selected period')
        date_end = date_start
        datetime_end = datetime_start
    else:
        global_summary.service()
        global_summary.usage(datetime_start, datetime_end)

    dateform = forms.DateForm()
    dateform['date'].field.initial = date_start

    global_summary.avail()
    global_summary.human_readable('disk_size')
    global_summary.human_readable('ram_size')

    return render_to_response(
    topbar + '/usage.html',{
        'dateform': dateform,
        'usage_list': global_summary.usage_list,
        'global_summary': global_summary.summary,
        'external_links': settings.EXTERNAL_MONITORING,
    }, context_instance = template.RequestContext(request))


@login_required
def tenant_usage(request, tenant_id):
    (date_start, date_end, datetime_start, datetime_end) = _get_start_and_end_date(request)
    if date_start > _current_month():
        messages.error(request, 'No data for the selected period')
        date_end = date_start
        datetime_end = datetime_start

    dateform = forms.DateForm()
    dateform['date'].field.initial = date_start

    usage = {}
    try:
        usage = api.usage_get(request, tenant_id, datetime_start, datetime_end)
    except api_exceptions.ApiException, e:
        LOG.error('ApiException getting usage info for tenant "%s"'
                  ' on date range "%s to %s"' % (tenant_id,
                                                 datetime_start,
                                                 datetime_end))
        messages.error(request, 'Unable to get usage info: %s' % e.message)

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

    return render_to_response(topbar + '/tenant_usage.html', {
        'dateform': dateform,
        'usage': usage,
        'instances': running_instances + terminated_instances,
        'tenant_id': tenant_id,
    }, context_instance = template.RequestContext(request))


@login_required
def index(request):
    for f in (TerminateInstance, RebootInstance):
        _, handled = f.maybe_handle(request)
        if handled:
            return handled

    instances = []
    try:
        instances = api.server_list(request)
    except Exception as e:
        LOG.error('Unspecified error in instance index', exc_info=True)
        messages.error(request, 'Unable to get instance list: %s' % e.message)

    # We don't have any way of showing errors for these, so don't bother
    # trying to reuse the forms from above
    terminate_form = TerminateInstance()
    reboot_form = RebootInstance()

    return render_to_response(topbar + '/instance_view.html', {
        'instances': instances,
        'terminate_form': terminate_form,
        'reboot_form': reboot_form,
    }, context_instance=template.RequestContext(request))


@login_required
def refresh(request):
    for f in (TerminateInstance, RebootInstance):
        _, handled = f.maybe_handle(request)
        if handled:
            return handled

    instances = []
    try:
        instances = api.server_list(request)
    except Exception as e:
        messages.error(request, 'Unable to get instance list: %s' % e.message)

    # We don't have any way of showing errors for these, so don't bother
    # trying to reuse the forms from above
    terminate_form = TerminateInstance()
    reboot_form = RebootInstance()

    return render_to_response(topbar + '/instance_table.html', {
        'instances': instances,
        'terminate_form': terminate_form,
        'reboot_form': reboot_form,
    }, context_instance=template.RequestContext(request))
