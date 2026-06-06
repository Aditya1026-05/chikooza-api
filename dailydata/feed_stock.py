from django.db.models import Sum

from dailydata.models import DailyData
from purchase.models import Purchase


def total_feed_purchased(flock, user, date=None):
    """
    U: Feed stock is derived from feed purchases, scoped to one farmer and flock.
    """
    queryset = Purchase.objects.filter(flock=flock, user=user, type="Feed")
    if date:
        queryset = queryset.filter(date__lte=date)
    return queryset.aggregate(total=Sum("quantity")).get("total") or 0


def total_feed_consumed_before_date(flock, user, date):
    """
    U: Only daily rows before the target day are available stock consumers.
    """
    return (
        DailyData.objects.filter(flock=flock, user=user, date__lt=date)
        .aggregate(total=Sum("feed_intake"))
        .get("total")
        or 0
    )


def available_feed_stock_for_date(flock, user, date):
    """
    U: Available feed for a day = purchased up to that day - consumed before that day.
    """
    return total_feed_purchased(flock, user, date) - total_feed_consumed_before_date(
        flock, user, date
    )


def recalculate_feed_snapshots(flock, user):
    """
    U: Keep saved daily snapshots in sync after feed purchases or feed intake edits.
    """
    consumed = 0
    rows = DailyData.objects.filter(flock=flock, user=user).order_by("date", "id")

    for row in rows:
        consumed += row.feed_intake or 0
        purchased = total_feed_purchased(flock, user, row.date)
        next_total_feed = consumed
        next_feed_stock = purchased - consumed

        if row.total_feed != next_total_feed or row.feed_stock != next_feed_stock:
            row.total_feed = next_total_feed
            row.feed_stock = next_feed_stock
            row.save(update_fields=["total_feed", "feed_stock", "updated_at"])
