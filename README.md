# 🐄 Campo Ganadero — Sistema de Gestión Integral

Aplicación web para gestión de campo ganadero. Construida con Python + Streamlit,
base de datos PostgreSQL (Railway) y asistente IA con OpenAI.

## Módulos

| Módulo | Descripción |
|---|---|
| 📊 Dashboard | KPIs anuales y gráficos de ventas, mortandad y gastos |
| 💰 Ventas | Registro de cargas: fechas, categorías, kgs y precios |
| 💀 Mortandad | Bajas con categoría, potrero y descripción |
| 🔧 Trabajos a Corral | Sanidad, pesajes, tactos, vacunaciones |
| 📦 Inventario | Stock estimado + compras y ajustes |
| 💸 Gastos | Costos por tipo con gráficos |
| 🐾 Reproducción | Tactos, partos, destetes |
| 🌿 Potreros | Gestión de potreros y asignación de hacienda |
| 🤖 Asistente IA | Chat con OpenAI sobre los datos del campo |

---

## Instalación local

### 1. Clonar / descargar el proyecto

```bash
cd ~/campo-ganadero
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tu editor:
nano .env
```

Variables a completar:
- `APP_PASSWORD` — contraseña de acceso a la app (por defecto: `campo123`)
- `OPENAI_API_KEY` — tu clave de API de OpenAI (https://platform.openai.com/api-keys)
- `DATABASE_URL` — dejar en blanco para usar SQLite local, o poner la URL de PostgreSQL

### 4. Ejecutar la aplicación

```bash
streamlit run app.py
```

La app se abre en http://localhost:8501

---

## Despliegue en Railway

### 1. Crear cuenta en Railway
Ve a https://railway.app y creá una cuenta (gratis).

### 2. Nuevo proyecto con PostgreSQL

1. **New Project** → **Deploy from GitHub repo** (o subí el código)
2. Agregar servicio de base de datos: **New** → **Database** → **PostgreSQL**
3. Railway va a setear `DATABASE_URL` automáticamente

### 3. Variables de entorno en Railway

En tu servicio web, ir a **Variables** y agregar:
```
APP_PASSWORD = tu_contraseña_segura
OPENAI_API_KEY = tu_clave_openai
```

### 4. Deploy

Railway detecta automáticamente el `railway.toml` y arranca la app.
La URL pública aparece en el dashboard de Railway.

---

## Clave API de OpenAI

1. Ir a https://platform.openai.com/api-keys
2. Crear nueva API key
3. Pegarla en `OPENAI_API_KEY`

El asistente usa el modelo **gpt-4o-mini** (rápido y económico).
La API se factura por uso (tokens), aparte de la suscripción de ChatGPT Plus.

---

## Importar datos existentes desde Excel

Si tenés datos en Excel/Google Sheets, podés importarlos de dos formas:

**Opción A — Carga manual:** Usá los formularios de cada página.

**Opción B — Import masivo (próximamente):** Podemos agregar un importador
de CSV que lea tus planillas actuales y las cargue en la base de datos.
Avisame cuando quieras implementarlo.
