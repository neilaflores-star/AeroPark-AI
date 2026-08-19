# ✈️🅿️ AeroPark AI

*Orquestación Agéntica Cíclica y Memoria Persistente aplicada a la gestión inteligente de estacionamientos aeroportuarios (AEP / EZE)*

Trabajo Final — Inteligencia Artificial Aplicada a Organizaciones
Universidad Tecnológica Nacional, Facultad Regional Buenos Aires (UTN-FRBA)

*Integrantes:* Neila Flores · Julio Ignacio Olivera

🔗 *App en producción:* https://aero-park-ai.vercel.app

---

## 🧩 El problema

Los estacionamientos de Aeroparque (AEP) y Ezeiza (EZE) operan con tarifas estáticas y gestión reactiva, mientras enfrentan variables altamente volátiles: niebla, demoras de vuelos, paros gremiales y picos estacionales de demanda. Esto genera saturación en horas pico, plazas ociosas en horas valle y recargos injustos a pasajeros por demoras ajenas a su control.

## 🎯 La solución

AeroPark AI coordina de forma cíclica una red de agentes de IA que monitorean vuelos, clima y ocupación en tiempo real, recalculan tarifas dinámicamente y se comunican de forma proactiva con los pasajeros (simulado vía chat estilo WhatsApp) para ofrecerles extensiones de estadía con descuento ante contingencias.

## 🤖 Arquitectura de agentes

| Agente | Función |
|---|---|
| *Flight Agent* | Monitorea estado de vuelos y clima; detecta demoras y correlaciona con condiciones meteorológicas adversas |
| *Space Agent* | Controla el inventario de plazas en tiempo real, detecta cuellos de botella y reubica vehículos ante contingencias (ej. granizo) |
| *Pricing Agent* | Calcula tarifas dinámicas según ocupación y clima, respetando límites regulatorios |
| *UX Agent* | Interfaz proactiva con el pasajero vía chat; gestiona notificaciones y ofertas de extensión |
| *Weather Agent* | Detecta alertas meteorológicas preventivas (ej. riesgo de granizo) |

El sistema opera bajo un *ciclo OODA* (Observar → Orientar → Decidir → Actuar) y cuenta con *memoria persistente de tres niveles*: memoria de trabajo (JSON), memoria episódica (SQLite) y memoria semántica (JSON con reglas de negocio y estructura del dominio).

## 🖥️ Stack tecnológico

| Componente | Tecnología |
|---|---|
| Backend | Python + FastAPI |
| Base de datos | SQLite |
| Persistencia adicional | Archivos JSON (memoria de trabajo y semántica) |
| Frontend | HTML5 + CSS + JavaScript nativo |
| Despliegue | Render (backend) / Vercel (frontend) |

## 🚀 Simulaciones académicas incluidas

La app incluye 3 escenarios pre-cargados para demostrar el ciclo OODA en acción:

- *Escenario A* — Niebla en AEP: demora de vuelo, saturación de sector y ajuste de tarifas
- *Escenario B* — Hora pico en EZE: demanda casual simultánea y desvío de tráfico
- *Escenario C* — Granizo en vivo: reubicación preventiva de vehículos a sectores techados

## ⚙️ Cómo correrlo localmente

bash
# Clonar el repositorio
git clone https://github.com/neilaflores-star/AeroPark-AI.git
cd AeroPark-AI

# Instalar dependencias
pip install -r requirements.txt

# Levantar el backend (sirve también el frontend)
uvicorn backend.main:app --reload


Luego abrir http://localhost:8000 en el navegador.

## 📁 Estructura del proyecto


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


## 📄 Documentación académica

El diseño conceptual completo (problema, objetivos, arquitectura teórica) está documentado en el Trabajo de Medio Ciclo entregado previamente para la cátedra.

---

Proyecto desarrollado como trabajo final de la materia IA Aplicada a Organizaciones — UTN-FRBA, 2026.
