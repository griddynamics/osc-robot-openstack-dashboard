from openstack_dashboard.plugins import TopbarRoleCheckMiddleware
from openstack_dashboard.plugins import auth


class TopbarCheckMiddleware(TopbarRoleCheckMiddleware):
    roles = set([auth.Roles.PROJECT_ADMIN])


MIDDLEWARE_CLASSES = ("TopbarCheckMiddleware",)
