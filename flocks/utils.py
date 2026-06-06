import datetime
from dailydata.feed_stock import (
    total_feed_consumed_before_date,
    total_feed_purchased as stock_total_feed_purchased,
)
from dailydata.models import DailyData, Vaccines
from purchase.models import Purchase
from sales.models import Sales

def generate_remarks(daily_data):
    """
    Generate remarks for daily data showing vaccination names, feed purchases, and medicine administration.
    Gets all information from the database.
    
    Args:
        daily_data: DailyData object
    
    Returns:
        str: Generated remarks string
    """
    remarks = []
    
    # Get vaccination names for the day from FlockVaccination (only those with status "Start")
    from dailydata.models import FlockVaccination
    vaccinations = FlockVaccination.objects.filter(
        dailydata=daily_data,
        flock=daily_data.flock,
        status="Start"  # Only show vaccines on the day they start
    ).select_related('vaccine')
    
    # Add vaccination names to remarks
    for vaccination in vaccinations:
        remarks.append(vaccination.vaccine.name)
    
    # Get feed purchased on that day
    feed_purchases = Purchase.objects.filter(
        flock=daily_data.flock,
        type='Feed',
        date=daily_data.date
    )
    
    total_feed_purchased_today = 0
    for purchase in feed_purchases:
        if purchase.quantity:
            total_feed_purchased_today += purchase.quantity
    
    if total_feed_purchased_today > 0:
        remarks.append(f"Feed purchased: {total_feed_purchased_today}kg")
    
    # Check if medicine was given (stored in daily_data.medicine field)
    if daily_data.medicine:
        remarks.append("Meds")
    
    # Join all remarks with commas
    return ", ".join(remarks) if remarks else ""


def calculate_total_feed_purchased(flock, date=None, user=None):
    """
    Calculate total feed purchased for a flock up to a specific date
    """
    if user:
        # U: NEW: feed stock is tenant-scoped and comes from feed purchases.
        return stock_total_feed_purchased(flock, user, date)

    # U: OLD fallback kept for admin/report callers that do not pass a user yet.
    filters = {'flock': flock, 'type': 'Feed'}
    if date:
        filters['date__lte'] = date
    
    purchases = Purchase.objects.filter(**filters)
    total_quantity = 0
    
    for purchase in purchases:
        if purchase.quantity is not None:
            total_quantity += purchase.quantity
    
    return total_quantity


def calculate_current_bird_count(flock, daily_data=None, yesterday_daily_data=None):
    """
    Calculate current bird count considering only mortality (not sales)
    """
    if yesterday_daily_data:
        current_bird_count = yesterday_daily_data.current_bird_count
    else:
        current_bird_count = flock.flock_bird
    
    # Only subtract mortality, ignore sales
    if daily_data:
        actual_bird_count = current_bird_count - daily_data.mortality
    else:
        actual_bird_count = current_bird_count
    
    return actual_bird_count


def calculate_total_feed(yesterday_daily_data, feed_intake):
    """
    Calculate total feed consumed
    """
    if yesterday_daily_data:
        return yesterday_daily_data.total_feed + feed_intake
    else:
        return feed_intake


def calculate_feed_stock(total_feed_purchased, total_feed_consumed):
    """
    Calculate remaining feed stock
    """
    return total_feed_purchased - total_feed_consumed


def calculate_average_feed_per_bird(feed_intake, current_bird_count):
    """
    Calculate average feed consumption per bird (in grams)
    """
    if current_bird_count == 0:
        return 0
    return round((feed_intake * 1000) / current_bird_count, 2)


def calculate_total_average_feed(yesterday_avg_feed, current_avg_feed):
    """
    Calculate cumulative average feed
    """
    return round(yesterday_avg_feed + current_avg_feed, 2)


def calculate_total_mortality_percentage(flock, current_bird_count):
    """
    Calculate cumulative mortality percentage
    """
    total_dead_birds = flock.flock_bird - current_bird_count
    return round((total_dead_birds * 100) / flock.flock_bird, 2)

def cum_mort_fn(flock, current_bird_count):
    """
    Calculate cumulative mortality 
    """
    total_dead_birds = flock.flock_bird - current_bird_count
    return total_dead_birds


