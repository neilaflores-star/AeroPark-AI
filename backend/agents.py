from datetime import datetime, timedelta
import backend.persistence as db

class WeatherAgent:
    def __init__(self, state):
        self.state = state

    def check_hail_risk(self, location, date_range=None):
        """Monitorea preventivamente el clima para detectar riesgos de granizo."""
        self.state["weather_alert"] = "HAIL"
        db.log_incident(
            "CLIMA_ALERTA",
            f"Weather Agent: Detectó Alerta Meteorológica de Granizo (SMN) en {location}."
        )
        return True

class FlightAgent:
    def __init__(self, state):
        self.state = state

    def update_weather(self, weather):
        """Actualiza el clima en la memoria de trabajo y registra el evento si cambia."""
        old_weather = self.state.get("weather", "DESPEJADO")
        if old_weather != weather:
            self.state["weather"] = weather
            db.log_incident(
                "CLIMA_CAMBIO", 
                f"El clima en Aeroparque cambió de {old_weather} a {weather}."
            )
            # Si se limpia a DESPEJADO, reseteamos la alerta de granizo
            if weather == "DESPEJADO":
                self.state["weather_alert"] = None
            return True
        return False

    def update_flight_status(self, flight_id, new_status):
        """Actualiza el estado de un vuelo específico y devuelve si cambió."""
        changed = False
        for flight in self.state.get("active_flights", []):
            if flight["id"] == flight_id:
                old_status = flight["status"]
                if old_status != new_status:
                    flight["status"] = new_status
                    changed = True
                    db.log_incident(
                        "VUELO_CAMBIO", 
                        f"El vuelo {flight_id} ({flight['airline']}) desde {flight['origin']} cambió a {new_status}."
                    )
        return changed


class SpaceAgent:
    def __init__(self, state):
        self.state = state

    def register_car_entry(self, sector):
        """Registra el ingreso físico de un vehículo a un sector."""
        slots = self.state["parking_slots"]
        if sector in slots:
            if slots[sector]["occupied"] < slots[sector]["capacity"]:
                slots[sector]["occupied"] += 1
                db.log_incident(
                    "VEHICULO_INGRESO", 
                    f"Nuevo vehículo ingresado en sector {sector.upper()}. Ocupación: {slots[sector]['occupied']}/{slots[sector]['capacity']}."
                )
                return True
        return False

    def register_car_exit(self, sector):
        """Registra la salida física de un vehículo."""
        slots = self.state["parking_slots"]
        if sector in slots:
            if slots[sector]["occupied"] > 0:
                slots[sector]["occupied"] -= 1
                db.log_incident(
                    "VEHICULO_SALIDA", 
                    f"Vehículo egresado de sector {sector.upper()}. Ocupación: {slots[sector]['occupied']}/{slots[sector]['capacity']}."
                )
                return True
        return False

    def get_available_slots(self, sector, slot_type=None):
        """Devuelve las cocheras individuales disponibles según sector y tipo."""
        slots = self.state.get("slots", [])
        available = []
        for s in slots:
            if s["sector"] == sector and s["status"] == "available":
                if not slot_type or s["type"] == slot_type:
                    available.append(s)
        return available

    def reassign_slot_due_to_hazard(self, plate):
        """Reubica un vehículo de un slot descubierto a uno cubierto por contingencia de granizo."""
        slots = self.state.get("slots", [])
        current_slot = None
        for s in slots:
            if s.get("assigned_plate") == plate:
                current_slot = s
                break
        
        if not current_slot:
            return False, None, None
            
        # Si ya está techado, no requiere reubicación
        if current_slot["type"] == "covered":
            return True, current_slot["slot_id"], current_slot["slot_id"]
            
        # Encontrar una cochera techada disponible (puede ser en corta o valet)
        available_covered = [s for s in slots if s["type"] == "covered" and s["status"] == "available"]
        if not available_covered:
            return False, current_slot["slot_id"], None
            
        new_slot = available_covered[0]
        
        # Actualizar estado de las cocheras
        current_slot["status"] = "available"
        current_slot["assigned_plate"] = None
        
        new_slot["status"] = "reserved"
        new_slot["assigned_plate"] = plate
        
        # Actualizar sector del vehículo en simulated_cars
        old_sector = None
        for car in self.state.get("simulated_cars", []):
            if car["plate"] == plate:
                old_sector = car["sector"]
                car["sector"] = new_slot["sector"]
                car["assigned_slot"] = new_slot["slot_id"]
                break
                
        db.log_incident(
            "SPACE_REASIGNACION",
            f"Space Agent: Reubicó el vehículo {plate} desde plaza {current_slot['slot_id']} ({old_sector}) a plaza techada {new_slot['slot_id']} ({new_slot['sector']})."
        )
        return True, current_slot["slot_id"], new_slot["slot_id"]


