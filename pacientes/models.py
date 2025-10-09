from django.db import models

class Paciente(models.Model):
    paciente_id = models.AutoField(primary_key=True)
    numero_historia = models.CharField(max_length=50, unique=True)  # Prontuario
    # flags de cohorte (el importador los setea si los usás)
    id_depresion = models.BooleanField(default=False)
    id_ansiedad  = models.BooleanField(default=False)

    sexo = models.CharField(max_length=10, default="Otro")
    fecha_nacimiento = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'pacientes'
        managed = False  # mapeamos tabla existente

    def __str__(self):
        return f"{self.numero_historia} (ID {self.paciente_id})"


class Consulta(models.Model):
    consulta_id = models.AutoField(primary_key=True)
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        db_column='paciente_id',
        related_name='consultas',
    )
    fecha_consulta  = models.DateField()
    relato_consulta = models.TextField(blank=True, null=True)
    diagnostico     = models.TextField(blank=True, null=True)
    # En BD está como texto: 'Bajo' | 'Moderado' | 'Alto'
    nivel_riesgo    = models.CharField(max_length=16, null=True, blank=True, db_column='nivel_riesgo')
    # Existe en BD y es opcional
    n_consulta      = models.SmallIntegerField(null=True, blank=True, db_column='n_consulta')

    class Meta:
        db_table = 'consultas'
        managed  = False

    def __str__(self):
        return f"Consulta {self.consulta_id} - {self.paciente.numero_historia}"


class Medicacion(models.Model):
    """Mapea la tabla real `prescripcion`."""
    medicacion_id = models.AutoField(primary_key=True, db_column='prescripcion_id')
    consulta = models.ForeignKey(
        Consulta,
        on_delete=models.CASCADE,
        db_column='consulta_id',
        related_name='medicaciones'
    )
    # En la tabla la columna se llama 'medicamento'
    nombre  = models.CharField(max_length=200, db_column='medicamento')
    dosis   = models.CharField(max_length=100, blank=True, null=True)
    esquema = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'prescripcion'
        managed  = False

    def __str__(self):
        base = self.nombre or ''
        if self.dosis:
            base += f" {self.dosis}"
        if self.esquema:
            base += f" ({self.esquema})"
        return base
