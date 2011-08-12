from django_openstack.urls import TopbarRoleCheckMiddleware
from django_openstack import auth


class TopbarCheckMiddleware(TopbarRoleCheckMiddleware):
    roles = set([auth.Roles.PROJECT_ADMIN, auth.Roles.USER])


MIDDLEWARE_CLASSES = ("TopbarCheckMiddleware",)
