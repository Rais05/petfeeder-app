/**
 * =============================================================
 *   IoT Pet Feeder — Frontend Application Logic
 *   Built with Vanilla JS | Communicates with FastAPI backend
 * =============================================================
 */

// ─── API Configuration ────────────────────────────────────────
const API_BASE = "http://localhost:8000";

// ─── State ────────────────────────────────────────────────────
let selectedAmount = 50;
let isFeeding = false;
let sseSource = null;
let previousFoodLevel = null;

// ─── Utils ────────────────────────────────────────────────────
async function apiFetch(url, options = {}) {
    try {
        const res = await fetch(`${API_BASE}${url}`, {
            headers: { "Content-Type": "application/json" },
            ...options,
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }
        return await res.json();
    } catch (e) {
        if (e.message.includes("Failed to fetch") || e.message.includes("NetworkError")) {
            throw new Error("Tidak dapat terhubung ke server. Pastikan backend berjalan.");
        }
        throw e;
    }
}

function formatTime(isoString) {
    if (!isoString) return "—";
    try {
        const d = new Date(isoString);
        return d.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
    } catch { return isoString; }
}

function formatDateTime(isoString) {
    if (!isoString) return "—";
    try {
        const d = new Date(isoString);
        return d.toLocaleString("id-ID", {
            day: "2-digit", month: "short", year: "numeric",
            hour: "2-digit", minute: "2-digit",
        });
    } catch { return isoString; }
}

function timeAgo(isoString) {
    if (!isoString) return "—";
    try {
        const diff = Date.now() - new Date(isoString).getTime();
        const mins = Math.floor(diff / 60000);
        if (mins < 1) return "baru saja";
        if (mins < 60) return `${mins} menit lalu`;
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return `${hrs} jam lalu`;
        return `${Math.floor(hrs / 24)} hari lalu`;
    } catch { return isoString; }
}

// ─── Toast Notifications ─────────────────────────────────────
const TOAST_ICONS = { success: "✅", error: "❌", info: "ℹ️", warn: "⚠️" };
function showToast(message, type = "info", duration = 3500) {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${TOAST_ICONS[type]}</span><span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add("toast-fadeout");
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ─── Device Status UI ─────────────────────────────────────────
function updateDeviceStatus(state) {
    const dot = document.getElementById("badge-dot");
    const text = document.getElementById("badge-text");
    const online = state.online === true;

    dot.className = `badge-dot ${online ? "online" : "offline"}`;
    text.textContent = online ? "Online" : "Offline";

    // Food level
    const foodLevel = parseFloat(state.food_level) || 0;
    updateFoodGauge(foodLevel);

    // Stat cards
    document.getElementById("stat-food").textContent =
        foodLevel > 0 ? `${foodLevel.toFixed(0)}%` : "0%";
    document.getElementById("stat-count").textContent =
        state.feeding_count ?? "0";
    document.getElementById("stat-last").textContent =
        state.last_feed ? timeAgo(state.last_feed) : "Belum ada";
    document.getElementById("stat-wifi").textContent =
        state.wifi_rssi ? `${state.wifi_rssi} dBm` : "—";

    // Feeding state
    isFeeding = state.is_feeding === true;
    const feedBtn = document.getElementById("feed-btn");
    if (feedBtn) {
        feedBtn.disabled = isFeeding || !online;
        const btnText = feedBtn.querySelector(".feed-btn-text");
        if (isFeeding) {
            btnText.textContent = "Sedang memberi makan...";
        } else {
            btnText.textContent = "Beri Makan!";
        }
    }

    // Feeding overlay
    document.getElementById("feeding-overlay").style.display =
        isFeeding ? "flex" : "none";
}

function updateFoodGauge(level) {
    const fill = document.getElementById("gauge-fill");
    const label = document.getElementById("gauge-percent");
    const badge = document.getElementById("food-status-badge");
    const warning = document.getElementById("gauge-warning");

    const pct = Math.min(100, Math.max(0, level));
    fill.style.width = `${pct}%`;
    label.textContent = `${pct.toFixed(0)}%`;

    // Color based on level
    fill.classList.remove("danger", "warn");
    if (pct <= 15) {
        fill.classList.add("danger");
        badge.textContent = "Kritis!";
        badge.className = "card-badge danger";
        warning.style.display = "block";
    } else if (pct <= 30) {
        fill.classList.add("warn");
        badge.textContent = "Hampir Habis";
        badge.className = "card-badge warn";
        warning.style.display = "none";
    } else {
        badge.textContent = "Normal";
        badge.className = "card-badge";
        warning.style.display = "none";
    }

    // Trend indicator
    const trend = document.getElementById("food-trend");
    if (previousFoodLevel !== null && trend) {
        if (level < previousFoodLevel) trend.textContent = "▼";
        else if (level > previousFoodLevel) trend.textContent = "▲";
        else trend.textContent = "─";
    }
    previousFoodLevel = level;
}

// ─── Fetch Initial Status ─────────────────────────────────────
async function fetchStatus() {
    try {
        const data = await apiFetch("/api/status");
        updateDeviceStatus(data);
    } catch (e) {
        console.warn("[Status] Error:", e.message);
        document.getElementById("badge-text").textContent = "Server Offline";
        document.getElementById("badge-dot").className = "badge-dot offline";
    }
}

// ─── SSE Real-time Connection ─────────────────────────────────
function connectSSE() {
    if (sseSource) sseSource.close();
    sseSource = new EventSource(`${API_BASE}/api/events`);

    sseSource.onopen = () => {
        console.log("[SSE] Terhubung ke server");
    };

    sseSource.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleSSEMessage(msg);
        } catch (e) {
            console.warn("[SSE] Parse error:", e);
        }
    };

    sseSource.onerror = () => {
        console.warn("[SSE] Koneksi terputus, mencoba lagi dalam 5 detik...");
        sseSource.close();
        setTimeout(connectSSE, 5000);
    };
}

