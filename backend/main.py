import os
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import backend.persistence as db
import backend.agents as ag

app = FastAPI(title="AeroPark AI - API de Orquestación Agéntica")

# Habilitar CORS para permitir que el frontend se conecte desde cualquier origen (ej. Vercel, file:// o localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    """Endpoint de comprobación de salud para Render.com."""
    return {"status": "SUCCESS", "message": "AeroPark AI Backend en vivo", "version": "1.0.0"}

# Carga inicial del estado en memoria (Memoria de Trabajo)
state = db.load_working_memory()


# Instanciar los agentes con la memoria de trabajo cargada
weather_agent = ag.WeatherAgent(state)
flight_agent = ag.FlightAgent(state)
space_agent = ag.SpaceAgent(state)
pricing_agent = ag.PricingAgent(state)
ux_agent = ag.UXAgent(state)

# --- Modelos de Peticiones API (Pydantic) ---

class ReservationRequest(BaseModel):
    plate: str
    sector: str
    flight_id: str
    owner_name: str
    owner_phone: str
    entry_time: str
    scheduled_exit: str
    slot_id: str

class WeatherSim(BaseModel):
    weather: str

class FlightStatusSim(BaseModel):
    flight_id: str
    status: str

class CarSim(BaseModel):
    sector: str

class UXReply(BaseModel):
    phone: str
    message: str

class UserAuth(BaseModel):
    username: str
    password: str

class PasswordReset(BaseModel):
    username: str
    new_password: str

# --- Endpoints de la API ---

@app.post("/api/auth/register")
def register_user(payload: UserAuth):
    """Registra un nuevo usuario en el sistema."""
    success, msg = db.create_user(payload.username, payload.password)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    db.log_incident("USUARIO_REGISTRO", f"El usuario '{payload.username.lower()}' se ha registrado con éxito.")
    return {"status": "SUCCESS", "message": msg}

@app.post("/api/auth/login")
def login_user(payload: UserAuth):
    """Verifica credenciales de usuario."""
    success = db.verify_user(payload.username, payload.password)
    if not success:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
    db.log_incident("USUARIO_LOGIN", f"El usuario '{payload.username.lower()}' inició sesión.")
    return {"status": "SUCCESS", "username": payload.username.lower()}

@app.post("/api/auth/reset-password")
def reset_password(payload: PasswordReset):
    """Restablece la contraseña de un usuario."""
    success, msg = db.reset_user_password(payload.username, payload.new_password)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    db.log_incident("USUARIO_PASS_RESET", f"El usuario '{payload.username.lower()}' restableció su contraseña.")
    return {"status": "SUCCESS", "message": msg}

@app.get("/api/user/profile/{username}")
def get_user_profile(username: str):
    """Retorna información del perfil y reservas vigentes del usuario."""
    profile = db.get_user_profile_data(username)
    return {"status": "SUCCESS", "profile": profile}

@app.get("/api/status")
def get_status():

    """Retorna el estado de la memoria de trabajo, semántica y los incidentes recientes."""
    return {
        "working_memory": state,
        "semantic_memory": db.load_semantic_memory(),
        "incidents": db.get_incidents(15),
        "tariffs": state.get("current_tariffs")
    }

@app.post("/api/simulate/weather")
def simulate_weather(payload: WeatherSim):
    """Simula un cambio de clima y corre el ciclo de decisión de tarifas y alertas."""
    weather = payload.weather.upper()
    if weather not in ["DESPEJADO", "LLUVIA", "NIEBLA"]:
        raise HTTPException(status_code=400, detail="Clima inválido. Usar: DESPEJADO, LLUVIA, NIEBLA.")
    
    # 1. Ejecutar FlightAgent
    clima_cambio = flight_agent.update_weather(weather)
    
    # 2. Si hay cambio, el PricingAgent evalúa nuevas tarifas dinámicas
    tarifas_cambio = False
    if clima_cambio:
        tarifas_cambio = pricing_agent.recalculate_tariffs()
        
    # 3. UXAgent comprueba si hay pasajeros a alertar (por demoras previas)
    ux_agent.check_and_notify_passengers()
    
    # 4. Guardar cambios en persistencia
    db.save_working_memory(state)
    
    return {
        "status": "OK",
        "weather": state["weather"],
        "clima_cambio": clima_cambio,
        "tarifas_cambio": tarifas_cambio,
        "current_tariffs": state["current_tariffs"]
    }

