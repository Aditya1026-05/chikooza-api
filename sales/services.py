from rest_framework import status
from service_objects import services

from common.base_models import PublicId
from common.utils import error_response
from dailydata.models import DailyData
from flocks.models import Flock
from sales.models import Sales


class AddSalesService(services.Service):
    def process(self):
        data = self.data.get('data')
        average_weight = data.get('total_weight') / data.get('lifting_count')
        cost = data.get('total_weight') * data.get('rate_per_kg')
        flock = self.data.get('flock')
        sales = Sales.objects.create(
            public_id=PublicId.create_public_id(),
            flock=flock,
            sales_type=data.get('sales_type'),
            date=data.get('date'),
            lifting_count=data.get('lifting_count'),
            total_weight=data.get('total_weight'),
            average_weight=average_weight,
            rate_per_kg=data.get('rate_per_kg'),
            cost=cost,
            buyer=data.get('buyer'),
            vehicle_no=data.get('vehicle_no'),
            remarks=data.get('remarks'),
            feed_total=data.get('feed_total') or 0,
            med_price=data.get('med_price') or 0,
            vacc_price=data.get('vacc_price') or 0,
            admin_charges=data.get('admin_charges') or 0,
            rearing_charges=data.get('rearing_charges') or 0,
            performance_incentives=data.get('performance_incentives') or 0,
            rate_incentives=data.get('rate_incentives') or 0,
            eef_incentives=data.get('eef_incentives') or 0,
            sp_rate_incentives=data.get('sp_rate_incentives') or 0,
            production_cost_recovery=data.get('production_cost_recovery') or 0,
            shortages=data.get('shortages') or 0,
            excess_mortality=data.get('excess_mortality') or 0,
            fcr_recovery=data.get('fcr_recovery') or 0,
            less_tds=data.get('less_tds') or 0,
            less_amct=data.get('less_amct') or 0,
            other_taxes=data.get('other_taxes') or 0,
            buyer_phone_no=data.get('buyer_phone_no') or 0,
            buyer_address=data.get('buyer_address') or 0,
            buyer_email=data.get('buyer_email') or 0,
        )

        feed_total = data.get('feed_total') or 0
        med_price = data.get('med_price') or 0
        vacc_price = data.get('vacc_price') or 0
        total_cost = feed_total + med_price + vacc_price
        total_incentives = sales.rearing_charges + sales.performance_incentives + sales.rate_incentives + sales.eef_incentives + sales.sp_rate_incentives
        total_penalties = sales.production_cost_recovery + sales.shortages + sales.excess_mortality + sales.fcr_recovery
        total_taxes = sales.less_tds + sales.less_amct + sales.other_taxes
        flock.actual_birds = flock.actual_birds - data.get('lifting_count')
        integration_cost = (total_cost + total_incentives) - total_taxes - total_penalties
        sales.integration_cost = integration_cost
        sales.save()
        flock.save()
        return sales


class UpdateSalesService(services.Service):
    def process(self):
        data = self.data.get('data')
        sales = self.data.get('sales')
        sales.date = data.get('date') or sales.date
        if data.get('lifting_count'):
            lifting_count = data.get('lifting_count')
            sales.lifting_count = data.get('lifting_count')
            sales.average_weight = data.get('total_weight') / data.get('lifting_count') if data.get(
                'total_weight') else sales.total_weight / data.get('lifting_count')
        else:
            lifting_count = 0
        if data.get('total_weight'):
            sales.total_weight = data.get('total_weight')
            sales.average_weight = data.get('total_weight') / data.get('lifting_count') if data.get(
                'lifting_count') else data.get('total_weight') / sales.lifting_count
        if data.get('total_weight') and data.get('lifting_count'):
            sales.average_weight = data.get('total_weight') / data.get('lifting_count')
        elif data.get('total_weight') or data.get('lifting_count'):
            if data.get('total_weight'):
                sales.average_weight = data.get('total_weight') / sales.lifting_count
            else:
                sales.average_weight = sales.total_weight / data.get('lifting_count')
        if data.get('rate_per_kg'):
            sales.rate_per_kg = data.get('rate_per_kg')
        if data.get('cost'):
            sales.cost = data.get('cost')
        if data.get('buyer'):
            sales.buyer = data.get('buyer')
        if data.get('vehicle_no') :
            sales.vehicle_no = data.get('vehicle_no')
        if data.get('buyer_address'):
            sales.buyer_address = data.get('buyer_address')
        if data.get('buyer_phone_no'):
            sales.buyer_phone_no = data.get('buyer_phone_no')
        if data.get('buyer_email'):
            sales.buyer_email = data.get('buyer_email')
        if data.get('remarks'):
            sales.remarks = data.get('remarks')
        if data.get('feed_total'):
            sales.feed_total = data.get('feed_total')
        if data.get('med_price'):
            sales.med_price = data.get('med_price')
        if data.get('vacc_price'):
            sales.vacc_price = data.get('vacc_price')
        if data.get('admin_charges'):
            sales.admin_charges = data.get('admin_charges')
        if data.get('rearing_charges'):
            sales.rearing_charges = data.get('rearing_charges')
        if data.get('performance_incentives'):
            sales.performance_incentives = data.get('performance_incentives')
        if data.get('rate_incentives'):
            sales.rate_incentives = data.get('rate_incentives')
        if data.get('eef_incentives'):
            sales.eef_incentives = data.get('eef_incentives')
        if data.get('sp_rate_incentives'):
            sales.sp_rate_incentives = data.get('sp_rate_incentives')
        if data.get('production_cost_recovery'):
            sales.production_cost_recovery = data.get('production_cost_recovery')
        if data.get('shortages'):
            sales.shortages = data.get('shortages')
        if data.get('excess_mortality'):
            sales.excess_mortality = data.get('excess_mortality')
        if data.get('fcr_recovery'):
            sales.less_tds = data.get('fcr_recovery')
        if data.get('vehicle_no'):
            sales.less_tds = data.get('less_tds')
        if data.get('less_amct'):
            sales.less_amct = data.get('less_amct')
        if data.get('other_taxes'):
            sales.other_taxes = data.get('other_taxes')


        sales.flock.actual_birds = sales.flock.actual_birds - lifting_count
        sales.flock.save()
        feed_total = data.get('feed_total') or 0
        med_price = data.get('med_price') or 0
        vacc_price = data.get('vacc_price') or 0
        total_cost = feed_total + med_price + vacc_price
        total_incentives = sales.rearing_charges + sales.performance_incentives + sales.rate_incentives + sales.eef_incentives + sales.sp_rate_incentives
        total_penalties = sales.production_cost_recovery + sales.shortages + sales.excess_mortality + sales.fcr_recovery
        total_taxes = sales.less_tds + sales.less_amct + sales.other_taxes
        integration_cost = (total_cost + total_incentives) - total_taxes - total_penalties
        sales.integration_cost = integration_cost
        sales.save()
