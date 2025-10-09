# pacientes/views.py
from collections import defaultdict
import unicodedata
from django.shortcuts import render
from django.http import JsonResponse, Http404
from django.db.models import Count
from django.db.models.functions import Lower, Trim
from django.utils.dateparse import parse_date

from .models import Paciente, Consulta, Medicacion


# -----------------------------
# Helpers
# -----------------------------
def _parse_fecha(s: str):
    if not s:
        return None
    try:
        return parse_date(s)
    except Exception:
        return None


def _initial_paciente_id():
    """Primer paciente con al menos una consulta."""
    return (
        Consulta.objects.values_list('paciente_id', flat=True)
        .order_by('paciente_id')
        .distinct()
        .first()
    )


def _norm(s):
    """lower + trim + sin tildes"""
    if s is None:
        return None
    s = str(s).strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s


def _to_riesgo_num(v):
    """
    Convierte el valor de nivel_riesgo a 0/1/2.
    Acepta: 'bajo/moderado/alto', 'pos/neu/neg', 'positivo/neutral/negativo', 0/1/2.
    Devuelve None si no se puede mapear.
    """
    if v is None:
        return None
    s = _norm(v)

    if s in {"0", "0.0", "bajo", "pos", "positivo", "low"}:
        return 0
    if s in {"1", "1.0", "moderado", "medio", "neu", "neutral"}:
        return 1
    if s in {"2", "2.0", "alto", "neg", "negativo", "high"}:
        return 2
    return None


# -----------------------------
# Núcleo de evolución (robusto)
# -----------------------------
def _build_evolucion_json(paciente_id: int, desde: str = None, hasta: str = None, med_like: str = None):
    if not Paciente.objects.filter(pk=paciente_id).exists():
        raise Http404("Paciente no encontrado")

    d1 = _parse_fecha(desde)
    d2 = _parse_fecha(hasta)

    cons_qs = (
        Consulta.objects
        .filter(paciente_id=paciente_id)
        .order_by('fecha_consulta', 'n_consulta', 'consulta_id')
    )
    if d1:
        cons_qs = cons_qs.filter(fecha_consulta__gte=d1)
    if d2:
        cons_qs = cons_qs.filter(fecha_consulta__lte=d2)

    cons_list = list(cons_qs.values('consulta_id', 'fecha_consulta', 'nivel_riesgo', 'diagnostico'))

    # Prescripciones de esas consultas (⚠️ campo correcto: 'nombre')
    consulta_ids = [c['consulta_id'] for c in cons_list]
    meds_qs = Medicacion.objects.filter(consulta_id__in=consulta_ids)
    if med_like:
        meds_qs = meds_qs.filter(nombre__icontains=med_like)

    meds_by_cons = defaultdict(list)
    for m in meds_qs.values('consulta_id', 'nombre', 'dosis', 'esquema'):
        parts = [m['nombre'] or '']
        if m.get('dosis'):
            parts.append(str(m['dosis']))
        if m.get('esquema'):
            parts.append(f"({m['esquema']})")
        txt = " ".join([p for p in parts if p]).strip()
        if txt:
            meds_by_cons[m['consulta_id']].append(txt)

    # Mapas y vectores
    labels, riesgo, meds = [], [], []
    dates = []

    for c in cons_list:
        dt = c['fecha_consulta']
        labels.append(dt.isoformat())
        dates.append(dt)

        rnum = _to_riesgo_num(c.get('nivel_riesgo'))
        riesgo.append(rnum)  # puede ser None si el registro no trae riesgo

        lst = meds_by_cons.get(c['consulta_id'], [])
        meds.append(lst if lst else ["Sin medicación registrada"])

    # ====== Cálculo de pendiente (tendencia) — usa sólo puntos con riesgo definido ======
    slope = None
    xs, ys = [], []
    if len(dates) >= 2:
        t0 = dates[0]
        for d, r in zip(dates, riesgo):
            if r is None:
                continue
            xs.append((d - t0).days)
            ys.append(r)
        if len(xs) >= 2:
            n = len(xs)
            sumx = sum(xs); sumy = sum(ys)
            sumxy = sum(x*y for x, y in zip(xs, ys))
            sumx2 = sum(x*x for x in xs)
            denom = n * sumx2 - (sumx * sumx)
            slope = (n * sumxy - sumx * sumy) / denom if denom else 0.0

    # ====== Gaps / desistimiento (>60 días) ======
    gaps = []
    last_gap_days = 0
    desistio = False
    desist_from = None
    if len(dates) >= 2:
        for i in range(1, len(dates)):
            delta = (dates[i] - dates[i-1]).days
            gaps.append(delta)
        last_gap_days = gaps[-1] if gaps else 0
        if last_gap_days > 60:
            desistio = True
            desist_from = dates[-1].isoformat()

    # Índices NEG (2) para marcar con X
    neg_idx = [i for i, r in enumerate(riesgo) if r == 2]

    return {
        "labels": labels,
        "riesgo": riesgo,             # lista con 0/1/2 o None
        "meds": meds,                 # lista por punto
        "slope": slope,
        "gaps": gaps,
        "last_gap_days": last_gap_days,
        "desistio": desistio,
        "desist_from": desist_from,
        "neg_idx": neg_idx
    }


