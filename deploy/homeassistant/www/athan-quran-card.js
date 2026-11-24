// Athan Hub Quran player card for the Home dashboard's Quran view.
//
// Pick a reciter and a speaker, tap a surah, and it plays. The reciters, surahs
// and audio come from the Quran Hub integration (the Tarteel QUL library that
// Athan Hub uses), so "This phone" plays in the browser and any other speaker
// is driven by Quran Hub itself (the Echo through its Alexa skill).
//
// No optional chaining, ?? or flex gap: the LG TV's browser is Chromium 68.
//
//   type: custom:athan-quran-card

const STYLE = `
:host { display: block; --accent: 126, 240, 198; --ink: #10302a; }
ha-card { overflow: visible; max-width: 820px; margin: 0 auto; }
* { box-sizing: border-box; }
button { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; text-align: left; }
button:focus-visible { outline: 2px solid rgb(var(--accent)); outline-offset: 2px; border-radius: 12px; }
ha-icon { --mdc-icon-size: 22px; display: inline-flex; }

.head { padding: 22px 22px 8px; border-radius: inherit;
  background: radial-gradient(120% 170% at 0% 0%, rgba(var(--accent), 0.24) 0%, transparent 62%); }
h1 { font-size: 40px; font-weight: 300; letter-spacing: -0.02em; line-height: 1.05; margin: 0; }
h1 .ar { font-size: 28px; margin-left: 12px; opacity: 0.75; font-weight: 400; }

.pickers { padding: 10px 16px 4px; }
.reciter { width: 100%; display: flex; align-items: center; padding: 10px 12px; border-radius: 16px; background: rgba(255, 255, 255, 0.1); }
.reciter:hover { background: rgba(255, 255, 255, 0.15); }
.mono { flex: none; width: 42px; height: 42px; border-radius: 50%; margin-right: 12px; display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 15px; color: var(--ink); background: rgb(var(--accent)); }
.grow { flex: 1; min-width: 0; }
.small { font-size: 13px; color: var(--secondary-text-color); font-weight: 600; letter-spacing: 0.03em; text-transform: uppercase; }
.big { font-size: 17px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.chev { color: var(--secondary-text-color); transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1); }
.open .chev { transform: rotate(180deg); }

.sheet { display: none; margin-top: 8px; border-radius: 16px; background: rgba(20, 8, 40, 0.35); padding: 8px; }
.open .sheet { display: block; }
.sheet .rows { max-height: 360px; overflow-y: auto; -webkit-overflow-scrolling: touch; }
.opt { width: 100%; display: flex; align-items: center; min-height: 48px; padding: 6px 10px; border-radius: 12px; }
.opt:hover { background: rgba(255, 255, 255, 0.08); }
.opt.on { background: rgba(var(--accent), 0.18); }
.opt .tick { color: rgb(var(--accent)); visibility: hidden; }
.opt.on .tick { visibility: visible; }
.opt .style { font-size: 13px; color: var(--secondary-text-color); }
.section { padding: 10px 10px 4px; }

.speakers { display: flex; flex-wrap: wrap; margin: 8px -4px 0; }
.chip { margin: 4px; height: 38px; padding: 0 14px 0 10px; border-radius: 19px; display: inline-flex; align-items: center; font-size: 14px; font-weight: 600;
  background: rgba(255, 255, 255, 0.1); }
.chip ha-icon { --mdc-icon-size: 18px; margin-right: 6px; }
.chip[aria-pressed="true"] { background: rgb(var(--accent)); color: var(--ink); }

.search { display: flex; align-items: center; margin: 12px 16px 6px; padding: 0 6px 0 14px; border-radius: 14px; background: rgba(255, 255, 255, 0.1); }
.sheet .search { margin: 0 0 6px; }
.search:focus-within { background: rgba(255, 255, 255, 0.16); box-shadow: inset 0 0 0 1.5px rgba(var(--accent), 0.7); }
.search ha-icon { color: var(--secondary-text-color); margin-right: 8px; }
input { flex: 1; min-width: 0; height: 48px; border: 0; background: none; color: var(--primary-text-color); font: inherit; font-size: 17px; outline: none; caret-color: rgb(var(--accent)); }
input::placeholder { color: rgba(255, 255, 255, 0.6); }

.surahs { list-style: none; margin: 0; padding: 4px 8px 12px; }
.surah { width: 100%; display: flex; align-items: center; min-height: 64px; padding: 8px 10px; border-radius: 14px; }
.surah:hover { background: rgba(255, 255, 255, 0.07); }
.surah.now { background: rgba(var(--accent), 0.16); }
.star { position: relative; flex: none; width: 40px; height: 40px; margin-right: 14px; display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums; }
.star::before, .star::after { content: ''; position: absolute; top: 6px; left: 6px; width: 28px; height: 28px; border-radius: 5px;
  border: 1.5px solid rgba(var(--accent), 0.7); }
.star::after { transform: rotate(45deg); }
.now .star::before, .now .star::after { background: rgba(var(--accent), 0.25); }
.star span { position: relative; }
.name { font-size: 17px; font-weight: 600; }
.meaning { font-size: 14px; color: var(--secondary-text-color); margin-top: 2px; }
.ar { font-family: "Amiri Quran", "Amiri", "Noto Naskh Arabic", "Geeza Pro", serif; direction: rtl; }
.surah .ar { font-size: 24px; margin-left: 12px; }
.eq { display: none; color: rgb(var(--accent)); margin-left: 8px; }
.now .eq { display: inline-flex; }
.nothing { padding: 16px 20px 24px; color: var(--secondary-text-color); }

.player { position: -webkit-sticky; position: sticky; bottom: 12px; margin: 0 10px 10px; padding: 12px 12px 12px 16px; border-radius: 20px;
  background: rgba(30, 12, 60, 0.88); box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35); display: none; z-index: 2; }
.playing .player { display: block; }
.player .top { display: flex; align-items: center; }
.player .title { font-size: 16px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.player .sub { font-size: 13px; color: var(--secondary-text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px; }
.round { flex: none; width: 46px; height: 46px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-left: 8px; background: rgba(255, 255, 255, 0.12); }
.round.main { background: rgb(var(--accent)); color: var(--ink); }
.round:disabled { opacity: 0.4; cursor: default; }
.track { height: 4px; border-radius: 2px; margin-top: 10px; background: rgba(255, 255, 255, 0.15); overflow: hidden; }
.fill { height: 100%; width: 0; background: rgb(var(--accent)); transition: width 0.9s linear; }
.wait .fill { width: 30% !important; animation: slide 1.2s ease-in-out infinite; }
@keyframes slide { 0% { transform: translateX(-100%); } 100% { transform: translateX(340%); } }
.error { color: #ffb3b5; }
`;

