// // async function postRun() {
// //   const res = await fetch("/api/run", { method: "POST" });
// //   const txt = await res.text();
// //   try { return { ok: res.ok, data: JSON.parse(txt) }; }
// //   catch { return { ok: res.ok, data: txt }; }
// // }
// // document.addEventListener("DOMContentLoaded", () => {
// //   const runBtn = document.getElementById("runBtn");
// //   const runStatus = document.getElementById("runStatus");
// //   const results = document.getElementById("results");
// //   const statement = document.getElementById("statement");
// //   const emailTo = document.getElementById("emailTo");
// //   const emailSubject = document.getElementById("emailSubject");
// //   const emailBody = document.getElementById("emailBody");

// //   runBtn.addEventListener("click", async () => {
// //     results.style.display = "none";
// //     statement.textContent = emailTo.textContent = emailSubject.textContent = emailBody.textContent = "";
// //     runStatus.textContent = "Running pipeline…";
// //     runStatus.className = "status warn";

// //     const res = await postRun();
// //     if (!res.ok) {
// //       runStatus.textContent = "Pipeline failed.";
// //       runStatus.className = "status err";
// //       return;
// //     }

// //     const payload = res.data || {};
// //     const result = payload.result || payload; // accept either {result:{...}} or direct payload

// //     if (result.error) {
// //       runStatus.textContent = "Pipeline error.";
// //       runStatus.className = "status err";
// //       statement.textContent = JSON.stringify(result, null, 2);
// //       results.style.display = "block";
// //       return;
// //     }

// //     const finalStatement = result.statement || "<no statement>";
// //     const email = result.email || {};
// //     statement.textContent = finalStatement;
// //     emailTo.textContent = email.to || "(not specified)";
// //     emailSubject.textContent = email.subject || "(no subject)";
// //     emailBody.textContent = email.body_text || "(no body)";

// //     runStatus.textContent = "Pipeline finished.";
// //     runStatus.className = "status ok";
// //     results.style.display = "block";
// //   });
// // });

// async function postJSON(url, body) {
//   const res = await fetch(url, {
//     method: "POST",
//     headers: { "Content-Type": "application/json" },
//     body: body ? JSON.stringify(body) : "{}",
//   });
//   const txt = await res.text();
//   try { return { ok: res.ok, data: JSON.parse(txt) }; }
//   catch { return { ok: res.ok, data: txt }; }
// }

// async function uploadFiles(files) {
//   const form = new FormData();
//   for (const f of files) form.append("files", f);
//   const res = await fetch("/api/upload", { method: "POST", body: form });
//   const txt = await res.text();
//   try { return { ok: res.ok, data: JSON.parse(txt) }; }
//   catch { return { ok: res.ok, data: txt }; }
// }

// document.addEventListener("DOMContentLoaded", () => {
//   const fileInput = document.getElementById("fileInput");
//   const uploadBtn = document.getElementById("uploadBtn");
//   const runBtn = document.getElementById("runBtn");
//   const uploadStatus = document.getElementById("uploadStatus");
//   const runStatus = document.getElementById("runStatus");
//   const results = document.getElementById("results");
//   const statement = document.getElementById("statement");
//   const emailTo = document.getElementById("emailTo");
//   const emailSubject = document.getElementById("emailSubject");
//   const emailBody = document.getElementById("emailBody");

//   let uploadedDir = null;

//   uploadBtn.addEventListener("click", async () => {
//     results.style.display = "none";
//     runStatus.textContent = "";
//     uploadStatus.textContent = "Uploading…";
//     uploadStatus.className = "status warn";

//     const files = fileInput.files || [];
//     if (!files.length) {
//       uploadStatus.textContent = "Please select 1–10 files.";
//       uploadStatus.className = "status err";
//       return;
//     }

//     const res = await uploadFiles(files);
//     if (!res.ok || !res.data || !res.data.success) {
//       uploadStatus.textContent = "Upload failed.";
//       uploadStatus.className = "status err";
//       return;
//     }

//     uploadedDir = res.data.dir;
//     uploadStatus.textContent = `Uploaded ${res.data.count} file(s) to ${uploadedDir}`;
//     uploadStatus.className = "status ok";
//     runBtn.disabled = false;
//   });

//   runBtn.addEventListener("click", async () => {
//     results.style.display = "none";
//     statement.textContent = emailTo.textContent = emailSubject.textContent = emailBody.textContent = "";
//     runStatus.textContent = "Running pipeline…";
//     runStatus.className = "status warn";

