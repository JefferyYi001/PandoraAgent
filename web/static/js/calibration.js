/**
 * Calibration page - mouse position capture for region coordinates
 * Flow: select target region -> click Start -> move mouse -> press Enter to record corners
 */

let isCapturing = false;
let captureStep = 0; // 0 = idle, 1 = wait for corner1, 2 = wait for corner2
let corner1 = null, corner2 = null;

const regionKeys = ['taskbarRegion', 'chatListRegion', 'chatContentRegion', 'inputBoxRegion'];

document.addEventListener('DOMContentLoaded', () => {
    const slider = document.getElementById('matchThreshold');
    const display = document.getElementById('thresholdValue');
    if (slider) {
        slider.addEventListener('input', () => {
            display.textContent = slider.value;
        });
    }

    for (const key of regionKeys) {
        const saved = localStorage.getItem(key);
        if (saved) {
            document.getElementById(key).value = saved;
        }
    }

    // Listen for Enter key during capture
    document.addEventListener('keydown', onKeyDown);
});

function onKeyDown(e) {
    if (!isCapturing || e.key !== 'Enter') return;
    e.preventDefault();

    if (captureStep === 1) {
        fetch('/api/calibration/mouse_position')
            .then(r => r.json())
            .then(data => {
                corner1 = { x: data.x, y: data.y };
                captureStep = 2;
                document.getElementById('captureStatus').textContent = `角1: (${data.x}, ${data.y}) — 移动鼠标到右下角，按 Enter`;
            });
    } else if (captureStep === 2) {
        fetch('/api/calibration/mouse_position')
            .then(r => r.json())
            .then(data => {
                corner2 = { x: data.x, y: data.y };

                const left = Math.min(corner1.x, corner2.x);
                const top = Math.min(corner1.y, corner2.y);
                const width = Math.abs(corner2.x - corner1.x);
                const height = Math.abs(corner2.y - corner1.y);

                const target = document.querySelector('input[name="targetRegion"]:checked');
                if (target) {
                    fillTargetRegion(target.value, left, top, width, height);
                }

                document.getElementById('selectionCoords').textContent = `${left}, ${top}, ${width}, ${height}`;
                document.getElementById('selectionInfo').style.display = 'inline-block';

                // Reset
                isCapturing = false;
                captureStep = 0;
                corner1 = null;
                corner2 = null;
                document.getElementById('captureBtn').textContent = '开始捕获';
                document.getElementById('captureStatus').textContent = '完成';
            });
    }
}

function toggleCapture() {
    const target = document.querySelector('input[name="targetRegion"]:checked');
    if (!target) {
        alert('请先选择目标区域');
        return;
    }

    if (isCapturing) {
        // Cancel capture
        isCapturing = false;
        captureStep = 0;
        corner1 = null;
        corner2 = null;
        document.getElementById('captureBtn').textContent = '开始捕获';
        document.getElementById('captureStatus').textContent = '已取消';
        return;
    }

    isCapturing = true;
    captureStep = 1;
    document.getElementById('captureBtn').textContent = '取消捕获';
    document.getElementById('captureStatus').textContent = '移动鼠标到区域左上角，按 Enter';
}

function fillTargetRegion(targetId, left, top, width, height) {
    const input = document.getElementById(targetId);
    if (!input) return;
    const value = `${left}, ${top}, ${width}, ${height}`;
    input.value = value;
    localStorage.setItem(targetId, value);
}

async function saveRegions() {
    const regions = {};
    for (const key of regionKeys) {
        const val = document.getElementById(key).value;
        if (val) {
            regions[key] = val.split(',').map(s => parseInt(s.trim()));
        }
    }

    if (Object.keys(regions).length === 0) {
        alert('请先捕获至少一个区域');
        return;
    }

    const result = await apiPost('/config/wechat-regions', regions);
    const status = document.getElementById('saveStatus');
    if (result.success) {
        status.textContent = '已保存';
        setTimeout(() => { status.textContent = ''; }, 2000);
    } else {
        status.textContent = `保存失败: ${result.output || result.error}`;
        status.style.color = '#e74c3c';
    }
}

async function testMatch() {
    const regionRaw = document.getElementById('matchRegion').value;
    const templatePath = document.getElementById('templatePath').value;
    const threshold = parseFloat(document.getElementById('matchThreshold').value);

    if (!regionRaw || !templatePath) {
        alert('请填写测试区域和模板路径');
        return;
    }

    const result = await apiPost('/calibration/match_template', {
        region: regionRaw.split(',').map(s => parseInt(s.trim())),
        template_path: templatePath,
        threshold,
    });

    const display = document.getElementById('matchResult');
    display.textContent = result.success
        ? `匹配成功: ${result.output}\n位置: (${result.data?.position?.[0]}, ${result.data?.position?.[1]})`
        : `未匹配: ${result.data?.threshold || threshold}`;
}

async function analyzeRedDot() {
    const templatePath = document.getElementById('redDotTemplate').value;
    if (!templatePath) {
        alert('请填写红点模板路径');
        return;
    }

    const result = await apiPost('/calibration/analyze_red_dot', {
        template_path: templatePath,
    });

    const display = document.getElementById('redDotResult');
    display.textContent = result.success
        ? `${result.output}\n参数: ${JSON.stringify(result.data, null, 2)}`
        : `分析失败: ${result.output}`;
}