@app.post("/api/simulate/flight-status")
def simulate_flight_status(payload: FlightStatusSim):
    """Simula el cambio de estado de un vuelo (A TIEMPO, DEMORADO, CANCELADO)."""
    status = payload.status.upper()
    if status not in ["A TIEMPO", "DEMORADO", "CANCELADO"]:
        raise HTTPException(status_code=400, detail="Estado de vuelo inválido.")
    
    # 1. FlightAgent actualiza estado del vuelo
    vuelo_cambio = flight_agent.update_flight_status(payload.flight_id, status)
    
    # 2. PricingAgent recalcula (el retraso de un vuelo puede alterar la demanda)
    tarifas_cambio = False
    if vuelo_cambio:
        tarifas_cambio = pricing_agent.recalculate_tariffs()
        
    # 3. UXAgent verifica pasajeros afectados para notificar
    ux_agent.check_and_notify_passengers()
    
    # 4. Guardar cambios en persistencia
    db.save_working_memory(state)
    
    return {
        "status": "OK",
        "vuelo_cambio": vuelo_cambio,
        "tarifas_cambio": tarifas_cambio,
        "current_tariffs": state["current_tariffs"]
    }

@app.post("/api/simulate/car-entry")
def simulate_car_entry(payload: CarSim):
    """Simula la entrada física de un auto al sector seleccionado."""
    # 1. SpaceAgent registra entrada
    ok = space_agent.register_car_entry(payload.sector)
    if not ok:
        raise HTTPException(status_code=400, detail="Sector lleno o no existente.")
    
    # 2. PricingAgent recalcula por aumento de ocupación
    pricing_agent.recalculate_tariffs()
    
    # 3. Guardar persistencia
    db.save_working_memory(state)
    
    return {"status": "OK", "slots": state["parking_slots"], "tariffs": state["current_tariffs"]}

@app.post("/api/simulate/car-exit")
def simulate_car_exit(payload: CarSim):
    """Simula la salida física de un auto del sector seleccionado."""
    # 1. SpaceAgent registra salida
    ok = space_agent.register_car_exit(payload.sector)
    if not ok:
        raise HTTPException(status_code=400, detail="No hay autos en este sector.")
    
    # 2. PricingAgent recalcula por baja de ocupación
    pricing_agent.recalculate_tariffs()
    
    # 3. Guardar persistencia
    db.save_working_memory(state)
    
    return {"status": "OK", "slots": state["parking_slots"], "tariffs": state["current_tariffs"]}

@app.post("/api/ux/reply")
def ux_reply(payload: UXReply):
    """Simula la respuesta del pasajero a la propuesta de WhatsApp enviada por el UXAgent."""
    # 1. UXAgent procesa la respuesta
    respuesta = ux_agent.process_passenger_reply(payload.phone, payload.message)
    
    # 2. Guardar persistencia
    db.save_working_memory(state)
    
    return {
        "status": "OK",
        "reply_received": payload.message,
        "system_response": respuesta,
        "simulated_cars": state["simulated_cars"]
    }

@app.get("/api/ux/chat/{phone}")
def get_chat(phone: str):
    """Obtiene el historial de chat de un teléfono específico."""
    logs = db.get_chat_logs(phone)
    return {"phone": phone, "chat_logs": logs}

@app.post("/api/simulate/scenario-a")
def simulate_scenario_a():
    """Ejecuta la Simulación A: Niebla en AEP."""
    # 1. Establecer clima de niebla en FlightAgent
    flight_agent.update_weather("NIEBLA")
    
    # 2. Establecer vuelo AR-1302 como demorado por 3 horas
    flight_agent.update_flight_status("AR-1302", "DEMORADO")
    for flight in state["active_flights"]:
        if flight["id"] == "AR-1302":
            flight["eta"] = "17:30"
            
    # 3. Forzar ocupación al 93% en Corta Estadía
    state["parking_slots"]["corta"]["occupied"] = 93
    db.log_incident(
        "SPACE_ORIENTAR",
        "Space Agent: Detectó que 120 vehículos vinculados al vuelo AR-1302 demorarán su egreso. Saturación inminente de Corta."
    )
    
    # 4. PricingAgent recalcula tarifas (subirá Corta por niebla/ocupación)
    pricing_agent.recalculate_tariffs()
    
    # 5. UXAgent envía advertencia y WhatsApp de propuesta
    ux_agent.check_and_notify_passengers()
    
    # 6. Actualizar cartel LED
    state["led_sign"] = "Sector Corta COMPLETO - Solo Reservas"
    db.log_incident("CARTEL_LED", "Cartel LED actualizado a: 'Sector Corta COMPLETO - Solo Reservas'")
    
    # 7. Registrar en base de datos episódica
    db.log_incident("SIMULACION_A", "Ejecución de Simulación A: Niebla en AEP y demoras de AR-1302.")
    
    db.save_working_memory(state)
    return {"status": "SUCCESS", "working_memory": state}