const STORE = 'athan-quran-card';
const PHONE = 'browser';
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const fold = (s) => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ'`’\-\s]/g, '');
const initials = (name) => name.replace(/\(.*?\)/g, '').split(/[\s-]+/).filter((w) => /^[A-Z]/.test(w)).map((w) => w[0]).slice(0, 2).join('');

// "al kahf", "kahf", "18", "cave" and "الكهف" all find Al-Kahf.
export function matchSurah(surah, query) {
  const q = fold(query);
  if (!q) return true;
  if (/^\d+$/.test(q)) return String(surah.id) === q;
  return [surah.name_simple, surah.translated_name, surah.name_arabic].some((t) => fold(t).indexOf(q) >= 0);
}

// Archived duplicates are hidden; the rest sorted by name.
export function reciterList(recitations) {
  return recitations.filter((r) => !/archived/i.test(r.name)).sort((a, b) => a.name.localeCompare(b.name));
}

class AthanQuranCard extends HTMLElement {
  setConfig(config) {
    this.config = config || {};
    this._surahs = [];
    this._reciters = [];
    this._players = [];
    this._query = '';
    this._reciterQuery = '';
    this._now = null; // { surah, reciter, player, ayah, state, position, duration }
    let saved = {};
    try { saved = JSON.parse(localStorage.getItem(STORE) || '{}'); } catch (e) { saved = {}; }
    this._saved = { reciter: saved.reciter || null, player: saved.player || PHONE, recent: saved.recent || [] };
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
    this._skeleton();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._load();
    // A speaker that is switched off drops out of the list until it is back.
    const live = this._players.filter((p) => this._online(p.entity_id)).map((p) => p.entity_id).join();
    if (live !== this._live) { this._live = live; if (this._reciters.length) this._renderSpeakers(); }
  }