function handleSSEMessage(msg) {
    const { type, data } = msg;

    switch (type) {
        case "connected":
        case "status":
            updateDeviceStatus(data);
            break;

        case "feed":
            showToast(`✅ Makanan ${data.amount}g berhasil diberikan!`, "success");
            loadHistory();
            fetchStatus();
            break;

        case "schedule_added":
            showToast("📅 Jadwal baru ditambahkan", "info");
            loadSchedules();
            break;

        case "schedule_deleted":
            showToast("🗑️ Jadwal dihapus", "info");
            loadSchedules();
            break;

        case "log":
            console.log(`[Device] ${data.message}`);
            break;

        case "heartbeat":
            // Koneksi masih hidup
            break;
    }
}

// ─── Feed Now ─────────────────────────────────────────────────
document.getElementById("feed-btn").addEventListener("click", async () => {
    if (isFeeding) return;

    const btn = document.getElementById("feed-btn");
    const status = document.getElementById("feed-status");
    const overlay = document.getElementById("feeding-overlay");

    btn.disabled = true;
    btn.classList.add("feeding");
    status.textContent = "";
    status.className = "feed-status";
    overlay.style.display = "flex";

    try {
        const res = await apiFetch("/api/feed/now", {
            method: "POST",
            body: JSON.stringify({ amount: selectedAmount }),
        });
        status.textContent = `✅ ${res.message}`;
        showToast(`🐱 Makanan ${selectedAmount}g berhasil diberikan!`, "success", 4000);
        loadHistory();
        setTimeout(fetchStatus, 2000);
    } catch (e) {
        status.textContent = `❌ ${e.message}`;
        status.classList.add("error");
        overlay.style.display = "none";
        showToast(e.message, "error");
    } finally {
        btn.classList.remove("feeding");
        setTimeout(() => {
            btn.disabled = false;
            overlay.style.display = "none";
        }, 2000);
    }
});

// ─── Amount Selector ──────────────────────────────────────────
document.querySelectorAll(".amount-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        selectedAmount = parseInt(btn.dataset.amount);
        document.querySelectorAll(".amount-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById("amount-slider").value = selectedAmount;
        document.getElementById("amount-display").textContent = `${selectedAmount}g`;
    });
});

