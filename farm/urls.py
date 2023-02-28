from django.urls import include, path

from rest_framework.routers import DefaultRouter

from farm.views import CountryView, FarmView, StateView

router = DefaultRouter()
router.register(r"farm", FarmView, basename="add_farm")
router.register(r"state", StateView, basename="state")
router.register(r"country", CountryView, basename="country")

urlpatterns = [path("", include(router.urls))]
