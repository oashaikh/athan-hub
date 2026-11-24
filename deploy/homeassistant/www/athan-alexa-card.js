// Athan Hub "Ask Alexa" card for the Home dashboard.
//
// Type something and press Say for the Echo to read it out loud, or Ask for
// Alexa to carry it out as a spoken command. The phrase chips say themselves
// with one tap. Enter is Say.
//
// No optional chaining, ?? or flex gap: the LG TV's browser is Chromium 68.
//
//   type: custom:athan-alexa-card
//   entity: media_player.hallway_echo_pop   # shown as the speaker, with its state
//   phrases: [Dinner is ready, Time to pray]

const STYLE = `
:host { display: block; --accent: 92, 214, 255; }
ha-card { overflow: hidden; }
* { box-sizing: border-box; }
button { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; }
button:focus-visible { outline: 2px solid rgb(var(--accent)); outline-offset: 2px; }
ha-icon { --mdc-icon-size: 22px; display: inline-flex; }

.head { display: flex; align-items: center; padding: 20px 20px 14px 22px;
  background: radial-gradient(120% 170% at 0% 0%, rgba(var(--accent), 0.26) 0%, transparent 64%); }
.orb { flex: none; width: 46px; height: 46px; border-radius: 50%; margin-right: 14px; display: flex; align-items: center; justify-content: center;
  color: #10233a; background: radial-gradient(circle at 35% 30%, #c9f4ff 0%, rgb(var(--accent)) 55%, #2b8fd6 100%);
  box-shadow: 0 0 0 0 rgba(var(--accent), 0.6); }
.busy .orb { animation: pulse 1.2s ease-out infinite; }
@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(var(--accent), 0.55); } 100% { box-shadow: 0 0 0 18px rgba(var(--accent), 0); } }
.titles { flex: 1; min-width: 0; }
h1 { font-size: 30px; font-weight: 300; letter-spacing: -0.02em; line-height: 1.1; margin: 0; }
.speaker { margin-top: 3px; font-size: 14px; color: var(--secondary-text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 7px; vertical-align: 1px; background: rgb(126, 240, 198); }
.dot.off { background: rgba(255, 255, 255, 0.35); }

.body { padding: 2px 16px 18px; }
.field { display: flex; align-items: center; border-radius: 16px; padding: 0 6px 0 18px; background: rgba(255, 255, 255, 0.1); }
.field:focus-within { background: rgba(255, 255, 255, 0.16); box-shadow: inset 0 0 0 1.5px rgba(var(--accent), 0.75); }
input { flex: 1; min-width: 0; height: 54px; border: 0; background: none; color: var(--primary-text-color); font: inherit; font-size: 18px; outline: none; caret-color: rgb(var(--accent)); }
input::placeholder { color: rgba(255, 255, 255, 0.6); }
.clear { width: 40px; height: 40px; border-radius: 12px; display: flex; align-items: center; justify-content: center; color: var(--secondary-text-color); }
.empty .clear { visibility: hidden; }

.actions { display: flex; margin-top: 12px; }
.btn { flex: 1; height: 50px; border-radius: 25px; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 600;
  background: rgba(255, 255, 255, 0.12); transition: transform 0.12s, opacity 0.15s; }
.btn + .btn { margin-left: 10px; }
.btn ha-icon { margin-right: 8px; --mdc-icon-size: 20px; }
.btn.primary { background: rgb(var(--accent)); color: #10233a; }
.btn:active { transform: scale(0.97); }
.empty .btn { opacity: 0.45; pointer-events: none; }

.label { margin: 18px 2px 8px; font-size: 13px; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; color: var(--secondary-text-color); }
.chips { display: flex; flex-wrap: wrap; margin: 0 -4px; }
.chip { margin: 4px; height: 38px; padding: 0 16px 0 12px; border-radius: 19px; display: inline-flex; align-items: center; font-size: 14px; font-weight: 600;
  background: rgba(var(--accent), 0.14); border: 1px solid rgba(var(--accent), 0.28); }
.chip ha-icon { --mdc-icon-size: 18px; margin-right: 6px; color: rgb(var(--accent)); }
.chip:active { background: rgba(var(--accent), 0.3); }

.status { min-height: 20px; margin: 12px 4px 0; font-size: 14px; color: var(--secondary-text-color); }
.status.ok { color: rgb(var(--accent)); }
.status.bad { color: #ffb3b5; }
`;

