from django.contrib import admin
from .models import Paciente, Consulta, Medicacion

@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ("paciente_id", "numero_historia", "sexo", "fecha_nacimiento")
    search_fields = ("numero_historia",)

@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = ("consulta_id", "paciente", "fecha_consulta", "riesgo")
    list_filter = ("riesgo", "fecha_consulta")
    search_fields = ("paciente__numero_historia",)

@admin.register(Medicacion)
class MedicacionAdmin(admin.ModelAdmin):
    list_display = ("medicacion_id", "consulta", "nombre", "dosis", "esquema")
    search_fields = ("nombre",)
