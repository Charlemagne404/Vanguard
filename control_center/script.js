const PRESETS = {
  off: {
    guard_enabled: false,
  },
  relaxed: {
    guard_enabled: true,
    guard_threshold: 12,
    guard_window_seconds: 30,
    guard_new_account_hours: 12,
    guard_slowmode_seconds: 20,
    guard_cooldown_seconds: 240,
    guard_slowmode_scope: "trigger",
    guard_timeout_seconds: 0,
    guard_join_threshold: 9,
    guard_join_window_seconds: 45,
    guard_mention_per_message: 10,
    guard_mention_burst_threshold: 4,
    guard_mention_window_seconds: 20,
    guard_duplicate_threshold: 5,
    guard_duplicate_window_seconds: 25,
    guard_link_threshold: 7,
    guard_link_window_seconds: 45,
  },
  balanced: {
    guard_enabled: true,
    guard_threshold: 8,
    guard_window_seconds: 30,
    guard_new_account_hours: 24,
    guard_slowmode_seconds: 30,
    guard_cooldown_seconds: 300,
    guard_slowmode_scope: "active",
    guard_max_slowmode_channels: 3,
    guard_critical_slowmode_seconds: 120,
    guard_timeout_seconds: 300,
    guard_delete_trigger_message: false,
    guard_join_threshold: 6,
    guard_join_window_seconds: 45,
    guard_mention_per_message: 6,
    guard_mention_burst_threshold: 3,
    guard_mention_window_seconds: 20,
    guard_duplicate_threshold: 4,
    guard_duplicate_window_seconds: 25,
    guard_duplicate_min_chars: 12,
    guard_link_threshold: 5,
    guard_link_window_seconds: 45,
    guard_detect_joins: true,
    guard_detect_mentions: true,
    guard_detect_duplicates: true,
    guard_detect_links: true,
  },
  strict: {
    guard_enabled: true,
    guard_threshold: 6,
    guard_window_seconds: 20,
    guard_new_account_hours: 48,
    guard_slowmode_seconds: 45,
    guard_cooldown_seconds: 180,
    guard_slowmode_scope: "active",
    guard_max_slowmode_channels: 6,
    guard_critical_slowmode_seconds: 180,
    guard_timeout_seconds: 900,
    guard_delete_trigger_message: true,
    guard_join_threshold: 5,
    guard_join_window_seconds: 35,
    guard_mention_per_message: 4,
    guard_mention_burst_threshold: 2,
    guard_mention_window_seconds: 20,
    guard_duplicate_threshold: 3,
    guard_duplicate_window_seconds: 20,
    guard_duplicate_min_chars: 10,
    guard_link_threshold: 4,
    guard_link_window_seconds: 35,
    guard_detect_joins: true,
    guard_detect_mentions: true,
    guard_detect_duplicates: true,
    guard_detect_links: true,
  },
  siege: {
    guard_enabled: true,
    guard_threshold: 4,
    guard_window_seconds: 15,
    guard_new_account_hours: 72,
    guard_slowmode_seconds: 60,
    guard_cooldown_seconds: 120,
    guard_slowmode_scope: "active",
    guard_max_slowmode_channels: 12,
    guard_critical_slowmode_seconds: 300,
    guard_timeout_seconds: 1800,
    guard_delete_trigger_message: true,
    guard_join_threshold: 4,
    guard_join_window_seconds: 25,
    guard_mention_per_message: 3,
    guard_mention_burst_threshold: 2,
    guard_mention_window_seconds: 15,
    guard_duplicate_threshold: 3,
    guard_duplicate_window_seconds: 15,
    guard_duplicate_min_chars: 8,
    guard_link_threshold: 3,
    guard_link_window_seconds: 25,
    guard_detect_joins: true,
    guard_detect_mentions: true,
    guard_detect_duplicates: true,
    guard_detect_links: true,
  },
};

const state = {
  token: localStorage.getItem("vanguard-control-token") || "",
  guilds: [],
  selectedGuildId: null,
  detail: null,
};

const fieldIds = {
  welcome_channel_id: "welcome-channel",
  welcome_role_id: "welcome-role",
  welcome_message: "welcome-message",
  ops_channel_id: "ops-channel",
  log_channel_id: "log-channel",
  lockdown_role_id: "lockdown-role",
};

