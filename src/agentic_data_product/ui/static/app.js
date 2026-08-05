(() => {
  const STAGES = [
    { type: "business_requirement", label: "Business Requirement" },
    { type: "technical_requirement", label: "Technical Requirement" },
    { type: "data_model", label: "Data Model (mapping)" },
    { type: "semantic_model", label: "Semantic Model" },
    { type: "pipeline_specification", label: "Pipeline Specification" },
    { type: "metric_definitions", label: "Metric Definitions" },
    { type: "review_package", label: "Review Package" },
  ];

  const state = {
    runId: null,
    detail: null,
    artefacts: [],
    events: [],
    reviewerId: "consultant",
  };

  const $ = (id) => document.getElementById(id);

  function lines(text) {
    return text
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
  }

  function csv(text) {
    return text
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  }

  async function api(path, options = {}) {
    const resp = await fetch(path, {
      headers: { "content-type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const text = await resp.text();
    let body = null;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      body = text;
    }
    if (!resp.ok) {
      const detail = body && body.detail ? body.detail : text || resp.statusText;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return body;
  }

  async function loadConfig() {
    try {
      const profile = await api("/config/profile");
      $("config-chip").textContent =
        `${profile.profile_name} · ${profile.llm_provider}/${profile.llm_model} · graph=${profile.graph}`;
    } catch (err) {
      $("config-chip").textContent = `Config unavailable: ${err.message}`;
    }
  }

  function setStatus(status) {
    const el = $("run-status");
    el.textContent = status;
    el.className = `status-badge ${status}`;
  }

  function renderStages(detail, artefacts) {
    const present = new Map();
    for (const ref of artefacts) {
      const prev = present.get(ref.artefact_type);
      if (!prev || ref.version > prev.version) present.set(ref.artefact_type, ref);
    }
    const pendingType = detail.pending_review?.artefact?.artefact_type || null;
    const status = detail.run.status;
    const list = $("stage-list");
    list.innerHTML = "";
    for (const stage of STAGES) {
      const li = document.createElement("li");
      const ref = present.get(stage.type);
      let tag = "not started";
      if (ref) tag = `v${ref.version}`;
      if (pendingType === stage.type && status === "waiting_for_review") {
        li.classList.add("current");
        tag = `${tag} · waiting for review`;
      } else if (ref) {
        li.classList.add("done");
      }
      if (status === "approved" && stage.type === "review_package" && ref) {
        li.classList.add("done");
        tag = `${tag} · approved`;
      }
      li.innerHTML = `<span>${stage.label}</span><span class="tag">${tag}</span>`;
      list.appendChild(li);
    }
  }

  function renderArtefactSelect(artefacts, pending) {
    const select = $("artefact-select");
    select.innerHTML = "";
    const preferredId = pending?.artefact?.artefact_id;
    const preferredVersion = pending?.artefact?.version;
    const sorted = [...artefacts].sort((a, b) =>
      a.artefact_type === b.artefact_type
        ? b.version - a.version
        : a.artefact_type.localeCompare(b.artefact_type),
    );
    for (const ref of sorted) {
      const opt = document.createElement("option");
      opt.value = `${ref.artefact_id}|${ref.version}`;
      opt.textContent = `${ref.artefact_type} v${ref.version}`;
      if (
        preferredId &&
        ref.artefact_id === preferredId &&
        ref.version === preferredVersion
      ) {
        opt.selected = true;
      }
      select.appendChild(opt);
    }
  }

  function renderPending(detail) {
    const pending = detail.pending_review;
    const el = $("pending-meta");
    if (!pending) {
      el.textContent =
        detail.run.status === "approved"
          ? "Run approved — no pending review."
          : detail.run.status === "terminated"
            ? "Run terminated — no pending review."
            : "No pending review.";
      return;
    }
    const a = pending.artefact;
    el.textContent = `Pending: ${a.artefact_type} v${a.version}${
      pending.feedback ? ` · feedback: ${pending.feedback}` : ""
    }`;
  }

  function renderEvents(events) {
    const root = $("events-list");
    root.innerHTML = "";
    if (!events.length) {
      root.textContent = "No events yet.";
      return;
    }
    for (const ev of [...events].reverse()) {
      const div = document.createElement("div");
      div.className = "event";
      div.innerHTML = `<strong>${ev.action}</strong> · ${ev.entity_type} ${ev.entity_id}
        <div class="meta">${ev.created_at}${ev.actor ? ` · ${ev.actor}` : ""} · ${JSON.stringify(ev.details)}</div>`;
      root.appendChild(div);
    }
  }

  function setDecisionEnabled(enabled) {
    $("approve-btn").disabled = !enabled;
    $("reject-btn").disabled = !enabled;
    $("revisions-btn").disabled = !enabled;
  }

  async function loadArtefact() {
    if (!state.runId) return;
    const value = $("artefact-select").value;
    if (!value) return;
    const [artefactId, version] = value.split("|");
    const artefact = await api(
      `/runs/${state.runId}/artefacts/${artefactId}?version=${encodeURIComponent(version)}`,
    );
    $("artefact-viewer").textContent = JSON.stringify(artefact, null, 2);
  }

  async function refreshRun() {
    if (!state.runId) return;
    const [detail, artefacts, events] = await Promise.all([
      api(`/runs/${state.runId}`),
      api(`/runs/${state.runId}/artefacts`),
      api(`/runs/${state.runId}/events`),
    ]);
    state.detail = detail;
    state.artefacts = artefacts;
    state.events = events;
    $("run-id").textContent = detail.run.run_id;
    setStatus(detail.run.status);
    renderStages(detail, artefacts);
    renderPending(detail);
    renderArtefactSelect(artefacts, detail.pending_review);
    renderEvents(events);
    setDecisionEnabled(detail.run.status === "waiting_for_review");
    if (detail.pending_review || artefacts.length) {
      try {
        await loadArtefact();
      } catch (err) {
        $("artefact-viewer").textContent = `Failed to load artefact: ${err.message}`;
      }
    }
  }

  async function startRun(event) {
    event.preventDefault();
    $("submit-error").hidden = true;
    $("start-btn").disabled = true;
    const form = new FormData(event.target);
    state.reviewerId = String(form.get("created_by") || "consultant");
    const body = {
      title: String(form.get("title") || "").trim(),
      created_by: state.reviewerId,
      business_requirement: {
        title: String(form.get("title") || "").trim(),
        intent: String(form.get("intent") || "").trim(),
        objectives: lines(String(form.get("objectives") || "")),
        constraints: lines(String(form.get("constraints") || "")),
        success_criteria: lines(String(form.get("success_criteria") || "")),
        stakeholders: csv(String(form.get("stakeholders") || "")),
      },
      user_context: { user_id: state.reviewerId },
    };
    try {
      const detail = await api("/runs", { method: "POST", body: JSON.stringify(body) });
      state.runId = detail.run.run_id;
      $("run-panel").hidden = false;
      await refreshRun();
      $("run-panel").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      $("submit-error").textContent = err.message;
      $("submit-error").hidden = false;
    } finally {
      $("start-btn").disabled = false;
    }
  }

  async function submitDecision(decision) {
    if (!state.runId) return;
    $("decision-error").hidden = true;
    setDecisionEnabled(false);
    try {
      await api(`/runs/${state.runId}/reviews`, {
        method: "POST",
        body: JSON.stringify({
          decision,
          comments: $("review-comments").value || "",
          reviewer_id: state.reviewerId,
        }),
      });
      $("review-comments").value = "";
      await refreshRun();
    } catch (err) {
      $("decision-error").textContent = err.message;
      $("decision-error").hidden = false;
      setDecisionEnabled(state.detail?.run?.status === "waiting_for_review");
    }
  }

  $("br-form").addEventListener("submit", startRun);
  $("refresh-btn").addEventListener("click", () => {
    refreshRun().catch((err) => {
      $("decision-error").textContent = err.message;
      $("decision-error").hidden = false;
    });
  });
  $("load-artefact-btn").addEventListener("click", () => {
    loadArtefact().catch((err) => {
      $("artefact-viewer").textContent = err.message;
    });
  });
  $("approve-btn").addEventListener("click", () => submitDecision("approve"));
  $("reject-btn").addEventListener("click", () => submitDecision("reject"));
  $("revisions-btn").addEventListener("click", () => submitDecision("request_revisions"));

  // Deep-link: /ui/?run_id=...
  const params = new URLSearchParams(window.location.search);
  const existing = params.get("run_id");
  loadConfig();
  if (existing) {
    state.runId = existing;
    $("run-panel").hidden = false;
    refreshRun().catch((err) => {
      $("decision-error").textContent = err.message;
      $("decision-error").hidden = false;
    });
  }
})();
