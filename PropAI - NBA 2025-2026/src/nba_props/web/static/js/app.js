/**
 * NBA Props Predictor - Frontend JavaScript
 */

// ============================================
// API Helper
// ============================================

async function fetchAPI(url, options = {}) {
    const defaults = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    const config = { ...defaults, ...options };
    
    const response = await fetch(url, config);
    const data = await response.json();
    
    if (!response.ok) {
        throw new Error(data.error || `HTTP ${response.status}`);
    }
    
    return data;
}

// ============================================
// Toast Notifications
// ============================================

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span>
        <span class="toast-message">${message}</span>
    `;
    
    container.appendChild(toast);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ============================================
// Stats Update
// ============================================

async function updateStats() {
    try {
        const stats = await fetchAPI('/api/stats');
        
        // Update sidebar stats
        const gamesEl = document.getElementById('stat-games');
        const playersEl = document.getElementById('stat-players');
        
        if (gamesEl) gamesEl.textContent = stats.games;
        if (playersEl) playersEl.textContent = stats.players;
    } catch (e) {
        console.error('Failed to update stats:', e);
    }
}

// ============================================
// Initialize
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Update stats on page load
    updateStats();
    
    // Refresh stats every 30 seconds
    setInterval(updateStats, 30000);
});

// ============================================
// Utility Functions
// ============================================

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
}

function formatNumber(num, decimals = 1) {
    if (num === null || num === undefined) return '-';
    return Number(num).toFixed(decimals);
}

