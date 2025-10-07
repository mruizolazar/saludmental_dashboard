from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/pacientes/<int:paciente_id>/evolucion/', views.api_evolucion_paciente, name='api_evolucion_paciente'),
]
