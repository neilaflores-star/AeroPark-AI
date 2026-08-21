import os
import json
import sqlite3
import hashlib
import bcrypt
from datetime import datetime


# Rutas de persistencia
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKING_MEMORY_PATH = os.path.join(BASE_DIR, "working_memory.json")
SEMANTIC_MEMORY_PATH = os.path.join(BASE_DIR, "semantic_memory.json")
DB_PATH = os.path.join(BASE_DIR, "aeropark.db")

# Estado inicial por defecto de la Memoria de Trabajo
DEFAULT_WORKING_MEMORY = {
    "weather": "DESPEJADO",
    "weather_alert": None,
    "led_sign": "BIENVENIDOS A AEROPARK AI - SECTORES DISPONIBLES",
    "temp_discounts": [],
    "parking_slots": {
        "corta": {"capacity": 100, "occupied": 45},
        "larga": {"capacity": 250, "occupied": 110},
        "valet": {"capacity": 50, "occupied": 10}
    },
    "slots": [
        # Sector Corta (Techado/Covered)
        {"slot_id": "A-1", "sector": "corta", "type": "covered", "status": "reserved", "assigned_plate": "AE-123-BC"},
        {"slot_id": "A-2", "sector": "corta", "type": "covered", "status": "available", "assigned_plate": None},
        {"slot_id": "A-3", "sector": "corta", "type": "covered", "status": "available", "assigned_plate": None},
        {"slot_id": "A-4", "sector": "corta", "type": "covered", "status": "available", "assigned_plate": None},
        {"slot_id": "A-5", "sector": "corta", "type": "covered", "status": "available", "assigned_plate": None},
        {"slot_id": "A-6", "sector": "corta", "type": "covered", "status": "available", "assigned_plate": None},
        # Sector Larga (Descubierto/Uncovered)
        {"slot_id": "B-1", "sector": "larga", "type": "uncovered", "status": "available", "assigned_plate": None},
        {"slot_id": "B-2", "sector": "larga", "type": "uncovered", "status": "reserved", "assigned_plate": "AF-987-XY"},
        {"slot_id": "B-3", "sector": "larga", "type": "uncovered", "status": "available", "assigned_plate": None},
        {"slot_id": "B-4", "sector": "larga", "type": "uncovered", "status": "available", "assigned_plate": None},
        {"slot_id": "B-5", "sector": "larga", "type": "uncovered", "status": "available", "assigned_plate": None},
        {"slot_id": "B-6", "sector": "larga", "type": "uncovered", "status": "available", "assigned_plate": None},
        # Sector Valet (Techado/Covered)
        {"slot_id": "C-1", "sector": "valet", "type": "covered", "status": "reserved", "assigned_plate": "AD-456-ZZ"},
        {"slot_id": "C-2", "sector": "valet", "type": "covered", "status": "available", "assigned_plate": None},
        {"slot_id": "C-3", "sector": "valet", "type": "covered", "status": "available", "assigned_plate": None},
        {"slot_id": "C-4", "sector": "valet", "type": "covered", "status": "available", "assigned_plate": None},
        {"slot_id": "C-5", "sector": "valet", "type": "covered", "status": "available", "assigned_plate": None},
        {"slot_id": "C-6", "sector": "valet", "type": "covered", "status": "available", "assigned_plate": None}
    ],
    "active_flights": [
        {"id": "AR-1302", "airline": "Aerolíneas Argentinas", "origin": "Bariloche", "status": "A TIEMPO", "eta": "14:30"},
        {"id": "FO-5012", "airline": "Flybondi", "origin": "Córdoba", "status": "A TIEMPO", "eta": "15:10"},
        {"id": "WJ-3420", "airline": "JetSMART", "origin": "Mendoza", "status": "A TIEMPO", "eta": "15:45"},
        {"id": "AA-908", "airline": "American Airlines", "origin": "Miami", "status": "A TIEMPO", "eta": "16:20"},
        {"id": "LA-2415", "airline": "LATAM", "origin": "Santiago de Chile", "status": "A TIEMPO", "eta": "17:00"}
    ],
    "current_tariffs": {
        "corta": 1500,
        "larga": 1000,
        "valet": 2500
    },
    "simulated_cars": [
        {
            "plate": "AE-123-BC",
            "sector": "corta",
            "flight_id": "AR-1302",
            "owner_name": "Juan Pérez",
            "owner_phone": "+54 9 11 5555-1234",
            "entry_time": "12:00",
            "scheduled_exit": "15:30",
            "status": "ESTACIONADO",
            "assigned_slot": "A-1",
            "notified": False
        },
        {
            "plate": "AF-987-XY",
            "sector": "larga",
            "flight_id": "WJ-3420",
            "owner_name": "Valeria Gómez",
            "owner_phone": "+54 9 11 4444-9876",
            "entry_time": "10:00",
            "scheduled_exit": "16:45",
            "status": "ESTACIONADO",
            "assigned_slot": "B-2",
            "notified": False
        },
        {
            "plate": "AD-456-ZZ",
            "sector": "valet",
            "flight_id": "AA-908",
            "owner_name": "Carlos Rodríguez",
            "owner_phone": "+54 9 11 3333-4567",
            "entry_time": "08:00",
            "scheduled_exit": "17:30",
            "status": "ESTACIONADO",
            "assigned_slot": "C-1",
            "notified": False
        }
    ]
}

