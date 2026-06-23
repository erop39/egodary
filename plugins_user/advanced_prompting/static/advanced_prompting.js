/**
 * Advanced Prompting Plugin v0.1.0
 * Drag-and-drop редактор bucket-блоков для eGOdary.
 *
 * Инжектируется в index.html автоматически при наличии плагина.
 * Добавляет карточку "Advanced Prompting" в правую колонку,
 * появляющуюся после Generate.
 */
(function () {
  "use strict";

  // ── Константы ───────────────────────────────────────────────────────────
  const API_BASE = "/api/advanced-prompting";
  const CARD_ID = "adv-prompt-card";
  const STORAGE_KEY = "egodary_adv_prompt_open";

  // ── Состояние плагина ────────────────────────────────────────────────────
  let apBlocks = [];       // [{name, label, tags:[]}]
  let apDragIdx = null;    // индекс перетаскиваемого блока
  let apEnabled = false;   // карточка развёрнута

  // ── Утилиты ──────────────────────────────────────────────────────────────
  function esc(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function apApi(path, opts = {}) {
    return fetch(API_BASE + path, {
      headers: { "Content-Type": "application/json" },
      ...opts,
    }).then((r) => {
      if (!r.ok) throw new Error("Advanced Prompting API error: " + r.status);
      return r.json();
    });
  }

  // ── Инициализация карточки ───────────────────────────────────────────────
  function initCard() {
    if (document.getElementById(CARD_ID)) return;

    const aside = document.querySelector("aside") || document.querySelector(".right-column");
    if (!aside) return;

    const card = document.createElement("div");
    card.id = CARD_ID;
    card.className = "card result-card adv-prompt-card";
    card.style.display = "none";
    card.innerHTML = `
      <div class="card-title row-between adv-prompt-header" style="cursor:pointer" id="adv-prompt-toggle">
        <span>Advanced Prompting</span>
        <span class="adv-prompt-badge" id="adv-prompt-badge" style="font-size:11px;color:var(--text-muted)">▸ развернуть</span>
      </div>
      <div id="adv-prompt-body" style="display:none">
        <p style="font-size:11px;color:var(--text-muted);margin:0 0 10px">
          Перетаскивай блоки · редактируй теги · нажми Rebuild
        </p>
        <div id="adv-prompt-blocks"></div>
        <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap">
          <button class="btn btn-primary btn-sm" id="adv-prompt-rebuild">⟳ Rebuild</button>
          <button class="btn btn-secondary btn-sm" id="adv-prompt-reset">↺ Reset</button>
          <button class="btn btn-secondary btn-sm" id="adv-prompt-copy">Copy</button>
        </div>
        <textarea id="adv-prompt-output" rows="4" readonly
          style="margin-top:10px;width:100%;resize:vertical;font-size:12px;font-family:monospace"
          placeholder="Нажми Rebuild…"></textarea>
      </div>
    `;

    // Вставляем после карточки Positive (перед Negative)
    const negCard = document.getElementById("negative-card");
    if (negCard) {
      aside.insertBefore(card, negCard);
    } else {
      aside.appendChild(card);
    }

    injectStyles();
    bindCardEvents(card);
  }

  function bindCardEvents(card) {
    document.getElementById("adv-prompt-toggle").onclick = toggleBody;
    document.getElementById("adv-prompt-rebuild").onclick = doRebuild;
    document.getElementById("adv-prompt-reset").onclick = doReset;
    document.getElementById("adv-prompt-copy").onclick = doCopy;

    // Восстанавливаем состояние (открыто/закрыто)
    if (localStorage.getItem(STORAGE_KEY) === "1") {
      apEnabled = true;
      showBody();
    }
  }

  function toggleBody() {
    apEnabled = !apEnabled;
    localStorage.setItem(STORAGE_KEY, apEnabled ? "1" : "0");
    apEnabled ? showBody() : hideBody();
  }

  function showBody() {
    document.getElementById("adv-prompt-body").style.display = "";
    document.getElementById("adv-prompt-badge").textContent = "▾ свернуть";
  }

  function hideBody() {
    document.getElementById("adv-prompt-body").style.display = "none";
    document.getElementById("adv-prompt-badge").textContent = "▸ развернуть";
  }

  // ── Загрузка блоков из результата Generate ───────────────────────────────
  async function loadFromBuckets(buckets) {
    const card = document.getElementById(CARD_ID);
    if (!card) return;

    // Фильтруем пустые
    const filtered = {};
    for (const [k, v] of Object.entries(buckets || {})) {
      if (Array.isArray(v) && v.length) filtered[k] = v;
    }

    try {
      const data = await apApi("/from-generate", {
        method: "POST",
        body: JSON.stringify(filtered),
      });
      apBlocks = data.blocks || [];
    } catch {
      // Fallback: строим блоки локально
      apBlocks = Object.entries(filtered).map(([name, tags]) => ({
        name,
        label: name.charAt(0).toUpperCase() + name.slice(1),
        tags,
      }));
    }

    card.style.display = "";
    renderBlocks();
    document.getElementById("adv-prompt-output").value = "";
  }

  // ── Рендер блоков ────────────────────────────────────────────────────────
  function renderBlocks() {
    const container = document.getElementById("adv-prompt-blocks");
    if (!container) return;
    container.innerHTML = "";

    apBlocks.forEach((block, idx) => {
      const el = document.createElement("div");
      el.className = "adv-block";
      el.draggable = true;
      el.dataset.idx = idx;

      el.innerHTML = `
        <div class="adv-block-header">
          <span class="adv-block-drag" title="Перетащить">⠿</span>
          <span class="adv-block-label">${esc(block.label || block.name)}</span>
          <span class="adv-block-count">${block.tags.length}</span>
          <button class="adv-block-toggle btn-ghost" data-idx="${idx}" title="Развернуть">▸</button>
        </div>
        <div class="adv-block-body" id="adv-block-body-${idx}" style="display:none">
          <textarea class="adv-block-textarea" data-idx="${idx}" rows="2">${esc(block.tags.join(", "))}</textarea>
        </div>
      `;

      // Drag events
      el.addEventListener("dragstart", onDragStart);
      el.addEventListener("dragover", onDragOver);
      el.addEventListener("drop", onDrop);
      el.addEventListener("dragend", onDragEnd);

      // Toggle body
      el.querySelector(".adv-block-toggle").onclick = (e) => {
        const body = document.getElementById("adv-block-body-" + idx);
        const btn = e.currentTarget;
        if (body.style.display === "none") {
          body.style.display = "";
          btn.textContent = "▾";
        } else {
          body.style.display = "none";
          btn.textContent = "▸";
        }
      };

      // Textarea change → sync tags
      el.querySelector(".adv-block-textarea").addEventListener("input", (e) => {
        const i = parseInt(e.target.dataset.idx, 10);
        apBlocks[i].tags = e.target.value
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean);
        const countEl = container.querySelectorAll(".adv-block-count")[i];
        if (countEl) countEl.textContent = apBlocks[i].tags.length;
      });

      container.appendChild(el);
    });
  }

  // ── Drag & Drop ──────────────────────────────────────────────────────────
  function onDragStart(e) {
    apDragIdx = parseInt(e.currentTarget.dataset.idx, 10);
    e.currentTarget.classList.add("adv-block-dragging");
    e.dataTransfer.effectAllowed = "move";
  }

  function onDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    const target = e.currentTarget;
    const targetIdx = parseInt(target.dataset.idx, 10);
    document.querySelectorAll(".adv-block").forEach((el) => el.classList.remove("adv-block-over"));
    if (targetIdx !== apDragIdx) target.classList.add("adv-block-over");
  }

  function onDrop(e) {
    e.preventDefault();
    const targetIdx = parseInt(e.currentTarget.dataset.idx, 10);
    if (apDragIdx === null || apDragIdx === targetIdx) return;

    // Переставляем
    const moved = apBlocks.splice(apDragIdx, 1)[0];
    apBlocks.splice(targetIdx, 0, moved);
    renderBlocks();
  }

  function onDragEnd(e) {
    e.currentTarget.classList.remove("adv-block-dragging");
    document.querySelectorAll(".adv-block").forEach((el) => el.classList.remove("adv-block-over"));
    apDragIdx = null;
  }

  // ── Rebuild ──────────────────────────────────────────────────────────────
  async function doRebuild() {
    const btn = document.getElementById("adv-prompt-rebuild");
    btn.disabled = true;
    btn.textContent = "…";
    try {
      const model_id = document.querySelector("#model-chips .chip.active")?.dataset.id || "illustrious";
      const data = await apApi("/rebuild", {
        method: "POST",
        body: JSON.stringify({ blocks: apBlocks, model_id }),
      });
      document.getElementById("adv-prompt-output").value = data.positive || "";

      // Опционально — обновляем основной output-positive
      const mainOut = document.getElementById("output-positive");
      if (mainOut) mainOut.value = data.positive || "";
    } catch (err) {
      document.getElementById("adv-prompt-output").value = "Ошибка: " + err.message;
    } finally {
      btn.disabled = false;
      btn.textContent = "⟳ Rebuild";
    }
  }

  function doReset() {
    // Перезагружаем из текущего output-positive через buckets
    // (buckets хранятся в output-buckets debug pre)
    const bucketsEl = document.getElementById("output-buckets");
    if (!bucketsEl) return;
    try {
      const buckets = JSON.parse(bucketsEl.textContent || "{}");
      loadFromBuckets(buckets);
      document.getElementById("adv-prompt-output").value = "";
    } catch {
      // ignore
    }
  }

  function doCopy() {
    const val = document.getElementById("adv-prompt-output").value;
    if (val && navigator.clipboard) {
      navigator.clipboard.writeText(val);
    }
  }

  // ── Перехват Generate ────────────────────────────────────────────────────
  // Патчим XMLHttpRequest/fetch чтобы поймать ответ /api/generate
  // Вместо этого вешаемся на MutationObserver на output-buckets
  function watchBuckets() {
    const bucketsEl = document.getElementById("output-buckets");
    if (!bucketsEl) {
      // Ждём появления элемента
      setTimeout(watchBuckets, 500);
      return;
    }

    const observer = new MutationObserver(() => {
      try {
        const buckets = JSON.parse(bucketsEl.textContent || "{}");
        if (Object.keys(buckets).length > 0) {
          loadFromBuckets(buckets);
        }
      } catch {
        // ignore parse errors
      }
    });

    observer.observe(bucketsEl, { childList: true, characterData: true, subtree: true });
  }

  // ── Стили ────────────────────────────────────────────────────────────────
  function injectStyles() {
    if (document.getElementById("adv-prompt-styles")) return;
    const style = document.createElement("style");
    style.id = "adv-prompt-styles";
    style.textContent = `
      .adv-prompt-card { }

      .adv-prompt-header { user-select: none; }

      .adv-block {
        border: 1px solid var(--border);
        border-radius: 8px;
        margin-bottom: 6px;
        background: var(--bg-card);
        transition: opacity 0.15s, border-color 0.15s;
      }

      .adv-block-dragging {
        opacity: 0.45;
      }

      .adv-block-over {
        border-color: var(--accent);
        background: color-mix(in srgb, var(--accent) 8%, var(--bg-card));
      }

      .adv-block-header {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 7px 10px;
        cursor: default;
      }

      .adv-block-drag {
        cursor: grab;
        color: var(--text-muted);
        font-size: 14px;
        flex-shrink: 0;
      }

      .adv-block-drag:active { cursor: grabbing; }

      .adv-block-label {
        flex: 1;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
      }

      .adv-block-count {
        font-size: 11px;
        font-weight: 700;
        color: var(--count);
        min-width: 16px;
        text-align: right;
      }

      .adv-block-toggle {
        font-size: 11px;
        padding: 0 4px;
        flex-shrink: 0;
      }

      .adv-block-body {
        padding: 0 10px 8px;
      }

      .adv-block-textarea {
        width: 100%;
        font-size: 11px;
        font-family: monospace;
        background: var(--bg);
        color: var(--text);
        border: 1px solid var(--border);
        border-radius: 5px;
        padding: 5px 7px;
        resize: vertical;
        box-sizing: border-box;
      }
    `;
    document.head.appendChild(style);
  }

  // ── Точка входа ──────────────────────────────────────────────────────────
  function init() {
    initCard();
    watchBuckets();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    // DOM уже готов (скрипт defer — должно сработать)
    init();
  }
})();