const DEFAULT_PHRASES = ['Dinner is ready', 'Time to pray', 'Come downstairs please', 'Bedtime in ten minutes'];
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

class AthanAlexaCard extends HTMLElement {
  setConfig(config) {
    this.config = config || {};
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
    const phrases = this.config.phrases || DEFAULT_PHRASES;
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <ha-card class="empty">
        <div class="head">
          <div class="orb"><ha-icon icon="mdi:account-voice"></ha-icon></div>
          <div class="titles"><h1>${esc(this.config.title || 'Ask Alexa')}</h1><div class="speaker"></div></div>
        </div>
        <div class="body">
          <div class="field">
            <input type="text" maxlength="255" enterkeyhint="send" placeholder="Type a message or a command" aria-label="Message for Alexa">
            <button class="clear" aria-label="Clear"><ha-icon icon="mdi:close"></ha-icon></button>
          </div>
          <div class="actions">
            <button class="btn primary say"><ha-icon icon="mdi:account-voice"></ha-icon>Say it</button>
            <button class="btn ask"><ha-icon icon="mdi:send"></ha-icon>Ask Alexa</button>
          </div>
          <div class="label">Say now</div>
          <div class="chips">${phrases.map((p, i) => `<button class="chip" data-i="${i}"><ha-icon icon="mdi:bullhorn-outline"></ha-icon>${esc(p)}</button>`).join('')}</div>
          <div class="status" role="status"></div>
        </div>
      </ha-card>`;
    const root = this.shadowRoot;
    this._card = root.querySelector('ha-card');
    this._input = root.querySelector('input');
    this._status = root.querySelector('.status');
    this._input.addEventListener('input', () => this._sync());
    this._input.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); this._say(this._input.value); } });
    root.querySelector('.clear').addEventListener('click', () => { this._input.value = ''; this._sync(); this._input.focus(); });
    root.querySelector('.say').addEventListener('click', () => this._say(this._input.value));
    root.querySelector('.ask').addEventListener('click', () => this._ask(this._input.value));
    root.querySelectorAll('.chip').forEach((chip) => chip.addEventListener('click', () => this._say(phrases[Number(chip.dataset.i)], true)));
  }

  set hass(hass) {
    this._hass = hass;
    const id = this.config.entity;
    const state = id ? hass.states[id] : null;
    const name = state ? state.attributes.friendly_name || id : 'Echo';
    const on = state && state.state !== 'unavailable' && state.state !== 'off';
    const text = `<span class="dot${on ? '' : ' off'}"></span>${esc(name)}${state && state.state === 'unavailable' ? ' · offline' : ''}`;
    if (text !== this._speaker) {
      this._speaker = text;
      this.shadowRoot.querySelector('.speaker').innerHTML = text;
    }
  }

  getCardSize() { return 5; }

  _sync() { this._card.classList.toggle('empty', !this._input.value.trim()); }

  _show(text, kind) {
    clearTimeout(this._timer);
    this._status.textContent = text;
    this._status.className = `status ${kind || ''}`;
    if (kind) this._timer = setTimeout(() => { this._status.textContent = ''; }, 5000);
  }

  async _run(label, work, keepText) {
    const message = this._input.value;
    this._card.classList.add('busy');
    this._show(label);
    try {
      await work();
      if (!keepText) { this._input.value = ''; this._sync(); }
      this._show('Done', 'ok');
    } catch (e) {
      this._input.value = message;
      this._show(`Alexa did not get that: ${(e && e.message) || e}`, 'bad');
    } finally {
      this._card.classList.remove('busy');
    }
  }

  _say(text, keepText) {
    const message = String(text || '').trim();
    if (!message || !this._hass) return;
    this._run('Saying it…', () => this._hass.callService('script', 'alexa_say', { message }), keepText);
  }

  _ask(text) {
    const command = String(text || '').trim();
    if (!command || !this._hass) return;
    // script.ask_alexa reads the dashboard's text box, as the iPhone widgets do.
    this._run('Asking Alexa…', () => this._hass
      .callService('input_text', 'set_value', { value: command }, { entity_id: 'input_text.alexa_command' })
      .then(() => this._hass.callService('script', 'ask_alexa', {})));
  }
}

customElements.define('athan-alexa-card', AthanAlexaCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: 'athan-alexa-card', name: 'Athan Ask Alexa', description: 'Say a message or send a command to an Echo' });
