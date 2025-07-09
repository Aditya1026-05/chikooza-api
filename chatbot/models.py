#MV-2025-07-04-<7>  STARTS
from django.contrib.auth.models import User
from django.db import models

class ChatLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    query = models.TextField()
    response = models.TextField()
    query_id = models.CharField(max_length=36)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['query_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['user']),
        ]
#MV-2025-07-04-<7>  ENDS