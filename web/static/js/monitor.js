/**
 * Monitor page - real-time status via SSE + periodic polling
 */

document.addEventListener('DOMContentLoaded', () => {
    refreshStatus();
    connectSSE();
});

function connectSSE() {
    const eventSource = new EventSource('/api/sse/events');
    const logDiv = document.getElementById('liveLog');

    eventSource.onmessage = (event) => {
        try {
            const status = JSON.parse(event.data);
            updateStatusUI(status);
            appendLog(logDiv, status);

            const totalMsg = document.getElementById('totalMessages');
            if (totalMsg) totalMsg.textContent = status.total_messages || 0;

            const tools = document.getElementById('toolsLoaded');
            if (tools) tools.textContent = status.tools_loaded || 0;

            const skills = document.getElementById('skillsLoaded');
            if (skills) skills.textContent = status.skills_loaded || 0;
        } catch (e) {
            console.error('SSE parse error:', e);
        }
    };

    eventSource.onerror = () => {
        if (logDiv) logDiv.textContent = 'SSE 连接中断，尝试重连...';
        eventSource.close();
        setTimeout(() => connectSSE(), 5000);
    };
}

function appendLog(logDiv, status) {
    if (!logDiv) return;

    const timestamp = new Date().toLocaleTimeString();
    const line = `[${timestamp}] 状态: ${status.state} | 失败: ${status.consecutive_failures || 0}`;

    logDiv.textContent += line + '\n';

    // Keep last 100 lines
    const lines = logDiv.textContent.split('\n');
    if (lines.length > 100) {
        logDiv.textContent = lines.slice(-100).join('\n');
    }

    // Auto scroll to bottom
    logDiv.scrollTop = logDiv.scrollHeight;
}