document.getElementById("amount-slider").addEventListener("input", (e) => {
    selectedAmount = parseInt(e.target.value);
    document.getElementById("amount-display").textContent = `${selectedAmount}g`;
    document.querySelectorAll(".amount-btn").forEach(b => b.classList.remove("active"));
    const matching = document.querySelector(`.amount-btn[data-amount="${selectedAmount}"]`);
    if (matching) matching.classList.add("active");
});

// ─── Schedule Manager ─────────────────────────────────────────
const DAYS_ID = { Mon: "Sen", Tue: "Sel", Wed: "Rab", Thu: "Kam", Fri: "Jum", Sat: "Sab", Sun: "Min" };

document.getElementById("btn-add-schedule").addEventListener("click", () => {
    const form = document.getElementById("schedule-form");
    form.style.display = form.style.display === "none" ? "flex" : "none";
});

document.getElementById("btn-cancel-schedule").addEventListener("click", () => {
    document.getElementById("schedule-form").style.display = "none";
});

document.querySelectorAll(".day-btn").forEach(btn => {
    btn.addEventListener("click", () => btn.classList.toggle("active"));
});

document.getElementById("btn-save-schedule").addEventListener("click", async () => {
    const hour = parseInt(document.getElementById("sch-hour").value);
    const minute = parseInt(document.getElementById("sch-minute").value);
    const amount = parseInt(document.getElementById("sch-amount").value);
    const label = document.getElementById("sch-label").value.trim();

    const activeDays = [...document.querySelectorAll(".day-btn.active")]
        .map(b => b.dataset.day);

    if (isNaN(hour) || isNaN(minute) || isNaN(amount)) {
        showToast("⚠️ Isi semua kolom jadwal dengan benar", "warn");
        return;
    }
    if (activeDays.length === 0) {
        showToast("⚠️ Pilih minimal satu hari", "warn");
        return;
    }

    const saveBtn = document.getElementById("btn-save-schedule");
    saveBtn.disabled = true;
    saveBtn.textContent = "Menyimpan...";

    try {
        await apiFetch("/api/schedule", {
            method: "POST",
            body: JSON.stringify({
                hour, minute, amount,
                label: label || `Jadwal ${hour.toString().padStart(2, "0")}:${minute.toString().padStart(2, "0")}`,
                days: activeDays,
            }),
        });
        document.getElementById("schedule-form").style.display = "none";
        showToast("📅 Jadwal berhasil ditambahkan!", "success");
        loadSchedules();
    } catch (e) {
        showToast(e.message, "error");
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = "💾 Simpan Jadwal";
    }
});

async function loadSchedules() {
    try {
        const data = await apiFetch("/api/schedule");
        renderSchedules(data.schedules || []);
    } catch (e) {
        console.warn("[Schedules] Error:", e.message);
    }
}

function renderSchedules(schedules) {
    const list = document.getElementById("schedule-list");
    const empty = document.getElementById("schedule-empty");

    // Remove old items (keep empty state)
    [...list.children].forEach(ch => { if (!ch.id) ch.remove(); });

    if (schedules.length === 0) {
        empty.style.display = "flex";
        return;
    }
    empty.style.display = "none";

    schedules.forEach(s => {
        if (document.getElementById(`sch-${s.id}`)) return; // already rendered

        const item = document.createElement("div");
        item.className = `schedule-item${s.enabled ? "" : " disabled"}`;
        item.id = `sch-${s.id}`;

        const daysStr = s.days?.map(d => DAYS_ID[d] || d).join(", ") || "Setiap hari";

        item.innerHTML = `
      <div class="sch-time">${String(s.hour).padStart(2, "0")}:${String(s.minute).padStart(2, "0")}</div>
      <div class="sch-info">
        <div class="sch-label">${s.label}</div>
        <div class="sch-meta">${daysStr}</div>
      </div>
      <span class="sch-amount-badge">${s.amount}g</span>
      <div class="sch-actions">
        <button class="sch-btn toggle" title="${s.enabled ? 'Nonaktifkan' : 'Aktifkan'}"
          onclick="toggleSchedule('${s.id}')">${s.enabled ? "⏸" : "▶"}</button>
        <button class="sch-btn delete" title="Hapus"
          onclick="deleteSchedule('${s.id}')">✕</button>
      </div>
    `;
        list.appendChild(item);
    });
}

