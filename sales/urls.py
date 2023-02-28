from django.urls import path, include
from rest_framework.routers import DefaultRouter

from sales.views import SalesView, AgeView, GraphView

router = DefaultRouter()
router.register(r"sales", SalesView, basename="sales")
router.register(r"age", AgeView, basename="age")
router.register(r"graph", GraphView, basename="graph")
urlpatterns = [
    path("", include(router.urls))
]
