const DEFAULT_RENDER_BACKEND = "https://tu-backend-aeropark-dashboard.onrender.com";

function getApiBaseUrl() {
    const saved = localStorage.getItem("aeropark_backend_url");
    if (saved && saved.trim()) {
        let clean = saved.trim();
        if (clean.endsWith("/")) clean = clean.slice(0, -1);
        if (!clean.endsWith("/api")) clean += "/api";
        return clean;
    }
    if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" || window.location.protocol === "file:") {
        return "http://127.0.0.1:8000/api";
    }
    return `${DEFAULT_RENDER_BACKEND}/api`;
}

let API_BASE = getApiBaseUrl();

function setCustomBackendUrl(url) {
    if (url) {
        localStorage.setItem("aeropark_backend_url", url);
    } else {
        localStorage.removeItem("aeropark_backend_url");
    }
    API_BASE = getApiBaseUrl();
    fetchStatus();
}

window.configureApiBackendUrl = () => {
    const current = localStorage.getItem("aeropark_backend_url") || "";
    const input = prompt("Ingresá la URL de tu backend de Render.com (ejemplo: https://tu-backend.onrender.com):", current);
    if (input !== null) {
        setCustomBackendUrl(input.trim());
        alert("URL del Backend configurada exitosamente: " + API_BASE);
    }
};

let currentSelectedPhone = "";
let isBackendConnected = true;
let pollingInterval = null;

let currentSlots = [];
let selectedSlotId = null;


document.addEventListener("DOMContentLoaded", () => {
    checkSession();
    setupEventListeners();
});

function clearAuthInputs() {
    const inputIds = [
        "login-username", "login-password",
        "register-username", "register-password", "register-password-confirm",
        "recover-username", "recover-password", "recover-password-confirm"
    ];
    inputIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = "";
    });

    const msgIds = [
        "login-error-msg", "login-success-msg",
        "register-error-msg", "register-success-msg",
        "recover-error-msg", "recover-success-msg"
    ];
    msgIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.style.display = "none";
            el.textContent = "";
        }
    });
}

function checkSession() {
    const user = localStorage.getItem("aeropark_user");
    const overlay = document.getElementById("auth-overlay");
    const profile = document.getElementById("user-profile-display");
    const logoutBtn = document.getElementById("btn-logout");
    const btnOpenBooking = document.getElementById("btn-open-booking");
    
    if (user) {
        overlay.classList.add("hidden");
        profile.style.display = "flex";
        document.getElementById("username-span").textContent = user;
        logoutBtn.style.display = "inline-block";
        if (btnOpenBooking) btnOpenBooking.style.display = "inline-block";
        
        initApp();
        if (!pollingInterval) {
            pollingInterval = setInterval(fetchStatus, 2500);
        }
        renderUserProfile(user);
    } else {
        overlay.classList.remove("hidden");
        profile.style.display = "none";
        logoutBtn.style.display = "none";
        if (btnOpenBooking) btnOpenBooking.style.display = "none";
        clearAuthInputs();
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
    }
}

async function initApp() {
    await fetchStatus();
    
    // Seleccionar por defecto el primer usuario de la lista si hay alguno
    const selectUser = document.getElementById("select-user");
    if (selectUser && selectUser.options.length > 0) {
        currentSelectedPhone = selectUser.value;
        await fetchChatLogs(currentSelectedPhone);
    }
}

async function renderUserProfile(username) {
    if (!username) return;
    const tabContainer = document.getElementById("user-profile-tab-card");
    const modalContainer = document.getElementById("modal-profile-body");

    try {
        const res = await fetch(`${API_BASE}/user/profile/${username}`);
        if (!res.ok) return;
        const data = await res.json();
        const profile = data.profile || { username, active_reservations: [], total_reservations: 0 };
        
        let reservationsHtml = "";
        if (profile.active_reservations.length === 0) {
            reservationsHtml = `<div class="profile-no-res" style="text-align: center; color: var(--color-text-secondary); padding: 20px; background: rgba(255,255,255,0.02); border-radius: 8px; border: 1px dashed var(--border-color);">
                No tenés reservas activas registradas en este momento.
            </div>`;
        } else {
            reservationsHtml = profile.active_reservations.map(res => `
                <div class="profile-res-card" style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: 8px; padding: 14px; margin-bottom: 10px;">
                    <div class="profile-res-header" style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span class="badge active" style="font-weight: 600;">🚗 Patente: ${res.plate}</span>
                        <span class="badge badge-tiempo">Sector ${res.sector.toUpperCase()} (${res.assigned_slot})</span>
                    </div>
                    <div class="profile-res-details" style="font-size: 13px; color: var(--color-text-secondary); display: grid; grid-template-columns: 1fr 1fr; gap: 6px;">
                        <p><strong>Pasajero:</strong> ${res.owner_name}</p>
                        <p><strong>Teléfono:</strong> ${res.owner_phone}</p>
                        <p><strong>Vuelo Regreso:</strong> ${res.flight_id}</p>
                        <p><strong>Horario:</strong> ${res.entry_time} hs - ${res.scheduled_exit} hs</p>
                    </div>
                </div>
            `).join("");
        }

        const profileContentHtml = `
            <div class="profile-summary" style="display: flex; align-items: center; gap: 16px; margin-bottom: 20px; padding: 16px; background: rgba(59, 130, 246, 0.05); border-radius: 12px; border: 1px solid rgba(59, 130, 246, 0.15);">
                <div class="profile-avatar" style="font-size: 38px; background: rgba(255,255,255,0.1); width: 60px; height: 60px; display: flex; align-items: center; justify-content: center; border-radius: 50%;">👤</div>
                <div class="profile-user-info">
                    <h3 style="margin: 0; font-size: 20px; font-weight: 700;">${profile.username.toUpperCase()}</h3>
                    <span style="color: var(--color-success); font-size: 12px; font-weight: 500;">● Usuario Autenticado</span>
                    <p style="margin: 4px 0 0 0; font-size: 13px; color: var(--color-text-secondary);">Reservas en el sistema: <strong>${profile.total_reservations}</strong></p>
                </div>
            </div>
            <div class="profile-reservations-section">
                <h4 style="margin-bottom: 12px; font-size: 15px;">Tus Reservas de Estacionamiento</h4>
                ${reservationsHtml}
            </div>
        `;

        if (tabContainer) tabContainer.innerHTML = profileContentHtml;
        if (modalContainer) modalContainer.innerHTML = profileContentHtml;
    } catch (err) {
        console.error("Error al obtener perfil:", err);
    }
}

