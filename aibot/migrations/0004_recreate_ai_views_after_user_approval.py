# Recreate AI SQL views after user verification/admin approval migration.

from django.db import migrations


FORWARD_SQL = """
DROP VIEW IF EXISTS ai_farm_data_view;
DROP VIEW IF EXISTS ai_farm_flock_data_view;
DROP VIEW IF EXISTS ai_purchase_data_view;
DROP VIEW IF EXISTS ai_dailydata_data_view;
DROP VIEW IF EXISTS ai_sale_data_view;

CREATE VIEW ai_farm_flock_data_view AS
SELECT
    u.user_ptr_id AS owner_id,
    f.id AS farm_id,
    f.name AS farm_name,
    f.address AS farm_address,
    f.city AS farm_city,
    f.pin AS farm_pin,
    f.shed_count,
    f.status AS farm_status,
    fl.id AS flock_id,
    fl.name AS flock_name,
    fl.hatch_date,
    fl.flock_size,
    fl.actual_birds,
    fl.chick_weight,
    fl.feed_sys,
    fl.drinking_sys,
    fl.ec_shed,
    fl.chick_cost AS flock_cost,
    fl.flock_bird,
    fl.status AS flock_status,
    b.name AS breed_name,
    h.name AS hatchery_name,
    i.name AS integrator_name
FROM users u
JOIN farms f ON u.user_ptr_id = f.user_id
LEFT JOIN flocks_flock fl ON fl.farm_id = f.id AND fl.user_id = u.user_ptr_id
LEFT JOIN flocks_breed b ON b.id = fl.breed_id
LEFT JOIN flocks_hatchery h ON h.id = fl.hatchery_id
LEFT JOIN flocks_integrator i ON i.id = fl.integrator_id;

CREATE VIEW ai_purchase_data_view AS
SELECT
    u.user_ptr_id AS owner_id,
    f.id AS farm_id,
    f.name AS farm_name,
    f.city AS farm_city,
    fl.id AS flock_id,
    fl.name AS flock_name,
    fl.flock_size,
    fl.actual_birds,
    fl.chick_cost AS flock_cost,
    pp.type AS purchase_type,
    pp.date AS purchase_date,
    pp.cost AS purchase_amount,
    pp.quantity,
    pp.item_name AS purchased_item,
    pp.item_type,
    pp.unit,
    pp.size,
    pp.company_name,
    pp.remarks AS purchase_remarks,
    pp.adjust,
    pp.adjust_type
FROM users u
JOIN farms f ON u.user_ptr_id = f.user_id
JOIN flocks_flock fl ON fl.farm_id = f.id AND fl.user_id = u.user_ptr_id
LEFT JOIN purchase_purchase pp ON pp.flock_id = fl.id AND pp.user_id = u.user_ptr_id;

CREATE VIEW ai_dailydata_data_view AS
SELECT
    u.user_ptr_id AS owner_id,
    f.id AS farm_id,
    f.name AS farm_name,
    f.city AS farm_city,
    fl.id AS flock_id,
    fl.name AS flock_name,
    fl.flock_size,
    fl.actual_birds,
    dd.id AS daily_data_id,
    dd.date AS record_date,
    dd.mortality AS birds_died,
    dd.total_mort,
    dd.current_bird_count AS birds_current,
    dd.feed_stock,
    dd.feed_intake AS feed_consumed_kg,
    dd.total_feed,
    dd.average_bird_weight,
    dd.average_feed,
    dd.total_average_feed,
    dd.fcr,
    dd.total_fcr,
    dd.cooling,
    dd.heating,
    dd.seek,
    dd.medicine,
    dd.remarks,
    dd.status AS daily_data_status,
    dt.name AS darkness_time_name,
    fa.name AS feed_availability_name,
    dd.flock_birds
FROM users u
JOIN farms f ON u.user_ptr_id = f.user_id
JOIN flocks_flock fl ON fl.farm_id = f.id AND fl.user_id = u.user_ptr_id
LEFT JOIN dailydata_dailydata dd ON dd.flock_id = fl.id AND dd.user_id = u.user_ptr_id
LEFT JOIN dailydata_darknesstime dt ON dt.id = dd.darkness_time_id
LEFT JOIN dailydata_feedavailability fa ON fa.id = dd.feed_availability_id;

CREATE VIEW ai_sale_data_view AS
SELECT
    u.user_ptr_id AS owner_id,
    f.id AS farm_id,
    f.name AS farm_name,
    f.city AS farm_city,
    fl.id AS flock_id,
    fl.name AS flock_name,
    fl.flock_size,
    fl.actual_birds,
    ss.id AS sale_id,
    ss.sales_type AS sale_type,
    ss.date AS sale_date,
    ss.lifting_count,
    ss.total_weight,
    ss.average_weight,
    ss.rate_per_kg,
    ss.cost AS sale_amount,
    ss.buyer,
    ss.vehicle_no,
    ss.remarks AS sale_remarks,
    ss.feed_total,
    ss.med_price,
    ss.vacc_price,
    ss.admin_charges,
    ss.rearing_charges,
    ss.performance_incentives,
    ss.rate_incentives,
    ss.production_cost_recovery,
    ss.shortages,
    ss.excess_mortality,
    ss.fcr_recovery,
    ss.integration_cost
FROM users u
JOIN farms f ON u.user_ptr_id = f.user_id
JOIN flocks_flock fl ON fl.farm_id = f.id AND fl.user_id = u.user_ptr_id
LEFT JOIN sales_sales ss ON ss.flock_id = fl.id;
"""


REVERSE_SQL = """
DROP VIEW IF EXISTS ai_farm_data_view;
DROP VIEW IF EXISTS ai_farm_flock_data_view;
DROP VIEW IF EXISTS ai_purchase_data_view;
DROP VIEW IF EXISTS ai_dailydata_data_view;
DROP VIEW IF EXISTS ai_sale_data_view;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("aibot", "0003_expand_ai_sql_views"),
        ("common", "0002_emailotp_registrationapprovalpolicy_and_more"),
    ]

    operations = [
        # U: NEW: common.0002 drops SQLite AI views before altering users; recreate
        # U: them afterward so the AI assistant keeps its tenant-scoped SQL views.
        migrations.RunSQL(FORWARD_SQL, REVERSE_SQL),
    ]
