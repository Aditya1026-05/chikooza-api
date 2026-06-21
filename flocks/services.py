import datetime

from service_objects import services

from common.base_models import PublicId
from common.constant import ERROR
from common.utils import validation_return_response
from farm.models import Farm
from flocks.models import Breed, Flock, Hatchery, Integrator


class AddFlockService(services.Service):
    """
    Class for business logic to add flocks.
    """

    def process(self):
        data = self.data.get("data")
        user = self.data.get("user")
        farm = Farm.objects.get(public_id=data.get("farm_public_id"), user=user)
        integration = data.get("integration")
        if integration:
            integrator = Integrator.objects.get(
                public_id=data.get("integrator_public_id")
            )
        else:
            integrator = None
        breed = Breed.objects.get(public_id=data.get("breed_public_id"))
        hatchery_public_id = data.get("hatchery_public_id")
        if hatchery_public_id:
            hatchery = Hatchery.objects.get(public_id=data.get("hatchery_public_id"))
        else:
            hatchery = None
        hatchery_vaccine = data.get("hatchery_vaccine")
        if hatchery_vaccine:
            hatch_vaccine = hatchery_vaccine
        else:
            hatch_vaccine = False
        flock = Flock.objects.create(
            public_id=PublicId.create_public_id(),
            user=user,
            farm=farm,
            name=data.get("flock_name"),
            integration=data.get("integration"),
            integrator=integrator,
            hatch_date=data.get("hatch_date"),
            flock_size=data.get("flock_size"),
            actual_birds=data.get("actual_birds"),
            breed=breed,
            hatchery=hatchery,
            hatchery_name=data.get("hatchery_name"),
            chick_weight=data.get("chick_weight"),
            hatchery_vaccine=hatch_vaccine,
            feed_sys=data.get("feed_sys"),
            drinking_sys=data.get("drinking_sys"),
            ec_shed=data.get("ec_shed"),
            chick_cost=data.get("chick_cost"),
            flock_bird=data.get("actual_birds"),
        )
        return flock


class UpdateFlockService(services.Service):
    """
    Class to update flock.
    """

    def process(self):
        data = self.data.get("data")
        flock = self.data.get("flock")
        name = data.get("flock_name")
        if name:
            flock.name = name
        integration = data.get("integration")
        flock.integration = data.get("integration")
        if integration:
            if data.get("integrator_public_id"):
                flock.integrator = Integrator.objects.get(
                    public_id=data.get("integrator_public_id")
                )
                flock.chick_cost = None
        else:
            if data.get("chick_cost"):
                flock.chick_cost = data.get("chick_cost")
                flock.integrator = None
        hatch_date = data.get("hatch_date")
        if hatch_date:
            flock.hatch_date = hatch_date
        flock_size = data.get("flock_size")
        if flock_size:
            flock.flock_size = flock_size
        actual_birds = data.get("actual_birds")
        if actual_birds:
            flock.actual_birds = actual_birds
            flock.flock_bird = actual_birds
        if data.get("breed_public_id"):
            breed = Breed.objects.get(public_id=data.get("breed_public_id"))
            flock.breed = breed
        if data.get("hatchery_public_id"):
            hatchery = Hatchery.objects.get(public_id=data.get("hatchery_public_id"))
            flock.hatchery = hatchery
        hatchery_name = data.get("hatchery_name")
        if hatchery_name:
            flock.hatchery_name = hatchery_name
        chick_weight = data.get("chick_weight")
        if chick_weight:
            flock.chick_weight = chick_weight
        hatchery_vaccine = data.get("hatchery_vaccine")
        if hatchery_vaccine:
            flock.hatchery_vaccine = hatchery_vaccine
        feed_sys = data.get("feed_sys")
        if feed_sys:
            flock.feed_sys = feed_sys
        drinking_sys = data.get("drinking_sys")
        if drinking_sys:
            flock.drinking_sys = drinking_sys
        ec_shed = data.get("ec_shed")
        if ec_shed is not None:
            flock.ec_shed = ec_shed
        flock.save()
        return flock
