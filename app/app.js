"use strict";
/* ---------- tiny helpers ---------- */
const $ = (s, r = document) => r.querySelector(s);
const view = $("#view");
const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} }
};
const norm = s => (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const THEMES = { alina: ["Alina", "linear-gradient(135deg,#3b2f8f,#14102b)"], maraina: ["Maraina", "linear-gradient(135deg,#a99bff,#f6f3ff)"],
                 ala: ["Ala", "linear-gradient(135deg,#34d399,#0d1f1a)"], tany: ["Tany", "linear-gradient(135deg,#f59e0b,#2a1d14)"] };
const state = { index: null, favs: new Set(store.get("favs", [])), recent: store.get("recent", []),
                theme: store.get("theme", "alina"), size: store.get("size", 1), timbre: store.get("timbre", "piano"), wrap: store.get("wrap", "auto") };
function applyTheme() {
  document.body.dataset.theme = state.theme; document.documentElement.style.setProperty("--sol", state.size);
  const m = document.querySelector('meta[name=theme-color]'); if (m) m.content = getComputedStyle(document.body).getPropertyValue("--bg").trim() || "#14102b";
}
applyTheme();

/* ---------- drawer ---------- */
const drawer = $("#drawer"), scrim = $("#scrim");
function drawerOpen(o) { drawer.classList.toggle("open", o); scrim.classList.toggle("on", o); drawer.setAttribute("aria-hidden", !o); }
$("#menuBtn").onclick = () => drawerOpen(!drawer.classList.contains("open"));
scrim.onclick = () => drawerOpen(false);
drawer.addEventListener("click", e => { if (e.target.closest("a")) drawerOpen(false); });
$("#themeBtn").onclick = () => { const k = Object.keys(THEMES); state.theme = k[(k.indexOf(state.theme) + 1) % k.length]; store.set("theme", state.theme); applyTheme(); };

/* ---------- data ---------- */
async function getIndex() { if (!state.index) state.index = await (await fetch("data/index.json")).json(); return state.index; }
const songCache = {};
async function getSong(id) { return songCache[id] || (songCache[id] = await (await fetch(`data/songs/${id}.json`)).json()); }
const label = s => (s.number != null ? s.number : "♪");
const fullTitle = s => (s.number != null ? `${s.number}. ` : "") + s.title;

/* ---------- list ---------- */
function itemHTML(s) {
  return `<a class="item" href="#/song/${s.id}"><div class="num">${label(s)}</div>
    <div class="t"><b>${esc(s.title)}</b><small>Do = ${esc(s.key)} · ${s.tempo} bpm${s.source ? " · " + esc(s.source) : ""}</small></div>
    <button class="fav ${state.favs.has(s.id) ? "on" : ""}" data-fav="${s.id}" aria-label="Tiana">${state.favs.has(s.id) ? "★" : "☆"}</button></a>`;
}
function bindFavs(root) {
  root.querySelectorAll("[data-fav]").forEach(b => b.onclick = e => {
    e.preventDefault(); e.stopPropagation(); const id = b.dataset.fav;
    state.favs.has(id) ? state.favs.delete(id) : state.favs.add(id); store.set("favs", [...state.favs]);
    b.classList.toggle("on", state.favs.has(id)); b.textContent = state.favs.has(id) ? "★" : "☆";
  });
}
function renderList(box, items, emptyMsg) {
  box.innerHTML = items.length ? items.map(itemHTML).join("") : `<div class="empty">${emptyMsg || "Tsy misy hita."}</div>`; bindFavs(box);
}
function filterIndex(q) {
  const n = norm(q).trim(); if (!n) return state.index;
  return state.index.filter(s => norm(s.title).includes(n) || String(s.number) === n || (s.number != null && String(s.number).startsWith(n)) || norm(s.source).includes(n));
}
const searchBox = ph => `<div class="search"><span>⌕</span><input id="q" type="search" inputmode="search" placeholder="${ph}" autocomplete="off"></div>`;

/* ---------- views ---------- */
async function home() {
  await getIndex(); $("#barTitle").textContent = "Solfa SDA";
  view.innerHTML = `<div class="hero"><h2>Fandraisana 🎶</h2><p>${state.index.length} hira · henoy sy vakio ny Solfa</p></div>
    ${searchBox("Hikaroka hira na laharana…")}
    <div id="res"></div>
    <div id="menu">
    <div class="grid3d">
      <a class="tile t1" href="#/list"><span class="ico">♬</span><b>Hira rehetra</b><small>${state.index.length} hira</small></a>
      <a class="tile t2" href="#/favs"><span class="ico">★</span><b>Tiana</b><small>${state.favs.size} voatendry</small></a>
      <a class="tile t3" href="#/recent"><span class="ico">⟲</span><b>Jinery farany</b><small>${state.recent.length} farany</small></a>
      <a class="tile t4" href="#/settings"><span class="ico">✦</span><b>Endrika</b><small>Thème sy feo</small></a>
    </div></div>`;
  tilt(view); const q = $("#q"), res = $("#res"), menu = $("#menu");
  q.oninput = () => { const on = q.value.trim() !== ""; menu.style.display = on ? "none" : ""; if (on) renderList(res, filterIndex(q.value)); else res.innerHTML = ""; };
}
function tilt(root) {
  root.querySelectorAll(".tile").forEach(t => {
    const mv = e => { const r = t.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
      t.style.transform = `rotateY(${(x - .5) * 22}deg) rotateX(${(.5 - y) * 22}deg) scale(1.03)`; t.style.setProperty("--gx", x * 100 + "%"); t.style.setProperty("--gy", y * 100 + "%"); };
    t.addEventListener("pointermove", mv); t.addEventListener("pointerdown", mv);
    ["pointerleave", "pointerup", "pointercancel"].forEach(ev => t.addEventListener(ev, () => t.style.transform = ""));
  });
}
async function listView(mode) {
  await getIndex();
  const titles = { list: "Hira rehetra", favs: "Tiana", recent: "Jinery farany" }; $("#barTitle").textContent = titles[mode];
  view.innerHTML = (mode === "list" ? searchBox("Hikaroka…") : "") + `<div id="res"></div>`; const res = $("#res");
  const base = () => mode === "favs" ? state.index.filter(s => state.favs.has(s.id))
    : mode === "recent" ? state.recent.map(id => state.index.find(s => s.id === id)).filter(Boolean) : state.index;
  const draw = q => renderList(res, q ? filterIndex(q) : base(), mode === "favs" ? "Tsy mbola misy hira tiana. Tsindrio ny ☆." : "Mbola tsy nisy hira nilalaovina.");
  draw(""); if (mode === "list") $("#q").oninput = e => draw(e.target.value);
}
function settings() {
  $("#barTitle").textContent = "Fanovana";
  view.innerHTML = `<div class="set"><h3>Endrika (thème)</h3><div class="themes">${Object.entries(THEMES).map(([k, [n, bg]]) =>
      `<div class="sw ${state.theme === k ? "on" : ""}" data-t="${k}" style="background:${bg}">${n}</div>`).join("")}</div></div>
    <div class="set"><h3>Haben'ny solfa</h3><input id="sz" type="range" min=".8" max="1.6" step=".05" value="${state.size}"></div>
    <div class="set"><h3>Feo (instrument)</h3><select id="tb">${[["piano", "Piano"], ["organ", "Orgue"], ["strings", "Korda"]].map(([k, n]) =>
      `<option value="${k}" ${state.timbre === k ? "selected" : ""}>${n}</option>`).join("")}</select></div>`;
  view.querySelectorAll(".sw").forEach(s => s.onclick = () => { state.theme = s.dataset.t; store.set("theme", state.theme); applyTheme(); settings(); });
  $("#sz").oninput = e => { state.size = +e.target.value; store.set("size", state.size); applyTheme(); };
  $("#tb").onchange = e => { state.timbre = e.target.value; store.set("timbre", state.timbre); };
}
function about() {
  $("#barTitle").textContent = "Momba";
  view.innerHTML = `<div class="set"><h3>Solfa SDA</h3><p style="color:var(--mut)">Prototype. Ny solfa dia soratana amin'ny format .drm ary lalaovina mivantana. Ny selectionneur (⬤ mavo) dia manaraka ny feo isaky ny note.</p></div>`;
}

/* ---------- audio engine ---------- */
const KEYS = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
class Player {
  constructor(song, timbre) {
    this.s = song; this.timbre = timbre; this.scale = 1; this.shift = 0; this.muted = new Set();
    this.ptr = 0; this.t0 = 0; this.startBeat = 0; this.status = "stopped"; this.buildTempoMap();
  }
  buildTempoMap() {
    const segs = []; let sec = 0, prev = null;
    for (const [beat, bpm] of this.s.tempos) {
      if (prev) sec += (beat - prev.beat) * prev.spb;
      prev = { beat, spb: 60 / (bpm * this.scale) }; segs.push({ beat, sec, spb: prev.spb });
    }
    this.segs = segs;
  }
  secAt(b) { let g = this.segs[0]; for (const x of this.segs) if (x.beat <= b) g = x; return g.sec + (b - g.beat) * g.spb; }
  beatAt(sec) { let g = this.segs[0]; for (const x of this.segs) if (x.sec <= sec) g = x; return g.beat + (sec - g.sec) / g.spb; }
  get duration() { return this.secAt(this.s.cells); }
  ensureCtx() {
    if (this.ctx) return;
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.comp = this.ctx.createDynamicsCompressor(); this.comp.connect(this.ctx.destination);
    this.master = this.ctx.createGain(); this.master.gain.value = .55; this.master.connect(this.comp);
    const W = re => this.ctx.createPeriodicWave(new Float32Array([0, ...re]), new Float32Array(re.length + 1));
    this.waves = { piano: W([1, .45, .25, .12, .06]), organ: W([1, .7, .5, .4, .25, .15]), strings: W([1, .6, .45, .35, .3, .22, .15, .1]) };
    this.out = null;
  }
  get beat() { return this.status === "stopped" || !this.ctx ? this.startBeat : Math.max(0, this.beatAt(this.ctx.currentTime - this.t0)); }
  killNodes() { try { this.out && this.out.disconnect(); } catch {} this.out = this.ctx.createGain(); this.out.connect(this.master); }
  startAt(beat) {
    this.killNodes(); this.t0 = this.ctx.currentTime - this.secAt(beat);
    const i = this.s.events.findIndex(e => e[0] >= beat - 1e-6); this.ptr = i < 0 ? this.s.events.length : i;
    if (!this.timer) this.timer = setInterval(() => this.tick(), 40);
  }
  async play() {
    this.ensureCtx(); if (this.ctx.state === "suspended") await this.ctx.resume();
    if (this.status === "stopped") this.startAt(this.startBeat);
    this.status = "playing";
  }
  async pause() { if (this.status === "playing") { await this.ctx.suspend(); this.status = "paused"; } }
  async toggle() { return this.status === "playing" ? this.pause() : this.play(); }
  seek(beat) {
    beat = Math.max(0, Math.min(this.s.cells - .01, beat));
    if (this.status === "stopped" || !this.ctx) { this.startBeat = beat; return; }
    this.startAt(beat);
  }
  async stop() { if (this.ctx) { if (this.ctx.state === "suspended") await this.ctx.resume(); this.killNodes(); } this.status = "stopped"; this.startBeat = 0; clearInterval(this.timer); this.timer = 0; this.onstop && this.onstop(); }
  tick() {
    if (!this.ctx || this.status !== "playing") return;
    const now = this.ctx.currentTime, E = this.s.events;
    while (this.ptr < E.length) {
      const e = E[this.ptr], at = this.t0 + this.secAt(e[0]);
      if (at > now + .35) break; this.ptr++;
      if (this.muted.has(e[4]) || at < now - .08) continue; this.note(e, at);
    }
    if (this.beat > this.s.cells + .5) this.stop();
  }
  note([b0, d, midi, vel], at) {
    const c = this.ctx, o = c.createOscillator(), g = c.createGain(), f = 440 * 2 ** ((midi + this.shift - 69) / 12);
    const dur = this.secAt(b0 + d) - this.secAt(b0), a = vel / 127 * .22, tb = this.timbre;
    o.setPeriodicWave(this.waves[tb]); o.frequency.value = f; o.connect(g); g.connect(this.out);
    g.gain.setValueAtTime(0, at);
    if (tb === "piano") { g.gain.linearRampToValueAtTime(a, at + .006); g.gain.exponentialRampToValueAtTime(a * .35, at + Math.min(.5, dur)); g.gain.setTargetAtTime(0, at + dur, .09); }
    else { const att = tb === "organ" ? .03 : .14; g.gain.linearRampToValueAtTime(a * .8, at + att); g.gain.setValueAtTime(a * .8, at + Math.max(att, dur)); g.gain.setTargetAtTime(0, at + dur, tb === "organ" ? .04 : .12); }
    o.start(at); o.stop(at + dur + .8);
  }
  setScale(x) { const b = this.beat, was = this.status; this.scale = x; this.buildTempoMap(); if (was !== "stopped") this.startAt(b); }
  dispose() { clearInterval(this.timer); if (this.ctx) this.ctx.close().catch(() => {}); }
}

/* ---------- song view ---------- */
let current = null, raf = 0, wakeLock = null;
const VC = ["--voiceS", "--voiceA", "--voiceT", "--voiceB"], VN = { S: "Soprano", A: "Alto", T: "Tenora", B: "Basy" };
const BRACE = `<svg viewBox="0 0 10 100" preserveAspectRatio="none"><path d="M10 1 C4 1 5 8 5 20 L5 40 C5 46 3 48 0.5 50 C3 52 5 54 5 60 L5 80 C5 92 4 99 10 99" fill="none" stroke="currentColor" stroke-width="1.4" vector-effect="non-scaling-stroke"/></svg>`;
function tokHTML(t) {
  if (t === "-") return "-"; if (t === "") return "&nbsp;";
  const [l, o] = t; return esc(l) + (o > 0 ? `<span class="o">${"'".repeat(o)}</span>` : o < 0 ? `<span class="o d">${",".repeat(-o)}</span>` : "");
}
function sepFor(prev, next) { return Math.abs(next[0] - .5) < 1e-6 ? "." : (Math.abs(prev[1] - .75) < 1e-6 ? ".," : ","); }
const fmt = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

/* lyric text per cell for one lyric line: {cell: "syl syl"} */
function lyricMap(line) {
  const m = {}; (line.items || []).forEach(([c, k, tx]) => { (m[c] = m[c] || []).push([k, tx]); });
  const out = {}; for (const c in m) out[c] = m[c].sort((a, b) => a[0] - b[0]).map(x => x[1]).join(" ");
  return out;
}
async function songView(id) {
  await getIndex(); const song = await getSong(id);
  if (current) current.dispose(); const P = current = new Player(song, state.timbre);
  const pref = store.get("pref:" + id, {}); let bpm = pref.bpm || song.tempo, shift = pref.shift || 0;
  P.scale = bpm / song.tempo; P.shift = shift; P.buildTempoMap();
  state.recent = [id, ...state.recent.filter(x => x !== id)].slice(0, 20); store.set("recent", state.recent);
  $("#barTitle").textContent = fullTitle(song);
  const N = song.cells, barSet = new Set(song.bars), peSet = new Set(song.phrase_ends), baseKey = KEYS.indexOf(song.key);
  let sysHTML = "";
  song.systems.forEach(sy => {
    const bs = song.bars.filter(x => x >= sy.start && x < sy.end); if (!bs.length || bs[0] !== sy.start) bs.unshift(sy.start);
    const lyr = (sy.lyr || (sy.lyrics || []).map(l => ({ label: "", items: [] }))).map(l => ({ label: l.label, map: lyricMap(l) }));
    let blocks = "";
    bs.forEach((a, bi) => {
      const b = bi + 1 < bs.length ? bs[bi + 1] : sy.end, n = b - a, first = bi === 0, last = b >= N;
      const endCls = last ? "end" : peSet.has(b) ? "dbl" : "";
      let g = `<div class="score" style="grid-template-columns:repeat(${n * 2 - 1},auto)">`;
      song.voices.forEach((vn, vi) => {
        for (let c = a; c < b; c++) {
          const slots = song.grid[vi][c];
          g += `<div class="cell" data-c="${c}" data-v="${vi}">` + slots.map((s, i) => (i ? `<span class="dot">${sepFor(slots[i - 1], s)}</span>` : "") +
            `<span class="sl" data-v="${vi}" data-s="${c + s[0]}" data-e="${c + s[0] + s[1]}">${tokHTML(s[2])}</span>`).join("") + `</div>`;
          if (c + 1 < b) g += `<div class="sep" data-v="${vi}">:</div>`;
        }
      });
      lyr.forEach(l => {
        for (let c = a; c < b; c++) {
          const tx = l.map[c] || "", lab = first && c === a && l.label ? `<u>${esc(l.label)}</u> ` : "";
          g += `<div class="lc" data-c="${c}">${lab}${esc(tx)}</div>`;
          if (c + 1 < b) g += `<div class="lsep"></div>`;
        }
      });
      g += `</div>`;
      blocks += `<div class="bar ${first && sy.lead ? "lead" : ""} ${endCls}" data-a="${a}" data-b="${b}"><i class="br">${BRACE}</i>${g}<i class="bl"></i></div>`;
    });
    sysHTML += `<section class="sys" data-a="${sy.start}" data-b="${sy.end}"><div class="rows">${blocks}</div></section>`;
  });
  const verses = (song.verses || []).map(v => `<div class="verse">${esc(v).replace(/\n/g, "<br>")}</div>`).join("");
  view.innerHTML = `<div class="head"><div><h2 class="title-big">${song.number != null ? song.number + ". " : ""}${esc(song.title.toUpperCase())}</h2>
      <div class="sub"><span id="keyTxt">Do dia ${esc(song.key)}</span> · ${song.meter === 6 ? "6/4" : song.meter + "/4"}${song.mood ? ` · <i>${esc(song.mood)}</i>` : ""}</div></div>
      <div class="src">${esc(song.source).replace(/ · /g, "<br>")}</div></div>
    <div class="transport"><button class="play" id="play" aria-label="Lalao">▶</button><button class="icon sm" id="rew" aria-label="Averina">⏮</button>
      <div class="now"><div class="time"><b id="pos">0:00</b> / ${fmt(P.duration)}</div><div class="progress"><i id="pg"></i></div></div>
      <button class="chip fav ${state.favs.has(id) ? "on" : ""}" id="favBtn" aria-label="Tiana">${state.favs.has(id) ? "★" : "☆"}</button></div>
    <div class="panel">
      <div class="ctl"><label>Hafainganam-pandeha</label><div class="stepper"><button id="bm">−</button><output id="bpm"></output><button id="bp">+</button></div><input id="tp" type="range" min="40" max="200" step="1"></div>
      <div class="ctl"><label>Fiovan'ny feo (transpose)</label><div class="stepper"><button id="sm">−</button><output id="sh"></output><button id="sp">+</button></div><input id="ts" type="range" min="-6" max="6" step="1"></div>
      <div class="ctl wide"><label>Feo <small>(tsindrio hanafina / hampiseho)</small></label><div class="voices">${song.voices.map((v, i) => `<button class="vbtn on" style="--vc:var(${VC[i]})" data-v="${i}">${esc(v)}</button>`).join("")}</div>
        <select id="tb">${[["piano", "Piano"], ["organ", "Orgue"], ["strings", "Korda"]].map(([k, n]) => `<option value="${k}" ${state.timbre === k ? "selected" : ""}>${n}</option>`).join("")}</select>
        <div class="solo"><label>Lalao irery</label><button class="on" data-solo="all">Rehetra</button>${song.voices.map((v, i) => `<button data-solo="${i}" style="--vc:var(${VC[i]})">${esc(VN[v] || v)}</button>`).join("")}</div></div></div>
    <div id="systems">${sysHTML}</div>${verses ? `<div class="verses">${verses}</div>` : ""}
    ${song.hasScan ? `<details class="scan"><summary>Sary tany am-boalohany (fanamarinana)</summary><img loading="lazy" alt="scan" src="data/scans/${song.number}.jpg"></details>` : ""}`;

  /* controls */
  const setBpm = v => { bpm = Math.max(40, Math.min(200, Math.round(v))); P.setScale(bpm / song.tempo); $("#bpm").textContent = bpm + " bpm"; $("#tp").value = bpm; save(); $(".time").innerHTML = `<b id="pos">${fmt(P.secAt(P.beat))}</b> / ${fmt(P.duration)}`; };
  const setShift = v => { shift = Math.max(-6, Math.min(6, v)); P.shift = shift; const k = KEYS[(baseKey + shift + 12) % 12];
    $("#sh").textContent = `Do dia ${k}` + (shift ? ` (${shift > 0 ? "+" : ""}${shift})` : ""); $("#ts").value = shift; $("#keyTxt").textContent = "Do dia " + k; save(); };
  const save = () => store.set("pref:" + id, { bpm, shift });
  setBpm(bpm); setShift(shift);
  $("#bm").onclick = () => setBpm(bpm - 4); $("#bp").onclick = () => setBpm(bpm + 4); $("#tp").oninput = e => setBpm(+e.target.value);
  $("#sm").onclick = () => setShift(shift - 1); $("#sp").onclick = () => setShift(shift + 1); $("#ts").oninput = e => setShift(+e.target.value);
  $("#tb").onchange = e => { P.timbre = state.timbre = e.target.value; store.set("timbre", state.timbre); };
  const playBtn = $("#play"); const setIcon = () => playBtn.textContent = P.status === "playing" ? "❚❚" : "▶";
  const keepAwake = async on => { try { if (on && navigator.wakeLock) wakeLock = await navigator.wakeLock.request("screen"); else if (wakeLock) { await wakeLock.release(); wakeLock = null; } } catch {} };
  playBtn.onclick = async () => { await P.toggle(); setIcon(); keepAwake(P.status === "playing"); loop(); };
  $("#rew").onclick = async () => { await P.stop(); setIcon(); paint(0); };
  P.onstop = () => { setIcon(); keepAwake(false); paint(0); };
  const applyMute = () => {
    view.querySelectorAll(".vbtn").forEach(b => b.classList.toggle("on", !P.muted.has(+b.dataset.v)));
    view.querySelectorAll(".solo button").forEach(b => b.classList.toggle("on", b.dataset.solo === "all" ? P.muted.size === 0 : P.muted.size === song.voices.length - 1 && !P.muted.has(+b.dataset.solo)));
    view.querySelectorAll(".cell[data-v],.sep[data-v]").forEach(x => x.classList.toggle("mute", P.muted.has(+x.dataset.v)));
    if (P.status !== "stopped") P.seek(P.beat); else paint(P.beat);
  };
  view.querySelectorAll(".vbtn").forEach(b => b.onclick = () => { const v = +b.dataset.v;
    if (!P.muted.has(v) && P.muted.size === song.voices.length - 1) return;           // keep at least one voice audible
    P.muted.has(v) ? P.muted.delete(v) : P.muted.add(v); applyMute(); });
  view.querySelectorAll(".solo button").forEach(b => b.onclick = () => { P.muted.clear();
    if (b.dataset.solo !== "all") song.voices.forEach((_, i) => { if (i !== +b.dataset.solo) P.muted.add(i); }); applyMute(); });
  $("#favBtn").onclick = e => { state.favs.has(id) ? state.favs.delete(id) : state.favs.add(id); store.set("favs", [...state.favs]); e.target.classList.toggle("on", state.favs.has(id)); e.target.textContent = state.favs.has(id) ? "★" : "☆"; };
  view.querySelectorAll(".cell").forEach(c => c.onclick = async () => { P.ensureCtx(); const was = P.status; P.seek(+c.dataset.c);
    if (was === "stopped") { await P.play(); setIcon(); keepAwake(true); loop(); } else if (was === "paused") paint(P.beat); });

  /* highlight loop: lights the slot sounding now in each voice (the "selectionneur") */
  const slots = [...view.querySelectorAll(".sl")].map(el => ({ el, v: +el.dataset.v, s: +el.dataset.s, e: +el.dataset.e, blank: !el.textContent.trim() }));
  const sysEls = [...view.querySelectorAll(".sys")]; let lastSys = null, lastLine = -1, lit = new Set(), colEls = [];
  function paint(beat) {
    const now = new Set(), playing = P.status !== "stopped";
    if (playing) for (const x of slots) if (!x.blank && beat >= x.s && beat < x.e && !P.muted.has(x.v)) now.add(x.el);
    for (const el of lit) if (!now.has(el)) el.classList.remove("act");
    for (const el of now) if (!lit.has(el)) el.classList.add("act"); lit = now;
    $("#pg").style.width = Math.min(100, beat / N * 100) + "%"; const pos = $("#pos"); if (pos) pos.textContent = fmt(P.secAt(beat));
    const ci = Math.min(N - 1, Math.floor(beat)), sEl = sysEls.find(s => ci >= +s.dataset.a && ci < +s.dataset.b);
    colEls.forEach(x => x.classList.remove("col")); colEls = sEl ? [...sEl.querySelectorAll(`[data-c="${ci}"]`)] : []; colEls.forEach(x => x.classList.add("col"));
    if (sEl !== lastSys) { lastSys && lastSys.classList.remove("cur"); sEl && sEl.classList.add("cur"); lastSys = sEl; }
    const barEl = colEls[0] && colEls[0].closest(".bar");
    if (barEl && playing) { const ln = barEl.offsetTop + (sEl ? sEl.offsetTop : 0); if (ln !== lastLine) { lastLine = ln; barEl.scrollIntoView({ block: "center", behavior: "smooth" }); } }
  }
  function loop() { cancelAnimationFrame(raf); const f = () => { if (current !== P) return; paint(P.beat); if (P.status === "playing") raf = requestAnimationFrame(f); }; f(); }
  const markLines = () => { view.querySelectorAll(".rows").forEach(r => { let top = -1; r.querySelectorAll(".bar").forEach(b => { const tp = b.offsetTop; b.classList.toggle("ls", tp !== top); top = tp; }); }); };
  markLines(); if (document.fonts && document.fonts.ready) document.fonts.ready.then(markLines); window.onresize = markLines;
  paint(0); window.__player = P;
}

/* ---------- router ---------- */
async function route() {
  const [, name, arg] = location.hash.slice(1).split("/"); window.scrollTo(0, 0);
  cancelAnimationFrame(raf); if (current && name !== "song") { current.dispose(); current = null; }
  document.querySelectorAll("#drawer nav a").forEach(a => a.classList.toggle("on", a.dataset.nav === (name || "home") || (name === "song" && a.dataset.nav === "list")));
  try {
    if (!name) await home(); else if (["list", "favs", "recent"].includes(name)) await listView(name);
    else if (name === "settings") settings(); else if (name === "about") about(); else if (name === "song") await songView(arg);
    else await home();
  } catch (e) { view.innerHTML = `<div class="empty">Hadisoana: ${esc(e.message)}</div>`; }
}
addEventListener("hashchange", route); route();
if ("serviceWorker" in navigator && location.protocol.startsWith("http")) navigator.serviceWorker.register("sw.js").catch(() => {});
