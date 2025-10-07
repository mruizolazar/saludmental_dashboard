from django.db import models

class Paciente(models.Model):
    paciente_id = models.AutoField(primary_key=True)
    numero_historia = models.CharField(max_length=50, unique=True)
    sexo = models.CharField(max_length=10)
    fecha_nacimiento = models.DateField()

    class Meta:
        db_table = 'pacientes'

    def __str__(self):
        return f"Paciente {self.numero_historia}"


class Consulta(models.Model):
    consulta_id = models.AutoField(primary_key=True)
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, db_column='paciente_id')
    fecha_consulta = models.DateField()
    relato_consulta = models.TextField(blank=True, null=True)
    diagnostico = models.TextField(blank=True, null=True)

    # 🆕 Campo nuevo: riesgo (0,1,2)
    RIESGO_CHOICES = [
        (0, "POS (bajo)"),
        (1, "NEU (medio)"),
        (2, "NEG (alto)"),
    ]
    riesgo = models.IntegerField(choices=RIESGO_CHOICES, default=1)

    class Meta:
        db_table = 'consultas'

    def __str__(self):
        return f"Consulta {self.consulta_id} - Paciente {self.paciente.numero_historia}"


# 🆕 Nueva tabla Medicacion
class Medicacion(models.Model):
    medicacion_id = models.AutoField(primary_key=True)
    consulta = models.ForeignKey(Consulta, on_delete=models.CASCADE, db_column='consulta_id', related_name='medicaciones')
    nombre = models.CharField(max_length=100)
    dosis = models.CharField(max_length=50, blank=True, null=True)
    esquema = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'medicaciones'

    def __str__(self):
        return f"{self.nombre} ({self.dosis or ''})"
