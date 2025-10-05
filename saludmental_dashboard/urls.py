from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('pacientes.urls')),  # Aquí sí incluís 'pacientes', no 'dashboard'
]
