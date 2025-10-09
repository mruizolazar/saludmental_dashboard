# pacientes/management/commands/cargar_todo.py
import csv
import re
import unicodedata
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


def _norm_text(s):
    if s is None:
        return None
    s = str(s).strip().lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')
    s = re.sub(r'\s+', ' ', s)
    return s


def _to_date(x):
    if pd.isna(x) or x is None:
        return None
    for dayfirst in (True, False):
        try:
            return pd.to_datetime(x, dayfirst=dayfirst).date()
        except Exception:
            pass
    return None


def _map_riesgo(v):
    if v is None or pd.isna(v):
        return None
    s = _norm_text(v)
    if s in {'0', 'bajo', 'low', 'pos', 'positivo'}:
        return 'Bajo'
    if s in {'1', 'medio', 'moderado', 'neu', 'neutral'}:
        return 'Moderado'
    if s in {'2', 'alto', 'high', 'neg', 'negativo'}:
        return 'Alto'
    return None


def _py(v, as_str=False):
    """Convierte pandas.NA/NaN a None. Si as_str=True, devuelve str(v) salvo None."""
    if v is None or pd.isna(v):
        return None
    return str(v) if as_str else v


class Command(BaseCommand):
    help = "Carga pacientes + consultas (depresión/ansiedad) + prescripciones (depresión)."

    def add_arguments(self, p):
        # archivos
        p.add_argument('--dep_consultas', required=True)
        p.add_argument('--dep_meds', required=True)
        p.add_argument('--ans_consultas', required=True)

        # salidas
        p.add_argument('--out_map', default='map_dep_consulta_ids.csv')
        p.add_argument('--log', default='carga_todo_log.csv')

        # columnas fallback
        p.add_argument('--col-id', dest='col_id', default='id_paciente')
        p.add_argument('--col-fecha', dest='col_fecha', default='fecha_consulta')
        p.add_argument('--col-relato', dest='col_relato', default='relato_consulta')
        p.add_argument('--col-riesgo', dest='col_riesgo', default='riesgo')
        p.add_argument('--col-med', dest='col_med', default='med')
        p.add_argument('--col-dosis', dest='col_dosis', default='dosis')
        p.add_argument('--col-esq', dest='col_esq', default='esquema')

        # columnas específicas por archivo
        p.add_argument('--col-id-dep', default=None)
        p.add_argument('--col-fecha-dep', default=None)
        p.add_argument('--col-id-meds', default=None)
        p.add_argument('--col-fecha-meds', default=None)
        p.add_argument('--col-id-ans', default=None)
        p.add_argument('--col-fecha-ans', default=None)

        p.add_argument('--reset', action='store_true')

    def handle(self, *args, **o):
        # paths
        p_dep_cons = Path(o['dep_consultas'])
        p_dep_meds = Path(o['dep_meds'])
        p_ans_cons = Path(o['ans_consultas'])
        for pth in (p_dep_cons, p_dep_meds, p_ans_cons):
            if not pth.exists():
                raise CommandError(f"No existe: {pth}")

        out_map = Path(o['out_map']).resolve()
        out_log = Path(o['log']).resolve()
        out_map.parent.mkdir(parents=True, exist_ok=True)
        out_log.parent.mkdir(parents=True, exist_ok=True)

        # leer excels
        self.stdout.write("📄 Leyendo archivos…")
        try:
            dep_cons = pd.read_excel(p_dep_cons)
            dep_meds = pd.read_excel(p_dep_meds)
            ans_cons = pd.read_excel(p_ans_cons)
        except Exception as e:
            raise CommandError(f"Error leyendo Excels: {e}")

        # normalizar headers
        dep_cons.columns = [_norm_text(c) for c in dep_cons.columns]
        dep_meds.columns = [_norm_text(c) for c in dep_meds.columns]
        ans_cons.columns = [_norm_text(c) for c in ans_cons.columns]

        # resolver nombres por archivo (usa específicos si vienen; si no, los generales)
        col_id_dep = _norm_text(o.get('col_id_dep') or o['col_id'])
        col_fecha_dep = _norm_text(o.get('col_fecha_dep') or o['col_fecha'])
        col_id_meds = _norm_text(o.get('col_id_meds') or o['col_id'])
        col_fecha_meds = _norm_text(o.get('col_fecha_meds') or o['col_fecha'])
        col_id_ans = _norm_text(o.get('col_id_ans') or o['col_id'])
        col_fecha_ans = _norm_text(o.get('col_fecha_ans') or o['col_fecha'])

        col_relato = _norm_text(o['col_relato'])
        col_riesgo = _norm_text(o['col_riesgo'])
        col_med = _norm_text(o['col_med'])
        col_dosis = _norm_text(o['col_dosis'])
        col_esq = _norm_text(o['col_esq'])

        # validar columnas mínimas por archivo
        miss = [x for x in (col_id_dep, col_fecha_dep) if x not in dep_cons.columns]
        if miss:
            raise CommandError(f"Depresión/consultas: faltan columnas {miss} (cols={list(dep_cons.columns)})")
        miss = [x for x in (col_id_meds, col_fecha_meds, col_med) if x not in dep_meds.columns]
        if miss:
            raise CommandError(f"Depresión/meds: faltan columnas {miss} (cols={list(dep_meds.columns)})")
        miss = [x for x in (col_id_ans, col_fecha_ans) if x not in ans_cons.columns]
        if miss:
            raise CommandError(f"Ansiedad/consultas: faltan columnas {miss} (cols={list(ans_cons.columns)})")

        # limpieza tipos (evitar pandas.NA)
        dep_cons[col_fecha_dep] = dep_cons[col_fecha_dep].map(_to_date)
        dep_cons[col_id_dep] = dep_cons[col_id_dep].astype('string').str.strip()

        dep_meds[col_fecha_meds] = dep_meds[col_fecha_meds].map(_to_date)
        dep_meds[col_id_meds] = dep_meds[col_id_meds].astype('string').str.strip()

        ans_cons[col_fecha_ans] = ans_cons[col_fecha_ans].map(_to_date)
        ans_cons[col_id_ans] = ans_cons[col_id_ans].astype('string').str.strip()

        # riesgo/relato a tipos Python (None si NA)
        if col_riesgo in dep_cons.columns:
            dep_cons[col_riesgo] = dep_cons[col_riesgo].map(_map_riesgo)
        if col_relato in dep_cons.columns:
            dep_cons[col_relato] = dep_cons[col_relato].astype('string')
            dep_cons[col_relato] = dep_cons[col_relato].where(~dep_cons[col_relato].isna(), None)

        # meds string→None si NA
        for c in (col_med, col_dosis, col_esq):
            if c in dep_meds.columns:
                dep_meds[c] = dep_meds[c].astype('string').str.strip()
                dep_meds[c] = dep_meds[c].where(~dep_meds[c].isna(), None)

        # filtrar filas válidas
        dep_cons = dep_cons[dep_cons[col_id_dep].notna() & dep_cons[col_fecha_dep].notna()].copy()
        dep_meds = dep_meds[
            dep_meds[col_id_meds].notna() &
            dep_meds[col_fecha_meds].notna() &
            dep_meds[col_med].notna()
        ].copy()
        ans_cons = ans_cons[ans_cons[col_id_ans].notna() & ans_cons[col_fecha_ans].notna()].copy()

        with connection.cursor() as cur, \
                open(out_map, 'w', newline='', encoding='utf-8') as mapf, \
                open(out_log, 'w', newline='', encoding='utf-8') as logf, \
                transaction.atomic():

            mapw = csv.writer(mapf); mapw.writerow(['id_paciente', 'fecha_consulta', 'consulta_id'])
            logw = csv.writer(logf); logw.writerow(['origen', 'id_paciente', 'fecha', 'detalle', 'extra'])

            if o['reset']:
                self.stdout.write("🧹 Reset tablas…")
                cur.execute("TRUNCATE TABLE prescripcion RESTART IDENTITY CASCADE")
                cur.execute("TRUNCATE TABLE consultas RESTART IDENTITY CASCADE")
                cur.execute("TRUNCATE TABLE pacientes RESTART IDENTITY CASCADE")

            # Pacientes (todos los archivos)
            ids_all = pd.concat(
                [dep_cons[col_id_dep], dep_meds[col_id_meds], ans_cons[col_id_ans]],
                ignore_index=True
            ).dropna().unique().tolist()

            created_pac = 0
            for ident in ids_all:
                cur.execute("""
                    INSERT INTO pacientes (numero_historia, id_depresion, id_ansiedad, sexo)
                    VALUES (%s, FALSE, FALSE, 'Otro')
                    ON CONFLICT (numero_historia) DO NOTHING
                """, [str(ident)])
                if cur.rowcount:
                    created_pac += 1

            # marcar cohortes
            cur.executemany("UPDATE pacientes SET id_depresion=TRUE WHERE numero_historia=%s",
                            [(str(x),) for x in dep_cons[col_id_dep].unique().tolist()])
            cur.executemany("UPDATE pacientes SET id_ansiedad=TRUE WHERE numero_historia=%s",
                            [(str(x),) for x in ans_cons[col_id_ans].unique().tolist()])

            def _get_pid(ident):
                cur.execute("SELECT paciente_id FROM pacientes WHERE numero_historia=%s", [str(ident)])
                r = cur.fetchone()
                return r[0] if r else None

            # Depresión — Consultas
            dep_cons_cargadas = 0
            for _, r in dep_cons.iterrows():
                ident = _py(r[col_id_dep], as_str=True)
                f = _py(r[col_fecha_dep])
                relato = _py(r.get(col_relato))
                riesgo = _py(r.get(col_riesgo))
                pid = _get_pid(ident)
                if not pid:
                    logw.writerow(['DEP_CONS', ident, f, 'SIN_PACIENTE', '']); continue
                cur.execute("""
                    INSERT INTO consultas (paciente_id, fecha_consulta, relato_consulta, diagnostico, nivel_riesgo, n_consulta)
                    VALUES (%s, %s, %s, 'depresion', %s, NULL)
                    ON CONFLICT ON CONSTRAINT uk_consulta_un_dia DO NOTHING
                    RETURNING consulta_id
                """, [pid, f, relato, riesgo])
                row = cur.fetchone()
                if not row:
                    cur.execute("""
                        SELECT consulta_id FROM consultas
                        WHERE paciente_id=%s AND fecha_consulta=%s
                        ORDER BY n_consulta NULLS FIRST, consulta_id
                        LIMIT 1
                    """, [pid, f])
                    row = cur.fetchone()
                if row:
                    mapw.writerow([ident, f, row[0]]); dep_cons_cargadas += 1
                else:
                    logw.writerow(['DEP_CONS', ident, f, 'NO_SE_CREO_CONSULTA', ''])

            # Depresión — Meds
            dep_meds_insert, dep_meds_cons_creadas = 0, 0
            for _, r in dep_meds.iterrows():
                ident = _py(r[col_id_meds], as_str=True)
                f = _py(r[col_fecha_meds])
                med = _py(r[col_med], as_str=True)   # med no puede ser None aquí
                dosis = _py(r.get(col_dosis), as_str=True)
                esq = _py(r.get(col_esq), as_str=True)
                pid = _get_pid(ident)
                if not pid:
                    logw.writerow(['DEP_MED', ident, f, 'SIN_PACIENTE', med]); continue
                # buscar consulta por paciente+fecha
                cur.execute("""
                    SELECT consulta_id FROM consultas
                    WHERE paciente_id=%s AND fecha_consulta=%s
                    ORDER BY n_consulta NULLS FIRST, consulta_id
                    LIMIT 1
                """, [pid, f])
                row = cur.fetchone()
                if row:
                    c_id = row[0]
                else:
                    # crear consulta mínima de depresión
                    cur.execute("""
                        INSERT INTO consultas (paciente_id, fecha_consulta, diagnostico, n_consulta)
                        VALUES (%s, %s, 'depresion', NULL)
                        RETURNING consulta_id
                    """, [pid, f])
                    c_id = cur.fetchone()[0]
                    dep_meds_cons_creadas += 1
                    mapw.writerow([ident, f, c_id])

                # usar la constraint por nombre (ya creada en SQL)
                cur.execute("""
                    INSERT INTO prescripcion (consulta_id, medicamento, dosis, esquema)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT ON CONSTRAINT ux_presc_dedupe DO NOTHING
                """, [c_id, med, dosis, esq])
                dep_meds_insert += cur.rowcount

            # Ansiedad — Consultas
            ans_cons_cargadas = 0
            for _, r in ans_cons.iterrows():
                ident = _py(r[col_id_ans], as_str=True)
                f = _py(r[col_fecha_ans])
                relato = _py(r.get(col_relato))
                riesgo = _py(r.get(col_riesgo))
                pid = _get_pid(ident)
                if not pid:
                    logw.writerow(['ANS_CONS', ident, f, 'SIN_PACIENTE', '']); continue
                cur.execute("""
                    INSERT INTO consultas (paciente_id, fecha_consulta, relato_consulta, diagnostico, nivel_riesgo, n_consulta)
                    VALUES (%s, %s, %s, 'ansiedad-panico', %s, NULL)
                    ON CONFLICT ON CONSTRAINT uk_consulta_un_dia DO NOTHING
                """, [pid, f, relato, riesgo])
                ans_cons_cargadas += 1

        self.stdout.write(self.style.SUCCESS(
            "✅ Carga finalizada. Revisá map/log para detalle."
        ))
