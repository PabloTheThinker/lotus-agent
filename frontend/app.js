const messagesEl = document.getElementById("messages");
const composer = document.getElementById("composer");
const input = document.getElementById("input");
const sendBtn = document.getElementById("sendBtn");
const statusEl = document.getElementById("status");
const hero = document.getElementById("hero");
const chatView = document.getElementById("chatView");
const startBtn = document.getElementById("startBtn");
const crisisBanner = document.getElementById("crisisBanner");
const crisisClose = document.getElementById("crisisClose");
const crisisTitle = document.getElementById("crisisTitle");
const crisisBody = document.getElementById("crisisBody");
const journeyToggle = document.getElementById("journeyToggle");
const journeyPanel = document.getElementById("journeyPanel");
const journeyStatement = document.getElementById("journeyStatement");
const journeyFill = document.getElementById("journeyFill");
const journeyMeter = document.getElementById("journeyMeter");
const journeyMeta = document.getElementById("journeyMeta");
const journeyCheckpoints = document.getElementById("journeyCheckpoints");
const setupBanner = document.getElementById("setupBanner");
const setupHint = document.getElementById("setupHint");
const setupClose = document.getElementById("setupClose");
const regionSelect = document.getElementById("regionSelect");

/** @type {{role: string, content: string}[]} */
const history = [];
let sessionToken = "";
let journeyOptIn = localStorage.getItem("lotus_journey_opt_in") === "1";
let serverJourneyOk = true;
let helpRegion = localStorage.getItem("lotus_crisis_region") || "US";

const CRISIS_HINT =
  /\b(kill myself|end my life|suicid|want to die|self[-\s]?harm|hurt (someone|them)|quiero morir|me quiero matar|je veux mourir|ich will sterben|quero morrer|voglio morire|不想活|死にたい|自杀|自殺|죽고)\b/i;

/** Cue-based only — undefined when no strong non-English signal. */
function detectLangCue(text) {
  if (/[¿¡]|\b(quiero|estoy|me siento|ayuda|matar|vivir|deprimid)/i.test(text)) return "es";
  if (/\b(je veux|je suis|mourir|aide|déprim)/i.test(text)) return "fr";
  if (/\b(quero|estou|morrer|ajuda|deprimid)/i.test(text)) return "pt";
  if (/\b(ich will|ich bin|sterben|hilfe|deprimiert)/i.test(text)) return "de";
  return "";
}

function detectLang(text) {
  return detectLangCue(text) || (navigator.language || "en").split("-")[0];
}

async function softSyncLang(text) {
  const lang = detectLangCue(text);
  if (!lang) return;
  try {
    const token = await ensureSession();
    await fetch("/api/prefs", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Lotus-Session": token,
      },
      body: JSON.stringify({ preferred_lang: lang, soft: true }),
    });
  } catch {
    /* offline ok */
  }
}

function setStatus(text, kind = "") {
  statusEl.textContent = text;
  statusEl.className = "status" + (kind ? ` ${kind}` : "");
}

async function localizeCrisis(lang) {
  try {
    const res = await fetch(
      `/api/crisis?lang=${encodeURIComponent(lang)}&region=${encodeURIComponent(helpRegion)}`
    );
    if (!res.ok) return;
    const data = await res.json();
    if (crisisTitle && data.title) crisisTitle.textContent = data.title;
    if (crisisBody && data.body_html) crisisBody.innerHTML = data.body_html;
  } catch {
    /* keep defaults */
  }
}

function showCrisis(force = false, lang = "en") {
  if (!crisisBanner) return;
  localizeCrisis(lang);
  if (force || !sessionStorage.getItem("lotus_crisis_dismissed")) {
    crisisBanner.classList.remove("hidden");
  }
}

function hideCrisis() {
  if (!crisisBanner) return;
  crisisBanner.classList.add("hidden");
  sessionStorage.setItem("lotus_crisis_dismissed", "1");
}

function syncJourneyToggle() {
  if (!journeyToggle || !journeyPanel) return;
  const on = journeyOptIn && serverJourneyOk;
  journeyToggle.setAttribute("aria-pressed", on ? "true" : "false");
  journeyToggle.textContent = on ? "Journey on" : "Journey off";
  journeyPanel.classList.toggle("hidden", !on);
  if (on) refreshJourney();
}

