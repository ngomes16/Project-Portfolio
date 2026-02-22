/**
 * File: web/src/components/AIChat.js
 * Purpose: Lightweight, local-only chat UI that simulates an AI trip planner reply.
 * This does NOT call external services; it uses canned responses for demo.
 */
const SAMPLE_REPLIES = [
  "How about a morning at the Art Institute, lunch at Lou Malnati's, then a sunset stroll along the Riverwalk?",
  "Consider grouping food costs into a shared kitty: $35/day per person will cover casual meals.",
  "For day two, book the architecture boat tour ahead of time. The 1pm slot avoids the midday rush.",
  "You're 72% funded for lodging. A $50 contribution from each person would close the gap.",
];

function bubble(text, role = 'ai') {
  const el = document.createElement('div');
  el.className = `chat-bubble ${role}`;
  el.textContent = text;
  return el;
}

export function renderAIChat(container) {
  container.innerHTML = '';
  const wrap = document.createElement('div');
  wrap.className = 'chat-wrap';
  const feed = document.createElement('div');
  feed.className = 'chat-feed';
  const form = document.createElement('form');
  form.className = 'chat-form';
  form.innerHTML = `
    <input class="chat-input" placeholder="Ask Trippi AI about your itinerary..." />
    <button class="btn btn-primary" type="submit">Send</button>
  `;

  feed.appendChild(bubble("Hi! I'm Trippi AI. Ask me about plans, budget, or vibes.", 'ai'));
  wrap.appendChild(feed);
  wrap.appendChild(form);
  container.appendChild(wrap);

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const input = form.querySelector('.chat-input');
    const text = (input.value || '').trim();
    if (!text) return;
    feed.appendChild(bubble(text, 'me'));
    input.value = '';
    setTimeout(() => {
      const reply = SAMPLE_REPLIES[Math.floor(Math.random() * SAMPLE_REPLIES.length)];
      feed.appendChild(bubble(reply, 'ai'));
      feed.scrollTop = feed.scrollHeight;
    }, 400);
  });

  const style = document.createElement('style');
  style.textContent = `
    .chat-wrap { display:grid; grid-template-rows: 1fr auto; height: 320px; }
    .chat-feed { overflow-y: auto; display:grid; gap: 8px; padding: 8px; border: 1px solid var(--border); border-radius: 12px; background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); }
    .chat-form { margin-top: 10px; display:flex; gap: 8px; }
    .chat-input { flex: 1; border-radius: 999px; border: 1px solid var(--border); padding: 12px 14px; background: #0c1218; color: var(--text); }
    .chat-bubble { max-width: 80%; padding: 10px 12px; border-radius: 14px; }
    .chat-bubble.ai { background: rgba(124,92,255,0.15); border: 1px solid rgba(124,92,255,0.4); }
    .chat-bubble.me { background: rgba(18,185,129,0.15); border: 1px solid rgba(18,185,129,0.4); justify-self: end; }
  `;
  container.appendChild(style);
}


