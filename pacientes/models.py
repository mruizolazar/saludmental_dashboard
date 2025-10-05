from django.db import models

class Paciente(models.Model):
    paciente_id = models.AutoField(primary_key=True)
    numero_historia = models.CharField(max_length=50, unique=True)
    sexo = models.CharField(max_length=10)
    fecha_nacimiento = models.DateField()

    class Meta:
        db_table = 'pacientes'

class Consulta(models.Model):
    consulta_id = models.AutoField(primary_key=True)
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, db_column='paciente_id')
    fecha_consulta = models.DateField()
    relato_consulta = models.TextField(blank=True, null=True)
    diagnostico = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'consultas'
        
        
