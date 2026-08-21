# ✈️🅿️ AeroPark AI

**Orquestación Agéntica Cíclica y Memoria Persistente aplicada a la gestión inteligente de estacionamientos aeroportuarios (AEP / EZE)**

Trabajo Final — Inteligencia Artificial Aplicada a Organizaciones
Universidad Tecnológica Nacional, Facultad Regional Buenos Aires (UTN-FRBA)

**Integrantes:** Neila Flores · Julio Ignacio Olivera

🔗 **App en producción:** https://aero-park-ai.vercel.app

---

## 🧩 El problema

Los estacionamientos de Aeroparque (AEP) y Ezeiza (EZE) operan con tarifas estáticas y gestión reactiva, mientras enfrentan variables altamente volátiles: niebla, demoras de vuelos, paros gremiales y picos estacionales de demanda. Esto genera saturación en horas pico, plazas ociosas en horas valle y recargos injustos a pasajeros por demoras ajenas a su control.

## 🎯 La solución

AeroPark AI coordina de forma cíclica una red de agentes de IA que monitorean vuelos, clima y ocupación en tiempo real, recalculan tarifas dinámicamente y se comunican de forma proactiva con los pasajeros (simulado vía chat estilo WhatsApp) para ofrecerles extensiones de estadía con descuento ante contingencias.

## 🤖 Arquitectura de agentes

| Agente | Función |
|---|---|
| **Flight Agent** | Monitorea estado de vuelos y clima; detecta demoras y correlaciona con condiciones meteorológicas adversas |
| **Space Agent** | Controla el inventario de plazas en tiempo real, detecta cuellos de botella y reubica vehículos ante contingencias (ej. granizo) |
| **Pricing Agent** | Calcula tarifas dinámicas según ocupación y clima, respetando límites regulatorios |
| **UX Agent** | Interfaz proactiva con el pasajero vía chat; gestiona notificaciones y ofertas de extensión |
| **Weather Agent** | Detecta alertas meteorológicas preventivas (ej. riesgo de granizo) |

El sistema opera bajo un **ciclo OODA** (Observar → Orientar → Decidir → Actuar) y cuenta con **memoria persistente de tres niveles**: memoria de trabajo (JSON), memoria episódica (SQLite) y memoria semántica (JSON con reglas de negocio y estructura del dominio).

## 👤 Cuenta de usuario y "Mis Reservas"

Cada pasajero puede registrarse, iniciar sesión y ver sus propias reservas (con opción de cancelarlas) en la pestaña **🎫 Mis Reservas**, dentro de la sección "Memoria Persistente & Perfil de Usuario" del dashboard.

## ⚠️ Antes de probar la app — problema conocido

**Si al intentar hacer una reserva no aparecen cocheras disponibles, recargá la página (F5).** Es un problema conocido de refresco de datos en el frontend, no significa que el estacionamiento esté lleno. Lo dejamos documentado acá a propósito: preferimos ser transparentes sobre esta limitación antes que dar la sensación de que todo funciona perfecto.

## 🖥️ Stack tecnológico

| Componente | Tecnología |
|---|---|
| Backend | Python + FastAPI |
| Base de datos | SQLite |
| Persistencia adicional | Archivos JSON (memoria de trabajo y semántica) |
| Frontend | HTML5 + CSS + JavaScript nativo |
| Despliegue | Render (backend) / Vercel (frontend) |
| Seguridad | Contraseñas con hash bcrypt (con salt); recuperación de contraseña con verificación de identidad; CORS restringido a orígenes autorizados |

## 🤝 Co-work con IA

El desarrollo se realizó en co-work con distintas herramientas de IA generativa:

- **Antigravity** — entorno agéntico principal usado para programar el backend, los agentes y el frontend directamente sobre el código.
- **Claude** — revisión y ajuste de la lógica de agentes/backend, diagnóstico de bugs reales en producción (seguridad del reset de contraseña, filtrado de reservas por usuario) y redacción de la documentación técnica del proyecto.
- **ChatGPT** y **Gemini** — apoyo en planificación, procedimientos y diseño de interfaces antes de la implementación.

## 🚀 Simulaciones académicas incluidas

La app incluye 3 escenarios pre-cargados para demostrar el ciclo OODA en acción:

- **Escenario A** — Niebla en AEP: demora de vuelo, saturación de sector y ajuste de tarifas
- **Escenario B** — Hora pico en EZE: demanda casual simultánea y desvío de tráfico
- **Escenario C** — Granizo en vivo: reubicación preventiva de vehículos a sectores techados

## ⚙️ Cómo correrlo localmente

```bash
# Clonar el repositorio
git clone https://github.com/neilaflores-star/AeroPark-AI.git
cd AeroPark-AI

# Instalar dependencias
pip install -r requirements.txt

# Levantar el backend (sirve también el frontend)
uvicorn backend.main:app --reload
```

Luego abrir `http://localhost:8000` en el navegador.

## 📁 Estructura del proyecto

```
AeroPark-AI/
├── backend/
│   ├── main.py           # Endpoints de la API (FastAPI)
│   ├── agents.py         # Lógica de los agentes
│   ├── persistence.py    # Manejo de memoria y base de datos
│   ├── working_memory.json
│   └── semantic_memory.json
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
└── requirements.txt
```

## 🔜 Limitaciones conocidas y próximos pasos

No queremos vender esto como un producto terminado, así que lo dejamos por escrito:

- **Persistencia en el hosting gratuito:** el backend corre en el plan gratuito de Render, que no tiene disco persistente. Los datos sobreviven mientras el proceso sigue activo, pero se resetean si el servicio se redespliega o se duerme por inactividad. Migrar a un almacenamiento persistente gratuito (ej. Turso) es el paso lógico siguiente.
- **Perfiles de usuario:** existen 2 tipos en la interfaz (Admin y Usuario normal) — el usuario `admin` ve las pestañas de memoria interna, el resto no. Pero es una diferenciación solo visual: el backend no valida el rol en ningún endpoint, así que esos datos siguen siendo accesibles llamando a la API directamente. Falta mover esa validación al backend y que el rol sea un campo real de la base de datos, no una comparación de texto contra "admin".

## 📄 Documentación académica

El diseño conceptual completo (problema, objetivos, arquitectura teórica) está documentado en el Trabajo de Medio Ciclo entregado previamente para la cátedra, y el detalle completo de la entrega final (arquitectura, evaluación UX, ciberseguridad y reflexión del equipo) en `Informe_Final_AeroPark_AI.docx`.

---

## 💬 Una palabra final

Ninguno de los dos es programador. Este proyecto lo armamos dirigiendo el desarrollo con IA en vez de escribiendo cada línea a mano, y en el camino nos tocó debuggear cosas que ni sabíamos que existían —desde un problema de seguridad real en el login hasta un bug de CSS escondido en tres lugares distintos—. Fue un desafío grande, pero nos enriqueció bastante más de lo que esperábamos al arrancar la materia.

---

*Proyecto desarrollado como trabajo final de la materia IA Aplicada a Organizaciones — UTN-FRBA, 2026.*
