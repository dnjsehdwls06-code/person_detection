// person_detection 프론트엔드 (해시 라우팅 SPA)
const $ = (s) => document.querySelector(s);
const VIEWS = ["dashboard", "analyze", "result", "history", "stats", "users"];
let me = null;
let chart = null;

// ---------- 공통 유틸 ----------
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmtTime = (iso) => iso ? iso.replace("T", " ") : "";
const today = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const daysAgo = (n) => new Date(Date.now() - new Date().getTimezoneOffset() * 60000 - n * 86400000).toISOString().slice(0, 10);
const badge = (s) => `<span class="badge ${s}">${s === "COMPLETED" ? "성공" : "실패"}</span>`;

function toast(msg, isErr = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast" + (isErr ? " err" : "");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.add("hidden"), 3000);
}
const loading = (on) => $("#loading").classList.toggle("hidden", !on);
function showError(sel, msg) { const el = $(sel); el.textContent = msg || ""; el.classList.toggle("hidden", !msg); }

async function api(url, opts = {}) {
  const res = await fetch(url, opts);
  let data = null;
  try { data = await res.json(); } catch { /* 본문 없음 */ }
  if (res.status === 401 && !url.startsWith("/auth/")) { showLogin(); throw new Error("로그인이 필요합니다."); }
  if (!res.ok) throw new Error(data?.detail || "요청을 처리하지 못했습니다.");
  return data;
}
const jsonOpts = (method, body) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

// ---------- 로그인 / 라우팅 ----------
function showLogin() {
  me = null;
  $("#app-view").classList.add("hidden");
  $("#login-view").classList.remove("hidden");
}

function showApp() {
  $("#login-view").classList.add("hidden");
  $("#app-view").classList.remove("hidden");
  $("#whoami").textContent = `${me.display_name} (${me.username})`;
  route();
}

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  showError("#login-error", "");
  try {
    const data = await api("/auth/login", jsonOpts("POST", { username: f.get("username"), password: f.get("password") }));
    me = data.user;
    e.target.reset();
    if (!location.hash) location.hash = "#dashboard";
    showApp();
  } catch (err) { showError("#login-error", err.message); }
});

$("#logout-btn").addEventListener("click", async () => {
  await fetch("/auth/logout", { method: "POST" });
  location.hash = "";
  showLogin();
});

function route() {
  if (!me) return;
  const [name, arg] = (location.hash.slice(1) || "dashboard").split("/");
  const view = VIEWS.includes(name) ? name : "dashboard";
  VIEWS.forEach((v) => $(`#view-${v}`).classList.toggle("hidden", v !== view));
  document.querySelectorAll(".sidebar nav a").forEach((a) =>
    a.classList.toggle("active", a.dataset.view === (view === "result" ? "history" : view)));
  ({ dashboard: loadDashboard, analyze: () => {}, result: () => loadResult(arg), history: loadHistory, stats: loadStats, users: loadUsers })[view]();
}
window.addEventListener("hashchange", route);

// ---------- 대시보드 ----------
async function loadDashboard() {
  try {
    const [s, recent] = await Promise.all([api("/api/stats/summary"), api("/api/analyses?limit=5")]);
    $("#sum-faces").textContent = s.today_faces;
    $("#sum-ok").textContent = s.today_completed;
    $("#sum-fail").textContent = s.today_failed;
    $("#sum-total").textContent = s.total_analyses;
    $("#recent-body").innerHTML = recent.length ? recent.map((a) => `
      <tr><td><a href="#result/${a.id}">#${a.id}</a></td><td>${fmtTime(a.analyzed_at)}</td><td>${esc(a.original_name)}</td>
      <td>${a.face_count ?? "-"}</td><td>${badge(a.status)}</td></tr>`).join("")
      : `<tr><td colspan="5" class="empty">아직 분석 이력이 없습니다.</td></tr>`;
  } catch (err) { toast(err.message, true); }
}

// ---------- 이미지 업로드 / 분석 ----------
const fileInput = $("#file-input");
const drop = $("#drop");

function setPreview(file) {
  if (!file) return;
  $("#preview").src = URL.createObjectURL(file);
  $("#preview").classList.remove("hidden");
  $("#drop-text").innerHTML = `${esc(file.name)}<br><small>${(file.size / 1024 / 1024).toFixed(2)} MB</small>`;
  showError("#upload-error", "");
}
fileInput.addEventListener("change", () => setPreview(fileInput.files[0]));
["dragover", "dragenter"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, () => drop.classList.remove("over")));
drop.addEventListener("drop", (e) => {
  e.preventDefault();
  if (e.dataTransfer.files.length) { fileInput.files = e.dataTransfer.files; setPreview(fileInput.files[0]); }
});

