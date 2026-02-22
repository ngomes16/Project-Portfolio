/**
 * File: web/src/components/TripCarousel.js
 * Purpose: Render a horizontally scrollable carousel of trips with a parallax
 * gradient background and small interactions. Pure DOM/ESM, no framework.
 */
import { formatCurrency } from '../utils/format.js';

export function renderTripCarousel(container, trips) {
  container.innerHTML = '';

  const wrapper = document.createElement('div');
  wrapper.className = 'trip-carousel';

  for (const trip of trips) {
    const card = document.createElement('article');
    card.className = 'trip-card';
    card.innerHTML = `
      <div class="tc-bg"></div>
      <div class="tc-content">
        <div class="tc-top">
          <span class="tc-dates">${trip.dateRange}</span>
          <span class="tc-budget">Goal · ${formatCurrency(trip.goalBudget)}</span>
        </div>
        <h4 class="tc-name">${trip.name}</h4>
        <p class="tc-dest">${trip.destination}</p>
        <div class="tc-avatars">${trip.members
          .slice(0, 4)
          .map((m, i) => `<span class="tc-avatar" style="z-index:${10 - i}; background:${m.avatarColor}">${m.name[0]}</span>`) 
          .join('')}</div>
      </div>
    `;
    wrapper.appendChild(card);
  }

  container.appendChild(wrapper);

  // styles added here to keep component isolated
  const style = document.createElement('style');
  style.textContent = `
    .trip-carousel { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(260px, 1fr); gap: 14px; overflow-x: auto; padding-bottom: 6px; }
    .trip-card { position: relative; height: 180px; border-radius: 16px; overflow: hidden; border: 1px solid var(--border); background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01)); box-shadow: var(--shadow); }
    .tc-bg { position: absolute; inset: 0; background: radial-gradient(400px 200px at 20% 10%, rgba(124,92,255,0.2), transparent), radial-gradient(400px 200px at 80% 90%, rgba(18,185,129,0.2), transparent); filter: blur(12px); }
    .tc-content { position: relative; height: 100%; padding: 14px; display: flex; flex-direction: column; justify-content: space-between; }
    .tc-top { display:flex; justify-content: space-between; color: var(--muted); font-size: 12px; }
    .tc-name { margin: 6px 0 0; font-size: 18px; }
    .tc-dest { color: var(--muted); margin: 2px 0 0; }
    .tc-avatars { display:flex; align-items:center; gap: 0; }
    .tc-avatar { display:inline-flex; align-items:center; justify-content:center; width:28px; height:28px; border-radius:50%; color:#00120d; font-weight:700; border: 2px solid var(--card); margin-left: -8px; }
  `;
  container.appendChild(style);
}