//     const payload = uploadedDir ? { upload_dir: uploadedDir } : {};
//     const res = await postJSON("/api/run", payload);
//     if (!res.ok) {
//       runStatus.textContent = "Pipeline failed.";
//       runStatus.className = "status err";
//       return;
//     }

//     const result = res.data.result || res.data; // accept {result:{...}} or direct
//     if (result.error) {
//       runStatus.textContent = "Pipeline error.";
//       runStatus.className = "status err";
//       statement.textContent = JSON.stringify(result, null, 2);
//       results.style.display = "block";
//       return;
//     }

//     statement.textContent = (result.statement || "<no statement>");
//     const email = result.email || {};
//     emailTo.textContent = email.to || "(not specified)";
//     emailSubject.textContent = email.subject || "(no subject)";
//     emailBody.textContent = email.body_text || "(no body)";

//     runStatus.textContent = "Pipeline finished.";
//     runStatus.className = "status ok";
//     results.style.display = "block";
//   });
// });

// webapp/static/app.js
const StatusTone = {
  OK: "ok",
  WARN: "warn",
  ERROR: "err",
  INFO: "info",
};

async function getJSON(url) {
  const res = await fetch(url);
  const txt = await res.text();
  try { return { ok: res.ok, data: JSON.parse(txt) }; }
  catch { return { ok: res.ok, data: { _raw: txt } }; }
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : "{}",
  });
  const txt = await res.text();
  try { return { ok: res.ok, data: JSON.parse(txt) }; }
  catch { return { ok: res.ok, data: { _raw: txt } }; }
}

async function uploadFiles(files) {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  const res = await fetch("/api/upload", { method: "POST", body: form });
  const txt = await res.text();
  try { return { ok: res.ok, data: JSON.parse(txt) }; }
  catch { return { ok: res.ok, data: { _raw: txt } }; }
}

function formatSize(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "—";
  const units = ["B", "KB", "MB", "GB"];
  const idx = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const value = bytes / 1024 ** idx;
  return `${value.toFixed(value >= 10 || idx === 0 ? 0 : 1)} ${units[idx]}`;
}

function setStatus(node, message, tone = StatusTone.INFO) {
  if (!node) return;
  node.textContent = message;
  node.className = `status ${tone ? tone : ""}`.trim();
}

function toggleBusy(button, busy, showSpinner = true) {
  if (!button) return;
  button.disabled = Boolean(busy);
  if (showSpinner) {
    button.classList.toggle("is-loading", Boolean(busy));
  } else {
    button.classList.remove("is-loading");
  }
}

function createLogEntry(message, tone = StatusTone.INFO) {
  const li = document.createElement("li");
  li.className = `log-entry ${tone}`;
  const time = document.createElement("time");
  const now = new Date();
  time.dateTime = now.toISOString();
  time.textContent = now.toLocaleTimeString();
  const span = document.createElement("span");
  span.textContent = message;
  li.append(time, span);
  return li;
}