function resultHtml(a) {
  if (a.status !== "COMPLETED") {
    return `<p>${badge(a.status)} 분석 #${a.id} · ${fmtTime(a.analyzed_at)}</p>
      <p class="error">${esc(a.failure_reason || "분석에 실패했습니다.")}</p>
      <button class="btn primary" onclick="retryAnalysis(${a.id})">재분석</button>`;
  }
  return `<p>${badge(a.status)} 분석 #${a.id} · ${fmtTime(a.analyzed_at)}${a.retry_of ? ` · #${a.retry_of}의 재분석` : ""}</p>
    <div class="muted">검출된 얼굴 수</div>
    <div class="result-count">${a.face_count}명</div>
    <p class="notice">※ 이미지에서 검출된 <b>얼굴 수</b>입니다. 뒷모습·정수리만 보이는 탑뷰 사진 등에서는 실제 고객 수와 다를 수 있습니다.</p>
    <img class="result-img" src="/api/analyses/${a.id}/image?kind=result&t=${Date.now()}" alt="얼굴 검출 결과 이미지">
    <p class="muted">파일: ${esc(a.original_name)}</p>`;
}

$("#upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = fileInput.files[0];
  if (!file) return showError("#upload-error", "분석할 이미지 파일을 선택해 주세요.");
  const body = new FormData();
  body.append("file", file);
  $("#analyze-btn").disabled = true;
  loading(true);
  try {
    const a = await api("/api/analyses", { method: "POST", body });
    $("#analyze-result").innerHTML = `<h2>분석 결과</h2>` + resultHtml(a);
    toast(a.status === "COMPLETED" ? `분석 완료: 얼굴 ${a.face_count}명` : "분석에 실패했습니다.", a.status !== "COMPLETED");
  } catch (err) {
    showError("#upload-error", err.message);
  } finally {
    $("#analyze-btn").disabled = false;
    loading(false);
  }
});

async function loadResult(id) {
  try {
    const a = await api(`/api/analyses/${encodeURIComponent(id)}`);
    $("#result-detail").innerHTML = resultHtml(a) + `<p><a class="btn" href="#history">← 이력으로</a></p>`;
  } catch (err) {
    $("#result-detail").innerHTML = `<p class="error">${esc(err.message)}</p>`;
  }
}

async function retryAnalysis(id) {
  loading(true);
  try {
    const a = await api(`/api/analyses/${id}/retry`, { method: "POST" });
    toast(a.status === "COMPLETED" ? `재분석 완료 (#${a.id}): 얼굴 ${a.face_count}명` : "재분석도 실패했습니다.", a.status !== "COMPLETED");
    location.hash = `#result/${a.id}`;
  } catch (err) { toast(err.message, true); }
  finally { loading(false); }
}
window.retryAnalysis = retryAnalysis;

