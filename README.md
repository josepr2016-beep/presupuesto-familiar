# 💰 Presupuesto Familiar

Aplicación web para gestión de presupuesto familiar, construida en **Python (Flask + SQLite)**,
con diseño **mobile-first** para registrar gastos desde el celular y un panel de
control ampliado para gestión y análisis desde el computador. Todos los montos se
manejan en **Pesos Colombianos (COP)**.

## 📁 Estructura del proyecto

```
presupuesto_familiar/
├── app.py                 # Rutas y arranque de la aplicación Flask
├── config.py               # Configuración (rutas, clave secreta, DB)
├── extensions.py            # Instancia de SQLAlchemy
├── models.py                # Modelos: Category, Account, Transaction, Budget, BalanceCheck
├── utils.py                  # Formato COP, nombres de meses, rangos de fechas
├── requirements.txt
├── Procfile                   # Comando de arranque para Render/Railway/Heroku
├── render.yaml                 # Blueprint: despliegue en un clic (Web Service + Postgres)
├── .gitignore
├── instance/                 # (Solo en local) Se crea automáticamente -> aquí vive presupuesto.db
├── static/
│   ├── css/style.css         # Estilos mobile-first
│   └── js/main.js            # Filtro dinámico de categorías por tipo
└── templates/
    ├── base.html              # Layout con navbar superior + barra inferior (celular)
    ├── registro.html           # Módulo 3: registro diario (mobile-first)
    ├── categorias.html         # Módulo 2: gestión de categorías
    ├── cuentas.html            # Módulo 5: gestión de cuentas
    ├── presupuesto.html        # Módulo 4: presupuesto mensual
    ├── dashboard.html          # Módulo 4: consolidación + alertas
    └── conciliacion.html       # Módulo 5: conciliación de saldos
```

## 🧠 Modelo de datos (resumen)

| Tabla           | Propósito                                                             |
|-----------------|------------------------------------------------------------------------|
| `categories`    | Categorías personalizadas, agrupadas en `ingreso` / `gasto` / `ahorro` |
| `accounts`      | Cuentas bancarias y efectivo, con saldo inicial                        |
| `transactions`  | Movimientos diarios (tipo, categoría, cuenta, monto, fecha)            |
| `budgets`       | Presupuesto asignado por categoría/mes/año                              |
| `balance_checks`| Saldos reales ingresados manualmente para conciliar                      |

El **saldo teórico** de cada cuenta se calcula así:

```
saldo_teórico = saldo_inicial + Σ ingresos - Σ gastos - Σ ahorros (en esa cuenta)
```

Al comparar ese saldo teórico contra el saldo real que el usuario observa en el
banco/billetera, la diferencia revela posibles **"gastos fantasma"** (dinero que
salió de la cuenta pero nunca se registró en la app).

## 🚀 Instalación local (paso a paso)

### 1. Requisitos previos
- Python 3.9 o superior instalado (`python --version`)
- pip

### 2. Clonar o copiar el proyecto
Descomprime la carpeta `presupuesto_familiar` donde prefieras.

### 3. Crear un entorno virtual (recomendado)
```bash
cd presupuesto_familiar
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En macOS/Linux:
source venv/bin/activate
```

### 4. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 5. Ejecutar la aplicación
```bash
python app.py
```
Al iniciar, la aplicación:
- Crea automáticamente la carpeta `instance/` y el archivo `presupuesto.db` (SQLite).
- Crea automáticamente categorías básicas de ejemplo (Salario, Mercado, Arriendo, etc.)
  si la base de datos está vacía.

Verás en la consola algo como:
```
 * Running on http://127.0.0.1:5000
 * Running on http://0.0.0.0:5000
```

Abre tu navegador en **http://127.0.0.1:5000**

## 📱 Acceso desde el celular (misma red WiFi)

Como el servidor corre con `host="0.0.0.0"`, cualquier dispositivo conectado
a la **misma red WiFi del hogar** puede acceder usando la IP local del computador:

1. En el computador donde corre `python app.py`, obtén su IP local:
   - Windows: `ipconfig` (busca "Dirección IPv4", ej. `192.168.1.10`)
   - macOS/Linux: `ifconfig` o `ip a`
2. Desde el celular (conectado al mismo WiFi), abre el navegador y visita:
   ```
   http://192.168.1.10:5000
   ```
3. Puedes guardar esa URL como acceso directo en la pantalla de inicio del celular
   (en Chrome/Safari: menú → "Agregar a pantalla de inicio") para que se sienta
   como una app nativa.

> 💡 Primero, agrega tus cuentas reales en el módulo **Cuentas** y ajusta/crea tus
> categorías en **Categorías** antes de empezar a registrar movimientos.

## ☁️ Despliegue en la nube — para NO depender del PC encendido

Esta es la forma recomendada de usar la app: un único servidor **siempre
encendido** en la nube, al que se conectan tanto el celular como el PC. El
proyecto ya está preparado para esto (`config.py`, `Procfile`, `render.yaml`).

