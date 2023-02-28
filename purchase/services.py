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
        if data.get("type") == "Feed":
            purchase = Purchase.objects.create(
                public_id=PublicId.create_public_id(),
                flock=Flock.objects.get(public_id=data.get("flock_public_id")),
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
                flock=Flock.objects.get(public_id=data.get("flock_public_id")),
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
                flock=Flock.objects.get(public_id=data.get("flock_public_id")),
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
        if data.get("date"):
            purchase.date = data.get("date")
        if data.get("cost"):
            purchase.cost = data.get("cost")
        if data.get("quantity"):
            purchase.quantity = data.get("quantity")
        if data.get("company_name"):
            purchase.company_name = data.get("company_name")
        if data.get("item_name"):
            purchase.item_name = data.get("item_name")
        if data.get("item_type"):
            purchase.item_type = data.get("item_type")
        if data.get("unit"):
            purchase.unit = data.get("unit")
        if data.get("size"):
            purchase.size = data.get("size")
        if data.get("remarks"):
            purchase.remarks = data.get("remarks")
        purchase.save()