// ---------- 분석 이력 ----------
async function loadHistory() {
  const f = new FormData($("#history-form"));
  const q = new URLSearchParams({ order: f.get("order") });
  if (f.get("start")) q.set("start", f.get("start"));
  if (f.get("end")) q.set("end", f.get("end"));
  if (f.get("start") && f.get("end") && f.get("end") < f.get("start")) {
    return showError("#history-error", "종료일이 시작일보다 빠를 수 없습니다.");
  }
  showError("#history-error", "");
  try {
    const rows = await api(`/api/analyses?${q}`);
    $("#history-body").innerHTML = rows.length ? rows.map((a) => `
      <tr><td>#${a.id}</td><td>${fmtTime(a.analyzed_at)}</td><td>${esc(a.original_name)}</td>
      <td>${a.face_count ?? "-"}</td><td>${badge(a.status)}</td>
      <td class="muted">${a.retry_of ? `#${a.retry_of} 재분석` : ""}${a.status === "FAILED" ? esc(a.failure_reason || "") : ""}</td>
      <td>${a.status === "FAILED" ? `<button class="btn small" onclick="retryAnalysis(${a.id})">재분석</button>`
                                  : `<a class="btn small" href="#result/${a.id}">보기</a>`}</td></tr>`).join("")
      : `<tr><td colspan="7" class="empty">조건에 맞는 분석 이력이 없습니다.</td></tr>`;
  } catch (err) { showError("#history-error", err.message); }
}
$("#history-form").addEventListener("submit", (e) => { e.preventDefault(); loadHistory(); });

// ---------- 통계 ----------
const statsForm = $("#stats-form");
statsForm.start.value = daysAgo(6);
statsForm.end.value = today();

function statsQuery() {
  const f = new FormData(statsForm);
  return new URLSearchParams({ start: f.get("start"), end: f.get("end"), unit: f.get("unit") });
}

async function loadStats() {
  const q = statsQuery();
  if (q.get("end") < q.get("start")) return showError("#stats-error", "종료일이 시작일보다 빠를 수 없습니다.");
  showError("#stats-error", "");
  try {
    const s = await api(`/api/stats?${q}`);
    const unitName = s.unit === "hour" ? "시간대별" : "일별";
    $("#stats-title").textContent = `${unitName} 얼굴 검출 수 (${s.start} ~ ${s.end})`;
    $("#stats-total").textContent = `합계 ${s.total_faces}명 · 성공 분석 ${s.total_analyses}건`;
    $("#stats-col").textContent = s.unit === "hour" ? "시간대" : "날짜";
    $("#stats-body").innerHTML = s.items.map((i) => `<tr><td>${i.label}</td><td>${i.faces}</td><td>${i.analyses}</td></tr>`).join("");
    drawChart(s, unitName);
  } catch (err) { showError("#stats-error", err.message); }
}

function drawChart(s, unitName) {
  if (!window.Chart) return showError("#stats-error", "그래프 라이브러리를 불러오지 못했습니다. 표의 수치를 확인해 주세요.");
  chart?.destroy();
  chart = new Chart($("#stats-chart"), {
    type: "bar",
    data: {
      labels: s.items.map((i) => s.unit === "hour" ? `${i.label.slice(0, 2)}시` : i.label.slice(5)),
      datasets: [{ label: `${unitName} 얼굴 수 합계`, data: s.items.map((i) => i.faces), backgroundColor: "#c08552", borderRadius: 4 }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true },
        tooltip: { callbacks: { title: (c) => s.items[c[0].dataIndex].label, label: (c) => ` 얼굴 ${c.raw}명 (분석 ${s.items[c.dataIndex].analyses}건)` } },
      },
      scales: {
        x: { title: { display: true, text: s.unit === "hour" ? "시간대" : "날짜" } },
        y: { beginAtZero: true, ticks: { precision: 0 }, title: { display: true, text: "얼굴 수(명)" } },
      },
    },
    plugins: [{ // 막대 위 수치 표시
      id: "values",
      afterDatasetsDraw(c) {
        const ctx = c.ctx;
        ctx.save();
        ctx.font = "12px sans-serif";
        ctx.fillStyle = "#4b3425";
        ctx.textAlign = "center";
        c.getDatasetMeta(0).data.forEach((bar, i) => {
          const v = c.data.datasets[0].data[i];
          if (v > 0) ctx.fillText(v, bar.x, bar.y - 4);
        });
        ctx.restore();
      },
    }],
  });
}

statsForm.addEventListener("submit", (e) => { e.preventDefault(); loadStats(); });
statsForm.querySelectorAll("input[name=unit]").forEach((r) => r.addEventListener("change", loadStats));
$("#csv-btn").addEventListener("click", () => {
  const q = statsQuery();
  if (q.get("end") < q.get("start")) return showError("#stats-error", "종료일이 시작일보다 빠를 수 없습니다.");
  location.href = `/api/stats/export.csv?${q}`;
});

// ---------- 사용자 관리 ----------
async function loadUsers() {
  try {
    me = await api("/api/auth/me");
    const f = $("#profile-form");
    f.display_name.value = me.display_name;
    $("#profile-info").textContent = `아이디: ${me.username} · 가입일: ${fmtTime(me.created_at)}`;
    $("#whoami").textContent = `${me.display_name} (${me.username})`;
  } catch (err) { toast(err.message, true); }
}

$("#profile-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/users/me", jsonOpts("PUT", { display_name: e.target.display_name.value.trim() }));
    toast("이름을 저장했습니다.");
    loadUsers();
  } catch (err) { toast(err.message, true); }
});

$("#pw-btn").addEventListener("click", async () => {
  const f = $("#profile-form");
  try {
    await api("/api/users/me/password", jsonOpts("PUT", { current_password: f.current_password.value, new_password: f.new_password.value }));
    f.current_password.value = f.new_password.value = "";
    toast("비밀번호를 변경했습니다.");
  } catch (err) { toast(err.message, true); }
});

$("#delete-btn").addEventListener("click", async () => {
  if (!confirm("계정을 삭제할까요? 이 작업은 되돌릴 수 없습니다.")) return;
  try {
    await api("/api/users/me", { method: "DELETE" });
    await fetch("/auth/logout", { method: "POST" });
    toast("계정을 삭제했습니다.");
    showLogin();
  } catch (err) { toast(err.message, true); }
});

$("#register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    await api("/api/users", jsonOpts("POST", Object.fromEntries(f)));
    e.target.reset();
    toast("새 사용자를 등록했습니다.");
  } catch (err) { toast(err.message, true); }
});

// ---------- 시작 ----------
(async () => {
  try {
    me = await api("/api/auth/me");
    showApp();
  } catch { showLogin(); }
})();
