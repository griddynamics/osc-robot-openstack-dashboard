# vim: tabstop=4 shiftwidth=4 softtabstop=4


# Copyright 2011 Grid Dynamics Consulting Services, Inc.  All rights reserved.
#
#    This software is provided to Cisco Systems, Inc. as "Supplier Materials"
#    under the license terms governing Cisco's use of such Supplier Materials described
#    in the Master Services Agreement between Grid Dynamics Consulting Services, Inc. and Cisco Systems, Inc.,
#    as amended by Amendment #1.  If the parties are unable to agree upon the terms
#    of the Amendment #1 by July 31, 2011, this license shall automatically terminate and
#    all rights in the Supplier Materials shall revert to Grid Dynamics, unless Grid Dynamics specifically
#    and otherwise agrees in writing.

from django.contrib import messages
import json

class AjaxMessagingMiddleware(object):
    def process_response(self, request, response):
        if request.is_ajax():
            if response["Content-Type"] in ["application/javascript", "application/json"]:
                try:
                    content = json.loads(response.content)
                except ValueError:
                    return response
                django_messages = []

                for message in messages.get_messages(request):
                    django_messages.append({
                        "level": message.level,
                        "message": message.message,
                        "tags": message.tags,
                    })

                try:
                    content["django_messages"] = django_messages
                except:
                    #content is not a dict
                    pass
                else:
                    response.content = json.dumps(content)
        return response