"use strict";

const state = {
  config: null,
  session: null,
  token: null,
  pendingAttempt: null,
  attemptNumber: 0,
  timer: null,
};

const elements = {
  admissionView: document.querySelector("#admission-view"),
  workspaceView: document.querySelector("#workspace-view"),
  configSkeleton: document.querySelector("#config-skeleton"),
  admissionForm: document.querySelector("#admission-form"),
  admissionError: document.querySelector("#admission-error"),
  roundCode: document.querySelector("#round-code"),
  preset: document.querySelector("#preset"),
  presetHelper: document.querySelector("#preset-helper"),
  roundStatus: document.querySelector("#round-status"),
  startButton: document.querySelector("#start-button"),
  globalAlert: document.querySelector("#global-alert"),
  globalAlertTitle: document.querySelector("#global-alert-title"),
  globalAlertMessage: document.querySelector("#global-alert-message"),
  retryConfig: document.querySelector("#retry-config"),
  promptForm: document.querySelector("#prompt-form"),
  prompt: document.querySelector("#prompt"),
  providerKey: document.querySelector("#provider-key"),
  credentialField: document.querySelector("#credential-field"),
  characterCount: document.querySelector("#character-count"),
  submitAttempt: document.querySelector("#submit-attempt"),
  retryAttempt: document.querySelector("#retry-attempt"),
  attemptError: document.querySelector("#attempt-error"),
  attemptCount: document.querySelector("#attempt-count"),
  timeLeft: document.querySelector("#time-left"),
  sessionState: document.querySelector("#session-state"),
  modelLabel: document.querySelector("#model-label"),
  sessionId: document.querySelector("#session-id"),
  copySession: document.querySelector("#copy-session"),
  responseFeed: document.querySelector("#response-feed"),
  emptyResponse: document.querySelector("#empty-response"),
  responseStatus: document.querySelector("#response-status"),
  successPanel: document.querySelector("#success-panel"),
  nextRoundHint: document.querySelector("#next-round-hint"),
  newSession: document.querySelector("#new-session"),
  newSessionDialog: document.querySelector("#new-session-dialog"),
  themeToggle: document.querySelector("#theme-toggle"),
};

class ApiError extends Error {
  constructor(error, status) {
    super(error?.message || "The request could not be completed.");
    this.code = error?.code || "REQUEST_FAILED";
    this.retryable = Boolean(error?.retryable);
    this.requestId = error?.request_id || null;
    this.status = status;
  }
}

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, options);
  } catch (error) {
    const networkError = new ApiError({ message: "The sandbox could not be reached. Check your connection and retry.", retryable: true }, 0);
    networkError.cause = error;
    throw networkError;
  }

  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(body.error, response.status);
  return body.data;
}

function setButtonLoading(button, loading, activeLabel, idleLabel) {
  button.disabled = loading;
  const label = button.querySelector("span:first-child") || button;
  label.textContent = loading ? activeLabel : idleLabel;
}

function showFieldError(element, error) {
  const requestReference = error.requestId ? ` Reference: ${error.requestId}.` : "";
  element.textContent = `${error.message}${requestReference}`;
  element.hidden = false;
}

function clearFieldError(element) {
  element.textContent = "";
  element.hidden = true;
}

function applyTheme(theme) {
  if (theme === "light" || theme === "dark") {
    document.documentElement.dataset.theme = theme;
  } else {
    delete document.documentElement.dataset.theme;
  }
}