  _online(id) {
    const state = this._hass && this._hass.states[id];
    return Boolean(state) && state.state !== 'unavailable';
  }

  connectedCallback() { if (this._hass && !this._unsub && this._reciters.length) this._subscribe(); }

  disconnectedCallback() {
    if (this._unsub) { this._unsub.then((u) => u()).catch(() => {}); this._unsub = null; }
  }

  getCardSize() { return 12; }

  _save() {
    try { localStorage.setItem(STORE, JSON.stringify(this._saved)); } catch (e) { /* private mode */ }
  }

  async _load() {
    const ws = (type) => this._hass.callWS({ type });
    try {
      const all = await Promise.all([ws('quran_hub/surahs'), ws('quran_hub/recitations'), ws('quran_hub/players')]);
      this._surahs = all[0];
      this._reciters = reciterList(all[1]);
      this._players = all[2].filter((p) => p.supported);
    } catch (e) {
      this.shadowRoot.querySelector('.surahs').innerHTML = `<li class="nothing error">Quran Hub is not answering: ${esc(e.message || e)}</li>`;
      return;
    }
    const pick = this._reciter() || this._reciters.find((r) => /alafasy|afasy/i.test(r.name)) || this._reciters[0];
    this._saved.reciter = pick ? pick.id : null;
    this._subscribe();
    this._renderReciter();
    this._renderSpeakers();
    this._renderSurahs();
  }

  _subscribe() {
    if (this._unsub || !this.isConnected) return;
    this._unsub = this._hass.connection.subscribeMessage((e) => this._remoteEvent(e), { type: 'quran_hub/remote/subscribe' });
    this._unsub.catch(() => { this._unsub = null; });
  }

  _reciter(id) {
    const want = id === undefined ? this._saved.reciter : id;
    return this._reciters.find((r) => r.id === want) || null;
  }

  // ---- markup ------------------------------------------------------------

