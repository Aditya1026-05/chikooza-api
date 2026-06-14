from service_objects import services

from common.base_models import PublicId
from farm.models import Country, Farm, State


class AddFarmService(services.Service):
    """
    Class to write business logic to add farm details.
    """

    def process(self):
        data = self.data.get("data")
        state_data = data.get("state_public_id")
        state = State.objects.get(public_id=state_data)
        country_data = data.get("country_public_id")
        country = Country.objects.get(public_id=country_data)
        farm = Farm.objects.create(
            public_id=PublicId.create_public_id(),
            user=self.data.get("user"),
            name=data.get("name"),
            address=data.get("address"),
            city=data.get("city"),
            district=data.get("district", ""),
            state=state,
            country=country,
            pin=data.get("pin"),
            lat_long=data.get("lat_long") if data.get("lat_long") else '',
            shed_count=data.get("shed_count"),
            status=data.get("status"),
        )
        return farm


class UpdateFarmService(services.Service):
    """
    Class to write business logic for updating farm details.
    """

    def process(self):
        data = self.data.get("data")
        farm = self.data.get("farm")
        name = data.get("name")
        address = data.get("address")
        city = data.get("city")
        district = data.get("district")
        state_public_id = data.get("state_public_id")
        country_public_id = data.get("country_public_id")
        pin = data.get("pin")
        lat_long = data.get("lat_long")
        shed_count = data.get("shed_count")
        if name:
            farm.name = name
        if address:
            farm.address = address
        if city:
            farm.city = city
        if district is not None:
            farm.district = district
        if state_public_id:
            state = State.objects.get(public_id=state_public_id)
            farm.state = state
        if country_public_id:
            country = Country.objects.get(public_id=country_public_id)
            farm.country = country
        if pin:
            farm.pin = pin
        if lat_long:
            farm.lat_long = lat_long
        if shed_count:
            farm.shed_count = shed_count
        farm.save()
