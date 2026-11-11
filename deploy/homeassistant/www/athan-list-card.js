// Athan Hub family list card for the Home dashboard's Lists view.
//
// Works on any Home Assistant to-do list entity and adds what the built-in
// card lacks: items assigned to people, collapsible list and person groups,
// swipe left to delete, and select several (or all) to delete, with undo.
//
// An assignment is stored as a first line "@Name" in the item's description,
// so it survives in Home Assistant itself and shows in its own to-do panel.
// Lists that cannot hold descriptions (the Shopping list) are not assignable.
//
//   type: custom:athan-list-card
//   entity: todo.to_do
//   title: To-do
//   color: "126, 240, 198"     # r, g, b of the list's accent
//   count: "{n} open"          # header count; {n} is the number left
//   empty: All clear           # header text when nothing is left
//   order: due                 # due | alpha | manual (default)
//   people: [Judy, Osama]      # default: every person in Home Assistant

const STYLE = `
:host { display: block; --accent: 255, 209, 102; }
ha-card { overflow: hidden; caret-color: rgb(var(--accent)); }
* { box-sizing: border-box; }
::selection { background: rgba(var(--accent), 0.35); }
button { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; }
button:focus-visible, input:focus-visible, textarea:focus-visible, .head:focus-visible {
  outline: 2px solid rgb(var(--accent)); outline-offset: 2px; border-radius: 10px;
}
ha-icon { --mdc-icon-size: 22px; display: inline-flex; }

.head {
  display: flex; align-items: center; gap: 12px; padding: 20px 14px 14px 22px; cursor: pointer;
  background: radial-gradient(120% 160% at 0% 0%, rgba(var(--accent), 0.24) 0%, transparent 62%);
  user-select: none; -webkit-user-select: none;
}
.title { flex: 1; min-width: 0; display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; }
h1 { font-size: 40px; font-weight: 300; letter-spacing: -0.02em; line-height: 1.05; margin: 0; }
.count { font-size: 16px; font-weight: 600; color: rgb(var(--accent)); font-variant-numeric: tabular-nums; white-space: nowrap; }
.icon-btn { width: 44px; height: 44px; border-radius: 12px; display: inline-flex; align-items: center; justify-content: center; color: var(--secondary-text-color); }
.icon-btn:hover { background: rgba(255, 255, 255, 0.1); color: var(--primary-text-color); }
.icon-btn.on { background: rgba(var(--accent), 0.22); color: rgb(var(--accent)); }
.chev { transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1); }
.collapsed .chev { transform: rotate(-90deg); }
.collapsed .body { display: none; }

.add { padding: 2px 16px 10px; }
.add-field { display: flex; align-items: center; gap: 4px; background: rgba(255, 255, 255, 0.1); border-radius: 14px; padding: 0 4px 0 16px; }
.add-field:focus-within { background: rgba(255, 255, 255, 0.16); box-shadow: inset 0 0 0 1.5px rgba(var(--accent), 0.7); }
.add input { flex: 1; min-width: 0; height: 48px; border: 0; background: none; color: var(--primary-text-color); font: inherit; font-size: 17px; outline: none; }
.add input::placeholder { color: rgba(255, 255, 255, 0.62); }
.who { display: flex; flex-wrap: wrap; gap: 8px; padding: 10px 2px 2px; }
.add:not(.active) .who { display: none; }

.chip { display: inline-flex; align-items: center; gap: 8px; height: 36px; padding: 0 14px 0 4px; border-radius: 18px; background: rgba(255, 255, 255, 0.1); font-size: 14px; font-weight: 600; }
.chip.anyone { padding-left: 14px; }
.chip[aria-pressed="true"] { background: rgba(var(--accent), 0.9); color: #2a1150; }
.avatar { width: 28px; height: 28px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: #2a1150; background: rgb(var(--person)); flex: none; overflow: hidden; }
.avatar img { width: 100%; height: 100%; object-fit: cover; }

.group-head { display: flex; align-items: center; gap: 8px; padding: 10px 14px 4px 18px; font-size: 14px; font-weight: 600; color: var(--secondary-text-color); }
.group-head .toggle { flex: 1; min-width: 0; display: flex; align-items: center; gap: 10px; min-height: 36px; text-align: left; font-weight: 600; }
.group-head .n { font-variant-numeric: tabular-nums; opacity: 0.8; font-weight: 500; }
.group-head .chev { --mdc-icon-size: 20px; cursor: pointer; }
.group.collapsed .rows { display: none; }
.group-head .clear { padding: 6px 10px; border-radius: 10px; font-size: 13px; color: rgb(var(--accent)); }

.rows { list-style: none; margin: 0; padding: 0 0 4px; }
.item { position: relative; overflow: hidden; }
.bin { position: absolute; inset: 0; display: flex; align-items: center; justify-content: flex-end; padding-right: 24px; background: #e5484d; color: #fff; opacity: 0; }
.slide { position: relative; display: flex; align-items: flex-start; gap: 14px; padding: 12px 18px; min-height: 52px;
  background: transparent; touch-action: pan-y; transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1); }
.item.dragging .slide { transition: none; }
.item.swiped .slide { background: rgba(42, 17, 80, 0.55); }
.check { flex: none; width: 26px; height: 26px; margin-top: 1px; border-radius: 8px; border: 2px solid rgba(255, 255, 255, 0.55);
  display: inline-flex; align-items: center; justify-content: center; color: #2a1150; transition: background 0.15s, border-color 0.15s; }
.check:hover { border-color: rgb(var(--accent)); }
.check ha-icon { --mdc-icon-size: 18px; visibility: hidden; }
.done .check, .picked .check { background: rgb(var(--accent)); border-color: rgb(var(--accent)); }
.done .check ha-icon, .picked .check ha-icon { visibility: visible; }
.selecting .check { border-radius: 50%; }
.text { flex: 1; min-width: 0; padding-top: 1px; cursor: pointer; }
.summary { font-size: 18px; line-height: 1.35; overflow-wrap: anywhere; }
.done .summary { text-decoration: line-through; text-decoration-color: rgba(255, 255, 255, 0.5); }
.done .text, .done .meta-who { opacity: 0.55; }
.meta { display: flex; flex-wrap: wrap; gap: 4px 12px; margin-top: 3px; font-size: 14px; color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
.meta .late { color: #ffc2a8; font-weight: 600; }
.notes { white-space: pre-line; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.meta-who { margin-top: 1px; }

.editor { display: grid; gap: 10px; padding: 0 18px 16px 58px; }
.editor input, .editor textarea { width: 100%; border: 0; border-radius: 12px; background: rgba(255, 255, 255, 0.1); color: var(--primary-text-color); font: inherit; font-size: 16px; padding: 12px 14px; outline: none; }
.editor input:focus, .editor textarea:focus { box-shadow: inset 0 0 0 1.5px rgba(var(--accent), 0.7); }
.editor textarea { min-height: 72px; resize: vertical; }
.editor input[type="date"] { color-scheme: dark; max-width: 220px; }
.editor .who { padding: 0; }
.editor label { font-size: 13px; font-weight: 600; color: var(--secondary-text-color); display: grid; gap: 6px; }
.actions { display: flex; gap: 10px; flex-wrap: wrap; }
.btn { height: 40px; padding: 0 18px; border-radius: 20px; font-size: 14px; font-weight: 600; background: rgba(255, 255, 255, 0.12); }
.btn.primary { background: rgb(var(--accent)); color: #2a1150; }
.btn.danger { color: #ffb3b5; margin-left: auto; }
.btn:disabled { opacity: 0.4; cursor: default; }

.empty { padding: 18px 22px 22px; color: var(--secondary-text-color); font-size: 15px; }
.bar, .toast { display: flex; align-items: center; gap: 10px; margin: 6px 12px 12px; padding: 8px 8px 8px 16px; border-radius: 16px; background: rgba(42, 17, 80, 0.72); font-size: 15px; }
.bar .grow, .toast .grow { flex: 1; }
.toast .btn { color: rgb(var(--accent)); background: none; }
`;