  _skeleton() {
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <ha-card>
        <div class="head"><h1>Quran<span class="ar" lang="ar">القرآن</span></h1></div>
        <div class="pickers">
          <div class="reciter-box">
            <button class="reciter" aria-expanded="false">
              <span class="mono">…</span>
              <span class="grow"><div class="small">Reciter</div><div class="big">Loading reciters…</div></span>
              <ha-icon class="chev" icon="mdi:chevron-down"></ha-icon>
            </button>
            <div class="sheet">
              <div class="search"><ha-icon icon="mdi:magnify"></ha-icon><input class="find-reciter" placeholder="Search reciters" aria-label="Search reciters"></div>
              <div class="rows"></div>
            </div>
          </div>
          <div class="speakers"></div>
        </div>
        <div class="search"><ha-icon icon="mdi:magnify"></ha-icon><input class="find-surah" placeholder="Search 114 surahs: name, meaning or number" aria-label="Search surahs"></div>
        <ul class="surahs"><li class="nothing">Loading surahs…</li></ul>
        <div class="player" role="region" aria-label="Now playing">
          <div class="top">
            <div class="grow"><div class="title"></div><div class="sub"></div></div>
            <button class="round prev" aria-label="Previous surah"><ha-icon icon="mdi:skip-previous"></ha-icon></button>
            <button class="round main toggle" aria-label="Pause"><ha-icon icon="mdi:pause"></ha-icon></button>
            <button class="round next" aria-label="Next surah"><ha-icon icon="mdi:skip-next"></ha-icon></button>
            <button class="round stop" aria-label="Stop"><ha-icon icon="mdi:stop"></ha-icon></button>
          </div>
          <div class="track"><div class="fill"></div></div>
        </div>
        <audio preload="auto"></audio>
      </ha-card>`;
    const root = this.shadowRoot;
    this._card = root.querySelector('ha-card');
    this._audio = root.querySelector('audio');
    const box = root.querySelector('.reciter-box');
    root.querySelector('.reciter').addEventListener('click', () => {
      const open = !box.classList.contains('open');
      box.classList.toggle('open', open);
      root.querySelector('.reciter').setAttribute('aria-expanded', String(open));
      if (open) { this._renderReciterRows(); root.querySelector('.find-reciter').focus(); }
    });
    root.querySelector('.find-reciter').addEventListener('input', (e) => { this._reciterQuery = e.target.value; this._renderReciterRows(); });
    root.querySelector('.rows').addEventListener('click', (e) => {
      const opt = e.target.closest('[data-id]');
      if (!opt) return;
      this._chooseReciter(Number(opt.dataset.id));
      box.classList.remove('open');
    });
    root.querySelector('.speakers').addEventListener('click', (e) => {
      const chip = e.target.closest('[data-player]');
      if (!chip) return;
      this._saved.player = chip.dataset.player;
      this._save();
      this._renderSpeakers();
    });
    root.querySelector('.find-surah').addEventListener('input', (e) => { this._query = e.target.value; this._renderSurahs(); });
    root.querySelector('.surahs').addEventListener('click', (e) => {
      const row = e.target.closest('[data-surah]');
      if (row) this._play(Number(row.dataset.surah));
    });
    root.querySelector('.toggle').addEventListener('click', () => this._toggle());
    root.querySelector('.stop').addEventListener('click', () => this._stop());
    root.querySelector('.prev').addEventListener('click', () => this._skip(-1));
    root.querySelector('.next').addEventListener('click', () => this._skip(1));
    this._audio.addEventListener('ended', () => this._phoneEnded());
    this._audio.addEventListener('timeupdate', () => this._phoneProgress());
    this._audio.addEventListener('play', () => this._phoneState('playing'));
    this._audio.addEventListener('pause', () => { if (!this._audio.ended) this._phoneState('paused'); });
    this._audio.addEventListener('error', () => { if (this._now && this._now.player === PHONE) this._fail('That recording could not be played.'); });
  }

  _renderReciter() {
    const r = this._reciter();
    const root = this.shadowRoot;
    root.querySelector('.mono').textContent = r ? initials(r.name) || 'Q' : '…';
    root.querySelector('.reciter .big').textContent = r ? r.name : 'Choose a reciter';
  }

  _renderReciterRows() {
    const q = fold(this._reciterQuery);
    const row = (r) => `<button class="opt${r.id === this._saved.reciter ? ' on' : ''}" data-id="${r.id}">
        <span class="grow"><div class="big">${esc(r.name)}</div><div class="style">${esc([r.style, r.source_kind === 'ayah' ? 'ayah by ayah' : 'whole surah'].filter(Boolean).join(' · '))}</div></span>
        <ha-icon class="tick" icon="mdi:check"></ha-icon></button>`;
    const found = this._reciters.filter((r) => !q || fold(r.name).indexOf(q) >= 0);
    const recent = q ? [] : this._saved.recent.map((id) => this._reciter(id)).filter(Boolean);
    this.shadowRoot.querySelector('.rows').innerHTML =
      (recent.length ? `<div class="small section">Recent</div>${recent.map(row).join('')}<div class="small section">All reciters</div>` : '')
      + (found.length ? found.map(row).join('') : '<div class="nothing">No reciter by that name</div>');
  }

  _chooseReciter(id) {
    this._saved.reciter = id;
    this._saved.recent = [id].concat(this._saved.recent.filter((x) => x !== id)).slice(0, 4);
    this._save();
    this._renderReciter();
  }

  _renderSpeakers() {
    const chips = [{ entity_id: PHONE, name: 'This device', icon: 'mdi:cellphone-sound' }].concat(this._players.filter((p) => this._online(p.entity_id)).map((p) => ({
      entity_id: p.entity_id, name: p.name, icon: p.platform === 'alexa_media' ? 'mdi:speaker' : 'mdi:television',
    })));
    // ponytail: a remembered speaker that is off shows "This device" until it is back.
    const chosen = chips.some((c) => c.entity_id === this._saved.player) ? this._saved.player : PHONE;
    this._player = chosen;
    this.shadowRoot.querySelector('.speakers').innerHTML = chips.map((c) =>
      `<button class="chip" data-player="${esc(c.entity_id)}" aria-pressed="${c.entity_id === chosen}"><ha-icon icon="${c.icon}"></ha-icon>${esc(c.name)}</button>`).join('');
  }

  _renderSurahs() {
    const now = this._now ? this._now.surah.id : 0;
    const list = this._surahs.filter((s) => matchSurah(s, this._query));
    this.shadowRoot.querySelector('.surahs').innerHTML = list.length ? list.map((s) => `<li><button class="surah${s.id === now ? ' now' : ''}" data-surah="${s.id}">
        <span class="star"><span>${s.id}</span></span>
        <span class="grow"><div class="name">${esc(s.name_simple)}<ha-icon class="eq" icon="mdi:volume-high"></ha-icon></div><div class="meaning">${esc(s.translated_name)} · ${s.ayah_count} ayahs</div></span>
        <span class="ar" lang="ar">${esc(s.name_arabic)}</span></button></li>`).join('')
      : '<li class="nothing">No surah matches that</li>';
  }

  _renderPlayer() {
    const n = this._now;
    this._card.classList.toggle('playing', Boolean(n));
    if (!n) return;
    const root = this.shadowRoot;
    const where = n.player === PHONE ? 'This device' : (this._players.find((p) => p.entity_id === n.player) || { name: n.player }).name;
    root.querySelector('.player .title').textContent = `${n.surah.id}. ${n.surah.name_simple}`;
    const sub = root.querySelector('.player .sub');
    sub.className = `sub${n.error ? ' error' : ''}`;
    sub.textContent = n.error || (n.state === 'preparing' ? `Getting it ready for ${where}…`
      : `${n.reciter.name} · ${where}${n.ayah ? ` · ayah ${n.ayah} of ${n.surah.ayah_count}` : ''}`);
    const playing = n.state === 'playing' || n.state === 'preparing';
    const toggle = root.querySelector('.toggle');
    const icon = playing ? 'mdi:pause' : 'mdi:play';
    if (toggle.dataset.icon !== icon) { toggle.dataset.icon = icon; toggle.innerHTML = `<ha-icon icon="${icon}"></ha-icon>`; }
    toggle.setAttribute('aria-label', playing ? 'Pause' : 'Play');
    toggle.disabled = n.state === 'preparing' || Boolean(n.error);
    root.querySelector('.prev').disabled = n.surah.id === 1;
    root.querySelector('.next').disabled = n.surah.id === 114;
    root.querySelector('.player').classList.toggle('wait', n.state === 'preparing');
    root.querySelector('.fill').style.width = n.duration ? `${Math.min(100, (100 * n.position) / n.duration)}%` : '0';
  }

  // ---- playing -----------------------------------------------------------

  async _play(surahId) {
    const surah = this._surahs.find((s) => s.id === surahId);
    const reciter = this._reciter();
    if (!surah || !reciter) return;
    await this._stop(true);
    const player = this._player || PHONE;
    const token = {};
    this._token = token;
    this._now = { surah, reciter, player, ayah: 0, state: 'preparing', position: 0, duration: 0, error: null };
    this._renderSurahs();
    this._renderPlayer();
    this._mediaSession();
    try {
      if (player === PHONE) {
        this._now.ayah = reciter.capability === 'ayah' ? 1 : 0;
        await this._phoneLoad(token);
      } else {
        const res = await this._hass.callWS({
          type: 'quran_hub/remote/play', entity_id: player, recitation_id: reciter.id, surah_id: surah.id,
          start_ayah: 1, end_ayah: surah.ayah_count, repetitions: 1, playback_speed: 1,
        });
        if (this._token !== token) return;
        this._now.state = 'playing';
        this._now.duration = res.duration_ms || 0;
        this._renderPlayer();
      }
    } catch (e) {
      if (this._token === token) this._fail(e.message || String(e));
    }
  }

  _fail(message) {
    if (!this._now) return;
    this._now.error = message;
    this._now.state = 'stopped';
    this._renderPlayer();
  }

  async _stop(quiet) {
    const n = this._now;
    this._token = null;
    this._audio.pause();
    this._audio.removeAttribute('src');
    this._next = null;
    if (n && n.player !== PHONE && !n.error) {
      try { await this._hass.callWS({ type: 'quran_hub/remote/stop', entity_id: n.player }); } catch (e) { /* already stopped */ }
    }
    if (!quiet) {
      this._now = null;
      this._renderSurahs();
      this._renderPlayer();
    }
  }

  _skip(step) {
    if (this._now) this._play(this._now.surah.id + step);
  }

  _toggle() {
    const n = this._now;
    if (!n || n.error) return;
    if (n.player === PHONE) {
      if (this._audio.paused) this._audio.play().catch((e) => this._fail(e.message)); else this._audio.pause();
      return;
    }
    const pause = n.state === 'playing';
    this._hass.callService('media_player', pause ? 'media_pause' : 'media_play', {}, { entity_id: n.player });
    n.state = pause ? 'paused' : 'playing';
    this._renderPlayer();
  }

  _remoteEvent(e) {
    const n = this._now;
    if (!n || n.player === PHONE || e.entity_id !== n.player || n.state === 'preparing') return;
    n.position = e.position_ms || 0;
    n.duration = e.duration_ms || n.duration;
    const key = e.verse_key ? String(e.verse_key).split(':') : null;
    if (key && Number(key[0]) === n.surah.id) n.ayah = Number(key[1]);
    if (e.state === 'finished' || e.state === 'stopped') {
      this._now = null;
      this._renderSurahs();
    } else {
      n.state = e.state;
    }
    this._renderPlayer();
  }

  // This device: a surah recording is one file; ayah reciters play ayah by ayah,
  // with the next ayah's link fetched ahead so the gap stays short.
  _url(n, ayah) {
    const msg = { type: 'quran_hub/audio_url', recitation_id: n.reciter.id, surah_id: n.surah.id };
    if (n.reciter.capability === 'ayah') msg.verse_key = `${n.surah.id}:${ayah}`;
    return this._hass.callWS(msg).then((r) => r.url);
  }

  async _phoneLoad(token) {
    const n = this._now;
    const url = await this._url(n, n.ayah);
    if (this._token !== token) return;
    this._audio.src = url;
    await this._audio.play();
    this._phoneState('playing');
    this._prefetch(token);
  }

  _prefetch(token) {
    const n = this._now;
    this._next = null;
    if (!n || !n.ayah || n.ayah >= n.surah.ayah_count) return;
    const ayah = n.ayah + 1;
    this._next = this._url(n, ayah).then((url) => (this._token === token ? { ayah, url } : null)).catch(() => null);
  }

  async _phoneEnded() {
    const n = this._now;
    if (!n || n.player !== PHONE) return;
    const token = this._token;
    const next = this._next ? await this._next : null;
    if (next && this._token === token) {
      n.ayah = next.ayah;
      this._audio.src = next.url;
      this._audio.play().catch((e) => this._fail(e.message));
      this._prefetch(token);
      this._renderPlayer();
      return;
    }
    if (this._token !== token) return;
    this._now = null;
    this._renderSurahs();
    this._renderPlayer();
  }

  _phoneProgress() {
    const n = this._now;
    if (!n || n.player !== PHONE) return;
    if (n.reciter.capability === 'ayah') {
      n.position = n.ayah - 1 + (this._audio.duration ? this._audio.currentTime / this._audio.duration : 0);
      n.duration = n.surah.ayah_count;
    } else {
      n.position = this._audio.currentTime;
      n.duration = this._audio.duration || 0;
    }
    this._renderPlayer();
  }

  _phoneState(state) {
    if (this._now && this._now.player === PHONE && !this._now.error) { this._now.state = state; this._renderPlayer(); }
  }

  _mediaSession() {
    if (!('mediaSession' in navigator) || !window.MediaMetadata) return;
    const n = this._now;
    navigator.mediaSession.metadata = new window.MediaMetadata({ title: `${n.surah.name_simple} · ${n.surah.name_arabic}`, artist: n.reciter.name, album: 'Quran' });
    navigator.mediaSession.setActionHandler('nexttrack', () => this._skip(1));
    navigator.mediaSession.setActionHandler('previoustrack', () => this._skip(-1));
  }
}

customElements.define('athan-quran-card', AthanQuranCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: 'athan-quran-card', name: 'Athan Quran player', description: 'Play any surah by any reciter on this device or a speaker' });
