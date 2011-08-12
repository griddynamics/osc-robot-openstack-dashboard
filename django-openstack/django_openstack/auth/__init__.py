class Roles:
    USER = 'user'
    PROJECT_ADMIN = 'projadmin'
    SOFTWARE_ADMIN = 'softadmin'
    HARDWARE_ADMIN = 'hardadmin'
    ALL_ROLES = (HARDWARE_ADMIN, SOFTWARE_ADMIN,
                 PROJECT_ADMIN, USER)

    @staticmethod
    def get_max_role(roles):
        if not roles:
            return Roles.USER
        for role in Roles.ALL_ROLES:
            if role in roles:
                return role

    @staticmethod
    def needs_tenant(roles):
        return not (Roles.HARDWARE_ADMIN in roles) and not (Roles.SOFTWARE_ADMIN in roles)
