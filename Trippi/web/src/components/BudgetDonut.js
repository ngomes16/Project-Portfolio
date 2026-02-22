/**
 * File: web/src/components/BudgetDonut.js
 * Purpose: Simple SVG donut chart showing totals by budget category.
 */
import { colorFor } from '../utils/colors.js';
import { formatCurrency } from '../utils/format.js';

export function renderBudgetDonut(container, items) {
  container.innerHTML = '';

  const totals = {};
  for (const it of items) totals[it.category] = (totals[it.category] || 0) + it.total;
  const entries = Object.entries(totals);
  const grand = entries.reduce((s, [, v]) => s + v, 0) || 1;

  const size = 180; const stroke = 18; const r = (size - stroke) / 2; const c = 2 * Math.PI * r;
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', `0 0 ${size} ${size}`);
  svg.setAttribute('width', size);
  svg.setAttribute('height', size);

  let offset = 0;
  for (const [cat, total] of entries) {
    const frac = total / grand;
    const len = frac * c;
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', size/2);
    circle.setAttribute('cy', size/2);
    circle.setAttribute('r', r);
    circle.setAttribute('fill', 'transparent');
    circle.setAttribute('stroke', colorFor(cat));
    circle.setAttribute('stroke-width', stroke);
    circle.setAttribute('stroke-dasharray', `${len} ${c - len}`);
    circle.setAttribute('stroke-dashoffset', String(-offset));
    circle.setAttribute('pathLength', String(c));
    circle.setAttribute('opacity', '0.95');
    svg.appendChild(circle);
    offset += len;
  }

  const wrapper = document.createElement('div');
  wrapper.className = 'donut-wrap';
  const legend = document.createElement('div');
  legend.className = 'donut-legend';
  for (const [cat, total] of entries) {
    const row = document.createElement('div');
    row.className = 'legend-row';
    row.innerHTML = `<span class="swatch" style="background:${colorFor(cat)}"></span>${cat}<span class="amt">${formatCurrency(total)}</span>`;
    legend.appendChild(row);
  }

  const center = document.createElement('div');
  center.className = 'donut-center';
  center.innerHTML = `<div class="grand">${formatCurrency(grand)}</div><div class="label">Total</div>`;

  const donut = document.createElement('div');
  donut.className = 'donut';
  donut.appendChild(svg);
  donut.appendChild(center);

  wrapper.appendChild(donut);
  wrapper.appendChild(legend);
  container.appendChild(wrapper);

  const style = document.createElement('style');
  style.textContent = `
    .donut-wrap { display:grid; grid-template-columns: 200px 1fr; gap: 16px; align-items:center; }
    @media (max-width: 520px) { .donut-wrap { grid-template-columns: 1fr; justify-items:center; } }
    .donut { position:relative; width:${size}px; height:${size}px; display:grid; place-items:center; }
    .donut-center { position:absolute; width: 100%; height: 100%; display:grid; place-items:center; text-align:center; }
    .grand { font-weight:800; letter-spacing:-0.02em; }
    .label { color: var(--muted); font-size: 12px; margin-top: -6px; }
    .donut-legend { display:grid; gap: 10px; }
    .legend-row { display:grid; grid-template-columns: 16px 1fr auto; gap: 10px; align-items:center; color: var(--muted); }
    .legend-row .amt { color: var(--text); }
    .swatch { width: 12px; height: 12px; border-radius: 3px; }
  `;
  container.appendChild(style);
}


