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
  for (const f of files) form.append("files", f);
  const res = await fetch("/api/upload", { method: "POST", body: form });
  const txt = await res.text();
  try { return { ok: res.ok, data: JSON.parse(txt) }; }
  catch { return { ok: res.ok, data: { _raw: txt } }; }
}

document.addEventListener("DOMContentLoaded", () => {
  const fileInput = document.getElementById("fileInput");
  const uploadBtn = document.getElementById("uploadBtn");
  const runBtn = document.getElementById("runBtn");
  const uploadStatus = document.getElementById("uploadStatus");
  const runStatus = document.getElementById("runStatus");
  const results = document.getElementById("results");
  const statement = document.getElementById("statement");
  const emailTo = document.getElementById("emailTo");
  const emailSubject = document.getElementById("emailSubject");
  const emailBody = document.getElementById("emailBody");

  let uploadedDir = null;

  uploadBtn.addEventListener("click", async () => {
    results.style.display = "none";
    runStatus.textContent = "";
    uploadStatus.textContent = "Uploading…";
    uploadStatus.className = "status warn";

    const files = fileInput.files || [];
    if (!files.length) {
      uploadStatus.textContent = "Please select 1–10 files.";
      uploadStatus.className = "status err";
      return;
    }

    const res = await uploadFiles(files);
    if (!res.ok || !res.data || !res.data.success) {
      uploadStatus.textContent = `Upload failed: ${JSON.stringify(res.data)}`;
      uploadStatus.className = "status err";
      return;
    }

    uploadedDir = res.data.dir;
    uploadStatus.textContent = `Uploaded ${res.data.count} file(s) to ${uploadedDir}`;
    uploadStatus.className = "status ok";
    runBtn.disabled = false;
  });

  runBtn.addEventListener("click", async () => {
    results.style.display = "none";
    statement.textContent = emailTo.textContent = emailSubject.textContent = emailBody.textContent = "";
    runStatus.textContent = "Running pipeline…";
    runStatus.className = "status warn";

    const payload = uploadedDir ? { upload_dir: uploadedDir } : {};
    const res = await postJSON("/api/run", payload);

    // Always display something useful
    if (!res.ok) {
      runStatus.textContent = "Pipeline call failed at HTTP layer.";
      runStatus.className = "status err";
      statement.textContent = JSON.stringify(res.data, null, 2);
      results.style.display = "block";
      return;
    }

    const d = res.data || {};
    if (d.success === false) {
      runStatus.textContent = "Pipeline error.";
      runStatus.className = "status err";
      statement.textContent = JSON.stringify(d, null, 2);
      results.style.display = "block";
      return;
    }

    // Success path: either structured result or raw
    if (d.result && d.result.statement) {
      statement.textContent = d.result.statement;
      const email = d.result.email || {};
      emailTo.textContent = email.to || "(not specified)";
      emailSubject.textContent = email.subject || "(no subject)";
      emailBody.textContent = email.body_text || "(no body)";
      runStatus.textContent = "Pipeline finished.";
      runStatus.className = "status ok";
      results.style.display = "block";
      return;
    }

    // Non-JSON: show raw content for debugging
    runStatus.textContent = d.note || "Pipeline returned non-JSON content.";
    runStatus.className = "status warn";
    statement.textContent = JSON.stringify(d, null, 2);
    results.style.display = "block";
  });
});
