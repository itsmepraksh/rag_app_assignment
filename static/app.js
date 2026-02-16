const fileInput = document.getElementById('fileInput');
const dropZone = document.getElementById('dropZone');
const fileList = document.getElementById('fileList');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const chatMessages = document.getElementById('chatMessages');
const statusText = document.getElementById('status');
const debugToggle = document.getElementById('debugToggle');
const debugPanel = document.getElementById('debugPanel');
const debugOutput = document.getElementById('debugOutput');
const sessionIdText = document.getElementById('sessionIdText');
const newSessionBtn = document.getElementById('newSessionBtn');
const resetSessionBtn = document.getElementById('resetSessionBtn');

const SESSION_KEY = 'documind_session_id';
let currentSessionId = loadOrCreateSessionId();

function loadOrCreateSessionId() {
    const saved = localStorage.getItem(SESSION_KEY);
    if (saved && saved.trim()) return saved.trim();
    const sid = crypto.randomUUID();
    localStorage.setItem(SESSION_KEY, sid);
    return sid;
}

function setSessionId(newId) {
    currentSessionId = newId;
    localStorage.setItem(SESSION_KEY, currentSessionId);
    sessionIdText.textContent = currentSessionId.slice(0, 8);
}

function setStatus(text, type = 'ready') {
    statusText.textContent = text;
    statusText.className = `status-pill ${type}`;
}

function escapeHtml(text) {
    return String(text)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function addMessage(text, isUser = false, meta = {}) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${isUser ? 'user' : 'bot'}`;
    if (isUser) {
        msgDiv.textContent = text;
    } else {
        const safeText = escapeHtml(text || '');
        msgDiv.innerHTML = `<div>${safeText}</div>`;

        if (Array.isArray(meta.citations) && meta.citations.length > 0) {
            const cites = document.createElement('div');
            cites.className = 'citations';
            cites.innerHTML = `<strong>Citations:</strong> ${meta.citations.map(c => `<span class="citation-chip">${escapeHtml(c)}</span>`).join('')}`;
            msgDiv.appendChild(cites);
        }

        if (meta.latencyMs != null || meta.traceId) {
            const metaDiv = document.createElement('div');
            metaDiv.className = 'message-meta';
            const parts = [];
            if (meta.latencyMs != null) parts.push(`Latency: ${meta.latencyMs} ms`);
            if (meta.traceId) parts.push(`Trace: ${meta.traceId}`);
            metaDiv.textContent = parts.join(' | ');
            msgDiv.appendChild(metaDiv);
        }
    }
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Scroll to bottom on load
window.addEventListener('load', () => {
    setSessionId(currentSessionId);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    setStatus('System Ready', 'ready');
});

// File Upload Logic
dropZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setStatus('Processing file...', 'processing');
    const formData = new FormData();
    formData.append('file', file);
    setTimeout(() => setStatus('Running OCR pipeline (if needed)...', 'ocr'), 300);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        if (response.ok) {
            addFileToList(file.name, result.chunks);
            setStatus('File indexed and ready', 'ready');
        } else {
            setStatus('Upload error: ' + (result.detail || 'Unknown error'), 'error');
        }
    } catch (err) {
        setStatus('Upload failed', 'error');
    } finally {
        fileInput.value = '';
    }
});

function addFileToList(name, chunks) {
    const item = document.createElement('div');
    item.className = 'file-item';
    item.innerHTML = `
        <span>${name}</span>
        <span style="color: var(--text-muted); font-size: 0.75rem;">${chunks} chunks</span>
    `;
    fileList.appendChild(item);
}

// Helper: Show thinking indicator
function showThinking() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot thinking';
    msgDiv.id = 'thinking-msg';
    msgDiv.innerHTML = '<span class="dot">.</span><span class="dot">.</span><span class="dot">.</span>';
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Helper: Remove thinking indicator
function removeThinking() {
    const el = document.getElementById('thinking-msg');
    if (el) el.remove();
}

// Query Logic
async function handleSend() {
    const query = userInput.value.trim();
    if (!query) return;

    addMessage(query, true);
    userInput.value = '';

    // Show thinking indicator in chat
    showThinking();
    setStatus('Retrieving and reranking context...', 'processing');

    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query,
                session_id: currentSessionId,
                debug: !!debugToggle.checked
            })
        });
        const result = await response.json();

        removeThinking();

        if (response.ok) {
            const answer = result.answer || result.response || '';
            addMessage(answer, false, {
                citations: result.citations || [],
                latencyMs: result.latency_ms ?? null,
                traceId: result.agent_trace_id || ''
            });
            renderDebug(result);
            const lower = answer.toLowerCase();
            if (lower.includes('web fallback') || lower.includes('not configured')) {
                setStatus('Web fallback unavailable; local docs only', 'web');
            } else if (lower.includes('source: http')) {
                setStatus('Web-search fallback used', 'web');
            } else {
                setStatus('System Ready', 'ready');
            }
        } else {
            addMessage('Error: ' + (result.detail || 'Request failed'));
            setStatus('Query failed', 'error');
        }
    } catch (err) {
        removeThinking();
        addMessage('Sorry, something went wrong.');
        setStatus('Network or server error', 'error');
    }
}

function renderDebug(result) {
    const data = {
        agent_trace_id: result.agent_trace_id,
        latency_ms: result.latency_ms,
        citations: result.citations || [],
        supporting_chunks: result.supporting_chunks || [],
        sources: result.sources || []
    };
    debugOutput.textContent = JSON.stringify(data, null, 2);
    if (debugToggle.checked) debugPanel.open = true;
}

newSessionBtn.addEventListener('click', () => {
    setSessionId(crypto.randomUUID());
    addMessage(`Started new session: ${currentSessionId.slice(0, 8)}`, false);
    setStatus('New session started', 'ready');
});

resetSessionBtn.addEventListener('click', async () => {
    try {
        const res = await fetch(`/api/conversations/${encodeURIComponent(currentSessionId)}/reset`, { method: 'POST' });
        if (!res.ok) throw new Error('reset failed');
        addMessage('Conversation memory reset for current session.', false);
        setStatus('Session memory reset', 'ready');
    } catch (_err) {
        setStatus('Failed to reset session memory', 'error');
    }
});

sendBtn.addEventListener('click', handleSend);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSend();
});
