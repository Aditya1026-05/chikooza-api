import json

from django.http import HttpResponse
from django.utils.encoding import force_str

from common.constant import APP_RESULT, MESSAGE


class PageNotFoundMiddleware(object):
    """
    Middleware for json response on page not found error.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            response.status_code == 404
            and "application/json" not in response["content-type"]
        ):
            data = {"message": f"This url {request.path} not found."}
            response = HttpResponse(
                json.dumps(data), content_type="application/json", status=404
            )
        return response


class AuthenticationErrorMessage:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code in [401, 403, 405]:
            # OAuth responses may be plain HttpResponse objects rather than DRF responses.
            response_data = getattr(response, "data", None)
            if isinstance(response_data, dict):
                message = str(
                    response_data.get("detail")
                    or response_data.get("error")
                    or "Authentication failed."
                )
                data = {MESSAGE: message, APP_RESULT: response_data}
            else:
                message = (
                    force_str(getattr(response, "content", b"")).strip()
                    or "Authentication failed."
                )
                data = {MESSAGE: message, APP_RESULT: {"detail": message}}
            response = HttpResponse(
                json.dumps(data),
                content_type="application/json",
                status=response.status_code,
            )
        return response
