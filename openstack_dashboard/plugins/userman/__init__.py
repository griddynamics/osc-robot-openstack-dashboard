from openstack_dashboard.plugins import TopbarRoleCheckMiddleware
from openstack_dashboard.plugins import auth


class TopbarCheckMiddleware(TopbarRoleCheckMiddleware):
    roles = set([auth.Roles.HARDWARE_ADMIN, auth.Roles.SOFTWARE_ADMIN])


MIDDLEWARE_CLASSES = ("TopbarCheckMiddleware",)