function setupEventListeners() {
    // 1. Selector de Clima
    const weatherButtons = document.querySelectorAll(".btn-weather");
    weatherButtons.forEach(button => {
        button.addEventListener("click", async () => {
            const weather = button.getAttribute("data-weather");
            try {
                const res = await fetch(`${API_BASE}/simulate/weather`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ weather })
                });
                if (res.ok) {
                    await fetchStatus();
                }
            } catch (err) {
                console.error("Error al simular clima:", err);
            }
        });
    });

    // 2. Selector de Pasajero
    const selectUser = document.getElementById("select-user");
    selectUser.addEventListener("change", async (e) => {
        currentSelectedPhone = e.target.value;
        await fetchChatLogs(currentSelectedPhone);
    });

    // 3. Enviar Mensaje de Chat
    const btnSendChat = document.getElementById("btn-send-chat");
    const chatInput = document.getElementById("chat-input");
    
    const sendChatMessage = async () => {
        const message = chatInput.value.trim();
        if (!message || !currentSelectedPhone) return;
        
        chatInput.value = "";
        try {
            const res = await fetch(`${API_BASE}/ux/reply`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ phone: currentSelectedPhone, message })
            });
            if (res.ok) {
                await fetchStatus();
                await fetchChatLogs(currentSelectedPhone);
            }
        } catch (err) {
            console.error("Error al enviar mensaje:", err);
        }
    };

    btnSendChat.addEventListener("click", sendChatMessage);
    chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendChatMessage();
    });

    // 4. Acciones Rápidas (Aceptar / Rechazar)
    const quickButtons = document.querySelectorAll(".btn-quick");
    quickButtons.forEach(button => {
        button.addEventListener("click", async () => {
            const message = button.getAttribute("data-reply");
            if (!currentSelectedPhone) return;
            try {
                const res = await fetch(`${API_BASE}/ux/reply`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ phone: currentSelectedPhone, message })
                });
                if (res.ok) {
                    await fetchStatus();
                    await fetchChatLogs(currentSelectedPhone);
                }
            } catch (err) {
                console.error("Error en respuesta rápida:", err);
            }
        });
    });

    // 5. Reiniciar Datos
    const btnReset = document.getElementById("btn-reset");
    btnReset.addEventListener("click", async () => {
        if (confirm("¿Estás seguro de que querés reiniciar el simulador a los valores de fábrica? Se borrará la base de datos episódica.")) {
            try {
                const res = await fetch(`${API_BASE}/reset`, { method: "POST" });
                if (res.ok) {
                    alert("Simulador reiniciado correctamente.");
                    currentSelectedPhone = "";
                    await initApp();
                }
            } catch (err) {
                console.error("Error al reiniciar app:", err);
            }
        }
    });

    // 6. Pestañas de Memoria y Perfil
    const tabButtons = document.querySelectorAll(".tab-btn");
    tabButtons.forEach(button => {
        button.addEventListener("click", async () => {
            tabButtons.forEach(b => b.classList.remove("active"));
            button.classList.add("active");
            
            const tabId = button.getAttribute("data-tab");
            const tabContents = document.querySelectorAll(".tab-content");
            tabContents.forEach(c => c.classList.remove("active"));
            document.getElementById(`tab-${tabId}`).classList.add("active");

            if (tabId === "profile") {
                const user = localStorage.getItem("aeropark_user");
                if (user) await renderUserProfile(user);
            }
        });
    });

    // 7. Toggle entre Login, Registro y Recuperación de Contraseña
    const linkShowRegister = document.getElementById("link-show-register");
    const linkShowLogin = document.getElementById("link-show-login");
    const linkShowRecover = document.getElementById("link-show-recover");
    const linkRecoverShowLogin = document.getElementById("link-recover-show-login");
    
    const formLogin = document.getElementById("form-login");
    const formRegister = document.getElementById("form-register");
    const formRecover = document.getElementById("form-recover");
    const authSubtitle = document.getElementById("auth-subtitle");

    if (linkShowRegister) {
        linkShowRegister.addEventListener("click", (e) => {
            e.preventDefault();
            clearAuthInputs();
            formLogin.style.display = "none";
            if (formRecover) formRecover.style.display = "none";
            formRegister.style.display = "flex";
            authSubtitle.textContent = "Crea una cuenta para registrarte";
        });
    }

    if (linkShowLogin) {
        linkShowLogin.addEventListener("click", (e) => {
            e.preventDefault();
            clearAuthInputs();
            formRegister.style.display = "none";
            if (formRecover) formRecover.style.display = "none";
            formLogin.style.display = "flex";
            authSubtitle.textContent = "Iniciar sesión para acceder al panel";
        });
    }

    if (linkShowRecover) {
        linkShowRecover.addEventListener("click", (e) => {
            e.preventDefault();
            clearAuthInputs();
            formLogin.style.display = "none";
            formRegister.style.display = "none";
            if (formRecover) formRecover.style.display = "flex";
            authSubtitle.textContent = "Restablece tu contraseña";
        });
    }

    if (linkRecoverShowLogin) {
        linkRecoverShowLogin.addEventListener("click", (e) => {
            e.preventDefault();
            clearAuthInputs();
            if (formRecover) formRecover.style.display = "none";
            formRegister.style.display = "none";
            formLogin.style.display = "flex";
            authSubtitle.textContent = "Iniciar sesión para acceder al panel";
        });
    }

    // 8. Envío de Formulario de Login
    formLogin.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = document.getElementById("login-username").value.trim();
        const password = document.getElementById("login-password").value;
        const errorMsg = document.getElementById("login-error-msg");
        const successMsg = document.getElementById("login-success-msg");
        
        if (errorMsg) errorMsg.style.display = "none";
        if (successMsg) successMsg.style.display = "none";
        
        try {
            const res = await fetch(`${API_BASE}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            });
            const data = await res.json();
            
            if (res.ok) {
                localStorage.setItem("aeropark_user", data.username);
                checkSession();
            } else {
                if (errorMsg) {
                    errorMsg.textContent = data.detail || "Usuario o contraseña incorrectos.";
                    errorMsg.style.display = "block";
                }
            }
        } catch (err) {
            if (errorMsg) {
                errorMsg.textContent = "No se pudo conectar con el servidor.";
                errorMsg.style.display = "block";
            }
        }
    });

    // 9. Envío de Formulario de Registro
    if (formRegister) {
        formRegister.addEventListener("submit", async (e) => {
            e.preventDefault();
            const username = document.getElementById("register-username").value.trim();
            const password = document.getElementById("register-password").value;
            const confirmPassword = document.getElementById("register-password-confirm").value;
            const errorMsg = document.getElementById("register-error-msg");
            const successMsg = document.getElementById("register-success-msg");
            
            if (errorMsg) errorMsg.style.display = "none";
            if (successMsg) successMsg.style.display = "none";
            
            if (password !== confirmPassword) {
                if (errorMsg) {
                    errorMsg.textContent = "Las contraseñas no coinciden.";
                    errorMsg.style.display = "block";
                }
                return;
            }
            
            try {
                const res = await fetch(`${API_BASE}/auth/register`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username, password })
                });
                const data = await res.json();
                
                if (res.ok) {
                    if (successMsg) {
                        successMsg.textContent = "¡Cuenta creada con éxito! Redirigiendo al inicio de sesión...";
                        successMsg.style.display = "block";
                    }
                    const createdUser = username;
                    setTimeout(() => {
                        clearAuthInputs();
                        formRegister.style.display = "none";
                        if (formRecover) formRecover.style.display = "none";
                        formLogin.style.display = "flex";
                        authSubtitle.textContent = "Iniciar sesión para acceder al panel";
                        
                        const loginUserInput = document.getElementById("login-username");
                        if (loginUserInput) loginUserInput.value = createdUser;
                        
                        const loginSuccessMsg = document.getElementById("login-success-msg");
                        if (loginSuccessMsg) {
                            loginSuccessMsg.textContent = `¡Cuenta '${createdUser}' creada con éxito! Por favor ingresá tu contraseña.`;
                            loginSuccessMsg.style.display = "block";
                        }
                        const loginPassInput = document.getElementById("login-password");
                        if (loginPassInput) loginPassInput.focus();
                    }, 1200);
                } else {
                    if (errorMsg) {
                        errorMsg.textContent = data.detail || "Error al registrarse.";
                        errorMsg.style.display = "block";
                    }
                }
            } catch (err) {
                if (errorMsg) {
                    errorMsg.textContent = "No se pudo conectar con el servidor.";
                    errorMsg.style.display = "block";
                }
            }
        });
    }

    // 10. Envío de Formulario de Recuperación de Contraseña
    if (formRecover) {
        formRecover.addEventListener("submit", async (e) => {
            e.preventDefault();
            const username = document.getElementById("recover-username").value.trim();
            const newPassword = document.getElementById("recover-password").value;
            const confirmPassword = document.getElementById("recover-password-confirm").value;
            const errorMsg = document.getElementById("recover-error-msg");
            const successMsg = document.getElementById("recover-success-msg");

            if (errorMsg) errorMsg.style.display = "none";
            if (successMsg) successMsg.style.display = "none";

            if (newPassword !== confirmPassword) {
                if (errorMsg) {
                    errorMsg.textContent = "Las contraseñas no coinciden.";
                    errorMsg.style.display = "block";
                }
                return;
            }

            try {
                const res = await fetch(`${API_BASE}/auth/reset-password`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username, new_password: newPassword })
                });
                const data = await res.json();

                if (res.ok) {
                    if (successMsg) {
                        successMsg.textContent = "¡Contraseña restablecida con éxito! Redirigiendo al inicio de sesión...";
                        successMsg.style.display = "block";
                    }
                    const resetUser = username;
                    setTimeout(() => {
                        clearAuthInputs();
                        formRecover.style.display = "none";
                        formLogin.style.display = "flex";
                        authSubtitle.textContent = "Iniciar sesión para acceder al panel";
                        
                        const loginUserInput = document.getElementById("login-username");
                        if (loginUserInput) loginUserInput.value = resetUser;
                        
                        const loginSuccessMsg = document.getElementById("login-success-msg");
                        if (loginSuccessMsg) {
                            loginSuccessMsg.textContent = "Contraseña restablecida. Podés ingresar ahora.";
                            loginSuccessMsg.style.display = "block";
                        }
                        const loginPassInput = document.getElementById("login-password");
                        if (loginPassInput) loginPassInput.focus();
                    }, 1200);
                } else {
                    if (errorMsg) {
                        errorMsg.textContent = data.detail || "No se pudo restablecer la contraseña.";
                        errorMsg.style.display = "block";
                    }
                }
            } catch (err) {
                if (errorMsg) {
                    errorMsg.textContent = "No se pudo conectar con el servidor.";
                    errorMsg.style.display = "block";
                }
            }
        });
    }

    // 11. Botón de Cerrar Sesión
    const btnLogout = document.getElementById("btn-logout");
    if (btnLogout) {
        btnLogout.addEventListener("click", () => {
            localStorage.removeItem("aeropark_user");
            checkSession();
            // Limpiar visor de memoria
            document.getElementById("json-working-memory").textContent = "";
            document.getElementById("table-episodic-body").innerHTML = "";
            const profileTabCard = document.getElementById("user-profile-tab-card");
            if (profileTabCard) profileTabCard.innerHTML = "";
        });
    }

    // 12. Modal de Perfil al hacer clic en el nombre de usuario
    const userProfileDisplay = document.getElementById("user-profile-display");
    const profileModal = document.getElementById("profile-modal");
    const btnCloseProfile = document.getElementById("btn-close-profile");

    if (userProfileDisplay) {
        userProfileDisplay.addEventListener("click", async () => {
            const user = localStorage.getItem("aeropark_user");
            if (user && profileModal) {
                profileModal.style.display = "flex";
                await renderUserProfile(user);
            }
        });
    }

    if (btnCloseProfile) {
        btnCloseProfile.addEventListener("click", () => {
            if (profileModal) profileModal.style.display = "none";
        });
    }

    // 13. Botones de Simulación Escenarios A, B, C
    const btnSimA = document.getElementById("btn-sim-a");
    if (btnSimA) {
        btnSimA.addEventListener("click", async () => {
            try {
                const res = await fetch(`${API_BASE}/simulate/scenario-a`, { method: "POST" });
                if (res.ok) await fetchStatus();
            } catch (err) {
                console.error("Error al ejecutar simulación A:", err);
            }
        });
    }

    const btnSimB = document.getElementById("btn-sim-b");
    if (btnSimB) {
        btnSimB.addEventListener("click", async () => {
            try {
                const res = await fetch(`${API_BASE}/simulate/scenario-b`, { method: "POST" });
                if (res.ok) await fetchStatus();
            } catch (err) {
                console.error("Error al ejecutar simulación B:", err);
            }
        });
    }

    const btnSimC = document.getElementById("btn-sim-c");
    if (btnSimC) {
        btnSimC.addEventListener("click", async () => {
            try {
                const res = await fetch(`${API_BASE}/simulate/scenario-c`, { method: "POST" });
                if (res.ok) {
                    await fetchStatus();
                    alert("Simulación C (Granizo en Vivo) ejecutada con éxito.\nEl auto de Valeria Gómez en Larga Estadía ha sido reubicado preventivamente a una plaza techada de contingencia con bonificación del 100%.");
                }
            } catch (err) {
                console.error("Error al ejecutar simulación C:", err);
            }
        });
    }

    // 14. Abrir Modal de Reserva (Desde Header o Hero Banner)
    const btnOpenBooking = document.getElementById("btn-open-booking");
    const btnHeroBooking = document.getElementById("btn-hero-booking");

    const openBookingModalHandler = () => {
        document.getElementById("booking-modal").style.display = "flex";
        const loggedUser = localStorage.getItem("aeropark_user") || "";
        const nameInput = document.getElementById("book-name");
        if (nameInput && !nameInput.value && loggedUser) {
            nameInput.value = loggedUser.charAt(0).toUpperCase() + loggedUser.slice(1);
        }
        const currentSector = document.getElementById("book-sector").value;
        render2DSlotsGrid(currentSector);
    };

    if (btnOpenBooking) btnOpenBooking.addEventListener("click", openBookingModalHandler);
    if (btnHeroBooking) btnHeroBooking.addEventListener("click", openBookingModalHandler);

    // 15. Cerrar Modales
    const btnCloseBooking = document.getElementById("btn-close-booking");
    if (btnCloseBooking) {
        btnCloseBooking.addEventListener("click", () => {
            document.getElementById("booking-modal").style.display = "none";
        });
    }

    const btnCloseUpgrade = document.getElementById("btn-close-upgrade");
    if (btnCloseUpgrade) {
        btnCloseUpgrade.addEventListener("click", () => {
            document.getElementById("upgrade-modal").style.display = "none";
        });
    }

    // 16. Cambiar de sector en modal actualiza la grilla de slots
    const bookSector = document.getElementById("book-sector");
    if (bookSector) {
        bookSector.addEventListener("change", (e) => {
            selectedSlotId = null;
            render2DSlotsGrid(e.target.value);
        });
    }

    // 17. Botón Auto-seleccionar Cochera Libre
    const btnAutoSelectSlot = document.getElementById("btn-auto-select-slot");
    if (btnAutoSelectSlot) {
        btnAutoSelectSlot.addEventListener("click", () => {
            const sector = document.getElementById("book-sector").value;
            const available = currentSlots.filter(s => s.sector === sector && s.status === "available");
            if (available.length > 0) {
                selectedSlotId = available[0].slot_id;
                render2DSlotsGrid(sector);
            } else {
                alert("No hay cocheras libres disponibles en este sector.");
            }
        });
    }

    // 18. Confirmar Reserva y manejar alerta preventiva de granizo
    const formBooking = document.getElementById("form-booking");
    if (formBooking) {
        formBooking.addEventListener("submit", async (e) => {
            e.preventDefault();
            
            if (!selectedSlotId) {
                alert("Por favor selecciona una cochera de la grilla 2D.");
                return;
            }
            
            const name = document.getElementById("book-name").value;
            const phone = document.getElementById("book-phone").value;
            const plate = document.getElementById("book-plate").value;
            const flight = document.getElementById("book-flight").value;
            const entry = document.getElementById("book-entry").value;
            const exit = document.getElementById("book-exit").value;
            const sector = document.getElementById("book-sector").value;
            
            // Si el sector es descubierto (larga) y hay alerta de granizo o clima de lluvia/niebla activo
            const currentWeather = document.getElementById("current-weather-badge").textContent;
            
            if (sector === "larga" && (currentWeather === "LLUVIA" || currentWeather === "NIEBLA")) {
                openUpgradeModal({
                    owner_name: name,
                    owner_phone: phone,
                    plate,
                    flight_id: flight,
                    entry_time: entry,
                    scheduled_exit: exit,
                    sector,
                    slot_id: selectedSlotId
                });
                return;
            }
            
            await sendReservation({
                owner_name: name,
                owner_phone: phone,
                plate,
                flight_id: flight,
                entry_time: entry,
                scheduled_exit: exit,
                sector,
                slot_id: selectedSlotId
            });
        });
    }
}

async function fetchStatus() {
    try {
        const res = await fetch(`${API_BASE}/status`);
        if (!res.ok) throw new Error("Backend response error");
        
        const data = await res.json();
        isBackendConnected = true;
        
        // Guardar cocheras globalmente
        currentSlots = data.working_memory.slots || [];
        
        // Actualizar Cartelera LED
        const ledSign = document.getElementById("led-sign-display");
        if (ledSign) {
            ledSign.textContent = data.working_memory.led_sign || "BIENVENIDOS A AEROPARK AI";
        }
        
        // Si el modal de reserva está abierto, actualizar grilla en vivo manteniendo seleccion
        const bookingModal = document.getElementById("booking-modal");
        if (bookingModal && bookingModal.style.display === "flex") {
            render2DSlotsGrid(document.getElementById("book-sector").value);
        }
        
        // Renderizar componentes
        updateWeatherUI(data.working_memory.weather);
        renderFlights(data.working_memory.active_flights);
        renderTariffs(data.tariffs);
        renderSlots(data.working_memory.parking_slots);
        updateUserSelector(data.working_memory.simulated_cars);
        
        // Renderizar Memoria y Perfil
        document.getElementById("json-working-memory").textContent = JSON.stringify(data.working_memory, null, 4);
        document.getElementById("json-semantic-memory").textContent = JSON.stringify(data.semantic_memory, null, 4);
        renderEpisodicMemory(data.incidents);

        const activeTabBtn = document.querySelector(".tab-btn.active");
        if (activeTabBtn && activeTabBtn.getAttribute("data-tab") === "profile") {
            const user = localStorage.getItem("aeropark_user");
            if (user) await renderUserProfile(user);
        }

        // Si tenemos un usuario seleccionado, recargar su chat
        if (currentSelectedPhone) {
            await fetchChatLogs(currentSelectedPhone);
        }

    } catch (err) {
        if (isBackendConnected) {
            console.warn("No se pudo conectar al servidor de Python en localhost:8000");
            isBackendConnected = false;
            showConnectionError();
        }
    }
}

function showConnectionError() {
    const weatherBadge = document.getElementById("current-weather-badge");
    if (weatherBadge) {
        weatherBadge.textContent = "DESCONECTADO";
        weatherBadge.className = "badge badge-cancelado";
    }
    
    const list = document.getElementById("flights-list");
    if (list) {
        list.innerHTML = `<div style="color: var(--color-danger); text-align: center; padding: 15px; font-size: 13px;">
            ⚠️ Servidor Backend no conectado.<br>
            <span style="font-size: 11px; color: var(--color-text-secondary); display: block; margin-top: 4px;">
                Si desplegaste tu backend en Render.com, configurá su URL pública:
            </span>
            <button class="btn btn-primary btn-sm" style="margin-top: 10px; font-size: 12px;" onclick="window.configureApiBackendUrl()">⚙️ Configurar URL de Render</button>
        </div>`;
    }
}


function updateWeatherUI(weather) {
    // Actualizar badge de clima actual
    const badge = document.getElementById("current-weather-badge");
    badge.textContent = weather;
    badge.className = "badge active";
    
    // Activar botón del clima correspondiente
    const buttons = document.querySelectorAll(".btn-weather");
    buttons.forEach(btn => {
        if (btn.getAttribute("data-weather") === weather) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });
}

function renderFlights(flights) {
    const list = document.getElementById("flights-list");
    list.innerHTML = "";
    
    flights.forEach(f => {
        const item = document.createElement("div");
        item.className = "flight-item";
        
        const badgeClass = f.status === "A TIEMPO" ? "badge-tiempo" : 
                           f.status === "DEMORADO" ? "badge-demorado" : "badge-cancelado";
        
        const actionButton = f.status === "A TIEMPO" ? 
            `<button class="btn-simulate-delay" onclick="simulateFlightStatus('${f.id}', 'DEMORADO')">Demorar</button>` :
            `<button class="btn-simulate-delay" style="background: rgba(16, 185, 129, 0.1); color: #34d399; border-color: rgba(16, 185, 129, 0.2);" onclick="simulateFlightStatus('${f.id}', 'A TIEMPO')">A Tiempo</button>`;

        item.innerHTML = `
            <div class="flight-info-left">
                <div class="flight-id-airline">
                    <span class="flight-id">${f.id}</span>
                    <span class="flight-airline">${f.airline}</span>
                </div>
                <span class="flight-route">Procedencia: ${f.origin}</span>
            </div>
            <div class="flight-info-right">
                <span class="flight-eta">${f.eta}</span>
                <span class="badge ${badgeClass}">${f.status}</span>
                ${actionButton}
            </div>
        `;
        list.appendChild(item);
    });
}

async function simulateFlightStatus(flightId, status) {
    try {
        const res = await fetch(`${API_BASE}/simulate/flight-status`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ flight_id: flightId, status })
        });
        if (res.ok) {
            await fetchStatus();
        }
    } catch (err) {
        console.error("Error al simular estado de vuelo:", err);
    }
}

// Vinculamos la función global para que los clicks inline en el HTML funcionen
window.simulateFlightStatus = simulateFlightStatus;

function renderTariffs(tariffs) {
    const grid = document.getElementById("tariffs-grid");
    grid.innerHTML = "";
    
    if (!tariffs) return;

    Object.keys(tariffs).forEach(sector => {
        const item = document.createElement("div");
        item.className = `tariff-item ${sector}`;
        item.innerHTML = `
            <div class="tariff-label">${sector === "corta" ? "Corta Estadía" : sector === "larga" ? "Larga Estadía" : "Valet Parking"}</div>
            <div class="tariff-price">$${tariffs[sector]}</div>
            <div class="subtitle" style="font-size: 9px;">ARS / hora</div>
        `;
        grid.appendChild(item);
    });
}

function renderSlots(slots) {
    const container = document.getElementById("slots-container");
    container.innerHTML = "";
    
    if (!slots) return;

    Object.keys(slots).forEach(sector => {
        const s = slots[sector];
        const pct = Math.round((s.occupied / s.capacity) * 100);
        
        let barColor = "var(--color-success)";
        if (pct >= 85) {
            barColor = "var(--color-danger)";
        } else if (pct >= 70) {
            barColor = "var(--color-warning)";
        }
        
        const row = document.createElement("div");
        row.className = "slot-row";
        row.innerHTML = `
            <div class="slot-meta">
                <span class="slot-name">${sector === "corta" ? "Corta Estadía" : sector === "larga" ? "Larga Estadía" : "Valet Parking"}</span>
                <span class="slot-nums">${s.occupied} / ${s.capacity} plazas (${pct}%)</span>
            </div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width: ${pct}%; background-color: ${barColor};"></div>
            </div>
            <div class="slot-sim-buttons">
                <button class="btn" onclick="simulateCarEvent('${sector}', 'entry')">Ingreso (+)</button>
                <button class="btn" onclick="simulateCarEvent('${sector}', 'exit')">Salida (-)</button>
            </div>
        `;
        container.appendChild(row);
    });
}

async function simulateCarEvent(sector, type) {
    try {
        const url = type === "entry" ? `${API_BASE}/simulate/car-entry` : `${API_BASE}/simulate/car-exit`;
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ sector })
        });
        if (res.ok) {
            await fetchStatus();
        }
    } catch (err) {
        console.error("Error al simular movimiento de auto:", err);
    }
}

window.simulateCarEvent = simulateCarEvent;

function updateUserSelector(cars) {
    const select = document.getElementById("select-user");
    const previousVal = select.value;
    
    // Guardar opción previa
    select.innerHTML = "";
    
    cars.forEach(car => {
        const option = document.createElement("option");
        option.value = car.owner_phone;
        
        // Agregar distintivo visual si está alertado
        let statusEmoji = "🅿️";
        if (car.status === "ALERTADO") statusEmoji = "⚠️";
        if (car.status === "EXTENDIDO") statusEmoji = "✅";
        if (car.status === "RECHAZADO") statusEmoji = "❌";
        
        option.textContent = `${statusEmoji} ${car.owner_name} (${car.plate}) - ${car.flight_id}`;
        select.appendChild(option);
    });

    if (previousVal && Array.from(select.options).some(o => o.value === previousVal)) {
        select.value = previousVal;
        currentSelectedPhone = previousVal;
    } else if (cars.length > 0) {
        select.value = cars[0].owner_phone;
        currentSelectedPhone = cars[0].owner_phone;
    }
}

async function fetchChatLogs(phone) {
    if (!phone) return;
    try {
        const res = await fetch(`${API_BASE}/ux/chat/${phone}`);
        if (res.ok) {
            const data = await res.json();
            renderChat(data.chat_logs);
        }
    } catch (err) {
        console.error("Error al obtener logs de chat:", err);
    }
}

function renderChat(logs) {
    const container = document.getElementById("chat-messages");
    container.innerHTML = "";
    
    if (logs.length === 0) {
        container.innerHTML = `<div style="text-align: center; color: var(--color-text-secondary); font-size: 11px; padding: 20px;">
            No hay mensajes en este chat. Simulá una demora de vuelo para disparar el mensaje del agente.
        </div>`;
        return;
    }

    logs.forEach(msg => {
        const bubble = document.createElement("div");
        const senderClass = msg.sender === "SYSTEM" ? "system" : "client";
        bubble.className = `chat-bubble ${senderClass}`;
        
        // Limpiar el timestamp para mostrar solo hora
        let timeStr = "";
        try {
            timeStr = msg.timestamp.split(" ")[1].substring(0, 5);
        } catch (e) {
            timeStr = "12:00";
        }

        bubble.innerHTML = `
            ${msg.message}
            <span class="time">${timeStr}</span>
        `;
        container.appendChild(bubble);
    });
    
    // Auto scroll al fondo del chat
    container.scrollTop = container.scrollHeight;
}

function renderEpisodicMemory(incidents) {
    const tbody = document.getElementById("table-episodic-body");
    tbody.innerHTML = "";
    
    if (incidents.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" style="text-align: center;">No hay eventos registrados en la memoria episódica.</td></tr>`;
        return;
    }

    incidents.forEach(inc => {
        const row = document.createElement("tr");
        
        let typeBadge = `<span class="badge" style="background-color: rgba(255, 255, 255, 0.05); color: #fff; border: 1px solid rgba(255, 255, 255, 0.15);">${inc.type}</span>`;
        if (inc.type.includes("PRECIO")) {
            typeBadge = `<span class="badge" style="background-color: rgba(59, 130, 246, 0.15); color: #93c5fd; border: 1px solid rgba(59, 130, 246, 0.3);">${inc.type}</span>`;
        } else if (inc.type.includes("VUELO") || inc.type.includes("CLIMA")) {
            typeBadge = `<span class="badge" style="background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3);">${inc.type}</span>`;
        } else if (inc.type.includes("ACEPTA") || inc.type.includes("INGRESO")) {
            typeBadge = `<span class="badge" style="background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3);">${inc.type}</span>`;
        }

        row.innerHTML = `
            <td style="color: var(--color-text-secondary); white-space: nowrap;">${inc.timestamp}</td>
            <td>${typeBadge}</td>
            <td style="font-weight: 400;">${inc.description}</td>
        `;
        tbody.appendChild(row);
    });
}

