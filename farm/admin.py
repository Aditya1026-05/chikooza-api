from django.contrib import admin

# Register your models here.
from farm.models import Country, Farm, State


class StateAdmin(admin.ModelAdmin):
    list_display = ("public_id", "name")


class CountryAdmin(admin.ModelAdmin):
    list_display = ("public_id",)


class FarmAdmin(admin.ModelAdmin):
    list_display = ("public_id",)


admin.site.register(State, StateAdmin)
admin.site.register(Farm, FarmAdmin)
admin.site.register(Country, CountryAdmin)
