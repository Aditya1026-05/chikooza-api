from django.http import HttpResponse
from django.template.loader import get_template
from rest_framework import status
from rest_framework.response import Response
from xhtml2pdf import pisa

from common.base_models import Otp, PublicId, RegistrationApprovalPolicy, Users
from common.constant import ERROR, INVALID_OTP
from common.utils import (
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


def create_user(data, sign_up=None, phone_verified=False, email_verified=False):
    mobile_number_validation(data.get("mobile_number"))
    approval_policy = RegistrationApprovalPolicy.get_default()
    auto_approved = approval_policy.should_auto_approve(
        email=data.get("email"),
        phone_verified=phone_verified,
        email_verified=email_verified,
    )
    approval_status = (
        Users.APPROVAL_APPROVED if auto_approved else Users.APPROVAL_PENDING
    )
    users = Users.objects.create(
        username=data.get("username"),
        first_name=data.get("name"),
        email=data.get("email"),
        mobile_number=data.get("mobile_number"),
        public_id=PublicId.create_public_id(),
        is_phone_verified=phone_verified,
        is_email_verified=email_verified,
        approval_status=approval_status,
        is_active=auto_approved,
    )

    users.set_password(data.get("password"))
    users.save()
    get_or_create_oauth_application(users)
    return get_detail(
        "User Registered"
        if auto_approved
        else "Registration submitted for admin approval",
        {
            "public_id": users.public_id,
            "approval_status": users.approval_status,
            "is_active": users.is_active,
        },
        status.HTTP_201_CREATED,
    )


def render_to_pdf(template_src, context_dict=None, filename=None):
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
