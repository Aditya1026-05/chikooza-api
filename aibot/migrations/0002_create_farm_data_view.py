from django.db import migrations

SQL_VIEW = """
DROP VIEW IF EXISTS ai_farm_data_view;

CREATE VIEW ai_farm_data_view AS
SELECT 
    -- ===== User Information =====
    u.user_ptr_id AS owner_id,
    
    -- ===== Farm Details =====
    f.id AS farm_id,
    f.name AS farm_name,
    
    -- ===== Flock Information =====
    fl.id AS flock_id,
    fl.name AS flock_name,
    
    -- ===== Daily Metrics =====
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
    
    -- ===== Sales Data =====
    ss.id AS sale_id,
    ss.sales_type AS sale_type,
    ss.date AS sale_date,
    ss.total_weight,
    ss.average_weight,
    ss.rate_per_kg,
    ss.cost AS sale_amount,
    ss.remarks AS sale_remarks,
    ss.feed_total,
    ss.med_price,
    
    -- ===== Purchase Data =====
    pp.type AS purchase_type,
    pp.date AS purchase_date,
    pp.cost AS purchase_amount,
    pp.quantity,
    pp.item_name AS purchased_item,
    pp.item_type,
    pp.unit,
    pp.size
    
FROM 
    users u
JOIN 
    farms f ON u.user_ptr_id = f.user_id
JOIN 
    flocks_flock fl ON fl.farm_id = f.id AND fl.user_id = u.user_ptr_id
LEFT JOIN 
    dailydata_dailydata dd ON dd.flock_id = fl.id AND dd.user_id = u.user_ptr_id
LEFT JOIN 
    sales_sales ss ON ss.flock_id = fl.id
LEFT JOIN 
    purchase_purchase pp ON pp.flock_id = fl.id AND pp.user_id = u.user_ptr_id
"""

REVERSE_SQL = "DROP VIEW IF EXISTS ai_farm_data_view;"

class Migration(migrations.Migration):

    dependencies = [
        ("aibot", "0001_initial"),
        ("farm", "__latest__"),
        ("flocks", "__latest__"),
        ("dailydata", "__latest__"),
        ("sales", "__latest__"),
        ("purchase", "__latest__")
    ]

    operations = [
        migrations.RunSQL(
            SQL_VIEW,
            REVERSE_SQL
        )
    ]