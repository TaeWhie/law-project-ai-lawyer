// Persistent Client ID for this browser
if (!localStorage.getItem('legalClientId')) {
    localStorage.setItem('legalClientId', 'client_' + Math.random().toString(36).substr(2, 9));
}
const clientId = localStorage.getItem('legalClientId');
let sessionId = null;

const chatWindow = document.getElementById('chat-window');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const issueContainer = document.getElementById('issue-container');
const historyContainer = document.getElementById('history-container');
const progressContainer = document.getElementById('progress-container');

async function loadHistory() {
    try {
        const baseUrl = window.location.protocol === 'file:' ? 'http://localhost:8000' : '';
        const response = await fetch(`${baseUrl}/api/history/${clientId}`);
        const history = await response.json();
        renderHistorySidebar(history);
    } catch (e) { console.error('History load failed', e); }
}

function renderHistorySidebar(history) {
    historyContainer.innerHTML = '';
    history.forEach(item => {
        const div = document.createElement('div');
        div.className = `history-item ${item.session_id === sessionId ? 'active' : ''}`;
        div.innerText = item.title || '새 상담';
        div.onclick = () => switchSession(item.session_id);
        historyContainer.appendChild(div);
    });
}

async function switchSession(sid) {
    sessionId = sid;
    chatWindow.innerHTML = '';
    issueContainer.innerHTML = '';

    // UI Loading state
    appendMessage('기록을 불러오는 중...', 'ai loading');

    try {
        const baseUrl = window.location.protocol === 'file:' ? 'http://localhost:8000' : '';
        const response = await fetch(`${baseUrl}/api/chat-history/${clientId}/${sid}`);
        const data = await response.json();

        chatWindow.innerHTML = ''; // Clear loading
        data.messages.forEach(msg => {
            appendMessage(msg.content, msg.role);
        });
        updateBadges(data.detected_issues);
        updateProgress(data.detected_issues, data.issue_progress || {}, data.issue_checklist || {});
        loadHistory(); // Refresh sidebar active state
    } catch (e) {
        console.error('Switch failed', e);
        appendMessage('기록을 불러오지 못했습니다.', 'ai');
    }
}

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    appendMessage(text, 'user');
    userInput.value = '';
    const loadingMessage = appendMessage('분석 중...', 'ai loading');

    try {
        const baseUrl = window.location.protocol === 'file:' ? 'http://localhost:8000' : '';

        // Use fetch with manual SSE parsing (EventSource doesn't support POST)
        const response = await fetch(`${baseUrl}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            },
            body: JSON.stringify({ message: text, client_id: clientId, session_id: sessionId })
        });

        if (response.status === 403) {
            loadingMessage.innerText = '상담은 최대 3개까지만 가능합니다. 기존 상담을 완료하거나 삭제해 주세요.';
            return;
        }

        // Parse SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let checklistUpdated = false;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep incomplete line in buffer

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const eventData = JSON.parse(line.substring(6));

                    switch (eventData.type) {
                        case 'checklist_update':
                            // Update checklist FIRST
                            updateBadges(eventData.payload.detected_issues);
                            updateProgress(
                                eventData.payload.detected_issues,
                                eventData.payload.issue_progress,
                                eventData.payload.issue_checklist
                            );
                            checklistUpdated = true;
                            break;

                        case 'message':
                            // Remove loading, show AI message
                            if (!sessionId) {
                                sessionId = eventData.payload.session_id;
                                loadHistory(); // Refresh sidebar
                            }
                            loadingMessage.remove();
                            appendMessage(eventData.payload.text, 'ai');
                            break;

                        case 'done':
                            // Mark as conclusion if terminal
                            if (eventData.payload.is_terminal) {
                                const lastMsg = chatWindow.lastElementChild;
                                if (lastMsg && lastMsg.classList.contains('ai')) {
                                    lastMsg.classList.add('ai-conclusion');
                                }
                            }
                            loadHistory(); // Update title in sidebar
                            break;

                        case 'error':
                            loadingMessage.innerText = `오류: ${eventData.payload.message}`;
                            break;
                    }
                }
            }
        }

    } catch (error) {
        loadingMessage.innerText = '오류가 발생했습니다. 다시 시도해 주세요.';
        console.error(error);
    }
}

function appendMessage(text, type) {
    const div = document.createElement('div');
    div.className = `message ${type}`;

    let formattedText = marked.parse(text);

    div.innerHTML = formattedText;
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return div;
}

// Dynamic fallback: convert snake_case key to display name (e.g. "wage_arrears" -> "Wage Arrears")
function formatIssueKey(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function updateBadges(issues) {
    issueContainer.innerHTML = '';
    if (!issues) return;

    issues.forEach(issue => {
        const span = document.createElement('span');
        span.className = 'badge';

        if (typeof issue === 'object' && issue.korean) {
            span.innerText = issue.korean;
        } else {
            span.innerText = formatIssueKey(issue);
        }

        issueContainer.appendChild(span);
    });
}

function startNewChat() {
    sessionId = null;
    chatWindow.innerHTML = '';
    issueContainer.innerHTML = '';
    progressContainer.innerHTML = '<div class="no-data-msg">이슈 감지 중...</div>';
    appendMessage('새로운 법률 상담을 시작합니다. 어떤 고민이 있으신가요?', 'ai');
    loadHistory(); // Check limits
}

function updateProgress(issues, progressMap, checklistMap = {}) {
    progressContainer.innerHTML = '';
    if (!issues || issues.length === 0) {
        progressContainer.innerHTML = '<div class="no-data-msg">이슈 감지 중...</div>';
        return;
    }

    issues.forEach(issue => {
        const issueKey = typeof issue === 'object' ? issue.key : issue;
        const issueName = typeof issue === 'object' ? issue.korean : formatIssueKey(issue);
        const percent = progressMap[issueKey] || 0;
        const checklist = checklistMap[issueKey] || [];

        const div = document.createElement('div');
        div.className = 'progress-item';

        let checklistHtml = '';
        if (checklist.length > 0) {
            checklistHtml = `
                <ul class="checklist">
                    ${checklist.map(item => {
                let statusClass = 'pending';
                let icon = '○';
                if (item.status === 'YES') {
                    statusClass = 'completed';
                    icon = '✓';
                } else if (item.status === 'NO') {
                    statusClass = 'failed';
                    icon = '✕';
                }
                return `
                            <li class="${statusClass}">
                                <span class="icon">${icon}</span>
                                <span class="req-text">${item.requirement}</span>
                            </li>
                        `;
            }).join('')}
                </ul>
            `;
        }

        div.innerHTML = `
            <div class="progress-label">
                <span>${issueName}</span>
                <span class="progress-percent">${percent}%</span>
            </div>
            <div class="progress-bar-bg">
                <div class="progress-fill" style="width: ${percent}%"></div>
            </div>
            ${checklistHtml}
        `;
        progressContainer.appendChild(div);
    });
}

// Event Listeners
sendBtn.addEventListener('click', sendMessage);
document.getElementById('reset-btn').addEventListener('click', startNewChat);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// Initial Load
loadHistory();
