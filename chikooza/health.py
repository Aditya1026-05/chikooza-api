"""Public health endpoints used by service managers and load balancers."""

from django.db import connection
from django.db.utils import DatabaseError
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def liveness(request):
    """Report whether the Django process can serve an HTTP request."""
    return JsonResponse({"status": "ok"})


@require_GET
def readiness(request):
    """Report whether the API can reach its configured database."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse(
            {"status": "unavailable", "checks": {"database": "unavailable"}},
            status=503,
        )

    return JsonResponse({"status": "ok", "checks": {"database": "ok"}})