// Replace full re-render on reload
async function reloadSchedules() {
    try {
        const data = await apiFetch("/api/schedule");
        const list = document.getElementById("schedule-list");
        const empty = document.getElementById("schedule-empty");

        // Remove all dynamic items
        [...list.querySelectorAll(".schedule-item")].forEach(el => el.remove());

        const schedules = data.schedules || [];
        empty.style.display = schedules.length === 0 ? "flex" : "none";

        schedules.forEach(s => {
            const item = document.createElement("div");
            item.className = `schedule-item${s.enabled ? "" : " disabled"}`;
            item.id = `sch-${s.id}`;
            const daysStr = s.days?.map(d => DAYS_ID[d] || d).join(", ") || "Setiap hari";
            item.innerHTML = `
        <div class="sch-time">${String(s.hour).padStart(2, "0")}:${String(s.minute).padStart(2, "0")}</div>
        <div class="sch-info">
          <div class="sch-label">${s.label}</div>
          <div class="sch-meta">${daysStr}</div>
        </div>
        <span class="sch-amount-badge">${s.amount}g</span>
        <div class="sch-actions">
          <button class="sch-btn toggle" title="${s.enabled ? 'Nonaktifkan' : 'Aktifkan'}"
            onclick="toggleSchedule('${s.id}')">${s.enabled ? "⏸" : "▶"}</button>
          <button class="sch-btn delete" title="Hapus"
            onclick="deleteSchedule('${s.id}')">✕</button>
        </div>
      `;
            list.appendChild(item);
        });
    } catch (e) {
        console.warn("[Schedules] Error:", e.message);
    }
}

// Make global for inline onclick
window.deleteSchedule = async function (id) {
    if (!confirm("Hapus jadwal ini?")) return;
    try {
        await apiFetch(`/api/schedule/${id}`, { method: "DELETE" });
        document.getElementById(`sch-${id}`)?.remove();
        showToast("🗑️ Jadwal dihapus", "info");
        reloadSchedules();
    } catch (e) {
        showToast(e.message, "error");
    }
};

window.toggleSchedule = async function (id) {
    try {
        await apiFetch(`/api/schedule/${id}/toggle`, { method: "PATCH" });
        reloadSchedules();
        showToast("📅 Jadwal diperbarui", "info");
    } catch (e) {
        showToast(e.message, "error");
    }
};

// ─── History ──────────────────────────────────────────────────
const TRIGGER_LABELS = {
    manual: ["Manual", "trigger-manual"],
    schedule: ["Jadwal", "trigger-schedule"],
    api: ["API", "trigger-api"],
};
const TRIGGER_ICONS = { manual: "🖐️", schedule: "⏰", api: "🔌" };

async function loadHistory() {
    try {
        const data = await apiFetch("/api/history?limit=20");
        renderHistory(data.history || []);
    } catch (e) {
        console.warn("[History] Error:", e.message);
    }
}

function renderHistory(entries) {
    const list = document.getElementById("history-list");
    const empty = document.getElementById("history-empty");
    list.querySelectorAll(".history-item").forEach(el => el.remove());

    if (entries.length === 0) {
        empty.style.display = "flex";
        return;
    }
    empty.style.display = "none";

    entries.forEach(entry => {
        const item = document.createElement("div");
        item.className = "history-item";
        const [tLabel, tClass] = TRIGGER_LABELS[entry.trigger] || ["Unknown", "trigger-api"];
        const icon = TRIGGER_ICONS[entry.trigger] || "📋";

        item.innerHTML = `
      <div class="hist-icon">${icon}</div>
      <div class="hist-body">
        <div class="hist-title">${entry.note || "Pemberian makan"}</div>
        <div class="hist-meta">
          ${formatDateTime(entry.timestamp)} · Sisa: ${entry.food_level_after ?? "?"}%
        </div>
      </div>
      <span class="hist-amount">${entry.amount}g</span>
      <span class="trigger-badge ${tClass}">${tLabel}</span>
    `;
        list.appendChild(item);
    });
}