const guardNumberFields = [
  ["guard_threshold", "guard-threshold"],
  ["guard_window_seconds", "guard-window-seconds"],
  ["guard_new_account_hours", "guard-new-account-hours"],
  ["guard_slowmode_seconds", "guard-slowmode-seconds"],
  ["guard_cooldown_seconds", "guard-cooldown-seconds"],
  ["guard_max_slowmode_channels", "guard-max-slowmode-channels"],
  ["guard_critical_slowmode_seconds", "guard-critical-slowmode-seconds"],
  ["guard_timeout_seconds", "guard-timeout-seconds"],
  ["guard_join_threshold", "guard-join-threshold"],
  ["guard_join_window_seconds", "guard-join-window-seconds"],
  ["guard_mention_per_message", "guard-mention-per-message"],
  ["guard_mention_burst_threshold", "guard-mention-burst-threshold"],
  ["guard_mention_window_seconds", "guard-mention-window-seconds"],
  ["guard_duplicate_threshold", "guard-duplicate-threshold"],
  ["guard_duplicate_window_seconds", "guard-duplicate-window-seconds"],
  ["guard_duplicate_min_chars", "guard-duplicate-min-chars"],
  ["guard_link_threshold", "guard-link-threshold"],
  ["guard_link_window_seconds", "guard-link-window-seconds"],
];

const guardCheckboxFields = [
  ["guard_enabled", "guard-enabled"],
  ["guard_delete_trigger_message", "guard-delete-trigger-message"],
  ["guard_detect_joins", "guard-detect-joins"],
  ["guard_detect_mentions", "guard-detect-mentions"],
  ["guard_detect_duplicates", "guard-detect-duplicates"],
  ["guard_detect_links", "guard-detect-links"],
];

const tokenInput = document.querySelector("#token-input");
const authForm = document.querySelector("#auth-form");
const refreshButton = document.querySelector("#refresh-guilds");
const guildList = document.querySelector("#guild-list");
const emptyState = document.querySelector("#empty-state");
const dashboard = document.querySelector("#dashboard");
const settingsForm = document.querySelector("#settings-form");
const resetButton = document.querySelector("#reset-form");
const guardPresetSelect = document.querySelector("#guard-preset-select");
const presetHint = document.querySelector("#preset-hint");
const toast = document.querySelector("#toast");

if (state.token) {
  tokenInput.value = state.token;
  loadGuilds();
}

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  state.token = tokenInput.value.trim();
  localStorage.setItem("vanguard-control-token", state.token);
  await loadGuilds();
});

refreshButton.addEventListener("click", async () => {
  await loadGuilds();
});

resetButton.addEventListener("click", () => {
  if (state.detail) {
    fillForm(state.detail);
    showToast("Reset unsaved changes.", "success");
  }
});

guardPresetSelect.addEventListener("change", () => {
  const selectedPreset = guardPresetSelect.value;
  if (selectedPreset === "custom" || !PRESETS[selectedPreset]) {
    presetHint.textContent = "Manual tuning active. Current values will be saved as a custom profile.";
    return;
  }
  applyPresetToForm(selectedPreset);
  presetHint.textContent = `${selectedPreset} preset applied to the form. Save changes to persist it.`;
});

settingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.selectedGuildId) {
    return;
  }
  try {
    const detail = await api(`/api/guilds/${state.selectedGuildId}`, {
      method: "PUT",
      body: JSON.stringify(buildPayload()),
    });
    state.detail = detail;
    syncGuildSummary(detail);
    renderGuildList();
    renderDetail(detail);
    showToast("Settings saved.", "success");
  } catch (error) {
    showToast(error.message || "Failed to save settings.", "error");
  }
});

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Vanguard-Control-Token": state.token,
      ...(options.headers || {}),
    },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (payload.errors) {
      const message = Object.entries(payload.errors)
        .map(([field, issue]) => `${field}: ${issue}`)
        .join(" | ");
      throw new Error(message);
    }
    throw new Error(payload.error || `Request failed with HTTP ${response.status}.`);
  }
  return payload;
}

