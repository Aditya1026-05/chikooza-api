from django.contrib import admin

from common.base_models import Users
from farm.models import Farm
from flocks.models import Flock


class FarmerWorkflowFilter(admin.SimpleListFilter):
    title = "1. Farmer"
    parameter_name = "farmer"
    user_query_path = "user"

    def lookups(self, request, model_admin):
        farmers = (
            Users.objects.filter(is_staff=False, is_superuser=False)
            .order_by("username")
            .only("id", "username", "email")
        )
        return [(str(user.pk), user.username or user.email) for user in farmers]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(**{f"{self.user_query_path}__id": self.value()})
        return queryset


class FarmWorkflowFilter(admin.SimpleListFilter):
    title = "2. Farm"
    parameter_name = "farm"
    farm_query_path = "farm"

    def lookups(self, request, model_admin):
        farmer_id = request.GET.get(FarmerWorkflowFilter.parameter_name)
        if not farmer_id:
            return []

        farms = (
            Farm.objects.select_related("user")
            .filter(user_id=farmer_id)
            .order_by("name")
        )
        return [(str(farm.pk), f"{farm.name} ({farm.user.username})") for farm in farms]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(**{f"{self.farm_query_path}__id": self.value()})
        return queryset


class FlockWorkflowFilter(admin.SimpleListFilter):
    title = "3. Flock"
    parameter_name = "flock"
    flock_query_path = "flock"

    def lookups(self, request, model_admin):
        farmer_id = request.GET.get(FarmerWorkflowFilter.parameter_name)
        farm_id = request.GET.get(FarmWorkflowFilter.parameter_name)
        if not farmer_id and not farm_id:
            return []

        flocks = Flock.objects.select_related("farm", "user").order_by(
            "farm__name",
            "name",
        )
        if farmer_id:
            flocks = flocks.filter(user_id=farmer_id)
        if farm_id:
            flocks = flocks.filter(farm_id=farm_id)
        return [
            (str(flock.pk), f"{flock.name} ({flock.farm.name})")
            for flock in flocks
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(**{f"{self.flock_query_path}__id": self.value()})
        return queryset


class FlockFarmerWorkflowFilter(FarmerWorkflowFilter):
    user_query_path = "flock__user"


class FlockFarmWorkflowFilter(FarmWorkflowFilter):
    farm_query_path = "flock__farm"
