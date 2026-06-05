from django.urls import path

from .views import DashboardView

app_name = "dashbord"

urlpatterns = [
	path("", DashboardView.as_view(), name="dashboard"),
	path("", DashboardView.as_view(), name="list-dashboard"),
]