@app.post("/api/simulate/scenario-b")
def simulate_scenario_b():
    """Ejecuta la Simulación B: Hora Pico en EZE (Demanda Casual)."""
    # 1. Clima Despejado
    flight_agent.update_weather("DESPEJADO")
    
    # 2. Cambiar vuelos por arribo simultáneo en EZE
    eze_flights = [
        {"id": "AA-908", "airline": "American Airlines", "origin": "Miami", "status": "A TIEMPO", "eta": "16:20"},
        {"id": "IB-6844", "airline": "Iberia", "origin": "Madrid", "status": "A TIEMPO", "eta": "16:30"},
        {"id": "LA-2415", "airline": "LATAM", "origin": "Santiago de Chile", "status": "A TIEMPO", "eta": "17:00"}
    ]
    state["active_flights"] = eze_flights
    db.log_incident("SPACE_LPR_AUTOPISTA", "Cámaras LPR en Autopista Riccheri detectan incremento anómalo de flujo vehicular hacia EZE.")
    
    # 3. Forzar ocupación de Corta Estadía al 95% (salto rápido)
    state["parking_slots"]["corta"]["occupied"] = 95
    db.log_incident(
        "SPACE_ORIENTAR",
        "Space Agent: Sensores registran salto rápido al 95% en Corta Estadía por vehículos casuales sin reserva en EZE."
    )
    
    # 4. PricingAgent aplica tarifa disuasoria máxima a Corta ($4000) y reduce 30% a Larga ($700)
    state["current_tariffs"]["corta"] = 4000
    state["current_tariffs"]["larga"] = 700
    db.log_tariff_change("corta", 4000, "Tarifa disuasoria máxima por ocupación proyectada de 95% (límite ORSNA)")
    db.log_tariff_change("larga", 700, "Descuento del 30% para absorber excedente espontáneo")
    db.log_incident("PRECIO_CONGELADO", "Pricing Agent: Se aplica tarifa disuasoria máxima a Corta ($4000) y descuento 30% a Larga ($700).")
    
    # 5. Registrar desvío de patente ABC-123
    state["temp_discounts"] = [{"plate": "ABC-123", "sector": "larga", "price": 700}]
    db.log_incident(
        "SPACE_LPR_BARRERA",
        "Cámara LPR valida patente [ABC-123] sin reserva. Bloquea acceso Corta y asocia descuento en Larga."
    )
    
    # 6. Actualizar cartel LED
    state["led_sign"] = "Sector Corta COMPLETO - Acompañantes desviar a Larga Estadía (30% OFF)"
    db.log_incident("CARTEL_LED", "Cartel LED actualizado a: 'Sector Corta COMPLETO - Acompañantes desviar a Larga (30% OFF)'")
    
    # 7. Registrar en base de datos episódica
    db.log_incident(
        "SIMULACION_B", 
        "Ejecución de Simulación B: Gestión de Demanda Casual en Hora Pico en EZE. Patente ABC-123 desviada."
    )
    
    db.save_working_memory(state)
    return {"status": "SUCCESS", "working_memory": state}

@app.post("/api/reserve")
def make_reservation(payload: ReservationRequest):
    """Crea una reserva de cochera individual."""
    # 1. Buscar la cochera seleccionada
    slots = state.get("slots", [])
    selected_slot = None
    for s in slots:
        if s["slot_id"] == payload.slot_id:
            selected_slot = s
            break
            
    if not selected_slot:
        raise HTTPException(status_code=400, detail="Cochera no encontrada.")
    if selected_slot["status"] != "available":
        raise HTTPException(status_code=400, detail="Cochera ya ocupada o reservada.")
        
    # 2. Actualizar estado de la cochera
    selected_slot["status"] = "reserved"
    selected_slot["assigned_plate"] = payload.plate.upper()
    
    # 3. Registrar reserva en simulated_cars
    new_car = {
        "plate": payload.plate.upper(),
        "sector": payload.sector,
        "flight_id": payload.flight_id.upper(),
        "owner_name": payload.owner_name,
        "owner_phone": payload.owner_phone,
        "entry_time": payload.entry_time,
        "scheduled_exit": payload.scheduled_exit,
        "status": "ESTACIONADO",
        "assigned_slot": payload.slot_id,
        "notified": False
    }
    state["simulated_cars"].append(new_car)
    
    # 4. Generar confirmación por UXAgent y registrar en chat
    msg = ux_agent.get_reservation_confirmation_message(new_car)
    db.log_chat_message(payload.owner_phone, "SYSTEM", msg)
    db.log_incident(
        "RESERVA_NUEVA",
        f"Nueva reserva creada: Patente {new_car['plate']} asignada a cochera {payload.slot_id} ({payload.sector.upper()})."
    )
    
    # 5. Incrementar contador de ocupación general
    if payload.sector in state["parking_slots"]:
        state["parking_slots"][payload.sector]["occupied"] += 1
        
    # 6. Recalcular tarifas si aplica
    pricing_agent.recalculate_tariffs()
    
    db.save_working_memory(state)
    return {"status": "SUCCESS", "car": new_car}

