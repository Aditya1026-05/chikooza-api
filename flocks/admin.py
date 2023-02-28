from django.contrib import admin

# Register your models here.
from flocks.models import Breed, Flock, Integrator


class BreedAdmin(admin.ModelAdmin):
    list_display = ("public_id", "name")


class FlockAdmin(admin.ModelAdmin):
    list_display = ("public_id", "name")


class IntegratorAdmin(admin.ModelAdmin):
    list_display = ("public_id", "name")


admin.site.register(Integrator, IntegratorAdmin)
admin.site.register(Breed, BreedAdmin)
admin.site.register(Flock, FlockAdmin)