# Estado de la Memoria Semántica (Reglas fijas del aeropuerto)
DEFAULT_SEMANTIC_MEMORY = {
    "airport": {
        "name": "Aeroparque Jorge Newbery / Ezeiza",
        "sectors": {
            "corta": {
                "description": "Estacionamiento multinivel cubierto frente a terminales", 
                "walk_time_mins": 3, 
                "min_price": 1000, 
                "max_price": 4000,
                "type": "covered",
                "base_price_hour": 1500,
                "base_price_day": 12000
            },
            "larga": {
                "description": "Estacionamiento descubierto económico alejado", 
                "walk_time_mins": 10, 
                "min_price": 600, 
                "max_price": 2500,
                "type": "uncovered",
                "base_price_hour": 1000,
                "base_price_day": 7000
            },
            "valet": {
                "description": "Servicio premium con recepción en puerta de embarque", 
                "walk_time_mins": 1, 
                "min_price": 2000, 
                "max_price": 6000,
                "type": "covered",
                "base_price_hour": 2500,
                "base_price_day": 18000
            }
        }
    },
    "pricing_rules": {
        "base_increase_on_rain": 0.10,     # +10% por lluvia
        "base_increase_on_fog": 0.25,      # +25% por niebla
        "occupancy_threshold_high": 0.85,  # >85% activa precios altos
        "delay_grace_minutes": 30          # Tolerancia sin recargo
    }
}

def init_db():
    """Inicializa la base de datos de Memoria Episódica en SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabla de Incidentes / Eventos del ciclo de decisión
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT NOT NULL
        )
    """)
    
    # Tabla de Historial de Chat (UX Agent)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            phone TEXT NOT NULL,
            sender TEXT NOT NULL, -- 'SYSTEM' o 'CLIENT'
            message TEXT NOT NULL
        )
    """)
    
    # Tabla de Historial de Tarifas (Pricing Agent)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tariff_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            sector TEXT NOT NULL,
            price INTEGER NOT NULL,
            reason TEXT NOT NULL
        )
    """)

    # Tabla de Usuarios para Autenticación
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()

# --- Funciones de lectura/escritura de Memoria de Trabajo (JSON) ---