async function loadGuilds() {
  if (!state.token) {
    showToast("Enter the control center token first.", "error");
    return;
  }
  try {
    const payload = await api("/api/guilds");
    state.guilds = payload.guilds || [];
    renderGuildList();
    const hashGuildId = window.location.hash.replace("#guild-", "");
    const preferredGuildId =
      state.guilds.find((guild) => String(guild.id) === hashGuildId)?.id ||
      state.selectedGuildId ||
      state.guilds[0]?.id ||
      null;
    if (preferredGuildId) {
      await selectGuild(preferredGuildId);
    } else {
      dashboard.classList.add("hidden");
      emptyState.classList.remove("hidden");
    }
  } catch (error) {
    state.guilds = [];
    renderGuildList();
    dashboard.classList.add("hidden");
    emptyState.classList.remove("hidden");
    showToast(error.message || "Failed to load guilds.", "error");
  }
}

function renderGuildList() {
  guildList.innerHTML = "";
  if (!state.guilds.length) {
    guildList.innerHTML = `<p class="field-help">No guilds available for this bot session.</p>`;
    return;
  }
  for (const guild of state.guilds) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "guild-card";
    if (String(guild.id) === String(state.selectedGuildId)) {
      button.classList.add("active");
    }
    button.innerHTML = `
      <strong>${escapeHtml(guild.name)}</strong>
      <span>${guild.member_count} members</span>
      <span>Guard ${guild.guard_enabled ? "enabled" : "disabled"} • preset ${escapeHtml(guild.guard_preset)}</span>
    `;
    button.addEventListener("click", () => selectGuild(guild.id));
    guildList.appendChild(button);
  }
}

async function selectGuild(guildId) {
  state.selectedGuildId = guildId;
  renderGuildList();
  try {
    const detail = await api(`/api/guilds/${guildId}`);
    state.detail = detail;
    window.location.hash = `guild-${guildId}`;
    renderDetail(detail);
  } catch (error) {
    showToast(error.message || "Failed to load guild detail.", "error");
  }
}

function renderDetail(detail) {
  emptyState.classList.add("hidden");
  dashboard.classList.remove("hidden");

  document.querySelector("#guild-name").textContent = detail.name;
  document.querySelector("#guild-meta").textContent =
    `${detail.member_count} members • ${detail.recent_cases_24h} cases in the last 24h`;
  document.querySelector("#guard-preset-badge").textContent = detail.settings.guard_preset;
  document.querySelector("#last-trigger-badge").textContent = formatTimestamp(
    detail.runtime_stats.last_trigger_at
  );
  document.querySelector("#stat-members").textContent = detail.member_count;
  document.querySelector("#stat-votes").textContent = detail.active_votes;
  document.querySelector("#stat-reminders").textContent = detail.pending_reminders;
  document.querySelector("#stat-cases").textContent = detail.recent_cases_24h;
  document.querySelector("#stat-triggers").textContent = detail.runtime_stats.triggers_total;
  document.querySelector("#stat-suppressed").textContent = detail.runtime_stats.suppressed_total;

  populateSelect("welcome-channel", detail.channels, "Channel not set");
  populateSelect("ops-channel", detail.channels, "Channel not set");
  populateSelect("log-channel", detail.channels, "Channel not set");
  populateSelect("welcome-role", detail.roles, "Role not set");
  populateSelect("lockdown-role", detail.roles, "Use @everyone");
  populateModRoles(detail.roles, detail.settings.mod_role_ids || []);
  fillForm(detail);
}

function fillForm(detail) {
  const settings = detail.settings;
  for (const [key, elementId] of Object.entries(fieldIds)) {
    const element = document.querySelector(`#${elementId}`);
    if (!element) {
      continue;
    }
    if (element.tagName === "TEXTAREA") {
      element.value = settings[key] || "";
    } else {
      element.value = settings[key] || "";
    }
  }

  const guard = settings.guard;
  for (const [key, elementId] of guardNumberFields) {
    document.querySelector(`#${elementId}`).value = guard[key];
  }
  for (const [key, elementId] of guardCheckboxFields) {
    document.querySelector(`#${elementId}`).checked = Boolean(guard[key]);
  }
  document.querySelector("#guard-slowmode-scope").value = guard.guard_slowmode_scope;
  guardPresetSelect.value = settings.guard_preset || "custom";
  presetHint.textContent =
    settings.guard_preset === "custom"
      ? "Manual tuning active. Current values will be saved as a custom profile."
      : `${settings.guard_preset} preset is active.`;
}

