import django_openstack.urls


class Roles:
    USER = 'user'
    PROJECT_ADMIN = 'projadmin'
    SOFTWARE_ADMIN = 'softadmin'
    HARDWARE_ADMIN = 'hardadmin'
    ALL_ROLES = (HARDWARE_ADMIN, SOFTWARE_ADMIN,
                 PROJECT_ADMIN, USER)

    @staticmethod
    def get_default_page(roles):
        for role in Roles.ALL_ROLES:
            if role in roles and role in django_openstack.urls.topbars:
                return role
        # here roles == ['hardadmin'] and no hardadmin topbar is installed
        return 'userman'

    @staticmethod
    def needs_tenant(roles):
        return not (Roles.HARDWARE_ADMIN in roles) and not (Roles.SOFTWARE_ADMIN in roles)