// --- Funciones del Slot Selector ---

function render2DSlotsGrid(filterSector = "corta") {
    const gridContainer = document.getElementById("slots-grid-2d");
    if (!gridContainer) return;
    gridContainer.innerHTML = "";
    
    // Filtrar slots por sector
    const filtered = currentSlots.filter(s => s.sector === filterSector);
    
    // Autoseleccionar si no hay o expiró la elección previa
    const isValidSelection = filtered.some(s => s.slot_id === selectedSlotId && s.status === "available");
    if (!isValidSelection) {
        const firstAvailable = filtered.find(s => s.status === "available");
        selectedSlotId = firstAvailable ? firstAvailable.slot_id : null;
    }

    if (filtered.length === 0) {
        gridContainer.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; color: var(--color-text-secondary); padding: 15px;">No hay cocheras en este sector.</div>`;
        return;
    }
    
    filtered.forEach(slot => {
        const slotBox = document.createElement("div");
        slotBox.className = `slot-box type-${slot.type} status-${slot.status}`;
        slotBox.textContent = slot.slot_id;
        
        if (slot.slot_id === selectedSlotId) {
            slotBox.classList.add("selected-slot");
        }
        
        if (slot.status === "available") {
            slotBox.addEventListener("click", () => {
                const prev = gridContainer.querySelector(".selected-slot");
                if (prev) prev.classList.remove("selected-slot");
                
                selectedSlotId = slot.slot_id;
                slotBox.classList.add("selected-slot");
                
                const selectedInfo = document.getElementById("slot-selected-info");
                if (selectedInfo) {
                    selectedInfo.textContent = `Cochera seleccionada: ${slot.slot_id} (${slot.type === 'covered' ? 'Techada' : 'Descubierta'})`;
                }
            });
        } else {
            slotBox.title = "Cochera reservada u ocupada";
        }
        gridContainer.appendChild(slotBox);
    });

    const selectedInfo = document.getElementById("slot-selected-info");
    if (selectedInfo) {
        if (selectedSlotId) {
            const currentObj = filtered.find(s => s.slot_id === selectedSlotId);
            const typeLabel = currentObj ? (currentObj.type === 'covered' ? 'Techada' : 'Descubierta') : '';
            selectedInfo.textContent = `Cochera seleccionada: ${selectedSlotId} (${typeLabel})`;
        } else {
            selectedInfo.textContent = "Ninguna cochera disponible seleccionada en este sector";
        }
    }
}

