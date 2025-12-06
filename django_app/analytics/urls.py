from django.urls import path
from analytics.views import dashboard_view, download_clean_csv

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("download/", download_clean_csv, name="download_clean_csv"),
]