# -----------------------------
# Dashboard (KPIs + gráficos superiores)
# -----------------------------
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

    # KPIs por diagnóstico (en universo filtrado)
    ansiedad_count = (
        consultas.filter(diagnostico__iregex=r'ansiedad')
        .values('paciente_id').distinct().count()
    )
    depresion_count = (
        consultas.filter(diagnostico__iregex=r'depresi[oó]n')
        .values('paciente_id').distinct().count()
    )

    # Top diagnósticos
    diagnosticos_top = (
        consultas.values('diagnostico')
        .annotate(total=Count('consulta_id'))
        .order_by('-total')[:5]
    )

    # Pie sexo
    sexo_labels = ["Femenino", "Masculino", "Otro"]
    sexo_data = [pacientes.filter(sexo=s).count() for s in sexo_labels]

    # Datalist de prontuarios
    todos_los_prontuarios = (
        Paciente.objects.values_list('numero_historia', flat=True)
        .distinct().order_by('numero_historia')
    )

    # Select de pacientes para evolución (solo con consultas)
    pacientes_map = list(
        Paciente.objects.filter(consultas__isnull=False)
        .distinct()
        .values('paciente_id', 'numero_historia')
        .order_by('numero_historia')[:500]
    )

    # ==== MEDICAMENTOS para el <select> (según filtros aplicados)
    # ⚠️ Campo correcto de Medicacion es 'nombre'
    med_qs = Medicacion.objects.filter(consulta__in=consultas).annotate(
        nom_trim=Trim('nombre')
    ).exclude(
        nom_trim__isnull=True
    ).exclude(
        nom_trim__exact=''
    )

    med_list = list(
        med_qs.values_list(Lower('nom_trim'), flat=True)
        .distinct()
        .order_by(Lower('nom_trim'))
    )
    med_list = [m.capitalize() for m in med_list]  # presentación

    context = {
        'pacientes_count': pacientes_count,
        'consultas_count': consultas_count,
        'ansiedad_count': ansiedad_count,
        'depresion_count': depresion_count,
        'sexo_labels': sexo_labels,
        'sexo_data': sexo_data,
        'diag_labels': [d['diagnostico'] or '(sin dato)' for d in diagnosticos_top],
        'diag_data': [d['total'] for d in diagnosticos_top],
        'filtro_sexo': sexo_filter,
        'filtro_desde': desde_filter,
        'filtro_hasta': hasta_filter,
        'filtro_prontuario': prontuario_filter,
        'todos_los_prontuarios': todos_los_prontuarios,
        'pacientes_map': pacientes_map,
        'initial_paciente_id': _initial_paciente_id(),
        'med_list': med_list,
    }
    return render(request, 'dashboard.html', context)


# -----------------------------
# APIs JSON usadas por el front
# -----------------------------
def api_evolucion_paciente(request, paciente_id: int):
    """
    GET /api/pacientes/<paciente_id>/evolucion/?desde=YYYY-MM-DD&hasta=YYYY-MM-DD&med=texto
    """
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    med   = request.GET.get('med')
    data = _build_evolucion_json(paciente_id, desde, hasta, med)
    return JsonResponse(data)
