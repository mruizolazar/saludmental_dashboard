from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Count, Prefetch
from .models import Paciente, Consulta, Medicacion

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

    # Conteos por diagnóstico
    ansiedad_ids = consultas.filter(diagnostico__iregex=r'ansiedad')\
                            .values_list('paciente_id', flat=True).distinct()
    depresion_ids = consultas.filter(diagnostico__iregex=r'depresi[oó]n')\
                             .values_list('paciente_id', flat=True).distinct()
    ansiedad_count = len(ansiedad_ids)
    depresion_count = len(depresion_ids)

    # Top diagnósticos (vacíos excluidos)
    diagnosticos_top = (
        consultas.exclude(diagnostico__isnull=True)
                 .exclude(diagnostico__exact='')
                 .values('diagnostico')
                 .annotate(total=Count('consulta_id'))
                 .order_by('-total')[:5]
    )

    # Serie sexo
    sexo_labels = ["Femenino", "Masculino", "Otro"]
    sexo_data = [pacientes.filter(sexo=s).count() for s in sexo_labels]

    # Prontuarios para datalist
    todos_los_prontuarios = Paciente.objects.values_list('numero_historia', flat=True)\
                                            .distinct().order_by('numero_historia')

    # SOLO pacientes que tienen consultas (para el selector del gráfico)
    pacs_con_consultas_ids = Consulta.objects.values_list('paciente_id', flat=True).distinct()
    pacientes_map = list(
        Paciente.objects
        .filter(paciente_id__in=pacs_con_consultas_ids)
        .values('paciente_id', 'numero_historia')
        .order_by('numero_historia')
    )
    initial_paciente_id = pacientes_map[0]['paciente_id'] if pacientes_map else None

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
        'pacientes_map': pacientes_map,
        'initial_paciente_id': initial_paciente_id,
    }
    return render(request, 'dashboard.html', context)


# ========= API: serie de evolución con medicamentos en tooltip =========
def api_evolucion_paciente(request, paciente_id: int):
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')

    pac = get_object_or_404(Paciente, pk=paciente_id)
    qs = Consulta.objects.filter(paciente=pac).order_by('fecha_consulta')
    if desde:
        qs = qs.filter(fecha_consulta__gte=desde)
    if hasta:
        qs = qs.filter(fecha_consulta__lte=hasta)

    qs = qs.prefetch_related(Prefetch('medicaciones', queryset=Medicacion.objects.order_by('medicacion_id')))

    labels, riesgo, meds = [], [], []
    for c in qs:
        labels.append(c.fecha_consulta.strftime("%Y-%m-%d"))
        riesgo.append(c.riesgo)
        items = []
        for m in c.medicaciones.all():
            nombre = (m.nombre or "").strip()
            dosis = (m.dosis or "").strip()
            esquema = (m.esquema or "").strip()
            if not nombre or nombre.lower() == "nan":
                continue
            txt = nombre
            if dosis and dosis.lower() != "nan":
                txt += f" {dosis}"
            if esquema and esquema.lower() != "nan":
                txt += f" ({esquema})"
            items.append(txt)
        meds.append(items or ["Sin medicación registrada"])

    return JsonResponse({"labels": labels, "riesgo": riesgo, "meds": meds})