async function refreshJourney() {
  if (!journeyOptIn || !serverJourneyOk) return;
  try {
    const res = await fetch("/api/journey");
    if (!res.ok) return;
    const data = await res.json();
    if (data.enabled === false) {
      serverJourneyOk = false;
      syncJourneyToggle();
      return;
    }
    if (!data.active) {
      journeyStatement.textContent = data.message || "Listening for what you want to rebuild toward…";
      journeyFill.style.width = "0%";
      journeyMeter.setAttribute("aria-valuenow", "0");
      journeyMeta.textContent = "";
      return;
    }
    const m = data.meter || {};
    const pct = Math.round(Math.min(1, Math.max(0, m.compound_score || 0)) * 100);
    journeyStatement.textContent = data.statement || "Your mission";
    journeyFill.style.width = `${pct}%`;
    journeyMeter.setAttribute("aria-valuenow", String(pct));
    const bits = [
      `${m.checkpoints_met || 0}/${m.checkpoints_total || 0} checkpoints`,
      `horizon: ${m.estimated_horizon || "—"}`,
      m.center_met ? "center met" : "center ahead",
      m.guidance_unlocked ? "guidance on" : "guidance locked",
    ];
    journeyMeta.textContent = bits.join(" · ");
    if (journeyCheckpoints) {
      const cps = Array.isArray(data.checkpoints) ? data.checkpoints : [];
      journeyCheckpoints.innerHTML = "";
      if (!cps.length) {
        journeyCheckpoints.hidden = true;
      } else {
        journeyCheckpoints.hidden = false;
        for (const c of cps.slice(0, 6)) {
          const li = document.createElement("li");
          const status = String(c.status || "pending");
          li.dataset.status = status;
          if (c.is_center) li.dataset.center = "1";
          li.textContent = `${c.is_center ? "◆ " : ""}${c.title || "Checkpoint"} · ${status}`;
          journeyCheckpoints.appendChild(li);
        }
      }
    }
  } catch {
    /* ignore */
  }
}

function addBubble(role, content) {
  const el = document.createElement("div");
  el.className = `bubble ${role}`;
  if (role === "assistant") {
    const who = document.createElement("span");
    who.className = "who";
    who.textContent = "L.O.T.U.S.";
    el.appendChild(who);
    const body = document.createElement("span");
    body.className = "body";
    body.textContent = content;
    el.appendChild(body);
  } else {
    el.textContent = content;
  }
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return el;
}

function openChat() {
  hero.classList.add("hidden");
  chatView.classList.remove("hidden");
  if (!messagesEl.querySelector(".bubble")) {
    addBubble(
      "system",
      "I'm here with you. Share what feels heavy — or what you need next."
    );
  }
  syncJourneyToggle();
  input.focus();
}

async function ensureSession() {
  if (sessionToken) return sessionToken;
  const res = await fetch("/api/session");
  if (!res.ok) throw new Error("Could not open a secure session");
  const data = await res.json();
  sessionToken = data.token;
  return sessionToken;
}

function showSetup(needed, hint) {
  if (!setupBanner) return;
  if (!needed || sessionStorage.getItem("lotus_setup_dismissed")) {
    setupBanner.classList.add("hidden");
    return;
  }
  if (setupHint && hint) setupHint.textContent = hint;
  setupBanner.classList.remove("hidden");
}

async function loadPrefs() {
  try {
    const res = await fetch("/api/prefs");
    if (!res.ok) return;
    const data = await res.json();
    const regions = data.crisis_regions || [];
    const primary = regions.find((r) => r && r !== "INTL") || helpRegion;
    helpRegion = primary;
    localStorage.setItem("lotus_crisis_region", helpRegion);
    if (regionSelect) regionSelect.value = helpRegion;
  } catch {
    /* ignore */
  }
}

async function saveRegion(region) {
  helpRegion = region || "US";
  localStorage.setItem("lotus_crisis_region", helpRegion);
  try {
    const token = await ensureSession();
    await fetch("/api/prefs", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Lotus-Session": token,
      },
      body: JSON.stringify({
        crisis_regions: [helpRegion, "INTL"],
      }),
    });
  } catch {
    /* offline ok */
  }
}

