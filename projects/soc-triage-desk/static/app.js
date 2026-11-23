const $ = (selector) => document.querySelector(selector);

const SAMPLE = "2026-11-22T08:10:00Z srv-auth-01 sshd[2101]: Failed password for invalid user admin from 203.0.113.45 port 50110 ssh2\n" +
"2026-11-22T08:10:08Z srv-auth-01 sshd[2102]: Failed password for invalid user administrator from 203.0.113.45 port 50111 ssh2\n" +
"2026-11-22T08:10:15Z srv-auth-01 sshd[2103]: Failed password for test from 203.0.113.45 port 50112 ssh2\n" +
"2026-11-22T08:10:22Z srv-auth-01 sshd[2104]: Failed password for deploy from 203.0.113.45 port 50113 ssh2\n" +
"2026-11-22T08:10:29Z srv-auth-01 sshd[2105]: Failed password for alice from 203.0.113.45 port 50114 ssh2\n" +
"2026-11-22T08:11:02Z srv-auth-01 sshd[2106]: Accepted publickey for alice from 203.0.113.45 port 50115 ssh2\n" +
"2026-11-22T08:15:10Z srv-auth-01 sudo: alice : TTY=pts/0 ; PWD=/home/alice ; USER=root ; COMMAND=/usr/bin/systemctl restart nginx\n" +
"2026-11-22T08:18:00Z srv-auth-02 sshd[3111]: Invalid user guest from 198.51.100.77 port 50120 ssh2\n" +
"2026-11-22T08:18:07Z srv-auth-02 sshd[3112]: Invalid user oracle from 198.51.100.77 port 50121 ssh2\n" +
"2026-11-22T08:18:14Z srv-auth-02 sshd[3113]: Invalid user support from 198.51.100.77 port 50122 ssh2";

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}
async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: Object.assign({"Content-Type":"application/json"}, options.headers || {}),
    ...options,
  });
  if (!response.ok) {
    let message = "Request failed (" + response.status + ")";
    try { message = (await response.json()).detail || message; } catch {}
    throw new Error(message);
  }
  return response.json();
}
function renderSummary(summary) {
  $("#metric-lines").textContent = summary.total_lines;
  $("#metric-events").textContent = summary.parsed_events;
  $("#metric-incidents").textContent = summary.incidents;
  $("#metric-critical").textContent = summary.critical;
  $("#metric-high").textContent = summary.high;
  $("#metric-medium").textContent = summary.medium;
}
function renderIncidents(items) {
  const host = $("#incidents"); host.replaceChildren();
  $("#incident-total").textContent = items.length + " incidents";
  if (!items.length) {
    host.append(el("p","muted","No incidents matched the current detection rules. This does not prove the system is secure."));
    return;
  }
  items.forEach(item => {
    const card = el("article","incident");
    const top = el("div","incident-top");
    top.append(el("span","severity " + item.severity.toLowerCase(),item.severity));
    top.append(el("h3","",item.title));
    top.append(el("span","rule-id",item.rule_id));
    card.append(top);
    card.append(el("p","",item.description));
    card.append(el("p","", "Events: " + item.event_count + " · IPs: " + (item.source_ips.join(", ") || "—") + " · Users: " + (item.usernames.join(", ") || "—")));
    if (item.evidence.length) {
      const evidence = el("div","evidence");
      evidence.textContent = item.evidence.map(e => "Line " + e.line_number + ": " + e.raw).join("\n");
      card.append(evidence);
    }
    host.append(card);
  });
}
function renderEvents(items) {
  const body = $("#events"); body.replaceChildren();
  $("#event-total").textContent = items.length + " events";
  if (!items.length) {
    const row = el("tr"); const cell = el("td","muted","No supported events found.");
    cell.colSpan=5; row.append(cell); body.append(row); return;
  }
  items.forEach(item => {
    const row = el("tr");
    [item.timestamp || "—",item.event_type.replaceAll("_"," "),item.username || "—",item.source_ip || "—",item.host || "—"].forEach((value,index) => {
      row.append(el("td",index===1 ? "event-type" : "",value));
    });
    body.append(row);
  });
}
async function loadRules() {
  const rules = await api("/api/rules");
  const host = $("#rules"); host.replaceChildren();
  rules.forEach(rule => {
    const item = el("div","rule");
    item.append(el("strong","",rule.id + " · " + rule.name));
    item.append(el("span","",rule.severity + " — " + rule.threshold));
    host.append(item);
  });
}
async function loadHistory() {
  const items = await api("/api/history?limit=8");
  const host = $("#history"); host.replaceChildren();
  if (!items.length) { host.append(el("p","muted","No saved analyses yet.")); return; }
  items.forEach(item => {
    const row = el("div","history-item");
    row.append(el("strong","",item.source_name));
    row.append(el("span","",item.parsed_events + " events · " + item.incidents + " incidents · " + item.created_at));
    host.append(row);
  });
}
$("#sample-btn").addEventListener("click", () => {
  $("#log-input").value = SAMPLE;
  $("#source-name").value = "SSH authentication demo sample";
  $("#message").textContent = "Sample loaded. Run the analysis.";
});
$("#analyze-btn").addEventListener("click", async () => {
  const button = $("#analyze-btn");
  const logText = $("#log-input").value;
  if (!logText.trim()) { $("#message").textContent = "Paste a log sample or load the demo first."; return; }
  button.disabled = true; $("#message").textContent = "Analyzing…";
  try {
    const result = await api("/api/analyze", {
      method:"POST",
      body:JSON.stringify({source_name:$("#source-name").value || "Pasted authentication log",log_text:logText}),
    });
    renderSummary(result.summary);
    renderIncidents(result.incidents);
    renderEvents(result.events);
    $("#message").textContent = "Analysis #" + result.id + " saved. Ignored lines: " + result.summary.ignored_lines + ".";
    await loadHistory();
  } catch (error) {
    $("#message").textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
Promise.all([loadRules(),loadHistory()]).catch(error => { $("#message").textContent = error.message; });
