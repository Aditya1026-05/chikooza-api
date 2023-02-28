from django.urls import include, path

from rest_framework.routers import DefaultRouter

from flocks import views

router = DefaultRouter()
router.register(r"flocks", views.FlockView, basename="flocks")
router.register(r"flocksDetail", views.FlockDetailView, basename="flocks_detail")
router.register(r"breeds", views.BreedView, basename="breeds")
router.register(r"integrators", views.IntegratorView, basename="integrators")
router.register(r"flockSummary", views.FlockSummaryView, basename="flockSummary")
urlpatterns = [path("", include(router.urls))]