document.addEventListener("DOMContentLoaded", () => {
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const browseBtn = document.getElementById("browseBtn");
  const clearBtn = document.getElementById("clearBtn");
  const uploadBtn = document.getElementById("uploadBtn");
  const runBtn = document.getElementById("runBtn");
  const uploadStatus = document.getElementById("uploadStatus");
  const runStatus = document.getElementById("runStatus");
  const fileList = document.getElementById("fileList");
  const pipelineLog = document.getElementById("pipelineLog");
  const results = document.getElementById("results");
  const statement = document.getElementById("statement");
  const emailTo = document.getElementById("emailTo");
  const emailSubject = document.getElementById("emailSubject");
  const emailBody = document.getElementById("emailBody");
  const rawPanel = document.getElementById("rawPanel");
  const rawOutput = document.getElementById("rawOutput");
  const toggleRaw = document.getElementById("toggleRaw");
  const copyStatement = document.getElementById("copyStatement");
  const healthBtn = document.getElementById("healthCheck");
  const acceptedExts = document.getElementById("acceptedExts");
  const fileLimit = document.getElementById("fileLimit");

  const selection = new Map();
  let uploadedDir = null;

  function resetResults() {
    if (results) results.hidden = true;
    if (statement) statement.textContent = "";
    if (emailTo) emailTo.textContent = "—";
    if (emailSubject) emailSubject.textContent = "—";
    if (emailBody) emailBody.textContent = "";
    if (rawOutput) rawOutput.textContent = "";
    if (rawPanel) rawPanel.hidden = true;
    if (toggleRaw) {
      toggleRaw.dataset.open = "false";
      toggleRaw.textContent = "Show raw JSON";
    }
  }

  function renderFileList() {
    fileList.innerHTML = "";
    if (!selection.size) {
      const empty = document.createElement("li");
      empty.className = "file-empty";
      empty.textContent = "No files selected yet.";
      fileList.appendChild(empty);
      return;
    }

    for (const [key, file] of selection.entries()) {
      const li = document.createElement("li");
      li.className = "file-item";
      li.dataset.key = key;

      const name = document.createElement("span");
      name.className = "file-name";
      name.textContent = file.name;

      const meta = document.createElement("span");
      meta.className = "file-meta";
      meta.textContent = formatSize(file.size);

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "chip remove";
      remove.textContent = "Remove";
      remove.addEventListener("click", () => {
        selection.delete(key);
        renderFileList();
      });

      li.append(name, meta, remove);
      fileList.appendChild(li);
    }
  }

  function addFiles(fileLikeList) {
    Array.from(fileLikeList || []).forEach((file) => {
      const key = `${file.name}-${file.lastModified}-${file.size}`;
      selection.set(key, file);
    });
    renderFileList();
    setStatus(uploadStatus, `${selection.size} file(s) ready to upload.`, StatusTone.INFO);
    toggleBusy(runBtn, true, false);
  }

  function clearSelection() {
    selection.clear();
    renderFileList();
    fileInput.value = "";
    uploadedDir = null;
    toggleBusy(runBtn, true, false);
    setStatus(uploadStatus, "Selection cleared.", StatusTone.INFO);
  }

  function appendLog(message, tone = StatusTone.INFO) {
    if (!pipelineLog) return;
    const entry = createLogEntry(message, tone);
    pipelineLog.appendChild(entry);
    pipelineLog.scrollTop = pipelineLog.scrollHeight;
  }

  function clearLog() {
    pipelineLog.innerHTML = "";
  }

  renderFileList();
  toggleBusy(runBtn, true, false);

  browseBtn?.addEventListener("click", () => fileInput.click());
  dropZone?.addEventListener("click", () => fileInput.click());
  dropZone?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInput.click();
    }
  });
  dropZone?.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropZone.classList.add("is-dragging");
  });
  dropZone?.addEventListener("dragleave", () => dropZone.classList.remove("is-dragging"));
  dropZone?.addEventListener("drop", (event) => {
    event.preventDefault();
    dropZone.classList.remove("is-dragging");
    addFiles(event.dataTransfer?.files);
  });
  fileInput?.addEventListener("change", (event) => addFiles(event.target.files));
  clearBtn?.addEventListener("click", clearSelection);

  uploadBtn?.addEventListener("click", async () => {
    if (!selection.size) {
      setStatus(uploadStatus, "Select 1 or more supported files first.", StatusTone.ERROR);
      return;
    }

    resetResults();
    setStatus(uploadStatus, "Uploading files…", StatusTone.WARN);
    toggleBusy(uploadBtn, true);
    toggleBusy(clearBtn, true, false);
    toggleBusy(browseBtn, true, false);
    toggleBusy(runBtn, true, false);

    const files = Array.from(selection.values());
    const response = await uploadFiles(files);

    toggleBusy(uploadBtn, false);
    toggleBusy(clearBtn, false, false);
    toggleBusy(browseBtn, false, false);

    if (!response.ok || !response.data?.success) {
      const message = response.data?.error || "Upload failed.";
      setStatus(uploadStatus, message, StatusTone.ERROR);
      toggleBusy(runBtn, true, false);
      return;
    }

    uploadedDir = response.data.dir;
    toggleBusy(runBtn, false);

    const skipped = response.data.skipped?.length
      ? ` Skipped: ${response.data.skipped.join(", ")}.`
      : "";
    const uploadedNames = new Set(
      Array.isArray(response.data.files)
        ? response.data.files.map((file) => file.name)
        : [],
    );
    fileList.querySelectorAll(".file-item").forEach((item) => {
      const nameNode = item.querySelector(".file-name");
      if (!nameNode) return;
      item.classList.toggle("uploaded", uploadedNames.has(nameNode.textContent));
    });
    setStatus(
      uploadStatus,
      `Uploaded ${response.data.count} file(s) to ${uploadedDir}.${skipped}`,
      StatusTone.OK,
    );
    appendLog("Documents uploaded. Ready to run pipeline.", StatusTone.OK);
  });

  runBtn?.addEventListener("click", async () => {
    if (!uploadedDir) {
      setStatus(runStatus, "Upload files before running the pipeline.", StatusTone.ERROR);
      return;
    }

    resetResults();
    clearLog();
    setStatus(runStatus, "Invoking policy agent…", StatusTone.WARN);
    appendLog("Calling policy_agent via ACP…", StatusTone.WARN);
    toggleBusy(runBtn, true);

    const payload = { upload_dir: uploadedDir };
    const response = await postJSON("/api/run", payload);

    toggleBusy(runBtn, false);

    if (!response.ok) {
      setStatus(runStatus, "Pipeline call failed at HTTP layer.", StatusTone.ERROR);
      if (statement) statement.textContent = JSON.stringify(response.data, null, 2);
      if (results) results.hidden = false;
      appendLog("HTTP error while contacting policy server.", StatusTone.ERROR);
      return;
    }

    const data = response.data || {};
    if (data.success === false) {
      setStatus(runStatus, "Pipeline reported an error.", StatusTone.ERROR);
      if (statement) statement.textContent = JSON.stringify(data, null, 2);
      if (results) results.hidden = false;
      appendLog(data.error || "Pipeline error", StatusTone.ERROR);
      return;
    }

    appendLog("Pipeline finished.", StatusTone.OK);

    const result = data.result || {};
    if (result.statement) {
      statement.textContent = result.statement;
    } else if (data.result_raw) {
      statement.textContent = data.result_raw;
    } else {
      statement.textContent = JSON.stringify(data, null, 2);
    }

    const email = result.email || {};
    if (emailTo) emailTo.textContent = email.to || "—";
    if (emailSubject) emailSubject.textContent = email.subject || "—";
    if (emailBody) emailBody.textContent = email.body_text || "";

    if (data.result_raw || Object.keys(result).length === 0) {
      if (rawOutput) rawOutput.textContent = JSON.stringify(data, null, 2);
      if (rawPanel) rawPanel.hidden = false;
      if (toggleRaw) {
        toggleRaw.dataset.open = "true";
        toggleRaw.textContent = "Hide raw JSON";
      }
    } else {
      if (rawOutput) rawOutput.textContent = JSON.stringify(data, null, 2);
      if (rawPanel) rawPanel.hidden = true;
      if (toggleRaw) {
        toggleRaw.dataset.open = "false";
        toggleRaw.textContent = "Show raw JSON";
      }
    }

    setStatus(runStatus, "Pipeline finished.", StatusTone.OK);
    if (results) results.hidden = false;
  });

  toggleRaw?.addEventListener("click", () => {
    const isOpen = toggleRaw.dataset.open === "true";
    if (rawPanel) rawPanel.hidden = isOpen;
    toggleRaw.dataset.open = isOpen ? "false" : "true";
    toggleRaw.textContent = isOpen ? "Show raw JSON" : "Hide raw JSON";
  });

  copyStatement?.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(statement?.textContent || "");
      copyStatement.textContent = "Copied!";
      setTimeout(() => { copyStatement.textContent = "Copy statement"; }, 2000);
    } catch (err) {
      copyStatement.textContent = "Copy failed";
      setTimeout(() => { copyStatement.textContent = "Copy statement"; }, 2000);
    }
  });

  healthBtn?.addEventListener("click", async () => {
    toggleBusy(healthBtn, true);
    const response = await getJSON("/api/health");
    toggleBusy(healthBtn, false);

    if (!response.ok) {
      appendLog("Health check failed.", StatusTone.ERROR);
      setStatus(runStatus, "Health check failed.", StatusTone.ERROR);
      return;
    }

    const info = response.data || {};
    const msg = info.ok
      ? `Policy server reachable at ${info.policy_server}.`
      : "Policy server reported a problem.";
    appendLog(msg, info.ok ? StatusTone.OK : StatusTone.ERROR);
    setStatus(runStatus, msg, info.ok ? StatusTone.OK : StatusTone.ERROR);
  });

  (async () => {
    const response = await getJSON("/api/health");
    if (response.ok && response.data) {
      const { allowed_extensions, max_upload_files } = response.data;
      if (Array.isArray(allowed_extensions) && allowed_extensions.length) {
        acceptedExts.textContent = allowed_extensions
          .map((ext) => ext.replace(/^\./, "").toUpperCase())
          .join(", ");
      }
      if (max_upload_files) {
        fileLimit.textContent = `${max_upload_files} file${max_upload_files === 1 ? "" : "s"} per run`;
      }
    }
  })();
});