@app.post("/api/simulate/scenario-c")
def simulate_scenario_c():
    """Ejecuta la Simulación C: Prevención y Resguardo de Granizo en Vivo (Upgrade de Emergencia)."""
    # 1. WeatherAgent activa alerta preventiva de granizo
    weather_agent.check_hail_risk("Aeroparque")
    
    # 2. Cambiar clima general a LLUVIA (para dar contexto visual)
    flight_agent.update_weather("LLUVIA")
    
    # 3. Space Agent identifica vehículos estacionados en descubierto en este momento
    # Valeria Gómez (patente AF-987-XY) está en plaza B-2 (uncovered)
    target_plate = "AF-987-XY"
    
    # 4. Space Agent ejecuta reubicación a techado
    success, old_slot, new_slot = space_agent.reassign_slot_due_to_hazard(target_plate)
    
    if success and old_slot and new_slot:
        # Encontrar datos de Valeria para enviar WhatsApp
        valeria_car = None
        for car in state.get("simulated_cars", []):
            if car["plate"] == target_plate:
                valeria_car = car
                break
        
        # 5. UX Agent notifica la acción por WhatsApp
        if valeria_car:
            msg = ux_agent.get_hail_relocation_message(valeria_car, old_slot, new_slot)
            db.log_chat_message(valeria_car["owner_phone"], "SYSTEM", msg)
            db.log_incident(
                "UX_NOTIFICACION",
                f"WhatsApp de alerta enviado a {valeria_car['owner_name']} avisando resguardo preventivo de {old_slot} a {new_slot}."
            )
            
        # 6. Actualizar cartel LED
        state["led_sign"] = "ALERTA DE GRANIZO - UPGRADE DE EMERGENCIA ACTIVO"
        db.log_incident("CARTEL_LED", "Cartel LED actualizado a: 'ALERTA DE GRANIZO - UPGRADE DE EMERGENCIA ACTIVO'")
        
        # 7. Registrar en SQLite el porcentaje de resguardo
        db.log_incident(
            "SIMULACION_C",
            "Ejecución de Simulación C: Resguardo de granizo completado. Tasa de éxito: 100% (1/1 expuesto)."
        )
    else:
        db.log_incident(
            "SIMULACION_C_FALLA",
            "No se pudo reubicar el vehículo expuesto. Razón: Sin cocheras techadas de contingencia disponibles."
        )
        
    # Recalcular tarifas por alerta de granizo
    pricing_agent.recalculate_tariffs()
    
    db.save_working_memory(state)
    return {"status": "SUCCESS", "working_memory": state}

@app.post("/api/reset")
def reset_app():
    """Reinicia la base de datos y el estado JSON a valores por defecto."""
    global state, weather_agent, flight_agent, space_agent, pricing_agent, ux_agent
    
    # 1. Eliminar archivos y recrear base de datos
    if os.path.exists(db.WORKING_MEMORY_PATH):
        os.remove(db.WORKING_MEMORY_PATH)
    if os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)
        
    db.init_db()
    
    # 2. Cargar estado por defecto
    state = db.load_working_memory()
    
    # 3. Reiniciar instancias
    weather_agent = ag.WeatherAgent(state)
    flight_agent = ag.FlightAgent(state)
    space_agent = ag.SpaceAgent(state)
    pricing_agent = ag.PricingAgent(state)
    ux_agent = ag.UXAgent(state)
    
    db.log_incident("SISTEMA_REINICIO", "El administrador reinició el aplicativo a valores de fábrica.")
    
    return {"status": "RESET_SUCCESSFUL"}

# --- Servir Frontend Estático ---
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Obtener la ruta absoluta de la carpeta frontend
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

# Ruta raíz sirve el index.html
@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# Montar los demás archivos estáticos (styles.css, app.js) en la raíz
app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")

