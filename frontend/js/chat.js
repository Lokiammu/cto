// Chat Module - Handles chat functionality and messaging

const CHAT = {
  messagesContainer: null,
  chatInput: null,
  sendBtn: null,
  sessionId: null,
  isWaitingForResponse: false,

  init() {
    this.messagesContainer = document.getElementById('messages-container');
    this.chatInput = document.getElementById('chatInput');
    this.sendBtn = document.getElementById('sendBtn');
    this.sessionId = 'session_' + Math.random().toString(36).substr(2, 9);

    this.setupEventListeners();
    this.loadChatHistory();
  },

  setupEventListeners() {
    if (this.sendBtn) {
      this.sendBtn.addEventListener('click', () => this.sendMessage());
    }

    if (this.chatInput) {
      this.chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });

      // Auto-grow textarea
      this.chatInput.addEventListener('input', (e) => {
        e.target.style.height = 'auto';
        e.target.style.height = Math.min(e.target.scrollHeight, 100) + 'px';
      });
    }
  },

  async sendMessage() {
    const content = this.chatInput.value.trim();

    if (!content) {
      return;
    }

    // Disable input while waiting
    this.isWaitingForResponse = true;
    this.sendBtn.disabled = true;
    this.chatInput.disabled = true;

    // Add user message
    this.addMessageToList('user', content, 'text');
    this.chatInput.value = '';
    this.chatInput.style.height = 'auto';

    // Save message to history
    const chatHistory = JSON.parse(localStorage.getItem('chatHistory')) || [];
    chatHistory.push({
      id: chatHistory.length + 1,
      sender: 'user',
      content,
      timestamp: new Date(),
      type: 'text'
    });
    localStorage.setItem('chatHistory', JSON.stringify(chatHistory));

    // Show typing indicator
    this.showTypingIndicator();

    try {
      // Get agent response
      const response = await API.sendChatMessage(this.sessionId, content);

      // Hide typing indicator
      this.hideTypingIndicator();

      // Add agent message
      this.addMessageToList('agent', response.content, response.type);
    } catch (error) {
      this.hideTypingIndicator();
      APP.showNotification('Failed to send message', 'error');
    } finally {
      // Re-enable input
      this.isWaitingForResponse = false;
      this.sendBtn.disabled = false;
      this.chatInput.disabled = false;
      this.chatInput.focus();
    }
  },

  addMessageToList(sender, content, type = 'text') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    const timestamp = new Date().toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    });

    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';
    bubbleDiv.textContent = content;

    const timestampDiv = document.createElement('div');
    timestampDiv.className = 'message-timestamp';
    timestampDiv.textContent = timestamp;

    const wrapper = document.createElement('div');
    wrapper.style.display = 'flex';
    wrapper.style.flexDirection = 'column';
    wrapper.style.gap = '4px';

    wrapper.appendChild(bubbleDiv);
    wrapper.appendChild(timestampDiv);
    messageDiv.appendChild(wrapper);

    this.messagesContainer.appendChild(messageDiv);
    this.scrollToBottom();
  },

  scrollToBottom() {
    if (this.messagesContainer) {
      setTimeout(() => {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
      }, 0);
    }
  },

  showTypingIndicator() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message agent';
    messageDiv.id = 'typing-indicator';

    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';

    for (let i = 0; i < 3; i++) {
      const dot = document.createElement('div');
      dot.className = 'typing-dot';
      bubbleDiv.appendChild(dot);
    }

    messageDiv.appendChild(bubbleDiv);
    this.messagesContainer.appendChild(messageDiv);
    this.scrollToBottom();
  },

  hideTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
      typingIndicator.remove();
    }
  },

  async loadChatHistory() {
    try {
      const chatHistory = JSON.parse(localStorage.getItem('chatHistory')) || mockChatHistory;

      // Clear container
      this.messagesContainer.innerHTML = '';

      // Display each message
      chatHistory.forEach(message => {
        this.addMessageToList(message.sender, message.content, message.type);
      });
    } catch (error) {
      console.error('Failed to load chat history:', error);
    }
  },

  clearHistory() {
    if (confirm('Are you sure you want to clear the chat history?')) {
      localStorage.removeItem('chatHistory');
      this.messagesContainer.innerHTML = '';
      APP.showNotification('Chat history cleared', 'info');
    }
  }
};
