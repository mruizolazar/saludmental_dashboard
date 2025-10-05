import csv
from django.core.management.base import BaseCommand
from pacientes.models import Paciente, Consulta
from datetime import datetime

class Command(BaseCommand):
    help = 'Recarga datos borrando y cargando desde CSV'

    def handle(self, *args, **kwargs):
        # Borra los datos antiguos
        self.stdout.write("Eliminando datos antiguos...")
        Consulta.objects.all().delete()
        Paciente.objects.all().delete()

        # Ruta a tu archivo CSV - cambia por la ruta correcta
        ruta_csv = r'C:\Users\User\Documents\datos_planos.csv'

        pacientes_dict = {}

        self.stdout.write("Cargando datos nuevos desde CSV...")

        with open(ruta_csv, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                numero_historia = row['numero_historia']
                sexo = row['sexo']
                fecha_nacimiento = row['fecha_nacimiento']
                fecha_consulta = row['fecha_consulta']
                relato_consulta = row['relato_consulta']
                diagnostico = row['diagnostico']

                # Crear paciente si no existe en este dict temporal
                if numero_historia not in pacientes_dict:
                    paciente = Paciente(
                        numero_historia=numero_historia,
                        sexo=sexo,
                        fecha_nacimiento=datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()
                    )
                    paciente.save()
                    pacientes_dict[numero_historia] = paciente
                else:
                    paciente = pacientes_dict[numero_historia]

                # Crear consulta
                consulta = Consulta(
                    paciente=paciente,
                    fecha_consulta=datetime.strptime(fecha_consulta, '%Y-%m-%d').date(),
                    relato_consulta=relato_consulta,
                    diagnostico=diagnostico
                )
                consulta.save()

        self.stdout.write(self.style.SUCCESS('Datos recargados correctamente.'))
