from django.shortcuts import render
from .models import Paciente, Consulta
from django.db import models

def dashboard(request):
    pacientes_count = Paciente.objects.count()
    consultas_count = Consulta.objects.count()
    diagnosticos_top = Consulta.objects.values('diagnostico').annotate(total=models.Count('consulta_id')).order_by('-total')[:5]

    context = {
        'pacientes_count': pacientes_count,
        'consultas_count': consultas_count,
        'diagnosticos_top': diagnosticos_top,
    }
    return render(request, 'dashboard.html', context)

