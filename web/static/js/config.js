/**
 * Config page - LLM API configuration and testing
 */

document.addEventListener('DOMContentLoaded', async () => {
    const config = await apiGet('/config');
    document.getElementById('apiUrl').value = config.llm?.api_url || '';
    document.getElementById('modelName').value = config.llm?.model || '';
    document.getElementById('maxTokens').value = config.llm?.max_tokens || 2000;
    document.getElementById('temperature').value = config.llm?.temperature || 0.7;
});

async function saveConfig() {
    const update = {
        llm: {
            api_url: document.getElementById('apiUrl').value,
            model: document.getElementById('modelName').value,
            max_tokens: parseInt(document.getElementById('maxTokens').value),
            temperature: parseFloat(document.getElementById('temperature').value),
        },
    };
    const result = await apiPost('/config/update', { key: 'llm', value: update });
    alert(result.status === 'updated' ? '配置已保存' : '保存失败');
}

async function testConnection() {
    const result = document.getElementById('testResult');
    result.textContent = '正在测试连接...';
    try {
        const resp = await fetch(document.getElementById('apiUrl').value + '/models', {
            headers: { 'Authorization': `Bearer ${document.getElementById('apiKey').value}` },
        });
        result.textContent = resp.ok ? '连接成功!' : `连接失败: ${resp.status}`;
    } catch (e) {
        result.textContent = `连接失败: ${e.message}`;
    }
}

async function testReply() {
    const result = document.getElementById('testResult');
    result.textContent = '正在生成回复...';

    const apiUrl = document.getElementById('apiUrl').value;
    const apiKey = document.getElementById('apiKey').value;
    const model = document.getElementById('modelName').value;
    const message = document.getElementById('testMessage').value;

    if (!message) {
        result.textContent = '请输入测试消息';
        return;
    }

    try {
        const resp = await fetch(apiUrl + '/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`,
            },
            body: JSON.stringify({
                model: model,
                messages: [{ role: 'user', content: message }],
                max_tokens: parseInt(document.getElementById('maxTokens').value),
                temperature: parseFloat(document.getElementById('temperature').value),
            }),
        });
        const data = await resp.json();
        const reply = data.choices?.[0]?.message?.content || 'No reply generated';
        result.textContent = reply;
    } catch (e) {
        result.textContent = `Error: ${e.message}`;
    }
}
