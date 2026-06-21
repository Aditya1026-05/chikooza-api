from django.urls import include, path

from rest_framework.routers import DefaultRouter

from dailydata.views import (
    DailyDataAverageFeedBirdsView,
    DailyDataDetailView,
    DailyDataFCRView,
    DailyDataLastDateView,
    DailyDataListView,
    DailyDataMortalityView,
    DailyDataView,
    DarknessTimeView,
    FeedAvailabilityView,
    FlockVaccinationView,
    PDFView,
    VaccinesView,
)

router = DefaultRouter()
router.register("dailyData", DailyDataView, basename="dailyy_data")
router.register(
    "dailyDataLastDate", DailyDataLastDateView, basename="daily_data_last_date"
)
router.register(
    "dailyDataMortality", DailyDataMortalityView, basename="daily_data_mortality"
)
router.register(
    "dailyDataAvgFeed", DailyDataAverageFeedBirdsView, basename="daily_data_avg_feed"
)
router.register("dailyDataFCR", DailyDataFCRView, basename="daily_data_fcr")

router.register("vaccines", VaccinesView, basename="vaccines")
router.register("flockVaccination", FlockVaccinationView, basename="flock_vaccination")
router.register("dailyDataDetail", DailyDataDetailView, basename="daily_data_detail")
router.register("dailyDataList", DailyDataListView, basename="daily_data_list")
router.register("darknessTime", DarknessTimeView, basename="daily_data_darkness_time")
router.register(
    "feedAvailability",
    FeedAvailabilityView,
    basename="daily_data_feed_availability",
)
router.register("pdf", PDFView, basename="pdf")
urlpatterns = [path("", include(router.urls))]
