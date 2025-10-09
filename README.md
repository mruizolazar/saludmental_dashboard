# 🧠 Dashboard Salud Mental

Este proyecto es una aplicación web desarrollada con **Django** y **PostgreSQL** para visualizar y gestionar información de pacientes y consultas del Centro de Salud Mental.  
El sistema permite registrar, analizar y presentar datos de salud mental mediante una interfaz moderna, responsiva y extensible.

---

## 🛠️ Tecnologías utilizadas

- Python 3.12 o superior  
- Django 5.2.4  
- PostgreSQL 14+  
- Pandas / OpenPyXL (para importación de datos desde Excel)  
- HTML5, CSS3, Bootstrap 5  
- Chart.js 4 (para gráficos interactivos)  
- Git + GitHub

---

## 📦 Requisitos

- Python 3.10 o superior  
- PostgreSQL instalado y en ejecución  
- Virtualenv (recomendado)  

---

## ⚙️ Instalación

1. **Clonar el repositorio**

```bash
git clone https://github.com/mruizolazar/saludmental_dashboard.git
cd saludmental_dashboard
```

2. **Crear y activar entorno virtual**

**Windows (PowerShell):**
```bash
python -m venv venv
.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python -m venv venv
source venv/bin/activate
```

3. **Instalar dependencias**

```bash
pip install -r requirements.txt
```

---

## 🗄️ Configuración de base de datos

1. Crear una base de datos en PostgreSQL:

```sql
CREATE DATABASE centro_salud_mental;
```

2. Revisar las credenciales en `settings.py` (por defecto):

```python
'NAME': 'centro_salud_mental',
'USER': 'postgres',
'PASSWORD': '1234',
'HOST': 'localhost',
'PORT': '5432',
```

> Si se desea, se puede usar un archivo `.env` para definir estas variables sin modificar el código.

---

## 🔧 Migraciones

Aplicar las migraciones iniciales de Django:

```bash
python manage.py migrate
```

---

## ▶️ Ejecución del servidor

Iniciar el servidor de desarrollo:

```bash
python manage.py runserver
```

Luego abrir en el navegador:

```
http://127.0.0.1:8000/
```

---

## 📊 Funcionalidades principales

- Dashboard general con métricas clave (pacientes, consultas, diagnósticos)
- Gráfico circular de pacientes por sexo  
- Gráfico de barras de diagnósticos más comunes  
- Gráfico de evolución del riesgo del paciente  
- Filtros por sexo, fechas, prontuario y medicamentos  
- Zoom y paneo en gráficos (Chart.js + Plugins)

---

## 📥 Importación de datos desde Excel

El proyecto incluye comandos personalizados para importar datos directamente desde archivos `.xlsx`.

Ejemplo de uso:

```bash
python manage.py importar_datos --ansiedad data/ansiedad-panico_consultas.xlsx \
                                --depresion data/depresion_consultas.xlsx \
                                --meds_dep data/depresion_medicamentos.xlsx
```

---

## 🧱 Estructura del proyecto

```
saludmental_dashboard/
│
├── pacientes/
│   ├── management/commands/     # Scripts de importación
│   ├── migrations/
│   ├── templates/pacientes/
│   └── views.py
│
├── saludmental_dashboard/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── static/
├── templates/
├── requirements.txt
└── manage.py
```

---

## 🧾 Notas

- Proyecto diseñado para entorno **local / educativo**.  
- No incluye usuario administrador por defecto.  
- El archivo `.env` y el entorno virtual (`venv/`) están excluidos en `.gitignore`.

---

## 📚 Licencia

Este proyecto se distribuye bajo la licencia **MIT** — libre para usar y modificar.
