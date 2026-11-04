// person_detection 웹 서버: 정적 화면 제공 + 로그인 쿠키 관리 + FastAPI 프록시
const path = require("path");
require("dotenv").config({ path: path.join(__dirname, "..", ".env") });
const express = require("express");

const PORT = Number(process.env.CLIENT_PORT || 3000);
const API_URL = process.env.API_URL || "http://127.0.0.1:8000";
const COOKIE = "pd_token";

const app = express();
app.disable("x-powered-by");

function getToken(req) {
  const cookies = Object.fromEntries(
    (req.headers.cookie || "").split(";").filter(Boolean).map((c) => {
      const i = c.indexOf("=");
      return [c.slice(0, i).trim(), decodeURIComponent(c.slice(i + 1).trim())];
    })
  );
  return cookies[COOKIE] || "";
}

function setCookie(res, token, maxAgeSec) {
  res.setHeader("Set-Cookie",
    `${COOKIE}=${encodeURIComponent(token)}; HttpOnly; SameSite=Lax; Path=/; Max-Age=${maxAgeSec}`);
}

function apiUnavailable(res) {
  res.status(502).json({ detail: "분석 서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요." });
}

// 로그인: FastAPI 토큰을 HttpOnly 쿠키로 보관 (브라우저 JS 에는 노출하지 않음)
app.post("/auth/login", express.json(), async (req, res) => {
  try {
    const r = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: req.body?.username || "", password: req.body?.password || "" }),
    });
    const data = await r.json();
    if (!r.ok) return res.status(r.status).json(data);
    setCookie(res, data.token, 12 * 3600);
    res.json({ user: data.user });
  } catch {
    apiUnavailable(res);
  }
});

app.post("/auth/logout", async (req, res) => {
  const token = getToken(req);
  if (token) {
    await fetch(`${API_URL}/api/auth/logout`, {
      method: "POST", headers: { Authorization: `Bearer ${token}` },
    }).catch(() => {});
  }
  setCookie(res, "", 0);
  res.json({ ok: true });
});

// /api/* 는 쿠키의 토큰을 Bearer 헤더로 바꿔 FastAPI 에 그대로 전달
app.use("/api", async (req, res) => {
  const headers = { Authorization: `Bearer ${getToken(req)}` };
  if (req.headers["content-type"]) headers["Content-Type"] = req.headers["content-type"];
  const hasBody = !["GET", "HEAD"].includes(req.method);
  try {
    const r = await fetch(API_URL + req.originalUrl, {
      method: req.method,
      headers,
      body: hasBody ? req : undefined,
      duplex: hasBody ? "half" : undefined,
    });
    res.status(r.status);
    for (const h of ["content-type", "content-disposition"]) {
      if (r.headers.get(h)) res.setHeader(h, r.headers.get(h));
    }
    res.send(Buffer.from(await r.arrayBuffer()));
  } catch {
    apiUnavailable(res);
  }
});

app.use(express.static(path.join(__dirname, "public")));

app.listen(PORT, () => console.log(`웹 서버 실행: http://localhost:${PORT} (API: ${API_URL})`));