### Opción recomendada: Render.com (plan gratuito, con Blueprint automático)

1. **Sube el proyecto a GitHub**
   ```bash
   cd presupuesto_familiar
   git init
   git add .
   git commit -m "Presupuesto Familiar - versión inicial"
   git branch -M main
   git remote add origin https://github.com/tu-usuario/presupuesto-familiar.git
   git push -u origin main
   ```

2. **Crea el Blueprint en Render**
   - Ve a https://render.com → crea una cuenta gratuita (puedes usar tu GitHub).
   - Clic en **New + → Blueprint**.
   - Selecciona tu repositorio `presupuesto-familiar`.
   - Render detecta automáticamente el archivo `render.yaml` incluido en el
     proyecto y crea por ti:
     - Un **Web Service** gratuito corriendo `gunicorn app:app`.
     - Una **base de datos PostgreSQL** gratuita, ya conectada mediante la
       variable de entorno `DATABASE_URL`.
     - Una `SECRET_KEY` generada automáticamente de forma segura.
   - Clic en **Apply** y espera a que termine el build (2-4 minutos).

3. **Listo.** Render te entrega una URL pública fija, por ejemplo:
   ```
   https://presupuesto-familiar.onrender.com
   ```
   Esa es la URL que usan **tanto el celular como el PC**, desde cualquier
   red con internet — el PC de la casa ya no necesita estar encendido.

4. Guarda esa URL como acceso directo en la pantalla de inicio del celular
   (menú del navegador → "Agregar a pantalla de inicio") para que se sienta
   como una app nativa.

> Si prefieres configurarlo manualmente en vez de usar el Blueprint: crea el
> Web Service con **Build Command** `pip install -r requirements.txt` y
> **Start Command** `gunicorn app:app --bind 0.0.0.0:$PORT`, luego crea una
> base PostgreSQL gratuita aparte y copia su "Internal Connection String"
> como variable de entorno `DATABASE_URL` del Web Service.

### ¿Por qué PostgreSQL y no SQLite en la nube?

El plan gratuito de la mayoría de proveedores (Render incluido) usa
**almacenamiento efímero**: el archivo `presupuesto.db` de SQLite se borraría
cada vez que el servicio se reinicia o se actualiza el código. Por eso el
proyecto ya viene preparado (`config.py` detecta la variable `DATABASE_URL`)
para usar automáticamente PostgreSQL en la nube y SQLite solo en tu PC local
— es el mismo código, gracias a SQLAlchemy, sin cambiar una sola línea.

### Alternativas a Render (mismo enfoque)

| Proveedor | Plan gratuito | Notas |
|---|---|---|
| **Render.com** | Sí | Recomendado, incluye `render.yaml` listo para usar en este proyecto |
| **Railway.app** | Crédito gratuito mensual | Igual de sencillo, también soporta Postgres gestionado |
| **Fly.io** | Plan gratuito limitado | Requiere un poco más de configuración (Dockerfile) |
| **VPS propio (DigitalOcean, etc.)** | Desde ~$5 USD/mes | Máximo control, requiere mantenimiento manual |

### Nota sobre el "cold start" del plan gratuito

En el plan gratuito de Render, si la app no recibe tráfico por ~15 minutos,
"se duerme" y la primera petición tarda unos 30-50 segundos en responder
mientras se reactiva. No afecta los datos (siguen seguros en PostgreSQL), solo
la primera carga. Si esto te resulta molesto, hay dos soluciones simples:
- Un servicio gratuito de "ping" (ej. UptimeRobot) que golpee `/health` cada
  10 minutos para mantenerla despierta.
- Subir al plan pago más económico de Render (~$7 USD/mes), que no duerme.

### Verificación de que quedó bien desplegado

Visita `https://tu-app.onrender.com/health` — debe responder:
```json
{"status": "ok", "db": "conectada"}
```

## 🔑 Flujo de uso recomendado

1. **Cuentas** → registra tus cuentas bancarias y efectivo con su saldo inicial real.
2. **Categorías** → ajusta o crea las categorías de Ingreso/Gasto/Ahorro que usa tu familia.
3. **Presupuesto** → al iniciar el mes, asigna cuánto planeas gastar/ahorrar por categoría.
4. **Registrar** (celular) → cada gasto o ingreso del día a día, en segundos.
5. **Dashboard** (PC) → revisa semanalmente el semáforo de ejecución presupuestal.
6. **Conciliación** (PC) → cada cierto tiempo, anota el saldo real del banco/billetera
   para detectar diferencias con el saldo teórico del sistema.

## 🛠️ Personalización rápida

- **Cambiar el color principal:** edita las variables CSS en `static/css/style.css` (`:root`).
- **Cambiar los umbrales del semáforo (80% / 100%):** en `app.py`, función `dashboard()`.
- **Agregar más campos al registro** (ej. adjuntar foto de factura): se recomienda
  agregar una columna `receipt_path` al modelo `Transaction` y manejar `request.files`.
