from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import FacultyProfile, StudentProfile, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "display_name", "email", "role", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("UMS profile", {"fields": ("role", "phone", "avatar_url")}),
    )


admin.site.register(StudentProfile)
admin.site.register(FacultyProfile)

admin.site.site_header = "UMS Superuser Console"
admin.site.site_title = "UMS Admin"