def load_working_memory():
    """Carga la Memoria de Trabajo. Si no existe, crea una con valores por defecto."""
    if not os.path.exists(WORKING_MEMORY_PATH):
        save_working_memory(DEFAULT_WORKING_MEMORY)
        return DEFAULT_WORKING_MEMORY
    try:
        with open(WORKING_MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_WORKING_MEMORY

def save_working_memory(data):
    """Guarda la Memoria de Trabajo en el archivo JSON."""
    with open(WORKING_MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- Funciones de lectura/escritura de Memoria Semántica (JSON) ---

def load_semantic_memory():
    """Carga la Memoria Semántica base. Si no existe, la crea."""
    if not os.path.exists(SEMANTIC_MEMORY_PATH):
        with open(SEMANTIC_MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SEMANTIC_MEMORY, f, indent=4, ensure_ascii=False)
        return DEFAULT_SEMANTIC_MEMORY
    with open(SEMANTIC_MEMORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# --- Funciones de la Memoria Episódica (SQLite) ---

def log_incident(incident_type, description):
    """Registra un evento/incidente en la base de datos episódica."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO incidents (timestamp, type, description) VALUES (?, ?, ?)",
        (now, incident_type, description)
    )
    conn.commit()
    conn.close()

def get_incidents(limit=30):
    """Recupera los incidentes históricos."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, type, description FROM incidents ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [{"timestamp": r[0], "type": r[1], "description": r[2]} for r in rows]

def log_chat_message(phone, sender, message):
    """Registra un mensaje de chat enviado o recibido por el UX Agent."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO chat_logs (timestamp, phone, sender, message) VALUES (?, ?, ?, ?)",
        (now, phone, sender, message)
    )
    conn.commit()
    conn.close()

def get_chat_logs(phone):
    """Recupera la conversación de un usuario específico."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT timestamp, sender, message FROM chat_logs WHERE phone = ? ORDER BY id ASC",
        (phone,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"timestamp": r[0], "sender": r[1], "message": r[2]} for r in rows]

def log_tariff_change(sector, price, reason):
    """Registra un cambio de tarifa para análisis histórico."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO tariff_history (timestamp, sector, price, reason) VALUES (?, ?, ?, ?)",
        (now, sector, price, reason)
    )
    conn.commit()
    conn.close()

def get_tariff_history(sector=None, limit=20):
    """Recupera el historial de precios dinámicos."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if sector:
        cursor.execute(
            "SELECT timestamp, sector, price, reason FROM tariff_history WHERE sector = ? ORDER BY id DESC LIMIT ?",
            (sector, limit)
        )
    else:
        cursor.execute(
            "SELECT timestamp, sector, price, reason FROM tariff_history ORDER BY id DESC LIMIT ?",
            (limit,)
        )
    rows = cursor.fetchall()
    conn.close()
    return [{"timestamp": r[0], "sector": r[1], "price": r[2], "reason": r[3]} for r in rows]

# --- Funciones de Usuarios (Autenticación) ---

def hash_password(password):
    """Devuelve el hash bcrypt de una contraseña."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def create_user(username, password):
    """Crea un usuario en la base de datos con contraseña hasheada."""
    username_clean = username.strip().lower()
    if not username_clean or not password:
        return False, "Usuario o contraseña vacíos."
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    pwd_hash = hash_password(password)
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username_clean, pwd_hash)
        )
        conn.commit()
        conn.close()
        return True, "Registro exitoso."
    except sqlite3.IntegrityError:
        conn.close()
        return False, "El nombre de usuario ya está registrado."
    except Exception as e:
        conn.close()
        return False, f"Error al registrar usuario: {str(e)}"

def verify_user(username, password):
    """Verifica si las credenciales son válidas usando bcrypt.checkpw."""
    username_clean = username.strip().lower()
    if not username_clean or not password:
        return False
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password_hash FROM users WHERE username = ?",
        (username_clean,)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), row[0].encode("utf-8"))
    except Exception:
        return False

def reset_user_password(username, current_password, new_password):
    """Actualiza la contraseña de un usuario existente validando su contraseña actual."""
    username_clean = username.strip().lower()
    if not username_clean or not current_password or not new_password:
        return False, "Todos los campos son obligatorios.", 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username_clean,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, "El nombre de usuario no existe.", 404
        
    stored_hash = row[0]
    try:
        is_valid = bcrypt.checkpw(current_password.encode("utf-8"), stored_hash.encode("utf-8"))
    except Exception:
        is_valid = False
        
    if not is_valid:
        conn.close()
        return False, "La contraseña actual es incorrecta.", 401
        
    new_pwd_hash = hash_password(new_password)
    cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_pwd_hash, username_clean))
    conn.commit()
    conn.close()
    return True, "Contraseña restablecida exitosamente.", 200


def get_user_profile_data(username):
    """Obtiene los datos de perfil y reservas asociadas de un usuario."""
    username_clean = username.strip().lower()
    wm = load_working_memory()
    sim_cars = wm.get("simulated_cars", [])
    
    # Buscar vehículos / reservas vinculados al usuario por su username de login
    # (antes filtraba por owner_name, que es el nombre del pasajero tipeado
    # en el formulario y casi nunca coincide con el username de la cuenta)
    user_cars = [car for car in sim_cars if car.get("username", "").strip().lower() == username_clean]
    
    return {
        "username": username_clean,
        "active_reservations": user_cars,
        "total_reservations": len(user_cars)
    }

# Inicializa la base de datos cuando se carga este módulo
init_db()
load_semantic_memory()

