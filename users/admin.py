from django.contrib import admin

# Register your models here.
from common.base_models import Otp, Users, UsersForgotPassword


class UsersAdmin(admin.ModelAdmin):
    list_display = ("username", "public_id", "email", "mobile_number")


class UsersForgotPasswordAdmin(admin.ModelAdmin):
    list_display = ("public_id", "otp", "users")


admin.site.register(Users, UsersAdmin)
admin.site.register(Otp)
admin.site.register(UsersForgotPassword, UsersForgotPasswordAdmin)
