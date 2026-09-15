from django.urls import path
from .views import DecisionAPIView

urlpatterns = [
    path("check/", DecisionAPIView.as_view(), name="decision-check"),
]
