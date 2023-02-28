from django.urls import include, path

from rest_framework.routers import DefaultRouter

from purchase import views

router = DefaultRouter()
router.register(r"purchase", views.PurchaseView, basename="purchase")
router.register(r"quantity", views.QuantityView, basename="quantity")

urlpatterns = [path("", include(router.urls))]