function openUpgradeModal(bookingData) {
    const upgradeModal = document.getElementById("upgrade-modal");
    upgradeModal.style.display = "flex";
    
    const btnAccept = document.getElementById("btn-accept-upgrade");
    const btnReject = document.getElementById("btn-reject-upgrade");
    
    // Limpiar event listeners viejos mediante clonación
    const newBtnAccept = btnAccept.cloneNode(true);
    const newBtnReject = btnReject.cloneNode(true);
    btnAccept.parentNode.replaceChild(newBtnAccept, btnAccept);
    btnReject.parentNode.replaceChild(newBtnReject, btnReject);
    
    newBtnAccept.addEventListener("click", async () => {
        // Cambiar sector a Corta Estadía (techado)
        bookingData.sector = "corta";
        // Buscar primera cochera techada disponible en corta
        const availableCovered = currentSlots.filter(s => s.sector === "corta" && s.status === "available");
        if (availableCovered.length > 0) {
            bookingData.slot_id = availableCovered[0].slot_id;
        } else {
            alert("No hay slots techados de corta disponibles, se mantendrá el seleccionado.");
        }
        upgradeModal.style.display = "none";
        await sendReservation(bookingData);
    });
    
    newBtnReject.addEventListener("click", async () => {
        upgradeModal.style.display = "none";
        await sendReservation(bookingData);
    });
}

async function sendReservation(bookingData) {
    try {
        const res = await fetch(`${API_BASE}/reserve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(bookingData)
        });
        const data = await res.json();
        if (res.ok) {
            alert(`¡Reserva Exitosa! Se te ha asignado la cochera ${data.car.assigned_slot}. El UX Agent te enviará la confirmación por WhatsApp.`);
            document.getElementById("booking-modal").style.display = "none";
            document.getElementById("form-booking").reset();
            selectedSlotId = null;
            await fetchStatus();
            const user = localStorage.getItem("aeropark_user");
            if (user) await renderUserProfile(user);
        } else {
            alert(data.detail || "Error al realizar la reserva.");
        }
    } catch (err) {
        console.error("Error al procesar reserva:", err);
    }
}
