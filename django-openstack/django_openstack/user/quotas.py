# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

from django_openstack import api
from django_openstack import forms
from django_openstack.urls import get_topbar_name


topbar = get_topbar_name(__file__)

urlpatterns = patterns(__name__,
    url(r'^quotas/$', 'index', name=topbar + '/quotas'),
)

@login_required
def index(request):
    quotas = api.admin_api(request).quota_sets.get(True)._info
    quotas['ram'] = int(quotas['ram']) / 100
    quotas.pop('id')

    return render_to_response(topbar + '/quotas.html',{
        'quotas': quotas,
    }, context_instance = template.RequestContext(request))

