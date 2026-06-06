from service_objects import services

from common.base_models import PublicId
from common.utils import validation_return_response
from dailydata.feed_stock import recalculate_feed_snapshots
from flocks.models import Flock
from purchase.models import Purchase


def _feed_purchase_quantity(data):
    """
    U: Feed stock comes from feed purchases, so feed quantity must be explicit.
    """
    unit = data.get("unit") or 0
    size = data.get("size") or 0
    if unit <= 0 or size <= 0:
        validation_return_response(
            "quantity",
            "Feed purchases must include number of bags and bag size greater than 0.",
        )
    return unit * size


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
            feed_quantity = _feed_purchase_quantity(data)
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
                # U: OLD: quantity=data.get("size") * data.get("unit") was inline only here.
                # U: NEW: one helper controls feed-stock quantity consistently.
                quantity=feed_quantity,
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

        if purchase.type == "Feed":
            recalculate_feed_snapshots(flock, users)

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
        if purchase.type == "Feed":
            # U: OLD: editing bag count/size could leave Purchase.quantity and
            # U: existing DailyData feed_stock snapshots stale.
            # U: NEW: recompute feed quantity and all dependent daily snapshots.
            purchase.quantity = _feed_purchase_quantity(
                {
                    "unit": purchase.unit,
                    "size": purchase.size,
                }
            )
        purchase.save()
        if purchase.type == "Feed":
            recalculate_feed_snapshots(purchase.flock, purchase.user)
