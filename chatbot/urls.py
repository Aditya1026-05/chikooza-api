#MV-2025-07-04-<2>  STARTS
from django.urls import path
from .views import chat_api

urlpatterns = [
    path('', chat_api, name='chat_api'), 
]
#MV-2025-07-04-<2>  ENDS