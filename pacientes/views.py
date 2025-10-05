from django.shortcuts import render
from .models import Paciente, Consulta
from django.db.models import Count
from django.db.models.functions import Lower
from django.db.models import Q

def dashboard(request):
    sexo_filter = request.GET.get('sexo', '')
    desde_filter = request.GET.get('desde', '')
    hasta_filter = request.GET.get('hasta', '')
    prontuario_filter = request.GET.get('prontuario', '')

    pacientes = Paciente.objects.all()

    if sexo_filter:
        pacientes = pacientes.filter(sexo=sexo_filter)
    if prontuario_filter:
        pacientes = pacientes.filter(numero_historia__icontains=prontuario_filter)

    consultas = Consulta.objects.filter(paciente__in=pacientes)
    if desde_filter:
        consultas = consultas.filter(fecha_consulta__gte=desde_filter)
    if hasta_filter:
        consultas = consultas.filter(fecha_consulta__lte=hasta_filter)

    pacientes_count = pacientes.count()
    consultas_count = consultas.count()

    # Contar pacientes únicos por tipo de diagnóstico
    ansiedad_ids = consultas.filter(diagnostico__iregex=r'ansiedad').values_list('paciente_id', flat=True).distinct()
    depresion_ids = consultas.filter(diagnostico__iregex=r'depresi[oó]n').values_list('paciente_id', flat=True).distinct()
    ansiedad_count = len(ansiedad_ids)
    depresion_count = len(depresion_ids)

    # Diagnósticos más comunes
    diagnosticos_top = (
        consultas.values('diagnostico')
        .annotate(total=Count('consulta_id'))
        .order_by('-total')[:5]
    )

    # Sexo gráfico
    sexo_labels = ["Femenino", "Masculino", "Otro"]
    sexo_data = [pacientes.filter(sexo=s).count() for s in sexo_labels]

    # Prontuarios únicos para el filtro
    todos_los_prontuarios = Paciente.objects.values_list('numero_historia', flat=True).distinct().order_by('numero_historia')

    context = {
        'pacientes_count': pacientes_count,
        'consultas_count': consultas_count,
        'ansiedad_count': ansiedad_count,
        'depresion_count': depresion_count,
        'sexo_labels': sexo_labels,
        'sexo_data': sexo_data,
        'diag_labels': [d['diagnostico'] for d in diagnosticos_top],
        'diag_data': [d['total'] for d in diagnosticos_top],
        'filtro_sexo': sexo_filter,
        'filtro_desde': desde_filter,
        'filtro_hasta': hasta_filter,
        'filtro_prontuario': prontuario_filter,
        'todos_los_prontuarios': todos_los_prontuarios,
    }

    return render(request, 'dashboard.html', context)