class PricingAgent:
    def __init__(self, state):
        self.state = state
        self.semantic = db.load_semantic_memory()

    def recalculate_tariffs(self):
        """Recalcula las tarifas dinámicas basadas en ocupación y clima."""
        weather = self.state.get("weather", "DESPEJADO")
        slots = self.state.get("parking_slots", {})
        tariffs = self.state.get("current_tariffs", {})
        weather_alert = self.state.get("weather_alert")
        
        # Reglas de negocio desde la memoria semántica
        rules = self.semantic.get("pricing_rules", {})
        sectors_config = self.semantic.get("airport", {}).get("sectors", {})
        
        # Ajuste por clima
        weather_multiplier = 1.0
        if weather == "LLUVIA":
            weather_multiplier += rules.get("base_increase_on_rain", 0.10)
        elif weather == "NIEBLA":
            weather_multiplier += rules.get("base_increase_on_fog", 0.25)
            
        tariffs_updated = False

        # Si hay alerta de granizo, Pricing Agent aprueba bonificación de upgrade de emergencia
        if weather_alert == "HAIL":
            db.log_incident(
                "PRICING_UPGRADE_BONIF",
                "Pricing Agent: Alerta de granizo activa. Aprobado descuento del 100% para upgrades de emergencia a techado."
            )

        for sector, config in sectors_config.items():
            base_price = config.get("base_price_hour", (config["min_price"] + config["max_price"]) // 2)
            
            # Ocupación del sector
            occupied = slots[sector]["occupied"]
            capacity = slots[sector]["capacity"]
            occupancy_rate = occupied / capacity if capacity > 0 else 0
            
            # Multiplicador por ocupación
            occupancy_multiplier = 1.0
            if occupancy_rate > rules.get("occupancy_threshold_high", 0.85):
                occupancy_multiplier = 1.30  # +30% por alta ocupación
            elif occupancy_rate < 0.40:
                occupancy_multiplier = 0.90  # -10% para incentivar demanda

            # Precio final calculado
            new_price = int(base_price * weather_multiplier * occupancy_multiplier)
            new_price = min(max(new_price, config["min_price"]), config["max_price"])
            new_price = (new_price // 10) * 10 # Redondeo limpio

            old_price = tariffs.get(sector, base_price)
            if old_price != new_price:
                tariffs[sector] = new_price
                tariffs_updated = True
                reason = f"Ajuste por clima ({weather}) y ocupación ({(occupancy_rate*100):.1f}%)"
                db.log_tariff_change(sector, new_price, reason)
                db.log_incident(
                    "PRECIO_CAMBIO",
                    f"Tarifa de {sector.upper()} actualizada de ${old_price} a ${new_price}. Razón: {reason}."
                )

        return tariffs_updated


class UXAgent:
    def __init__(self, state):
        self.state = state

    def get_reservation_confirmation_message(self, car):
        """Genera el mensaje de confirmación de reserva con QR y ubicación del slot."""
        slot_id = car.get("assigned_slot", "--")
        sector = car.get("sector", "corta").upper()
        piso = "Nivel 1 (Techado)" if car.get("sector") in ["corta", "valet"] else "Planta Baja (Descubierto)"
        return (
            f"¡Reserva Confirmada! Tu plaza {slot_id} te espera en {piso} en el sector {sector}. "
            f"Presenta este código QR en las barreras para ingresar: [QR_{car['plate']}_ACCESO]. "
            f"Ubicación en mapa: https://aeropark.ai/map/{slot_id}"
        )

    def get_hail_relocation_message(self, car, old_slot_id, new_slot_id):
        """Genera el mensaje de WhatsApp avisando sobre el resguardo preventivo por granizo."""
        return (
            f"⚠️ ALERTA METEOROLÓGICA (Granizo) detectada en Aeroparque.\n\n"
            f"Hola {car['owner_name']}. Para resguardar tu vehículo, el Space Agent lo ha reubicado "
            f"preventivamente de la plaza descubierta {old_slot_id} a la plaza techada de contingencia {new_slot_id}. "
            f"Esta acción cuenta con una bonificación del 100% (Upgrade sin cargo). Tu vehículo ya está protegido."
        )

    def check_and_notify_passengers(self):
        """Busca pasajeros estacionados cuyos vuelos estén demorados y los notifica por WhatsApp."""
        notifications_sent = 0
        cars = self.state.get("simulated_cars", [])
        flights = self.state.get("active_flights", [])
        
        # Mapear estados de vuelos
        flight_status = {f["id"]: f["status"] for f in flights}
        flight_etas = {f["id"]: f["eta"] for f in flights}
        
        for car in cars:
            fid = car["flight_id"]
            status = flight_status.get(fid, "A TIEMPO")
            eta = flight_etas.get(fid, "--:--")
            
            # Si el vuelo está demorado o cancelado y no lo hemos notificado todavía
            if status in ["DEMORADO", "CANCELADO"] and not car.get("notified", False):
                car["notified"] = True
                car["status"] = "ALERTADO"
                
                # Crear propuesta de extensión
                phone = car["owner_phone"]
                msg_body = (
                    f"Hola {car['owner_name']}. Detectamos que tu vuelo {fid} "
                    f"está {status.lower()} (Nueva hora est. de arribo: {eta}). "
                    f"Para tu tranquilidad, te ofrecemos congelar tu tarifa excedente con "
                    f"un 40% de descuento. ¿Querés extender tu reserva en el sector {car['sector'].upper()}? "
                    f"[Aceptar] / [Rechazar]"
                )
                db.log_chat_message(phone, "SYSTEM", msg_body)
                notifications_sent += 1
                
                db.log_incident(
                    "UX_NOTIFICACION",
                    f"WhatsApp enviado a {car['owner_name']} ({phone}) ofreciendo extensión por demora en vuelo {fid}."
                )
                
        return notifications_sent > 0

    def process_passenger_reply(self, phone, reply):
        """Procesa la respuesta del usuario en el chat de WhatsApp."""
        cars = self.state.get("simulated_cars", [])
        target_car = None
        
        for car in cars:
            if car["owner_phone"] == phone:
                target_car = car
                break
                
        if not target_car:
            return "No se encontró ningún vehículo registrado con ese número de teléfono."

        reply_clean = reply.strip().upper()
        db.log_chat_message(phone, "CLIENT", reply)
        
        if "ACEPTAR" in reply_clean or "SI" in reply_clean:
            target_car["status"] = "EXTENDIDO"
            # Extender la salida programada teóricamente 3 horas
            try:
                exit_dt = datetime.strptime(target_car["scheduled_exit"], "%H:%M")
                new_exit_dt = exit_dt + timedelta(hours=3)
                target_car["scheduled_exit"] = new_exit_dt.strftime("%H:%M")
            except Exception:
                target_car["scheduled_exit"] = "19:30"  # Fallback

            response_msg = (
                f"¡Perfecto! Hemos extendido tu estadía hasta las {target_car['scheduled_exit']} "
                f"con tarifa bonificada. Tu auto seguirá seguro en el sector {target_car['sector'].upper()}."
            )
            db.log_chat_message(phone, "SYSTEM", response_msg)
            db.log_incident(
                "UX_ACEPTACION",
                f"Pasajero {target_car['owner_name']} aceptó extensión. Salida prorrogada a las {target_car['scheduled_exit']}."
            )
            return response_msg
            
        elif "RECHAZAR" in reply_clean or "NO" in reply_clean:
            target_car["status"] = "RECHAZADO"
            response_msg = (
                "Entendido. No se aplicará el descuento y se calculará la tarifa por hora normal "
                "vigente al momento de tu salida."
            )
            db.log_chat_message(phone, "SYSTEM", response_msg)
            db.log_incident(
                "UX_RECHAZO",
                f"Pasajero {target_car['owner_name']} rechazó extensión. Se aplicará tarifa estándar."
            )
            return response_msg
        else:
            response_msg = "Respuesta no reconocida. Por favor responde 'Aceptar' o 'Rechazar'."
            db.log_chat_message(phone, "SYSTEM", response_msg)
            return response_msg
