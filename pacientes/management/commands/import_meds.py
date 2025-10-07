from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pacientes.models import Paciente, Consulta, Medicacion
import pandas as pd
from pathlib import Path

# Mapeo de texto -> nivel numérico de riesgo
MAP_RIESGO = {"Bajo": 0, "POS": 0, "Medio": 1, "NEU": 1, "Alto": 2, "NEG": 2}

class Command(BaseCommand):
    help = "Importa CONSULTAS y sus MEDICACIONES desde un XLSX (una fila = 1 medicamento)."

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, required=True, help="Ruta al XLSX")
        parser.add_argument("--sheet", type=str, default=None, help="Nombre de hoja (opcional)")

    @transaction.atomic
    def handle(self, *args, **opts):
        path = Path(opts["file"])
        if not path.exists():
            raise CommandError(f"Archivo no encontrado: {path}")

        read_kwargs = {}
        if opts["sheet"]:
            read_kwargs["sheet_name"] = opts["sheet"]

        try:
            df = pd.read_excel(path, **read_kwargs)
        except Exception as e:
            raise CommandError(f"No pude leer el XLSX: {e}")

        # Columnas mínimas esperadas en tu Excel
        required = ["ID_paciente", "fecha_consulta", "riesgo", "relato_consulta", "med"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise CommandError(f"Faltan columnas en el XLSX: {missing}")

        # Normalizaciones
        df["fecha_consulta"] = pd.to_datetime(df["fecha_consulta"], errors="coerce")
        if df["fecha_consulta"].isna().any():
            raise CommandError("Hay fechas inválidas en 'fecha_consulta'.")

        df["riesgo_nivel"] = df["riesgo"].astype(str).map(MAP_RIESGO).fillna(1).astype(int)

        # Nombre de medicamento (prefiere alias si existe)
        if "alias" in df.columns:
            df["nombre_med"] = df["alias"].where(df["alias"].notna(), df["med"]).astype(str)
        else:
            df["nombre_med"] = df["med"].astype(str)

        if "dosis" not in df.columns:
            df["dosis"] = ""
        if "esquema" not in df.columns:
            df["esquema"] = ""

        nuevas_consultas = 0
        nuevas_meds = 0

        # Agrupar por (ID_paciente, fecha) => 1 consulta con N medicaciones
        for (pid, fecha), block in df.groupby(["ID_paciente", "fecha_consulta"]):
            # Paciente: si no existe, se crea con defaults válidos para tu CHECK
            pac, _ = Paciente.objects.get_or_create(
                paciente_id=int(pid),
                defaults={
                    "numero_historia": f"AUTO-{int(pid)}",
                    "sexo": "Otro",                  # <- valor permitido por tu CHECK
                    "fecha_nacimiento": "2000-01-01"
                }
            )

            riesgo = int(block["riesgo_nivel"].max())
            relatos = block["relato_consulta"].dropna().astype(str).unique()
            relato = relatos[0] if relatos.size else None

            # --- Evitar MultipleObjectsReturned: NO usar get_or_create aquí ---
            qs = Consulta.objects.filter(paciente=pac, fecha_consulta=fecha.date()).order_by("consulta_id")
            if qs.exists():
                con = qs.first()
                # actualizar si cambia riesgo/relato
                changed = False
                if con.riesgo != riesgo:
                    con.riesgo = riesgo; changed = True
                if relato and (con.relato_consulta or "") != relato:
                    con.relato_consulta = relato; changed = True
                if changed:
                    con.save()
                created = False
            else:
                con = Consulta.objects.create(
                    paciente=pac,
                    fecha_consulta=fecha.date(),  # tu campo es DateField
                    relato_consulta=relato,
                    diagnostico=None,
                    riesgo=riesgo
                )
                created = True
                nuevas_consultas += 1

            # Medicaciones (evitar duplicados simples por nombre/dosis/esquema)
            meds_block = block[["nombre_med", "dosis", "esquema"]].dropna(subset=["nombre_med"])
            for _, row in meds_block.iterrows():
                nombre = (row["nombre_med"] or "").strip()
                dosis = (row["dosis"] or None)
                esquema = (row["esquema"] or None)

                if not nombre:
                    continue

                if not con.medicaciones.filter(nombre=nombre, dosis=dosis, esquema=esquema).exists():
                    Medicacion.objects.create(
                        consulta=con,
                        nombre=nombre,
                        dosis=dosis,
                        esquema=esquema,
                    )
                    nuevas_meds += 1

        self.stdout.write(self.style.SUCCESS(
            f"Importación OK. Consultas nuevas: {nuevas_consultas} | Medicaciones nuevas: {nuevas_meds}"
        ))
