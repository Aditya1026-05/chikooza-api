def is_admin_request(request):
    """
    Return whether the request may bypass normal farmer tenant scoping.

    Normal farmers see only their own rows. Staff and superusers may inspect
    all rows through API endpoints that explicitly use this gate.
    """
    user = getattr(request, "user", None)
    return bool(getattr(user, "is_superuser", False) or getattr(user, "is_staff", False))


def request_account_user(request):
    """
    Return the project user record attached to the request.
    Some legacy OAuth paths expose it as request.user.users; direct tests/admin
    paths may already pass the Users object itself.
    """
    user = getattr(request, "user", None)
    return getattr(user, "users", user)
