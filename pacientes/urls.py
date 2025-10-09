# pacientes/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Página principal del dashboard
    path('', views.dashboard, name='dashboard'),

    # API para obtener la evolución del paciente
    path('api/pacientes/<int:paciente_id>/evolucion/', views.api_evolucion_paciente, name='api_evolucion_paciente'),
]
