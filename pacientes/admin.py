from django.contrib import admin
from .models import Paciente, Consulta, Medicacion

# ---------- Inlines ----------
class MedicacionInline(admin.TabularInline):
    model = Medicacion
    extra = 0
    fields = ("nombre", "dosis", "esquema")  # <- antes 'medicamento'
    show_change_link = True

# ---------- Paciente ----------
@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display  = ("paciente_id", "numero_historia", "sexo", "fecha_nacimiento")
    search_fields = ("numero_historia",)
    list_filter   = ("sexo",)
    ordering      = ("paciente_id",)

# ---------- Consulta ----------
@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = (
        "consulta_id",
        "paciente",
        "fecha_consulta",
        "diagnostico",
        "nivel_riesgo",   # texto: Bajo / Moderado / Alto
        "n_consulta",
    )
    list_filter   = ("diagnostico", "nivel_riesgo")
    search_fields = ("paciente__numero_historia", "diagnostico", "relato_consulta")
    date_hierarchy = "fecha_consulta"
    ordering      = ("-fecha_consulta", "consulta_id")
    inlines       = [MedicacionInline]

# ---------- Medicacion ----------
@admin.register(Medicacion)
class MedicacionAdmin(admin.ModelAdmin):
    # campo correcto es 'nombre' (db_column='medicamento')
    list_display  = ("medicacion_id", "consulta", "nombre", "dosis", "esquema")
    search_fields = ("nombre", "consulta__paciente__numero_historia")
    ordering      = ("nombre", "medicacion_id")