function currentTheme() {
  const explicit = document.documentElement.dataset.theme;
  if (explicit) return explicit;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function toggleTheme() {
  const next = currentTheme() === "dark" ? "light" : "dark";
  applyTheme(next);
  localStorage.setItem("llm-sandbox-theme", next);
}

function renderConfig(config) {
  elements.preset.replaceChildren();
  for (const preset of config.presets) {
    const option = document.createElement("option");
    option.value = preset.id;
    option.textContent = `${preset.label} (${preset.model_label})`;
    option.dataset.credentialMode = preset.credential_mode;
    elements.preset.append(option);
  }
  elements.roundStatus.textContent = config.round_status === "open" ? "Round open" : "Unavailable";
  elements.roundStatus.classList.toggle("is-open", config.round_status === "open");
  elements.configSkeleton.hidden = true;
  elements.admissionForm.hidden = false;
  elements.startButton.disabled = config.round_status !== "open" || config.presets.length === 0;
  updatePresetHelper();
}

async function loadConfig() {
  elements.globalAlert.hidden = true;
  elements.configSkeleton.hidden = false;
  elements.admissionForm.hidden = true;
  try {
    state.config = await api("/api/v1/config");
    renderConfig(state.config);
  } catch (error) {
    elements.configSkeleton.hidden = true;
    elements.globalAlertTitle.textContent = "Sandbox unavailable";
    elements.globalAlertMessage.textContent = error.message;
    elements.globalAlert.hidden = false;
  }
}

function updatePresetHelper() {
  const option = elements.preset.selectedOptions[0];
  if (!option) return;
  elements.presetHelper.textContent = option.dataset.credentialMode === "participant_provided"
    ? "This preset requires your provider API key for each attempt."
    : "The event server provides the model credential.";
}

function renderSession(session) {
  state.session = session;
  state.token = session.session_token;
  state.attemptNumber = 0;
  elements.admissionView.hidden = true;
  elements.workspaceView.hidden = false;
  elements.modelLabel.textContent = session.model_label;
  elements.sessionId.textContent = session.session_id;
  elements.credentialField.hidden = session.credential_mode !== "participant_provided";
  elements.providerKey.required = session.credential_mode === "participant_provided";
  updateSessionFacts();
  startCountdown();
  elements.prompt.focus();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function updateSessionFacts() {
  if (!state.session) return;
  const used = state.session.attempt_limit - state.session.remaining_attempts;
  elements.attemptCount.textContent = `${used} / ${state.session.attempt_limit}`;
  elements.sessionState.textContent = state.session.solved ? "Solved" : "Active";
  elements.submitAttempt.disabled = state.session.solved || state.session.remaining_attempts <= 0;
}

function startCountdown() {
  clearInterval(state.timer);
  updateCountdown();
  state.timer = window.setInterval(updateCountdown, 1000);
}

function updateCountdown() {
  if (!state.session) return;
  const remaining = Math.max(0, new Date(state.session.expires_at).getTime() - Date.now());
  const minutes = Math.floor(remaining / 60000);
  const seconds = Math.floor((remaining % 60000) / 1000);
  elements.timeLeft.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  if (remaining === 0) {
    clearInterval(state.timer);
    elements.sessionState.textContent = "Expired";
    elements.submitAttempt.disabled = true;
  }
}

async function createSession(event) {
  event.preventDefault();
  clearFieldError(elements.admissionError);
  setButtonLoading(elements.startButton, true, "Opening sandbox", "Start challenge");
  try {
    const session = await api("/api/v1/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Round-Code": elements.roundCode.value },
      body: JSON.stringify({ preset_id: elements.preset.value }),
    });
    elements.roundCode.value = "";
    renderSession(session);
  } catch (error) {
    showFieldError(elements.admissionError, error);
    elements.roundCode.focus();
  } finally {
    setButtonLoading(elements.startButton, false, "Opening sandbox", "Start challenge");
  }
}

function loadingResponse(show) {
  const existing = document.querySelector("#loading-response");
  if (existing) existing.remove();
  if (!show) return;
  if (elements.emptyResponse) elements.emptyResponse.hidden = true;
  const loader = document.createElement("div");
  loader.id = "loading-response";
  loader.className = "loading-response";
  loader.setAttribute("aria-label", "Model is generating a response");
  loader.append(document.createElement("span"), document.createElement("span"), document.createElement("span"));
  elements.responseFeed.prepend(loader);
}

function appendResponse(data) {
  if (elements.emptyResponse) elements.emptyResponse.remove();
  const entry = document.createElement("article");
  entry.className = `response-entry${data.solved ? " is-solved" : ""}`;

  const meta = document.createElement("div");
  meta.className = "response-meta";
  const attempt = document.createElement("span");
  attempt.textContent = `ATTEMPT ${String(state.attemptNumber).padStart(2, "0")}`;
  const outcome = document.createElement("span");
  outcome.textContent = data.solved ? "PROOF FOUND" : "NO PROOF";
  meta.append(attempt, outcome);

  const body = document.createElement("pre");
  body.className = "response-body";
  body.textContent = data.model_response;

  const usage = document.createElement("p");
  usage.className = "response-usage";
  const input = data.usage.input_tokens ?? "unknown";
  const output = data.usage.output_tokens ?? "unknown";
  usage.textContent = `Input tokens: ${input} | Output tokens: ${output}`;
  entry.append(meta, body, usage);
  elements.responseFeed.prepend(entry);
}

async function runAttempt(prompt, idempotencyKey) {
  const headers = {
    "Authorization": `Bearer ${state.token}`,
    "Content-Type": "application/json",
    "Idempotency-Key": idempotencyKey,
  };
  if (state.session.credential_mode === "participant_provided") {
    headers["X-Provider-API-Key"] = elements.providerKey.value;
  }
  return api(`/api/v1/sessions/${state.session.session_id}/attempts`, {
    method: "POST",
    headers,
    body: JSON.stringify({ prompt }),
  });
}

