import argparse
import pandas as pd
from collections import defaultdict
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


# -------------------------
# Normalizadores
# -------------------------
def norm_str(x):
    if x is None:
        return None
    s = str(x).strip().lower()
    s = (
        s.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )
    return s


def map_sexo(x):
    """Devuelve 'Femenino' / 'Masculino' / 'Otro' a partir de variantes."""
    s = norm_str(x or "")
    if s.startswith("f"):
        return "Femenino"
    if s.startswith("m"):
        return "Masculino"
    if s in {"femenino", "fem"}:
        return "Femenino"
    if s in {"masculino", "masc"}:
        return "Masculino"
    return "Otro"


def map_riesgo(x):
    """Mapea variantes a 'Bajo' / 'Moderado' / 'Alto'."""
    s = norm_str(x or "")
    if s in {"0", "bajo", "pos", "positivo", "low", "baja"}:
        return "Bajo"
    if s in {"1", "moderado", "medio", "neu", "neutral", "medium"}:
        return "Moderado"
    if s in {"2", "alto", "neg", "negativo", "high", "alta"}:
        return "Alto"
    return None


def to_date_safe(x):
    if pd.isna(x) or x is None:
        return None
    try:
        return pd.to_datetime(x, dayfirst=True).date()
    except Exception:
        return None


class Command(BaseCommand):
    help = "Repara sexo de pacientes y nivel_riesgo de consultas usando los Excels originales."

    def add_arguments(self, parser: argparse.ArgumentParser):
        parser.add_argument("--dep_consultas", required=True)
        parser.add_argument("--ans_consultas", required=True)
        parser.add_argument("--dep_meds", required=True)

        parser.add_argument("--col-id-dep", default="id paciente")
        parser.add_argument("--col-fecha-dep", default="fecha consulta")
        parser.add_argument("--col-sexo-dep", default="sexo")

        parser.add_argument("--col-id-ans", default="prontuario")
        parser.add_argument("--col-fecha-ans", default="fecha consulta")
        parser.add_argument("--col-sexo-ans", default="sexo")

        parser.add_argument("--col-id-meds", default="id_paciente")
        parser.add_argument("--col-fecha-meds", default="fecha_consulta")
        parser.add_argument("--col-riesgo-meds", default="riesgo")

    def handle(self, *args, **o):
        dep_consultas = o["dep_consultas"]
        ans_consultas = o["ans_consultas"]
        dep_meds = o["dep_meds"]

        c_id_dep = o["col_id_dep"].strip().lower()
        c_fecha_dep = o["col_fecha_dep"].strip().lower()
        c_sexo_dep = o["col_sexo_dep"].strip().lower()

        c_id_ans = o["col_id_ans"].strip().lower()
        c_fecha_ans = o["col_fecha_ans"].strip().lower()
        c_sexo_ans = o["col_sexo_ans"].strip().lower()

        c_id_meds = o["col_id_meds"].strip().lower()
        c_fecha_meds = o["col_fecha_meds"].strip().lower()
        c_riesgo_m = o["col_riesgo_meds"].strip().lower()

        self.stdout.write("📄 Leyendo archivos…")

        # --- Depresión consultas ---
        df_dep = pd.read_excel(dep_consultas)
        df_dep.columns = [c.strip().lower() for c in df_dep.columns]

        # --- Ansiedad consultas ---
        df_ans = pd.read_excel(ans_consultas)
        df_ans.columns = [c.strip().lower() for c in df_ans.columns]

        # --- Depresión medicamentos ---
        df_meds = pd.read_excel(dep_meds)
        df_meds.columns = [c.strip().lower() for c in df_meds.columns]

        # ============== SEXO ==============
        self.stdout.write("🧭 Reparando SEXO...")
        sex_map = {}

        if c_sexo_dep in df_dep.columns:
            for _, r in df_dep.iterrows():
                pront = str(r.get(c_id_dep, "")).strip()
                if pront:
                    val = map_sexo(r.get(c_sexo_dep))
                    if pront not in sex_map:
                        sex_map[pront] = val

        if c_sexo_ans in df_ans.columns:
            for _, r in df_ans.iterrows():
                pront = str(r.get(c_id_ans, "")).strip()
                if pront and pront not in sex_map:
                    sex_map[pront] = map_sexo(r.get(c_sexo_ans))

        updated_sexo = 0
        with transaction.atomic(), connection.cursor() as cur:
            for pront, sexo in sex_map.items():
                cur.execute(
                    """
                    UPDATE pacientes
                       SET sexo = %s
                     WHERE numero_historia = %s
                       AND (sexo IS NULL OR sexo NOT IN ('Femenino','Masculino'));
                    """,
                    [sexo, pront],
                )
                updated_sexo += cur.rowcount

        self.stdout.write(f"✅ Sexo actualizado en {updated_sexo} pacientes.")

        # ============== RIESGO ==============
        self.stdout.write("🧭 Reparando RIESGO...")

        tmp = []
        for _, r in df_meds.iterrows():
            pront = str(r.get(c_id_meds, "")).strip()
            dt = to_date_safe(r.get(c_fecha_meds))
            riesgo = map_riesgo(r.get(c_riesgo_m))
            if pront and dt and riesgo:
                tmp.append((pront, dt, riesgo))

        if not tmp:
            self.stdout.write("⚠️ No se encontraron datos válidos de riesgo.")
            return

        df_risk = pd.DataFrame(tmp, columns=["prontuario", "fecha", "riesgo"])
        # priorizar alto > moderado > bajo
        prio = {"Bajo": 0, "Moderado": 1, "Alto": 2}
        df_risk["prio"] = df_risk["riesgo"].map(prio)
        df_risk = (
            df_risk.sort_values(["prontuario", "fecha", "prio"], ascending=[True, True, False])
            .drop_duplicates(subset=["prontuario", "fecha"], keep="first")
            .drop(columns=["prio"])
        )

        total = len(df_risk)
        self.stdout.write(f"🔎 Riesgos candidatos: {total}")

        # IMPORTANTE: escapar % en ILIKE para psycopg2 (%%)
        sql = """
            UPDATE consultas c
               SET nivel_riesgo = %s
              FROM pacientes p
             WHERE p.numero_historia = %s
               AND c.paciente_id = p.paciente_id
               AND c.fecha_consulta = %s
               AND (c.diagnostico ILIKE 'depresion' OR c.diagnostico ILIKE '%%depresi%%')
               AND (c.nivel_riesgo IS NULL OR c.nivel_riesgo = '');
        """

        updated = 0
        with transaction.atomic(), connection.cursor() as cur:
            for i, (_, row) in enumerate(df_risk.iterrows(), start=1):
                cur.execute(sql, [row["riesgo"], row["prontuario"], row["fecha"]])
                updated += cur.rowcount
                if i % 50 == 0:
                    self.stdout.write(f"  → procesadas {i}/{total}...")

        self.stdout.write(f"✅ Riesgo actualizado en {updated} consultas de depresión.")
        self.stdout.write("🎉 Reparación completada correctamente.")