function populateSelect(elementId, items, emptyLabel) {
  const select = document.querySelector(`#${elementId}`);
  select.innerHTML = "";
  const emptyOption = document.createElement("option");
  emptyOption.value = "";
  emptyOption.textContent = emptyLabel;
  select.appendChild(emptyOption);
  for (const item of items) {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = `#${item.name}`.replace("##", "#");
    if (item.mention.startsWith("<@&")) {
      option.textContent = item.name;
    }
    select.appendChild(option);
  }
}

function populateModRoles(roles, selectedRoleIds) {
  const container = document.querySelector("#mod-role-grid");
  container.innerHTML = "";
  for (const role of roles) {
    const label = document.createElement("label");
    label.className = "role-option";
    label.innerHTML = `
      <input type="checkbox" value="${role.id}" />
      <span>${escapeHtml(role.name)}</span>
    `;
    const input = label.querySelector("input");
    input.checked = selectedRoleIds.includes(role.id);
    container.appendChild(label);
  }
}

function buildPayload() {
  const payload = {
    welcome_channel_id: readOptionalSelect("welcome-channel"),
    welcome_role_id: readOptionalSelect("welcome-role"),
    welcome_message: document.querySelector("#welcome-message").value,
    ops_channel_id: readOptionalSelect("ops-channel"),
    log_channel_id: readOptionalSelect("log-channel"),
    lockdown_role_id: readOptionalSelect("lockdown-role"),
    mod_role_ids: [...document.querySelectorAll("#mod-role-grid input:checked")].map((input) =>
      Number(input.value)
    ),
    guard_preset: guardPresetSelect.value,
    guard: {
      guard_slowmode_scope: document.querySelector("#guard-slowmode-scope").value,
    },
  };

  for (const [key, elementId] of guardNumberFields) {
    payload.guard[key] = Number(document.querySelector(`#${elementId}`).value);
  }
  for (const [key, elementId] of guardCheckboxFields) {
    payload.guard[key] = document.querySelector(`#${elementId}`).checked;
  }
  return payload;
}

function applyPresetToForm(presetName) {
  const preset = PRESETS[presetName];
  if (!preset) {
    return;
  }
  for (const [key, value] of Object.entries(preset)) {
    const numberField = guardNumberFields.find(([fieldKey]) => fieldKey === key);
    const checkboxField = guardCheckboxFields.find(([fieldKey]) => fieldKey === key);
    if (numberField) {
      document.querySelector(`#${numberField[1]}`).value = value;
    } else if (checkboxField) {
      document.querySelector(`#${checkboxField[1]}`).checked = Boolean(value);
    } else if (key === "guard_slowmode_scope") {
      document.querySelector("#guard-slowmode-scope").value = value;
    }
  }
}

function readOptionalSelect(elementId) {
  const raw = document.querySelector(`#${elementId}`).value;
  return raw ? Number(raw) : null;
}

function syncGuildSummary(detail) {
  const index = state.guilds.findIndex((guild) => String(guild.id) === String(detail.id));
  if (index === -1) {
    return;
  }
  state.guilds[index] = {
    ...state.guilds[index],
    guard_enabled: detail.guard_enabled,
    guard_preset: detail.settings.guard_preset,
    recent_cases_24h: detail.recent_cases_24h,
    pending_reminders: detail.pending_reminders,
    active_votes: detail.active_votes,
    runtime_stats: detail.runtime_stats,
  };
}

function formatTimestamp(value) {
  if (!value) {
    return "Never";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Unknown";
  }
  return parsed.toLocaleString();
}

function showToast(message, tone) {
  toast.textContent = message;
  toast.className = `toast ${tone || ""}`;
  toast.classList.remove("hidden");
  window.clearTimeout(showToast.timeoutId);
  showToast.timeoutId = window.setTimeout(() => {
    toast.classList.add("hidden");
  }, 3600);
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