async function submitAttempt(event, retry = false) {
  if (event) event.preventDefault();
  clearFieldError(elements.attemptError);
  elements.retryAttempt.hidden = true;

  const prompt = retry ? state.pendingAttempt?.prompt : elements.prompt.value.trim();
  if (!prompt) {
    showFieldError(elements.attemptError, new ApiError({ message: "Write a prompt before running an attempt." }, 422));
    elements.prompt.focus();
    return;
  }
  if (prompt.length > state.config.prompt_max_characters) {
    showFieldError(elements.attemptError, new ApiError({ message: `Keep the prompt under ${state.config.prompt_max_characters} characters.` }, 422));
    elements.prompt.focus();
    return;
  }

  const idempotencyKey = retry && state.pendingAttempt
    ? state.pendingAttempt.idempotencyKey
    : crypto.randomUUID();
  state.pendingAttempt = { prompt, idempotencyKey };
  elements.submitAttempt.disabled = true;
  elements.retryAttempt.disabled = true;
  elements.responseStatus.textContent = retry ? "Retrying" : "Generating";
  elements.responseStatus.classList.add("is-active");
  loadingResponse(true);

  try {
    const data = await runAttempt(prompt, idempotencyKey);
    state.pendingAttempt = null;
    state.attemptNumber += 1;
    state.session.remaining_attempts = data.remaining_attempts;
    state.session.solved = data.solved;
    appendResponse(data);
    elements.prompt.value = "";
    updateCharacterCount();
    updateSessionFacts();
    elements.responseStatus.textContent = data.solved ? "Verified" : "Completed";
    if (data.solved) {
      elements.successPanel.hidden = false;
      elements.nextRoundHint.textContent = data.next_round_hint || "Your organizer will provide the next step.";
      elements.successPanel.scrollIntoView({ behavior: "smooth", block: "center" });
    } else {
      elements.prompt.focus();
    }
  } catch (error) {
    showFieldError(elements.attemptError, error);
    elements.retryAttempt.hidden = !error.retryable;
    if (!error.retryable) state.pendingAttempt = null;
    elements.responseStatus.textContent = "Request failed";
  } finally {
    loadingResponse(false);
    elements.responseStatus.classList.remove("is-active");
    elements.retryAttempt.disabled = false;
    updateSessionFacts();
  }
}

function updateCharacterCount() {
  const count = elements.prompt.value.length;
  const limit = state.config?.prompt_max_characters || 0;
  elements.characterCount.textContent = `${count} / ${limit}`;
  elements.characterCount.classList.toggle("is-over-limit", count > limit);
}

function resetSession() {
  clearInterval(state.timer);
  state.session = null;
  state.token = null;
  state.pendingAttempt = null;
  state.attemptNumber = 0;
  elements.responseFeed.replaceChildren(elements.emptyResponse || createEmptyResponse());
  elements.successPanel.hidden = true;
  elements.providerKey.value = "";
  elements.prompt.value = "";
  elements.workspaceView.hidden = true;
  elements.admissionView.hidden = false;
  elements.roundCode.focus();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function createEmptyResponse() {
  const empty = document.createElement("div");
  empty.id = "empty-response";
  empty.className = "empty-response";
  const glyph = document.createElement("span");
  glyph.className = "empty-glyph";
  glyph.setAttribute("aria-hidden", "true");
  glyph.textContent = "_";
  const copy = document.createElement("p");
  copy.textContent = "Your model responses will appear here. Start with a direct request, then adapt.";
  empty.append(glyph, copy);
  elements.emptyResponse = empty;
  return empty;
}

async function copySessionId() {
  if (!state.session) return;
  try {
    await navigator.clipboard.writeText(state.session.session_id);
    elements.copySession.textContent = "Session ID copied";
    window.setTimeout(() => { elements.copySession.textContent = "Copy session ID"; }, 1800);
  } catch {
    elements.copySession.textContent = "Copy unavailable";
  }
}

function initialize() {
  applyTheme(localStorage.getItem("llm-sandbox-theme"));
  elements.themeToggle.addEventListener("click", toggleTheme);
  elements.retryConfig.addEventListener("click", loadConfig);
  elements.preset.addEventListener("change", updatePresetHelper);
  elements.admissionForm.addEventListener("submit", createSession);
  elements.promptForm.addEventListener("submit", submitAttempt);
  elements.retryAttempt.addEventListener("click", (event) => submitAttempt(event, true));
  elements.prompt.addEventListener("input", updateCharacterCount);
  elements.copySession.addEventListener("click", copySessionId);
  elements.newSession.addEventListener("click", () => elements.newSessionDialog.showModal());
  elements.newSessionDialog.addEventListener("close", () => {
    if (elements.newSessionDialog.returnValue === "confirm") resetSession();
  });
  loadConfig();
}

initialize();
