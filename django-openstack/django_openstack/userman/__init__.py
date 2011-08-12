from django_openstack.urls import TopbarRoleCheckMiddleware
from django_openstack import auth


class TopbarCheckMiddleware(TopbarRoleCheckMiddleware):
    roles = set([auth.Roles.HARDWARE_ADMIN, auth.Roles.SOFTWARE_ADMIN])


MIDDLEWARE_CLASSES = ("TopbarCheckMiddleware",)
