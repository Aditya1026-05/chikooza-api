from oauth2_provider.contrib.rest_framework import (
    OAuth2Authentication,
    TokenMatchesOASRequirements,
)
from rest_framework import status, viewsets
from rest_framework.response import Response

from common.constant import ERROR, FLOCK_DOES_NOT_EXIST, PURCHASE_DOES_NOT_EXIST
from common.tenanting import is_admin_request, request_account_user
from common.utils import error_response, get_detail, list_response, success_response, validate_url_value
from flocks.models import Flock
from purchase.models import Purchase
from purchase.serializers import (
    AddPurchaseSerializer,
    GetPurchaseSerializer,
    QuantitySerializer,
    UpdatePurchaseSerializer,
)
from purchase.services import AddPurchaseService, UpdatePurchaseService


def _purchase_queryset_for_request(request):
    """
    U: Scope purchase records to the authenticated farmer unless an admin is explicitly requesting data.
    """
    if is_admin_request(request):
        return Purchase.objects.all()
    return Purchase.objects.filter(user=request_account_user(request))


def _flock_queryset_for_request(request):
    if is_admin_request(request):
        return Flock.objects.all()
    return Flock.objects.filter(user=request_account_user(request))


class PurchaseView(viewsets.ViewSet):
    """
    Class to perform crud operation for purchase.
    """

    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenMatchesOASRequirements]

    required_alternate_scopes = {
        "GET": [["read"]],
        "POST": [["create"]],
        "PATCH": [["update"]],
        "PUT": [["update"]],
    }

    @classmethod
    def create(cls, request):
        """
        Class to create purchase object.
        """
        try:
            serializer = AddPurchaseSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer_data = serializer.validated_data
                purchase = AddPurchaseService.execute(
                    {"data": serializer_data, "users": request.user.users}
                )
            return get_detail(
                "Purchase Created Successfully.",
                {"public_id": purchase.public_id},
                status.HTTP_201_CREATED,
            )

        except Flock.DoesNotExist:
            return Response({ERROR: FLOCK_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)

    @classmethod
    def retrieve(cls, request, pk):
        """
        Class to get purchase object.
        """
        try:
            validate_url_value(pk, "purchasePublicId")
            # U: OLD: Purchase.objects.get(public_id=pk)
            purchase = _purchase_queryset_for_request(request).get(public_id=pk)
            return get_detail(
                "Purchase details",
                GetPurchaseSerializer(purchase).data,
                status.HTTP_200_OK,
            )
        except Purchase.DoesNotExist:
            return Response({ERROR: PURCHASE_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)

    @classmethod
    def partial_update(cls, request, pk):
        try:
            validate_url_value(pk, "purchasePublicId")
            # U: OLD: update lookup only checked public_id and allowed cross-farmer updates.
            purchase = _purchase_queryset_for_request(request).get(public_id=pk)
            serializer = UpdatePurchaseSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer_data = serializer.validated_data
                UpdatePurchaseService.execute(
                    {"data": serializer_data, "purchase": purchase}
                )
                return success_response(
                    "Purchase update successfully",
                    "Purchase",
                    "Purchase update successfully",
                    200,
                )
            return Response({ERROR: PURCHASE_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)
        except Purchase.DoesNotExist:
            return Response({ERROR: PURCHASE_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)

    @classmethod
    def list(cls, request):
        try:
            # U: OLD: another farmer's flock id returned 200 with an empty list.
            # U: NEW: validate the flock through the tenant/admin scope first.
            flock = _flock_queryset_for_request(request).get(
                public_id=request.GET.get("flock_public_id")
            )
            purchase = _purchase_queryset_for_request(request).filter(
                flock=flock
            )
            if request.GET.get('filter') == 'feed':
                # U: OLD: list used flock_public_id only, so another farmer's flock purchases were visible.
                purchase = purchase.filter(type='Feed')
            return list_response(
                "Purchase List",
                purchase.count(),
                "purchase_list",
                GetPurchaseSerializer(purchase, many=True).data,
                status.HTTP_200_OK,
            )

        except Flock.DoesNotExist:
            return error_response(
                {ERROR: FLOCK_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )
        except Purchase.DoesNotExist:
            return Response({ERROR: PURCHASE_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)


class QuantityView(viewsets.ViewSet):
    """
    Class to get the total quantity of feed.
    """

    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenMatchesOASRequirements]

    required_alternate_scopes = {
        "GET": [["read"]],
        "POST": [["create"]],
        "PATCH": [["update"]],
        "PUT": [["update"]],
    }

    def list(cls, request):
        try:
            serializer = QuantitySerializer(data=request.GET)
            if serializer.is_valid(raise_exception=True):
                serializer_data = serializer.validated_data
                flock = _flock_queryset_for_request(request).get(
                    public_id=serializer_data["flock"].get("public_id")
                )
                purchases = _purchase_queryset_for_request(request).filter(
                    flock=flock,
                    # U: OLD: quantity silently returned 0 for another farmer's flock.
                    # U: NEW: reject inaccessible flock ids before summing.
                    type="Feed",
                    date__lte=serializer_data["date"],
                )
                quantity = 0
                for purchase in purchases:
                    quantity += purchase.quantity or 0
                return get_detail(
                    "Quantity of Feed", {"quantity": quantity}, status.HTTP_200_OK
                )
        except Flock.DoesNotExist:
            return error_response(
                {ERROR: FLOCK_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )
