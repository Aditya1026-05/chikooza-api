from service_objects import services

from common.base_models import PublicId
from flocks.models import Flock
from purchase.models import Purchase


class AddPurchaseService(services.Service):
    """
    Class to write business logic for creating purchase object.
    """

    def process(self):
        data = self.data.get("data")
        users = self.data.get("users")
        # U: OLD: each branch used Flock.objects.get(public_id=...) and could attach a purchase to another farmer's flock.
        # U: NEW: resolve the flock through the authenticated farmer before creating purchase records.
        flock = Flock.objects.get(public_id=data.get("flock_public_id"), user=users)
        if data.get("type") == "Feed":
            purchase = Purchase.objects.create(
                public_id=PublicId.create_public_id(),
                flock=flock,
                user=users,
                type=data.get("type"),
                date=data.get("date"),
                cost=data.get("cost"),
                remarks=data.get("remarks"),
                company_name=data.get("company_name"),
                item_name=data.get("item_name"),
                unit=data.get("unit"),
                size=data.get("size"),
                item_type=data.get("item_type"),
                quantity=data.get("size") * data.get("unit"),
            )
        elif data.get("type") in ["Medicine", "Vaccination", "Equipment"]:
            purchase = Purchase.objects.create(
                public_id=PublicId.create_public_id(),
                flock=flock,
                user=users,
                type=data.get("type"),
                date=data.get("date"),
                cost=data.get("cost"),
                remarks=data.get("remarks"),
                company_name=data.get("company_name"),
                item_name=data.get("item_name"),
                quantity=data.get("quantity"),
            )
        else:
            purchase = Purchase.objects.create(
                public_id=PublicId.create_public_id(),
                flock=flock,
                user=users,
                type=data.get("type"),
                date=data.get("date"),
                cost=data.get("cost"),
                remarks=data.get("remarks"),
            )

        return purchase


class UpdatePurchaseService(services.Service):
    """
    Class to update purchase object.
    """

    def process(self):
        purchase = self.data.get("purchase")
        data = self.data.get("data")
        # U: OLD: truthy checks skipped valid values such as 0 and made clearing optional fields impossible.
        # U: NEW: update fields based on serializer-provided keys.
        if "date" in data:
            purchase.date = data.get("date")
        if "cost" in data:
            purchase.cost = data.get("cost")
        if "quantity" in data:
            purchase.quantity = data.get("quantity")
        if "company_name" in data:
            purchase.company_name = data.get("company_name")
        if "item_name" in data:
            purchase.item_name = data.get("item_name")
        if "item_type" in data:
            purchase.item_type = data.get("item_type")
        if "unit" in data:
            purchase.unit = data.get("unit")
        if "size" in data:
            purchase.size = data.get("size")
        if "remarks" in data:
            purchase.remarks = data.get("remarks")
        purchase.save()
