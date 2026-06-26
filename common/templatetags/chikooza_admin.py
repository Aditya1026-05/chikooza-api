from datetime import date
from urllib.parse import urlencode

from django import template
from django.contrib.admin.models import LogEntry
from django.urls import reverse

from aibot.models import AIChatLog
from chatbot.models import ChatLog, ChatSession, KnowledgeDocument
from common.base_models import EmailOtp, Otp, RegistrationApprovalPolicy, Users, UsersForgotPassword
from dailydata.models import DailyData, DarknessTime, FeedAvailability, FlockVaccination, Vaccines
from farm.models import Country, Farm, State
from flocks.models import Breed, Flock, Hatchery, Integrator
from purchase.models import Purchase
from sales.models import Sales

register = template.Library()


def _admin_url(model, params=None):
    opts = model._meta
    url = reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist")
    if params:
        return f"{url}?{urlencode(params)}"
    return url


def _admin_add_url(model):
    opts = model._meta
    return reverse(f"admin:{opts.app_label}_{opts.model_name}_add")


def _can_view(user, model):
    opts = model._meta
    return (
        user.is_superuser
        or user.has_perm(f"{opts.app_label}.view_{opts.model_name}")
        or user.has_perm(f"{opts.app_label}.change_{opts.model_name}")
    )


def _can_add(user, model):
    opts = model._meta
    return user.is_superuser or user.has_perm(f"{opts.app_label}.add_{opts.model_name}")


def _link(user, label, model, params=None, add=False, description=""):
    if add:
        if not _can_add(user, model):
            return None
        url = _admin_add_url(model)
    else:
        if not _can_view(user, model):
            return None
        url = _admin_url(model, params=params)

    return {
        "label": label,
        "url": url,
        "description": description,
    }


def _visible_links(user, links):
    return [link for link in links if link]


@register.simple_tag(takes_context=True)
def chikooza_admin_dashboard(context):
    user = context["request"].user
    today = date.today()

    pending_param = {"approval_status__exact": Users.APPROVAL_PENDING}
    active_flock_param = {"status__exact": "1"}

    metrics = [
        {
            "label": "Pending farmers",
            "value": Users.objects.filter(approval_status=Users.APPROVAL_PENDING).count(),
            "url": _admin_url(Users, pending_param),
            "tone": "warning",
        },
        {
            "label": "Active farmers",
            "value": Users.objects.filter(is_active=True, is_staff=False, is_superuser=False).count(),
            "url": _admin_url(Users, {"is_active__exact": "1"}),
            "tone": "success",
        },
        {
            "label": "Active flocks",
            "value": Flock.objects.filter(status=True).count(),
            "url": _admin_url(Flock, active_flock_param),
            "tone": "primary",
        },
        {
            "label": "Daily entries today",
            "value": DailyData.objects.filter(date=today).count(),
            "url": _admin_url(DailyData),
            "tone": "info",
        },
    ]

    sections = [
        {
            "step": "1",
            "title": "Farmers",
            "summary": "Approve accounts, open a farmer, then inspect their workspace.",
            "links": _visible_links(
                user,
                [
                    _link(user, "Review pending farmers", Users, pending_param),
                    _link(user, "All farmer accounts", Users),
                    _link(user, "Registration policy", RegistrationApprovalPolicy),
                ],
            ),
        },
        {
            "step": "2",
            "title": "Farm setup",
            "summary": "Check the farm and flock setup before daily operations.",
            "links": _visible_links(
                user,
                [
                    _link(user, "Farms", Farm),
                    _link(user, "Flocks", Flock),
                    _link(user, "Add farm", Farm, add=True),
                    _link(user, "Add flock", Flock, add=True),
                ],
            ),
        },
        {
            "step": "3",
            "title": "Operations",
            "summary": "Follow the same flow farmers use: daily data, purchases, sales.",
            "links": _visible_links(
                user,
                [
                    _link(user, "Daily data", DailyData),
                    _link(user, "Vaccinations", FlockVaccination),
                    _link(user, "Purchases", Purchase),
                    _link(user, "Sales", Sales),
                ],
            ),
        },
        {
            "step": "4",
            "title": "Support",
            "summary": "Inspect AI/chat records and manage support knowledge.",
            "links": _visible_links(
                user,
                [
                    _link(user, "Farmer AI logs", AIChatLog),
                    _link(user, "Public chat sessions", ChatSession),
                    _link(user, "Public chat logs", ChatLog),
                    _link(user, "Knowledge documents", KnowledgeDocument),
                ],
            ),
        },
    ]

    master_links = _visible_links(
        user,
        [
            _link(user, "Countries", Country),
            _link(user, "States", State),
            _link(user, "Breeds", Breed),
            _link(user, "Hatcheries", Hatchery),
            _link(user, "Integrators", Integrator),
            _link(user, "Vaccines", Vaccines),
            _link(user, "Darkness time", DarknessTime),
            _link(user, "Feed availability", FeedAvailability),
            _link(user, "Mobile OTPs", Otp),
            _link(user, "Email OTPs", EmailOtp),
            _link(user, "Password OTPs", UsersForgotPassword),
        ],
    )

    recent_activity = LogEntry.objects.select_related("content_type", "user").order_by("-action_time")[:6]

    return {
        "metrics": metrics,
        "sections": sections,
        "master_links": master_links,
        "recent_activity": recent_activity,
    }
