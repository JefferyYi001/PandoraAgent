/**
 * Templates page - CRUD for reply templates
 */

document.addEventListener('DOMContentLoaded', loadTemplates);

async function loadTemplates() {
    const list = document.getElementById('templateList');
    list.innerHTML = '<p>模板管理功能待完善 - 当前版本使用 defaults.yaml 中的默认话术</p>';
}

async function addTemplate() {
    const name = document.getElementById('templateName').value;
    const category = document.getElementById('templateCategory').value;
    const content = document.getElementById('templateContent').value;
    const variablesRaw = document.getElementById('templateVariables').value;

    if (!name || !content) {
        alert('请填写模板名称和内容');
        return;
    }

    let variables = [];
    if (variablesRaw) {
        try {
            variables = JSON.parse(variablesRaw);
        } catch {
            alert('变量格式错误，请使用 JSON 数组格式');
            return;
        }
    }

    alert('模板已提交 (功能待完善)');
}