async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (data.ok) {
      serverJourneyOk = data.journey_ui !== false;
      if (data.setup_needed) {
        setStatus("Setup needed", "err");
        showSetup(true, data.setup_hint);
      } else {
        setStatus(
          data.gateway ? "Gateway ready" : "UI ready · start gateway",
          data.gateway ? "ok" : ""
        );
        showSetup(false);
      }
      syncJourneyToggle();
    } else {
      setStatus(data.error || "Unavailable", "err");
    }
  } catch {
    setStatus("Offline", "err");
  }
}

function parseSseChunk(buffer, onDelta) {
  const parts = buffer.split("\n\n");
  const rest = parts.pop() || "";
  for (const part of parts) {
    const dataLines = [];
    for (const line of part.split("\n")) {
      if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
      else if (line.startsWith("data: ")) dataLines.push(line.slice(6));
    }
    if (!dataLines.length) continue;
    const payload = dataLines.join("\n").trim();
    if (!payload || payload === "[DONE]") continue;
    try {
      const json = JSON.parse(payload);
      if (json.error) throw new Error(json.error);
      const delta =
        json.choices?.[0]?.delta?.content ??
        json.choices?.[0]?.message?.content ??
        "";
      if (delta) onDelta(delta);
    } catch (err) {
      if (err instanceof SyntaxError) continue;
      throw err;
    }
  }
  return rest;
}

async function sendMessage(text) {
  history.push({ role: "user", content: text });
  addBubble("user", text);
  void softSyncLang(text);
  if (CRISIS_HINT.test(text)) showCrisis(true, detectLang(text));

  const bubble = addBubble("assistant", "");
  const bodyEl = bubble.querySelector(".body");
  sendBtn.disabled = true;
  input.disabled = true;
  setStatus("Listening…", "ok");

  let reply = "";
  try {
    const token = await ensureSession();
    const res = await fetch("/api/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Lotus-Session": token,
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ messages: history, stream: true }),
    });

    if (!res.ok) {
      let errMsg = `HTTP ${res.status}`;
      try {
        const data = await res.json();
        errMsg = data.error || errMsg;
      } catch {
        /* ignore */
      }
      throw new Error(errMsg);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      buf = parseSseChunk(buf, (delta) => {
        reply += delta;
        bodyEl.textContent = reply;
        messagesEl.scrollTop = messagesEl.scrollHeight;
      });
    }
    if (buf.trim()) {
      parseSseChunk(buf + "\n\n", (delta) => {
        reply += delta;
        bodyEl.textContent = reply;
      });
    }

    if (!reply) {
      const fallback = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Lotus-Session": token,
        },
        body: JSON.stringify({ messages: history }),
      });
      const data = await fallback.json();
      if (!fallback.ok) throw new Error(data.error || `HTTP ${fallback.status}`);
      reply = data.content || "(No response)";
      bodyEl.textContent = reply;
    }

    history.push({ role: "assistant", content: reply });
    setStatus("With you", "ok");
    if (journeyOptIn) refreshJourney();
  } catch (err) {
    bubble.remove();
    addBubble(
      "system",
      `Could not reach L.O.T.U.S.: ${err.message}. Is the gateway running? (./scripts/lotus-gateway.sh)`
    );
    history.pop();
    setStatus("Error", "err");
  } finally {
    sendBtn.disabled = false;
    input.disabled = false;
    input.focus();
  }
}

startBtn.addEventListener("click", openChat);
crisisClose?.addEventListener("click", hideCrisis);
setupClose?.addEventListener("click", () => {
  setupBanner?.classList.add("hidden");
  sessionStorage.setItem("lotus_setup_dismissed", "1");
});

journeyToggle?.addEventListener("click", () => {
  journeyOptIn = !journeyOptIn;
  localStorage.setItem("lotus_journey_opt_in", journeyOptIn ? "1" : "0");
  syncJourneyToggle();
});

if (regionSelect) {
  regionSelect.value = helpRegion;
  regionSelect.addEventListener("change", () => saveRegion(regionSelect.value));
}

composer.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text || sendBtn.disabled) return;
  input.value = "";
  input.style.height = "auto";
  if (hero && !hero.classList.contains("hidden")) openChat();
  sendMessage(text);
});

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    composer.requestSubmit();
  }
});

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 144) + "px";
});

ensureSession().catch(() => setStatus("Session error", "err"));
loadPrefs();
checkHealth();
setInterval(checkHealth, 15000);
syncJourneyToggle();
