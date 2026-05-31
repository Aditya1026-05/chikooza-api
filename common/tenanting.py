def is_admin_request(request):
    """
    U: NEW: central admin/staff gate for tenant-scoped API querysets.
    U: Normal farmers see only their own rows; staff/superusers can inspect all
    U: rows through the API when supervisor/admin control is needed.
    """
    user = getattr(request, "user", None)
    return bool(
        getattr(user, "is_superuser", False)
        or getattr(user, "is_staff", False)
    )


def request_account_user(request):
    """
    Return the project user record attached to the request.
    Some legacy OAuth paths expose it as request.user.users; direct tests/admin
    paths may already pass the Users object itself.
    """
    user = getattr(request, "user", None)
    return getattr(user, "users", user)