def calculate_fcr(total_average_feed, average_bird_weight, flock_chick_weight, fallback_fcr=0):
    """
    Calculate Feed Conversion Ratio (FCR)
    """
    weight_gain = average_bird_weight - flock_chick_weight
    if weight_gain > 0:
        fcr = total_average_feed / weight_gain
        return round(fcr, 2) if fcr > 0 else 0
    else:
        return round(fallback_fcr, 2)


def calculate_total_fcr(total_average_feed, average_bird_weight, fallback_total_fcr=0):
    """
    Calculate total FCR
    """
    if average_bird_weight > 0:
        total_fcr = total_average_feed / average_bird_weight
        return round(total_fcr, 2)
    else:
        return fallback_total_fcr


def get_yesterday_daily_data(flock, current_date):
    """
    Get yesterday's daily data if it exists
    """
    yesterday = current_date - datetime.timedelta(days=1)
    try:
        return DailyData.objects.get(date=yesterday, flock=flock)
    except DailyData.DoesNotExist:
        return None


def calculate_age_in_days(flock_start_date, current_date):
    """
    Calculate age of flock in days
    """
    return (current_date - flock_start_date).days


def prepare_daily_data_response(daily_data, flock):
    """
    Prepare daily data response with calculated values for frontend
    This function returns both stored and calculated values
    """
    yesterday_data = get_yesterday_daily_data(flock, daily_data.date)
    
    # Calculate derived values that won't be stored in DB
    total_feed_purchased = calculate_total_feed_purchased(
        flock, daily_data.date, daily_data.user
    )
    calculated_current_bird_count = calculate_current_bird_count(flock, daily_data, yesterday_data)
    # U: OLD: calculated_total_feed = calculate_total_feed(yesterday_data, daily_data.feed_intake)
    # U: NEW: recalculate from all earlier daily rows so edited feed purchases/daily rows stay correct.
    calculated_total_feed = (
        total_feed_consumed_before_date(flock, daily_data.user, daily_data.date)
        + daily_data.feed_intake
    )
    calculated_feed_stock = calculate_feed_stock(total_feed_purchased, calculated_total_feed)
    calculated_avg_feed = calculate_average_feed_per_bird(daily_data.feed_intake, calculated_current_bird_count)
    
    yesterday_avg_feed = yesterday_data.total_average_feed if yesterday_data else 0
    calculated_total_avg_feed = calculate_total_average_feed(yesterday_avg_feed, calculated_avg_feed)
    
    calculated_total_mortality = calculate_total_mortality_percentage(flock, calculated_current_bird_count)
    cum_mort = cum_mort_fn(flock, calculated_current_bird_count)
    
    yesterday_fcr = yesterday_data.fcr if yesterday_data else 0
    calculated_fcr = calculate_fcr(
        calculated_total_avg_feed, 
        daily_data.average_bird_weight, 
        flock.chick_weight, 
        yesterday_fcr
    )
    
    yesterday_total_fcr = yesterday_data.total_fcr if yesterday_data else 0
    calculated_total_fcr = calculate_total_fcr(
        calculated_total_avg_feed, 
        daily_data.average_bird_weight, 
        yesterday_total_fcr
    )
    
    age_in_days = calculate_age_in_days(flock.hatch_date, daily_data.date)
    remarks = generate_remarks(daily_data)
    
    return {
        # Stored values (will be saved in DB)
        'date': daily_data.date,
        'age': age_in_days,
        'bird_count': calculated_current_bird_count,  # This might be stored
        'mortality': daily_data.mortality,
        'daily_feed': daily_data.feed_intake,
        'avg_bird_weight': daily_data.average_bird_weight,
        
        # Calculated values (won't be stored in DB but sent to frontend)
        'total_feed_purchased': total_feed_purchased,
        'total_feed_consumed': calculated_total_feed,
        'feed_stock': calculated_feed_stock,
        'average_feed_per_bird': calculated_avg_feed,
        'total_average_feed': calculated_total_avg_feed,
        'total_mortality_percentage': calculated_total_mortality,
        'fcr': calculated_fcr,
        'total_fcr': calculated_total_fcr,
        'cum_mort':cum_mort,
        'remarks':remarks,
        
        # Other stored boolean values
        'cooling': daily_data.cooling,
        'heating': daily_data.heating,
        'seek': daily_data.seek,
        'medicine': daily_data.medicine,
        # 'darkness_time': daily_data.darkness_time,
        # 'feed_availability': daily_data.feed_availability,
    }
