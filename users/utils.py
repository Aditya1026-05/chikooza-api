from django.http import HttpResponse
from django.template.loader import get_template
from rest_framework import status
from rest_framework.response import Response
from xhtml2pdf import pisa

from common.base_models import Otp, PublicId, Users
from common.constant import ERROR, INVALID_OTP
from common.utils import (
    create_token,
    get_detail,
    get_or_create_oauth_application,
    mobile_number_validation,
)

def verify_otp(mobile_number, otp):
    if Otp.objects.filter(mobile_number=mobile_number, otp=otp).exists():
        otp = Otp.objects.get(mobile_number=mobile_number, otp=otp)
        otp.is_verify = True
        otp.save()
        return otp
    return Response({ERROR: INVALID_OTP}, status.HTTP_400_BAD_REQUEST)


def create_user(data, sign_up=None):
    mobile_number_validation(data.get("mobile_number"))
    users = Users.objects.create(
        username=data.get("username"),
        first_name=data.get("name"),
        email=data.get("email"),
        mobile_number=data.get("mobile_number"),
        public_id=PublicId.create_public_id(),
    )

    users.set_password(data.get("password"))
    users.save()
    # U: OLD: Application.objects.create() used django-oauth-toolkit defaults,
    # U: which hash client_secret and break this legacy password-grant login flow.
    # U: NEW: create a server-owned OAuth application with a usable secret.
    user = get_or_create_oauth_application(users)
    data["status_code"] = 201
    token = create_token(
        users.username, data.get("password"), user.client_id, user.client_secret
    )
    token["public_id"] = users.public_id
    return get_detail(
        "User Registered", {"public_id": users.public_id}, status.HTTP_201_CREATED
    )

def render_to_pdf(template_src, context_dict=None, filename=None):
    # U: OLD: context_dict={} used a mutable default argument.
    # U: NEW: default to None and create a fresh dict for each PDF render.
    context_dict = context_dict or {}
    template = get_template(template_src)
    html = template.render(context_dict)
    response = HttpResponse(content_type="application/pdf")
    if filename:
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
    pdf_status = pisa.CreatePDF(html, dest=response)

    if pdf_status.err:
        return HttpResponse("Some errors were encountered <pre>" + html + "</pre>")

    return response
