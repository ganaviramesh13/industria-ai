from rest_framework import permissions


class IsAdministrator(permissions.BasePermission):
    """
    Allows access only to users with the Administrator role or superusers.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role == 'ADMIN' or request.user.is_superuser)
        )


class IsEngineer(permissions.BasePermission):
    """
    Allows access to users with the Engineer role (and admins for operational flexibility).
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role == 'ENGINEER' or request.user.role == 'ADMIN' or request.user.is_superuser)
        )


class IsSupervisor(permissions.BasePermission):
    """
    Allows access to users with the Supervisor role (and admins).
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role == 'SUPERVISOR' or request.user.role == 'ADMIN' or request.user.is_superuser)
        )


class IsReadOnly(permissions.BasePermission):
    """
    Allows read-only access (GET, HEAD, OPTIONS).
    """
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS

