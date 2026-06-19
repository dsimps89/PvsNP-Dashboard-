let catalog = [];
let selected = null;

const el = (id) => document.getElementById(id);

function setStatus(message) {
  el("status").textContent = message;
}

function renderList(items) {
  const box = el("problemList");
  box.innerHTML = "";
  items.forEach((item) => {
    const div = document.createElement("div");
    div.className = "problem";
    div.innerHTML = `
      <div class="title">${item.title}</div>
      <div class="sub">Page ${item.page} · ${item.status || 'unknown'} · ${item.functions.length} functions · ${item.warnings.length} warnings</div>
    `;
    div.onclick = () => selectProblem(item);
    box.appendChild(div);
  });
}

function selectProblem(item) {
  selected = item;
  el("selectedTitle").textContent = item.title;
  el("meta").innerHTML = `<span class="badge">Page ${item.page}</span><span class="badge">${item.status || 'unknown'}</span><span class="badge">${item.id}</span>`;
  el("codeView").textContent = item.code;

  el("warnings").innerHTML = "";
  item.warnings.forEach((warning) => {
    const li = document.createElement("li");
    li.textContent = warning;
    el("warnings").appendChild(li);
  });

  el("functions").innerHTML = "";
  item.functions.forEach((fn) => {
    const span = document.createElement("span");
    span.className = "badge";
    span.textContent = `${fn.name}(${fn.args.join(", ")})`;
    span.onclick = () => el("functionName").value = fn.name;
    el("functions").appendChild(span);
  });

  if (item.functions.length) {
    el("functionName").value = item.functions[0].name;
  }
}

el("uploadBtn").onclick = async () => {
  const file = el("pdfInput").files[0];
  if (!file) {
    setStatus("Select a PDF first.");
    return;
  }

  setStatus("Uploading and compiling catalog...");
  const form = new FormData();
  form.append("pdf", file);

  const res = await fetch("/api/upload", { method: "POST", body: form });
  const data = await res.json();

  if (!res.ok) {
    setStatus(data.error || "Upload failed.");
    return;
  }

  catalog = data.items || [];
  renderList(catalog);
  setStatus(`Compiled ${data.item_count} sections from ${data.page_count} pages. Warnings: ${data.summary.warning_count}`);
  if (catalog.length) selectProblem(catalog[0]);
};

el("search").oninput = () => {
  const q = el("search").value.toLowerCase();
  renderList(catalog.filter(item =>
    item.title.toLowerCase().includes(q) ||
    item.code.toLowerCase().includes(q)
  ));
};

el("runBtn").onclick = async () => {
  if (!selected) {
    el("runOutput").textContent = "No problem selected.";
    return;
  }

  let args = [];
  try {
    args = JSON.parse(el("argsJson").value || "[]");
  } catch {
    el("runOutput").textContent = "Args must be valid JSON.";
    return;
  }

  const res = await fetch("/api/run", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      code: selected.code,
      function_name: el("functionName").value,
      args,
      kwargs: {}
    })
  });

  const data = await res.json();
  el("runOutput").textContent = JSON.stringify(data, null, 2);
};