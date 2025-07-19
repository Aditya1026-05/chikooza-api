#MV-2025-07-10-<9>  STARTS
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIChatViewSet

router = DefaultRouter()
router.register(r'', AIChatViewSet, basename='aibot')

urlpatterns = [
    path('', include(router.urls)),
]
#MV-2025-07-10-<9>  ENDS