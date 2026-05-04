/**
 * WeChat config page - region coordinates and polling settings
 */

document.addEventListener('DOMContentLoaded', async () => {
    const config = await apiGet('/config');
    const defaults = config.defaults || {};
    const wechat = defaults.wechat || {};

    if (wechat.taskbar_region) {
        document.getElementById('taskbarRegion').value = wechat.taskbar_region.join(',');
    }
    if (wechat.chat_list_region) {
        document.getElementById('chatListRegion').value = wechat.chat_list_region.join(',');
    }
    if (wechat.chat_content_region) {
        document.getElementById('chatContentRegion').value = wechat.chat_content_region.join(',');
    }
    if (wechat.input_box_region) {
        document.getElementById('inputBoxRegion').value = wechat.input_box_region.join(',');
    }

    const polling = defaults.vision?.polling || {};
    document.getElementById('pollIntervalMin').value = polling.interval || 3;
    document.getElementById('pollIntervalMax').value = polling.max_interval || 8;
    document.getElementById('maxScroll').value = polling.max_scroll || 20;

    const agent = defaults.agent || {};
    document.getElementById('monitorTimeout').value = agent.monitor_timeout || 300;
});

async function saveWechatConfig() {
    const parseRegion = (id) => {
        const val = document.getElementById(id).value;
        return val.split(',').map(s => parseInt(s.trim()));
    };

    const wechat = {
        wechat: {
            taskbar_region: parseRegion('taskbarRegion'),
            chat_list_region: parseRegion('chatListRegion'),
            chat_content_region: parseRegion('chatContentRegion'),
            input_box_region: parseRegion('inputBoxRegion'),
        },
    };

    const result = await apiPost('/config/update', { key: 'wechat', value: wechat });
    alert(result.status === 'updated' ? '微信参数已保存' : '保存失败');
}

async function savePollingConfig() {
    const polling = {
        vision: {
            polling: {
                interval: parseInt(document.getElementById('pollIntervalMin').value),
                max_interval: parseInt(document.getElementById('pollIntervalMax').value),
                max_scroll: parseInt(document.getElementById('maxScroll').value),
            },
        },
        agent: {
            monitor_timeout: parseInt(document.getElementById('monitorTimeout').value),
        },
    };

    const result = await apiPost('/config/update', { key: 'polling', value: polling });
    alert(result.status === 'updated' ? '轮询设置已保存' : '保存失败');
}