document.getElementById("btn-refresh-history").addEventListener("click", () => {
    loadHistory();
    showToast("Riwayat diperbarui", "info", 2000);
});

// ─── Settings ─────────────────────────────────────────────────
async function loadSettings() {
    try {
        const data = await apiFetch("/api/settings");
        const s = data.settings;
        if (s.pet_name) {
            document.getElementById("pet-name-pill").textContent = `🐱 ${s.pet_name}`;
        }
        if (s.default_amount) {
            selectedAmount = s.default_amount;
            document.getElementById("amount-slider").value = selectedAmount;
            document.getElementById("amount-display").textContent = `${selectedAmount}g`;
        }
    } catch (e) {
        console.warn("[Settings] Error:", e.message);
    }
}

// ─── PWA Install Banner ───────────────────────────────────────
let deferredInstallPrompt = null;

window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredInstallPrompt = e;
    showInstallBanner();
});

function showInstallBanner() {
    if (document.getElementById("install-banner")) return;

    const banner = document.createElement("div");
    banner.id = "install-banner";
    banner.className = "install-banner";
    banner.innerHTML = `
    <div class="install-banner-icon">🐾</div>
    <div class="install-banner-text">
      <strong>Install PetFeeder App</strong>
      <span>Tambahkan ke layar utama untuk akses cepat</span>
    </div>
    <button class="install-banner-btn" id="btn-install">Install</button>
    <button class="install-banner-close" id="btn-install-close">✕</button>
  `;
    document.body.appendChild(banner);

    document.getElementById("btn-install").addEventListener("click", async () => {
        if (!deferredInstallPrompt) return;
        deferredInstallPrompt.prompt();
        const { outcome } = await deferredInstallPrompt.userChoice;
        console.log(`[PWA] Install outcome: ${outcome}`);
        deferredInstallPrompt = null;
        banner.remove();
    });

    document.getElementById("btn-install-close").addEventListener("click", () => {
        banner.remove();
    });
}

// ─── PWA Install Banner ──────────────────────────────────────
let deferredPrompt = null;
let installBannerClosed = localStorage.getItem("pwa-banner-closed") === "true";

window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    
    if (!installBannerClosed) {
        showInstallBanner();
    }
});