const PEOPLE_COLORS = ['255, 179, 138', '143, 211, 255', '126, 240, 198', '215, 196, 255', '255, 209, 102', '255, 156, 196'];
const TAG = /^@([^\n]+?)\s*(?:\n|$)/;

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const initials = (name) => name.split(/\s+/).map((p) => p[0]).join('').slice(0, 2).toUpperCase();

// "@Judy\nBring the blue one" -> { who: "Judy", notes: "Bring the blue one" }
export function parseDescription(description) {
  const m = (description || '').match(TAG);
  if (!m) return { who: null, notes: description || '' };
  return { who: m[1].trim(), notes: description.slice(m[0].length) };
}

export function buildDescription(who, notes) {
  const text = (who ? `@${who}\n` : '') + (notes || '').trim();
  return text.trim() ? text.replace(/\n$/, '') : null;
}

export function dueLabel(due, today = new Date()) {
  if (!due) return null;
  const d = due.includes('T') ? new Date(due) : new Date(`${due}T00:00:00`);
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const days = Math.round((new Date(d.getFullYear(), d.getMonth(), d.getDate()) - start) / 86400000);
  const time = due.includes('T') ? ` ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : '';
  if (days === 0) return { text: `Today${time}`, late: false };
  if (days === 1) return { text: `Tomorrow${time}`, late: false };
  const date = d.toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short' });
  return { text: days < 0 ? `Overdue · ${date}` : `${date}${time}`, late: days < 0 };
}

export function sortItems(items, order) {
  const list = [...items];
  if (order === 'alpha') list.sort((a, b) => a.summary.localeCompare(b.summary));
  if (order === 'due') {
    list.sort((a, b) => (a.due || '9999').localeCompare(b.due || '9999'));
  }
  return list;
}

class AthanListCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entity) throw new Error('athan-list-card: "entity" is required');
    this.config = config;
    this._items = [];
    this._hidden = new Set(); // deleted, waiting out the undo window
    this._selected = new Set();
    this._selecting = false;
    this._open = null; // uid of the item being edited
    this._addWho = null;
    this._ui = this._loadUi();
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
    this._skeleton();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first || this._people === undefined) this._people = this._findPeople();
    if (first) this._subscribe();
    const state = hass.states[this.config.entity];
    const features = state ? state.attributes.supported_features || 0 : 0;
    if (features !== this._features) {
      this._features = features;
      this._renderAdd();
      this._render();
    }
  }

  get _canAssign() { return Boolean(this._features & 64) && this._people.length > 0; }
  get _canDue() { return Boolean(this._features & 16); }
  get _canNotes() { return Boolean(this._features & 64); }

  connectedCallback() { if (this._hass && !this._unsub) this._subscribe(); }

  disconnectedCallback() {
    if (this._unsub) { this._unsub.then((u) => u()).catch(() => {}); this._unsub = null; }
    this._flushDeletes();
  }

  getCardSize() { return 6; }

  // ---- data -------------------------------------------------------------

  _subscribe() {
    if (!this._hass || this._unsub || !this.isConnected) return;
    this._unsub = this._hass.connection.subscribeMessage((msg) => {
      this._items = msg.items || [];
      this._render();
    }, { type: 'todo/item/subscribe', entity_id: this.config.entity });
    this._unsub.catch((e) => console.error('athan-list-card:', e));
  }

  _call(service, data) {
    return this._hass.callService('todo', service, data, { entity_id: this.config.entity })
      .catch((e) => this._toast(`Couldn't save: ${e.message || e}`));
  }

  _findPeople() {
    const states = Object.values(this._hass.states).filter((s) => s.entity_id.startsWith('person.'));
    const wanted = this.config.people;
    const names = wanted || states.map((s) => s.attributes.friendly_name).sort();
    return names.map((name, i) => {
      const s = states.find((p) => p.attributes.friendly_name === name);
      return { name, picture: s && s.attributes.entity_picture, color: PEOPLE_COLORS[i % PEOPLE_COLORS.length] };
    });
  }

  _person(name) { return this._people.find((p) => p.name === name); }

  // ---- per-viewer UI state (collapsed list and groups) --------------------

  _loadUi() {
    try { return JSON.parse(localStorage.getItem(`athan-list:${this.config.entity}`)) || { groups: {} }; } catch (_) { return { groups: {} }; }
  }

  _saveUi() {
    try { localStorage.setItem(`athan-list:${this.config.entity}`, JSON.stringify(this._ui)); } catch (_) { /* private mode */ }
  }

  // ---- rendering ---------------------------------------------------------

  _skeleton() {
    const accent = this.config.color || '255, 209, 102';
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <ha-card style="--accent: ${esc(accent)}">
        <div class="head" role="button" tabindex="0" aria-expanded="true">
          <div class="title"><h1>${esc(this.config.title || '')}</h1><span class="count"></span></div>
          <button class="icon-btn select" title="Select items" aria-pressed="false"><ha-icon icon="mdi:checkbox-multiple-marked-outline"></ha-icon></button>
          <ha-icon class="chev" icon="mdi:chevron-down"></ha-icon>
        </div>
        <div class="body">
          <div class="add"></div>
          <div class="list"></div>
          <div class="footer"></div>
        </div>
      </ha-card>`;
    const root = this.shadowRoot;
    this._card = root.querySelector('ha-card');
    const head = root.querySelector('.head');
    const toggle = () => {
      this._ui.collapsed = !this._ui.collapsed;
      this._saveUi();
      this._applyCollapsed();
    };
    head.addEventListener('click', (e) => { if (!e.target.closest('.select')) toggle(); });
    head.addEventListener('keydown', (e) => {
      if ((e.key === 'Enter' || e.key === ' ') && e.target === head) { e.preventDefault(); toggle(); }
    });
    root.querySelector('.select').addEventListener('click', () => this._setSelecting(!this._selecting));
    this._applyCollapsed();

    const list = root.querySelector('.list');
    list.addEventListener('click', (e) => this._onListClick(e));
    list.addEventListener('submit', (e) => e.preventDefault());
    list.addEventListener('keydown', (e) => {
      if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('.text')) { e.preventDefault(); e.target.click(); }
    });
    list.addEventListener('pointerdown', (e) => this._swipeStart(e));
    list.addEventListener('focusout', () => setTimeout(() => {
      if (this._dirty && !this._editing()) this._render();
    }));
    root.querySelector('.footer').addEventListener('click', (e) => this._onFooterClick(e));
  }

  _applyCollapsed() {
    this._card.classList.toggle('collapsed', Boolean(this._ui.collapsed));
    this.shadowRoot.querySelector('.head').setAttribute('aria-expanded', String(!this._ui.collapsed));
  }

  _renderAdd() {
    const add = this.shadowRoot.querySelector('.add');
    if (!(this._features & 1)) { add.innerHTML = ''; return; }
    add.innerHTML = `
      <div class="add-field">
        <input enterkeyhint="done" placeholder="Add to ${esc(this.config.title || 'the list')}" aria-label="New item">
        <button class="icon-btn go" title="Add"><ha-icon icon="mdi:plus"></ha-icon></button>
      </div>
      ${this._canAssign ? `<div class="who" role="group" aria-label="Assign to">${this._whoChips(this._addWho)}</div>` : ''}`;
    const input = add.querySelector('input');
    const submit = () => {
      const summary = input.value.trim();
      if (!summary) return;
      const data = { item: summary };
      const description = buildDescription(this._addWho, '');
      if (description) data.description = description;
      this._call('add_item', data);
      input.value = '';
      input.focus();
    };
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') submit(); });
    add.querySelector('.go').addEventListener('click', submit);
    add.addEventListener('focusin', () => add.classList.add('active'));
    add.addEventListener('focusout', () => setTimeout(() => {
      if (!add.contains(this.shadowRoot.activeElement)) add.classList.remove('active');
    }));
    add.querySelector('.who')?.addEventListener('click', (e) => {
      const chip = e.target.closest('.chip');
      if (!chip) return;
      this._addWho = chip.dataset.who || null;
      add.querySelectorAll('.chip').forEach((c) => c.setAttribute('aria-pressed', String(c === chip)));
      input.focus();
    });
  }

  _whoChips(current) {
    const anyone = `<button type="button" class="chip anyone" data-who="" aria-pressed="${!current}">Anyone</button>`;
    return anyone + this._people.map((p) => `
      <button type="button" class="chip" data-who="${esc(p.name)}" aria-pressed="${current === p.name}">
        ${this._avatar(p)}${esc(p.name)}</button>`).join('');
  }

  _avatar(p) {
    const inner = p.picture ? `<img src="${esc(p.picture)}" alt="">` : esc(initials(p.name));
    return `<span class="avatar" style="--person: ${p.color}">${inner}</span>`;
  }

  _editing() {
    const active = this.shadowRoot.activeElement;
    return Boolean(active && active.closest('.editor'));
  }

  _render() {
    if (!this._hass || this._features === undefined) return;
    const visible = this._items.filter((i) => !this._hidden.has(i.uid));
    const open = visible.filter((i) => i.status !== 'completed');
    const done = visible.filter((i) => i.status === 'completed');
    const n = open.length;
    const count = this.shadowRoot.querySelector('.count');
    count.textContent = n === 0 ? (this.config.empty || 'All done') : (this.config.count || '{n} left').replace('{n}', n);

    // Typing in an item's editor must not be wiped by someone else's change.
    if (this._editing()) { this._dirty = true; return; }
    this._dirty = false;

    const order = this.config.order;
    const groups = [];
    if (this._canAssign) {
      const by = new Map(this._people.map((p) => [p.name, []]));
      const anyone = [];
      for (const item of open) {
        const { who } = parseDescription(item.description);
        (who && by.has(who) ? by.get(who) : anyone).push(item);
      }
      for (const p of this._people) {
        if (by.get(p.name).length) groups.push({ key: `p:${p.name}`, label: p.name, person: p, items: by.get(p.name) });
      }
      if (anyone.length) groups.push({ key: 'anyone', label: 'Anyone', items: anyone });
    } else if (open.length) {
      groups.push({ key: 'open', label: null, items: open });
    }
    if (done.length) groups.push({ key: 'done', label: 'Done', items: done, done: true });

    const list = this.shadowRoot.querySelector('.list');
    if (!groups.length) {
      list.innerHTML = `<div class="empty">Nothing here yet. Add the first one above.</div>`;
    } else {
      list.innerHTML = groups.map((g) => this._group(g, sortItems(g.items, order))).join('');
    }
    this._card.classList.toggle('selecting', this._selecting);
    this._renderFooter();
    if (this._focusEditor) {
      this._focusEditor = false;
      list.querySelector('.editor input')?.focus();
    }
  }

  _group(g, items) {
    const collapsed = this._ui.groups[g.key] ?? (g.done && items.length > 3);
    const head = g.label === null ? '' : `
      <div class="group-head">
        <button class="toggle" data-group="${esc(g.key)}" aria-expanded="${!collapsed}">
          ${g.person ? this._avatar(g.person) : ''}<span>${esc(g.label)}</span><span class="n">${items.length}</span>
        </button>
        ${g.done && this._features & 2 ? '<button class="clear" data-clear>Clear</button>' : ''}
        <ha-icon class="chev" icon="mdi:chevron-down" data-group="${esc(g.key)}"></ha-icon>
      </div>`;
    return `<section class="group ${collapsed ? 'collapsed' : ''}">${head}
      <ul class="rows">${items.map((i) => this._row(i, !g.person)).join('')}</ul></section>`;
  }

  _row(item, showWho) {
    const { who, notes } = parseDescription(item.description);
    const person = who && this._person(who);
    const due = dueLabel(item.due);
    const picked = this._selected.has(item.uid);
    const done = item.status === 'completed';
    const label = this._selecting ? (picked ? 'Deselect' : 'Select') : (done ? 'Mark as not done' : 'Mark as done');
    const meta = [
      due ? `<span class="${due.late && !done ? 'late' : ''}">${esc(due.text)}</span>` : '',
      notes ? `<span class="notes">${esc(notes)}</span>` : '',
    ].join('');
    return `
      <li class="item ${done ? 'done' : ''} ${picked ? 'picked' : ''}" data-uid="${esc(item.uid)}">
        <div class="bin" aria-hidden="true"><ha-icon icon="mdi:trash-can-outline"></ha-icon></div>
        <div class="slide">
          <button class="check" aria-label="${label}: ${esc(item.summary)}"><ha-icon icon="mdi:check-bold"></ha-icon></button>
          <div class="text" role="button" tabindex="0" aria-expanded="${this._open === item.uid}">
            <div class="summary">${esc(item.summary)}</div>
            ${meta ? `<div class="meta">${meta}</div>` : ''}
          </div>
          ${showWho && person && !done ? `<span class="meta-who" title="${esc(person.name)}">${this._avatar(person)}</span>` : ''}
        </div>
        ${this._open === item.uid && !this._selecting ? this._editor(item, who, notes) : ''}
      </li>`;
  }

  _editor(item, who, notes) {
    return `
      <form class="editor">
        <input name="summary" value="${esc(item.summary)}" aria-label="Item" required>
        ${this._canAssign ? `<div class="who" role="group" aria-label="Assign to">${this._whoChips(who)}</div>` : ''}
        ${this._canDue ? `<label>Due <input type="date" name="due" value="${esc((item.due || '').slice(0, 10))}"></label>` : ''}
        ${this._canNotes ? `<label>Notes <textarea name="notes">${esc(notes)}</textarea></label>` : ''}
        <div class="actions">
          <button class="btn primary" type="submit">Save</button>
          <button class="btn" type="button" data-cancel>Cancel</button>
          ${this._features & 2 ? '<button class="btn danger" type="button" data-delete>Delete</button>' : ''}
        </div>
      </form>`;
  }

  _renderFooter() {
    const footer = this.shadowRoot.querySelector('.footer');
    this.shadowRoot.querySelector('.select').setAttribute('aria-pressed', String(this._selecting));
    this.shadowRoot.querySelector('.select').classList.toggle('on', this._selecting);
    let html = '';
    if (this._selecting) {
      const all = this._visible().length;
      const n = this._selected.size;
      html += `<div class="bar">
        <span class="grow">${n} selected</span>
        <button class="btn" data-all>${n === all && all ? 'Select none' : 'Select all'}</button>
        <button class="btn primary" data-delete-selected ${n ? '' : 'disabled'}>Delete</button>
        <button class="btn" data-done-selecting>Done</button></div>`;
    }
    if (this._pending) {
      html += `<div class="toast" role="status"><span class="grow">${esc(this._pending.text)}</span>
        ${this._pending.uids ? '<button class="btn" data-undo>Undo</button>' : ''}</div>`;
    }
    footer.innerHTML = html;
  }

  _visible() { return this._items.filter((i) => !this._hidden.has(i.uid)); }

  // ---- interaction -------------------------------------------------------

  _onListClick(e) {
    if (this._swallowClick) { this._swallowClick = false; return; }
    const t = e.target;
    const groupToggle = t.closest('[data-group]');
    if (groupToggle) {
      const key = groupToggle.dataset.group;
      const section = groupToggle.closest('.group');
      const collapsed = !section.classList.contains('collapsed');
      this._ui.groups[key] = collapsed;
      this._saveUi();
      section.classList.toggle('collapsed', collapsed);
      section.querySelector('button.toggle').setAttribute('aria-expanded', String(!collapsed));
      return;
    }
    if (t.closest('[data-clear]')) {
      const done = this._visible().filter((i) => i.status === 'completed').map((i) => i.uid);
      this._delete(done);
      return;
    }
    const li = t.closest('.item');
    if (!li) return;
    const uid = li.dataset.uid;
    const item = this._items.find((i) => i.uid === uid);
    if (!item) return;

    if (t.closest('.editor')) { this._onEditorClick(e, item); return; }

    if (this._selecting) {
      if (this._selected.has(uid)) this._selected.delete(uid); else this._selected.add(uid);
      this._render();
      return;
    }
    if (t.closest('.check')) {
      this._call('update_item', { item: uid, status: item.status === 'completed' ? 'needs_action' : 'completed' });
      return;
    }
    if (t.closest('.text') && this._features & 4) {
      this._open = this._open === uid ? null : uid;
      this._focusEditor = this._open !== null;
      this._render();
    }
  }

  _onEditorClick(e, item) {
    const form = e.target.closest('.editor');
    const chip = e.target.closest('.chip');
    if (chip) {
      e.preventDefault();
      form.querySelectorAll('.chip').forEach((c) => c.setAttribute('aria-pressed', String(c === chip)));
      return;
    }
    if (e.target.closest('[data-cancel]')) { this._closeEditor(); return; }
    if (e.target.closest('[data-delete]')) { this._closeEditor(); this._delete([item.uid]); return; }
    if (e.target.closest('[type="submit"]')) {
      e.preventDefault();
      const field = (name) => form.querySelector(`[name="${name}"]`);
      const summary = field('summary').value.trim();
      if (!summary) { field('summary').focus(); return; }
      const data = { item: item.uid, rename: summary };
      if (this._canDue) data.due_date = field('due').value || null;
      if (this._canNotes) {
        const picked = form.querySelector('.chip[aria-pressed="true"]');
        const who = this._canAssign ? (picked && picked.dataset.who) || null : parseDescription(item.description).who;
        data.description = buildDescription(who, field('notes').value);
      }
      this._call('update_item', data);
      this._closeEditor();
    }
  }

  _closeEditor() {
    this._open = null;
    this.shadowRoot.activeElement?.blur();
    this._render();
  }

  _setSelecting(on) {
    this._selecting = on;
    this._selected.clear();
    this._open = null;
    if (on && this._ui.collapsed) { this._ui.collapsed = false; this._applyCollapsed(); }
    this._render();
  }

  _onFooterClick(e) {
    const t = e.target;
    if (t.closest('[data-undo]')) { this._undo(); return; }
    if (t.closest('[data-done-selecting]')) { this._setSelecting(false); return; }
    if (t.closest('[data-all]')) {
      const all = this._visible().map((i) => i.uid);
      if (this._selected.size === all.length) this._selected.clear(); else all.forEach((u) => this._selected.add(u));
      this._render();
      return;
    }
    if (t.closest('[data-delete-selected]')) {
      const uids = [...this._selected];
      this._setSelecting(false);
      this._delete(uids);
    }
  }

  // Deletes wait out a 6 s undo window before Home Assistant is told, so an
  // accidental swipe or "select all" costs nothing.
  _delete(uids) {
    if (!uids.length) return;
    this._flushDeletes();
    uids.forEach((u) => this._hidden.add(u));
    const n = uids.length;
    this._pending = {
      uids, text: n === 1 ? 'Deleted 1 item' : `Deleted ${n} items`,
      timer: setTimeout(() => this._flushDeletes(), 6000),
    };
    this._render();
  }

  _flushDeletes() {
    const p = this._pending;
    if (!p || !p.uids) return;
    clearTimeout(p.timer);
    this._pending = null;
    const uids = p.uids.filter((u) => this._items.some((i) => i.uid === u));
    if (uids.length && this._hass) {
      this._call('remove_item', { item: uids }).finally(() => uids.forEach((u) => this._hidden.delete(u)));
    } else {
      p.uids.forEach((u) => this._hidden.delete(u));
    }
    if (this.isConnected) this._render();
  }

  _undo() {
    const p = this._pending;
    if (!p) return;
    clearTimeout(p.timer);
    p.uids.forEach((u) => this._hidden.delete(u));
    this._pending = null;
    this._render();
  }

  _toast(text) {
    if (this._pending && this._pending.uids) return;
    clearTimeout(this._pending && this._pending.timer);
    this._pending = { text, timer: setTimeout(() => { this._pending = null; this._renderFooter(); }, 5000) };
    this._renderFooter();
  }

  // ---- swipe left to delete --------------------------------------------

  _swipeStart(e) {
    const li = e.target.closest('.item');
    if (!li || this._selecting || !(this._features & 2) || e.target.closest('.editor, .check')) return;
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    const slide = li.querySelector('.slide');
    const bin = li.querySelector('.bin');
    const x0 = e.clientX;
    const y0 = e.clientY;
    let dx = 0;
    let active = false;
    const move = (ev) => {
      dx = Math.min(0, ev.clientX - x0);
      if (!active) {
        if (Math.abs(ev.clientY - y0) > 10) return end(null); // a scroll, not a swipe
        if (dx > -10) return undefined;
        active = true;
        li.classList.add('dragging', 'swiped');
        try { li.setPointerCapture(ev.pointerId); } catch (_) { /* already released */ }
      }
      slide.style.transform = `translateX(${dx}px)`;
      bin.style.opacity = String(Math.min(1, -dx / 80));
      return undefined;
    };
    const end = () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', end);
      window.removeEventListener('pointercancel', end);
      if (!active) return;
      this._swallowClick = true;
      setTimeout(() => { this._swallowClick = false; }, 0);
      li.classList.remove('dragging');
      if (-dx > li.offsetWidth * 0.35) {
        slide.style.transform = `translateX(-${li.offsetWidth}px)`;
        setTimeout(() => this._delete([li.dataset.uid]), 180);
      } else {
        slide.style.transform = '';
        bin.style.opacity = '0';
        setTimeout(() => li.classList.remove('swiped'), 280);
      }
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', end);
    window.addEventListener('pointercancel', end);
  }
}

if (!customElements.get('athan-list-card')) {
  customElements.define('athan-list-card', AthanListCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: 'athan-list-card',
    name: 'Athan Hub list',
    description: 'Family to-do list with assignees, collapsible groups, swipe and multi-select delete',
  });
}
