/**
 * File: web/src/components/ItineraryTimeline.js
 * Purpose: Render a simple vertical timeline of itinerary items grouped by category.
 */
import { colorFor } from '../utils/colors.js';
import { formatCurrency } from '../utils/format.js';

export function renderItineraryTimeline(container, items) {
  container.innerHTML = '';
  const list = document.createElement('div');
  list.className = 'timeline';

  for (const item of items) {
    const row = document.createElement('div');
    row.className = 'tl-row';
    row.innerHTML = `
      <div class="tl-marker" style="background:${colorFor(item.category)}"></div>
      <div class="tl-body">
        <div class="tl-title">${item.label}</div>
        <div class="tl-sub">${item.category} ${item.perPerson ? '• ' + formatCurrency(item.perPerson) + ' pp' : ''}</div>
      </div>
      <div class="tl-amt">${formatCurrency(item.total)}</div>
    `;
    list.appendChild(row);
  }
  container.appendChild(list);

  const style = document.createElement('style');
  style.textContent = `
    .timeline { display:grid; gap: 10px; }
    .tl-row { display:grid; grid-template-columns: 10px 1fr auto; gap: 12px; align-items:center; padding: 8px 10px; border: 1px solid var(--border); border-radius: 12px; background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)); }
    .tl-marker { width: 10px; height: 10px; border-radius: 50%; }
    .tl-title { font-weight:600; }
    .tl-sub { color: var(--muted); font-size: 12px; }
    .tl-amt { font-weight:700; }
  `;
  container.appendChild(style);
}