function showInstallBanner() {
    const banner = document.createElement("div");
    banner.id = "install-banner";
    banner.className = "install-banner";
    banner.innerHTML = `
        <div class="install-banner-content">
            <div class="install-banner-icon">📱</div>
            <div class="install-banner-text">
                <div class="install-banner-title">Pasang di Layar Utama?</div>
                <div class="install-banner-desc">Akses aplikasi lebih cepat tanpa membuka browser</div>
            </div>
            <div class="install-banner-actions">
                <button id="install-btn" class="install-btn primary">Pasang</button>
                <button id="dismiss-btn" class="install-btn secondary">Nanti</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(banner);
    
    document.getElementById("install-btn").addEventListener("click", async () => {
        if (deferredPrompt) {
            deferredPrompt.prompt();
            const result = await deferredPrompt.userChoice;
            if (result.outcome === "accepted") {
                showToast("✅ Aplikasi berhasil diinstall!", "success", 3000);
            } else {
                showToast("ℹ️ Instalasi dibatalkan", "info", 2000);
            }
            deferredPrompt = null;
            banner.remove();
        }
    });
    
    document.getElementById("dismiss-btn").addEventListener("click", () => {
        localStorage.setItem("pwa-banner-closed", "true");
        banner.remove();
    });
}

window.addEventListener("appinstalled", () => {
    console.log("[PWA] App berhasil diinstall!");
    showToast("🎉 PetFeeder berhasil diinstall!", "success", 5000);
    document.getElementById("install-banner")?.remove();
});

// ─── Offline/Online Status ───────────────────────────────────
function updateNetworkStatus() {
    const onlineIndicator = document.getElementById("online-indicator");
    if (navigator.onLine) {
        console.log("📡 Online");
        if (onlineIndicator) {
            onlineIndicator.style.display = "none";
        }
    } else {
        console.log("⚠️ Offline");
        if (!onlineIndicator) {
            const indicator = document.createElement("div");
            indicator.id = "online-indicator";
            indicator.innerHTML = `<div class="offline-banner">📵 Anda sedang offline</div>`;
            document.body.appendChild(indicator);
        } else {
            onlineIndicator.style.display = "flex";
        }
    }
}

window.addEventListener("online", updateNetworkStatus);
window.addEventListener("offline", updateNetworkStatus);

// ─── Touch Events (Swipe, Pull-to-Refresh) ───────────────────
let touchStartX = 0;
let touchStartY = 0;
let refreshing = false;

document.addEventListener("touchstart", (e) => {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
}, false);

document.addEventListener("touchend", (e) => {
    const touchEndX = e.changedTouches[0].clientX;
    const touchEndY = e.changedTouches[0].clientY;
    
    // Pull-to-refresh detection (swipe down from top)
    const swipeDownDistance = touchEndY - touchStartY;
    if (window.scrollY === 0 && swipeDownDistance > 100 && !refreshing) {
        refreshing = true;
        console.log("🔄 Pull-to-refresh detected");
        refreshStatus();
        setTimeout(() => { refreshing = false; }, 1500);
    }
    
    // Swipe left/right untuk navigate tabs (opsional future)
    const swipeDistance = touchEndX - touchStartX;
    if (Math.abs(swipeDistance) > 80) {
        // Future: implement tab navigation
    }
}, false);

// ─── Vibration Feedback ──────────────────────────────────────
function vibrate(pattern = 50) {
    if ("vibrate" in navigator) {
        navigator.vibrate(pattern);
    }
}

// Override button clicks untuk vibration
document.addEventListener("click", (e) => {
    const buttons = [
        "feed-btn", "add-schedule-btn", "save-settings-btn",
        "schedule-item", "delete-btn", "confirm-btn"
    ];
    
    const clicked = buttons.some(id => 
        e.target.closest(`[id*="${id}"]`) || 
        e.target.classList.contains("amount-btn") ||
        e.target.classList.contains("day-btn")
    );
    
    if (clicked) {
        vibrate(20);
    }
}, true);

// ─── Virtual Keyboard Awareness ───────────────────────────────
window.addEventListener("focusin", (e) => {
    if (e.target.matches("input, textarea")) {
        // Scroll into view untuk menghindari keyboard overlapping
        setTimeout(() => {
            e.target.scrollIntoView({ behavior: "smooth", block: "center" });
        }, 300);
    }
});

// ─── Prevent Zoom on Double-Tap (but allow pinch) ─────────────
let lastTouchEnd = 0;
document.addEventListener("touchend", (e) => {
    const now = Date.now();
    if (now - lastTouchEnd <= 300 && e.touches.length === 0) {
        e.preventDefault();
    }
    lastTouchEnd = now;
}, false);

// ─── Refresh Status (for pull-to-refresh) ─────────────────────
async function refreshStatus() {
    try {
        await fetchStatus();
        showToast("✅ Status diperbarui", "success", 2000);
    } catch (e) {
        showToast("❌ Gagal memperbarui status", "error", 2500);
    }
}

// ─── Init ─────────────────────────────────────────────────────
async function init() {
    console.log("🐾 PetFeeder App dimulai...");

    // Load initial data
    await Promise.allSettled([
        fetchStatus(),
        loadSchedules(),
        loadHistory(),
        loadSettings(),
    ]);

    // Connect SSE for real-time updates
    try {
        connectSSE();
    } catch (e) {
        console.warn("[SSE] Tidak tersedia, menggunakan polling");
        startPolling();
    }

    // Fallback polling
    startPolling();
}

document.addEventListener("DOMContentLoaded", init);

