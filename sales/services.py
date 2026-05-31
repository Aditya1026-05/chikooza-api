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
        # U: OLD: truthy checks skipped valid zero values, setting vehicle_no
        # U: also set less_tds=None, and every edit subtracted birds again.
        # U: NEW: update only supplied fields and adjust flock birds by the
        # U: lifting-count delta so editing a sale is idempotent.
        old_lifting_count = sales.lifting_count or 0
        if 'date' in data:
            sales.date = data.get('date')
        if 'lifting_count' in data:
            sales.lifting_count = data.get('lifting_count')
        if 'total_weight' in data:
            sales.total_weight = data.get('total_weight')
        if sales.lifting_count:
            sales.average_weight = sales.total_weight / sales.lifting_count
        else:
            sales.average_weight = 0
        if 'rate_per_kg' in data:
            sales.rate_per_kg = data.get('rate_per_kg')
        sales.cost = sales.total_weight * sales.rate_per_kg

        direct_fields = [
            'buyer',
            'vehicle_no',
            'buyer_address',
            'buyer_phone_no',
            'buyer_email',
            'remarks',
            'feed_total',
            'med_price',
            'vacc_price',
            'admin_charges',
            'rearing_charges',
            'performance_incentives',
            'rate_incentives',
            'eef_incentives',
            'sp_rate_incentives',
            'production_cost_recovery',
            'shortages',
            'excess_mortality',
            'fcr_recovery',
            'less_tds',
            'less_amct',
            'other_taxes',
        ]
        for field in direct_fields:
            if field in data:
                setattr(sales, field, data.get(field))

        lifting_delta = (sales.lifting_count or 0) - old_lifting_count
        sales.flock.actual_birds = sales.flock.actual_birds - lifting_delta
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
