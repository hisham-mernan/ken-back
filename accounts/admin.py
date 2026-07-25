

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import *
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password', 'role', 'is_active', 'is_verfied','is_forget_pass','is_email_changed')}),
        ('Personal info', {'fields': ('full_name', 'gender', 'birth_date', 'address', 'avatar', 'phone','otp_secret','email_temp')}),
        ('Permissions', {'fields': ('is_superuser', 'is_staff', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('created_at',)}),  # remove created_at from here!
    )
    readonly_fields = ('created_at','otp_created_at',)  

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    list_display = ('email', 'full_name', 'role', 'is_active', 'is_verfied')
    search_fields = ('email', 'full_name', 'phone')
    ordering = ('email',)


# Unregister SimpleJWT Token models
try:
    admin.site.unregister(OutstandingToken)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(BlacklistedToken)
except admin.sites.NotRegistered:
    pass

admin.site.register(Partners)
admin.site.register(Support)
admin.site.register(WebRating)
admin.site.register(WebsiteRate)
admin.site.register(Notification)

