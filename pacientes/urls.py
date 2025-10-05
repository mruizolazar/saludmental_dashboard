from django.urls import path
from . import views  # .views, no dashboard.views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
]
