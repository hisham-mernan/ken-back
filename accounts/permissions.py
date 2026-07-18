from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

from rest_framework.permissions import BasePermission

class IsAdminOrSupplier(BasePermission):
    def has_permission(self, request, view):
        return request.user and (request.user.is_authenticated and (request.user.role=='admin' or request.user.role=='supplier'))

class IsSupplier(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'supplier'


class IsGuest(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'guest'



class IsAdminForUnsafeMethods(permissions.BasePermission):
    """
    - SAFE methods (GET, HEAD, OPTIONS): allowed for all.
    - UNSAFE methods (POST, PUT, PATCH, DELETE): only allowed for admin users.
    """

    def has_permission(self, request, view):
      
        if request.method in permissions.SAFE_METHODS:
            return True
      
        return request.user.is_authenticated and request.user.role == 'admin'