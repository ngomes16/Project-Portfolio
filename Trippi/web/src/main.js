/**
 * File: web/src/main.js
 * Purpose: Entry point for the GitHub Pages site. Mounts interactive components
 * and wires sample data. Adds a lightweight portal: fake/demo auth by default with
 * optional Firebase web config if provided via global window.__TRIPPI_FIREBASE__.
 */
import { trips } from './data/sample.js';
import { renderTripCarousel } from './components/TripCarousel.js';
import { renderBudgetDonut } from './components/BudgetDonut.js';
import { renderItineraryTimeline } from './components/ItineraryTimeline.js';
import { renderAIChat } from './components/AIChat.js';

function byId(id) { return document.getElementById(id); }
function qs(sel, root = document) { return root.querySelector(sel); }

function mount() {
  let selectedTrip = trips[0];
  const carouselEl = byId('trip-carousel');
  const donutEl = byId('budget-donut');
  const timelineEl = byId('itinerary-timeline');
  const aiEl = byId('ai-chat');
  const selectEl = byId('trip-select');

  if (carouselEl) renderTripCarousel(carouselEl, trips);
  if (selectEl) {
    selectEl.innerHTML = trips.map((t, i) => `<option value="${i}">${t.name} — ${t.destination}</option>`).join('');
    selectEl.addEventListener('change', () => {
      const idx = Number(selectEl.value);
      selectedTrip = trips[idx];
      if (donutEl) renderBudgetDonut(donutEl, selectedTrip.itinerary);
      if (timelineEl) renderItineraryTimeline(timelineEl, selectedTrip.itinerary);
    });
  }
  if (donutEl) renderBudgetDonut(donutEl, selectedTrip.itinerary);
  if (timelineEl) renderItineraryTimeline(timelineEl, selectedTrip.itinerary);
  if (aiEl) renderAIChat(aiEl);

  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();

  // copy run command
  const copyBtn = byId('copy-code');
  if (copyBtn) {
    copyBtn.addEventListener('click', async () => {
      const text = 'cd mobile\nnpm install\nnpm start';
      try { await navigator.clipboard.writeText(text); copyBtn.textContent = 'Copied!'; setTimeout(() => copyBtn.textContent = 'Copy', 1200); } catch {}
    });
  }

  const copyRun = byId('copy-run');
  if (copyRun) copyRun.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText('cd mobile && npm install && npm start'); copyRun.textContent = 'Copied!'; setTimeout(() => copyRun.textContent = 'Copy run command', 1200); } catch {}
  });

  // reveal on scroll
  const observer = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) e.target.classList.add('is-visible');
  }, { threshold: 0.12 });
  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

  // theme toggle
  const themeToggle = byId('theme-toggle');
  const body = document.body;
  const saved = localStorage.getItem('trippi-theme');
  if (saved === 'dark') body.classList.add('theme-dark');
  if (themeToggle) themeToggle.addEventListener('click', () => {
    body.classList.toggle('theme-dark');
    localStorage.setItem('trippi-theme', body.classList.contains('theme-dark') ? 'dark' : 'light');
    themeToggle.textContent = body.classList.contains('theme-dark') ? '🌙' : '☀️';
  });

  // back to top smooth scroll
  const backToTop = byId('back-to-top');
  if (backToTop) backToTop.addEventListener('click', (e) => { e.preventDefault(); window.scrollTo({ top: 0, behavior: 'smooth' }); });

  // Portal: auth (demo or firebase) + dashboard
  const authError = byId('auth-error');
  const loginForm = byId('login-form');
  const signupBtn = byId('signup-btn');
  const demoBtn = byId('demo-btn');
  const authed = byId('authed');
  const whoami = byId('whoami');
  const signoutBtn = byId('signout-btn');
  const dashTrips = byId('dash-trips');
  const dashDonut = byId('dash-donut');
  const dashTimeline = byId('dash-timeline');

  let currentUser = null;

  function setUser(u) {
    currentUser = u;
    if (whoami) whoami.textContent = u ? (u.email || 'demo@user') : '';
    if (authed) authed.style.display = u ? 'block' : 'none';
    if (loginForm) loginForm.style.display = u ? 'none' : 'grid';
    renderDashboard();
  }

  async function initFirebaseIfAvailable() {
    const cfg = window.__TRIPPI_FIREBASE__;
    if (!cfg) return null;
    try {
      const { initializeApp } = await import('https://www.gstatic.com/firebasejs/10.13.1/firebase-app.js');
      const { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword, onAuthStateChanged, signOut } = await import('https://www.gstatic.com/firebasejs/10.13.1/firebase-auth.js');
      const app = initializeApp(cfg);
      const auth = getAuth(app);
      onAuthStateChanged(auth, (u) => setUser(u));
      return { auth, signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut };
    } catch (e) {
      return null;
    }
  }

  let fb = null;
  initFirebaseIfAvailable().then((sdk) => { fb = sdk; });

  function renderDashboard() {
    // Use selectedTrip for charts; use all trips for cards
    if (dashTrips) {
      dashTrips.innerHTML = trips.slice(0, 4).map(t => `
        <div class="card">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
              <div style="font-weight:700;">${t.name}</div>
              <div style="color:var(--muted);">${t.destination}</div>
            </div>
            <div style="color:var(--muted);">${t.dateRange}</div>
          </div>
        </div>
      `).join('');
    }
    if (dashDonut) renderBudgetDonut(dashDonut, selectedTrip.itinerary);
    if (dashTimeline) renderItineraryTimeline(dashTimeline, selectedTrip.itinerary);
  }

  if (demoBtn) demoBtn.addEventListener('click', () => setUser({ email: 'demo@trippi.app' }));
  if (signoutBtn) signoutBtn.addEventListener('click', async () => {
    if (fb) { try { await fb.signOut(fb.auth); } catch {} }
    setUser(null);
  });
  if (loginForm) loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = byId('login-email').value;
    const password = byId('login-password').value;
    authError.textContent = '';
    if (fb) {
      try { await fb.signInWithEmailAndPassword(fb.auth, email, password); } catch (err) { authError.textContent = err.message || 'Login failed'; }
    } else {
      // demo mode
      setUser({ email });
    }
  });
  if (signupBtn) signupBtn.addEventListener('click', async () => {
    const email = byId('login-email').value;
    const password = byId('login-password').value;
    authError.textContent = '';
    if (fb) {
      try { await fb.createUserWithEmailAndPassword(fb.auth, email, password); } catch (err) { authError.textContent = err.message || 'Signup failed'; }
    } else {
      setUser({ email });
    }
  });
}

window.addEventListener('DOMContentLoaded', mount);


