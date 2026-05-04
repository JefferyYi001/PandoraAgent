/**
 * App - Shared utility functions for the SPA
 */

const API_BASE = '/api';

async function apiGet(path) {
    const resp = await fetch(`${API_BASE}${path}`);
    return resp.json();
}

async function apiPost(path, data) {
    const resp = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`HTTP ${resp.status}: ${text}`);
    }
    return resp.json();
}

async function startAgent() {
    const result = await apiPost('/agent/start');
    alert(result.status === 'started' ? 'Agent 已启动' : 'Agent 已在运行');
    refreshStatus();
}

async function stopAgent() {
    await apiPost('/agent/stop');
    refreshStatus();
}

async function refreshStatus() {
    const status = await apiGet('/agent/status');
    updateStatusUI(status);
}

function updateStatusUI(status) {
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    if (dot && text) {
        if (status.running) {
            dot.className = 'status-dot running';
            text.textContent = '运行中';
        } else {
            dot.className = 'status-dot stopped';
            text.textContent = '已停止';
        }
    }

    const badge = document.getElementById('stateBadge');
    if (badge) badge.textContent = status.state?.toUpperCase() || 'IDLE';

    const contact = document.getElementById('activeContact');
    if (contact) contact.textContent = status.active_contact || '--';

    const msg = document.getElementById('lastMessage');
    if (msg) msg.textContent = status.last_message?.substring(0, 50) || '--';

    const failures = document.getElementById('consecutiveFailures');
    if (failures) failures.textContent = status.consecutive_failures || 0;

    const tools = document.getElementById('toolsLoaded');
    if (tools) tools.textContent = status.tools_loaded || 0;

    const skills = document.getElementById('skillsLoaded');
    if (skills) skills.textContent = status.skills_loaded || 0;

    const recent = document.getElementById('recentActions');
    if (recent && status.recent_actions?.length) {
        recent.textContent = status.recent_actions
            .map(a => `[${a.action}] ${a.result}`)
            .join('\n');
    }
}
