const fileInput = document.getElementById('fileInput');
const dropZone = document.getElementById('dropZone');
const fileList = document.getElementById('fileList');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const chatMessages = document.getElementById('chatMessages');
const statusText = document.getElementById('status');

// Helper: Add message to chat
function addMessage(text, isUser = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${isUser ? 'user' : 'bot'}`;
    msgDiv.textContent = text;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// File Upload Logic
dropZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    statusText.textContent = 'Processing File...';
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        
        if (response.ok) {
            addFileToList(file.name, result.chunks);
            statusText.textContent = 'File Ready';
        } else {
            statusText.textContent = 'Error: ' + result.detail;
        }
    } catch (err) {
        statusText.textContent = 'Upload Failed';
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

// Query Logic
async function handleSend() {
    const query = userInput.value.trim();
    if (!query) return;

    addMessage(query, true);
    userInput.value = '';
    statusText.textContent = 'Thinking...';

    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const result = await response.json();
        
        if (response.ok) {
            addMessage(result.response);
            statusText.textContent = 'System Ready';
        } else {
            addMessage("Error: " + result.detail);
        }
    } catch (err) {
        addMessage("Sorry, something went wrong.");
        statusText.textContent = 'Error';
    }
}

sendBtn.addEventListener('click', handleSend);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSend();
});
