/**
 * Crypto AI Chat Interface
 * Handles chat interactions, message display, and API communication
 */

class ChatInterface {
    constructor() {
        // DOM elements
        this.chatForm = document.getElementById('chat-form');
        this.questionInput = document.getElementById('question-input');
        this.sendButton = document.getElementById('send-button');
        this.clearButton = document.getElementById('clear-button');
        this.chatMessages = document.getElementById('chat-messages');
        this.typingIndicator = document.getElementById('typing-indicator');
        this.alertContainer = document.getElementById('alert-container');
        this.charCount = document.getElementById('char-count');
        this.statusIndicator = document.getElementById('status-indicator');
        
        // Session management
        this.sessionId = this.getOrCreateSessionId();
        
        // API configuration
        this.apiBaseUrl = '/api/chat';
        
        // State
        this.isProcessing = false;
        
        // Initialize
        this.init();
    }
    
    /**
     * Initialize the chat interface
     */
    init() {
        // Bind event listeners
        this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        this.clearButton.addEventListener('click', () => this.handleClear());
        this.questionInput.addEventListener('input', () => this.updateCharCount());
        this.questionInput.addEventListener('keydown', (e) => this.handleKeyDown(e));
        
        // Load chat history
        this.loadChatHistory();
        
        // Focus input
        this.questionInput.focus();
        
        console.log('Chat interface initialized with session:', this.sessionId);
    }
    
    /**
     * Get or create session ID
     */
    getOrCreateSessionId() {
        let sessionId = sessionStorage.getItem('chat_session_id');
        
        if (!sessionId) {
            sessionId = 'session-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('chat_session_id', sessionId);
        }
        
        return sessionId;
    }
    
    /**
     * Handle form submission
     */
    async handleSubmit(event) {
        event.preventDefault();
        
        if (this.isProcessing) {
            return;
        }
        
        const question = this.questionInput.value.trim();
        
        // Validate input
        const validation = this.validateInput(question);
        if (!validation.valid) {
            this.showAlert(validation.message, 'warning', 5000);
            this.questionInput.focus();
            return;
        }
        
        // Add user message to chat
        this.addMessage(question, 'user');
        
        // Clear input
        this.questionInput.value = '';
        this.updateCharCount();
        
        // Show typing indicator
        this.showTypingIndicator();
        
        // Disable input
        this.setProcessing(true);
        
        try {
            // Send request to API
            const response = await this.sendChatQuery(question);
            
            // Hide typing indicator
            this.hideTypingIndicator();
            
            // Handle response
            this.handleChatResponse(response);
            
        } catch (error) {
            console.error('Error sending chat query:', error);
            this.hideTypingIndicator();
            this.handleError(error);
        } finally {
            this.setProcessing(false);
            this.questionInput.focus();
        }
    }
    
    /**
     * Handle errors with user-friendly messages
     */
    handleError(error) {
        let errorMessage = 'Failed to send message. Please try again.';
        let detailedMessage = 'Sorry, I encountered an error processing your request.';
        
        // Check for specific error types
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            errorMessage = 'Network error. Please check your connection.';
            detailedMessage = 'Unable to connect to the server. Please check your internet connection and try again.';
        } else if (error.message.includes('timeout')) {
            errorMessage = 'Request timed out. Please try again.';
            detailedMessage = 'The request took too long to complete. Please try again in a moment.';
        } else if (error.message.includes('CSRF')) {
            errorMessage = 'Security validation failed. Please refresh the page.';
            detailedMessage = 'Your session may have expired. Please refresh the page and try again.';
        }
        
        this.showAlert(errorMessage, 'danger', 8000);
        this.addMessage(detailedMessage, 'assistant', true);
    }
    }
    
    /**
     * Send chat query to API
     */
    async sendChatQuery(question) {
        const startTime = Date.now();
        
        const headers = {
            'Content-Type': 'application/json'
        };
        
        // Add CSRF token if available
        if (window.CSRF_TOKEN) {
            headers['X-CSRF-Token'] = window.CSRF_TOKEN;
        }
        
        const response = await fetch(`${this.apiBaseUrl}/query`, {
            method: 'POST',
            headers: headers,
            credentials: 'same-origin',
            body: JSON.stringify({
                question: question,
                session_id: this.sessionId
            })
        });
        
        const responseTime = Date.now() - startTime;
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error?.message || 'Request failed');
        }
        
        const data = await response.json();
        data.responseTime = responseTime;
        
        return data;
    }
    
    /**
     * Handle chat response from API
     */
    handleChatResponse(response) {
        // Check if rejected
        if (response.rejected) {
            this.handleRejectedQuery(response);
            return;
        }
        
        // Check for PII detection
        if (response.pii_detected) {
            this.showPIIWarning(response.pii_warning);
            return;
        }
        
        // Add assistant response
        if (response.answer) {
            this.addMessage(
                response.answer, 
                'assistant', 
                false, 
                null, 
                response.metadata
            );
            
            // Show success feedback with subtle indicator
            this.showSuccessFeedback();
        }
    }
    
    /**
     * Show PII warning with detailed message
     */
    showPIIWarning(warningMessage) {
        const detailedMessage = warningMessage || 
            'Your question contained personally identifiable information (PII) such as names, ' +
            'email addresses, phone numbers, or other personal data. For your privacy and security, ' +
            'please rephrase your question without including any personal information.';
        
        this.showAlert(detailedMessage, 'danger', 10000);
        
        const piiHelpMessage = 
            '⚠️ **Privacy Protection Alert**\n\n' +
            detailedMessage + '\n\n' +
            '**Examples of PII to avoid:**\n' +
            '- Names (e.g., "John Smith")\n' +
            '- Email addresses\n' +
            '- Phone numbers\n' +
            '- Physical addresses\n' +
            '- Credit card or bank account numbers\n\n' +
            'Please ask your question again without personal information.';
        
        this.addMessage(piiHelpMessage, 'assistant', false, 'error');
    }
    
    /**
     * Show success feedback
     */
    showSuccessFeedback() {
        // Visual feedback - briefly highlight send button
        this.sendButton.classList.add('btn-success');
        setTimeout(() => {
            this.sendButton.classList.remove('btn-success');
            this.sendButton.classList.add('btn-primary');
        }, 500);
    }
    
    /**
     * Handle rejected query
     */
    handleRejectedQuery(response) {
        const reason = response.rejection_reason || 'Your question could not be processed';
        
        // Determine alert type based on rejection reason
        let alertType = 'warning';
        let messageType = 'warning';
        
        if (response.pii_detected) {
            alertType = 'danger';
            messageType = 'error';
        }
        
        // Check if it's a topic validation error
        const isTopicError = reason.toLowerCase().includes('topic') || 
                            reason.toLowerCase().includes('crypto') ||
                            reason.toLowerCase().includes('blockchain');
        
        if (isTopicError) {
            this.showTopicValidationError(reason);
        } else {
            this.showAlert(reason, alertType, 8000);
            this.addMessage(reason, 'assistant', false, messageType);
        }
    }
    
    /**
     * Show topic validation error with helpful guidance
     */
    showTopicValidationError(errorMessage) {
        this.showAlert(errorMessage, 'warning', 8000);
        
        const helpMessage = 
            '❌ **Topic Validation Error**\n\n' +
            errorMessage + '\n\n' +
            '**I can help you with:**\n' +
            '- Cryptocurrency price predictions and analysis\n' +
            '- Market trends (bullish, bearish, volatile)\n' +
            '- Blockchain technology questions\n' +
            '- DeFi, NFTs, and crypto trading strategies\n' +
            '- Technical analysis and indicators\n\n' +
            '**I cannot answer questions about:**\n' +
            '- Weather, sports, or general news\n' +
            '- Politics (unless directly related to crypto regulation)\n' +
            '- Personal advice unrelated to cryptocurrency\n\n' +
            'Please ask a cryptocurrency-related question.';
        
        this.addMessage(helpMessage, 'assistant', false, 'info');
    }
    
    /**
     * Add message to chat
     */
    addMessage(content, sender, isError = false, messageType = null, metadata = null) {
        const messageWrapper = document.createElement('div');
        messageWrapper.className = `message-wrapper ${sender}-message`;
        
        const messageBubble = document.createElement('div');
        messageBubble.className = 'message-bubble';
        
        if (messageType) {
            messageBubble.classList.add(messageType);
        }
        
        if (isError) {
            messageBubble.classList.add('error');
        }
        
        // Message header
        const messageHeader = document.createElement('div');
        messageHeader.className = 'message-header';
        
        if (sender === 'user') {
            messageHeader.innerHTML = '<i class="bi bi-person-circle"></i><strong>You</strong>';
        } else {
            messageHeader.innerHTML = '<i class="bi bi-robot"></i><strong>Crypto AI</strong>';
        }
        
        messageBubble.appendChild(messageHeader);
        
        // Message content
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = this.formatMessageContent(content);
        messageBubble.appendChild(messageContent);
        
        // Message metadata (for assistant messages with metadata)
        if (metadata && sender === 'assistant') {
            const metadataDiv = document.createElement('div');
            metadataDiv.className = 'message-metadata';
            metadataDiv.innerHTML = `
                <span class="badge bg-secondary">Tokens: ${metadata.tokens_input + metadata.tokens_output}</span>
                <span class="badge bg-secondary">Cost: $${metadata.cost_usd.toFixed(6)}</span>
                <span class="badge bg-secondary">Time: ${metadata.response_time_ms}ms</span>
            `;
            messageBubble.appendChild(metadataDiv);
        }
        
        // Message time
        const messageTime = document.createElement('div');
        messageTime.className = 'message-time';
        messageTime.textContent = this.formatTime(new Date());
        messageBubble.appendChild(messageTime);
        
        messageWrapper.appendChild(messageBubble);
        this.chatMessages.appendChild(messageWrapper);
        
        // Scroll to bottom
        this.scrollToBottom();
    }
    
    /**
     * Format message content (basic HTML formatting)
     */
    formatMessageContent(content) {
        // Escape HTML to prevent XSS
        const escapeHtml = (text) => {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        };
        
        // Convert line breaks to <br>
        let formatted = escapeHtml(content).replace(/\n/g, '<br>');
        
        // Convert **bold** to <strong>
        formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        
        // Convert *italic* to <em>
        formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');
        
        // Convert `code` to <code>
        formatted = formatted.replace(/`(.+?)`/g, '<code>$1</code>');
        
        // Convert bullet points
        formatted = formatted.replace(/^- (.+)$/gm, '<li>$1</li>');
        if (formatted.includes('<li>')) {
            formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        }
        
        return formatted;
    }
    
    /**
     * Format time
     */
    formatTime(date) {
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) {
            return 'Just now';
        } else if (diff < 3600000) {
            const minutes = Math.floor(diff / 60000);
            return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        } else {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
    }
    
    /**
     * Show typing indicator
     */
    showTypingIndicator() {
        this.typingIndicator.classList.remove('d-none');
        this.scrollToBottom();
    }
    
    /**
     * Hide typing indicator
     */
    hideTypingIndicator() {
        this.typingIndicator.classList.add('d-none');
    }
    
    /**
     * Show alert
     */
    showAlert(message, type = 'info', duration = 5000) {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.setAttribute('role', 'alert');
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        this.alertContainer.appendChild(alert);
        
        // Auto dismiss
        if (duration > 0) {
            setTimeout(() => {
                alert.classList.remove('show');
                setTimeout(() => alert.remove(), 150);
            }, duration);
        }
    }
    
    /**
     * Set processing state
     */
    setProcessing(processing) {
        this.isProcessing = processing;
        this.sendButton.disabled = processing;
        this.questionInput.disabled = processing;
        
        if (processing) {
            this.sendButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> <span class="d-none d-sm-inline ms-1">Sending...</span>';
        } else {
            this.sendButton.innerHTML = '<i class="bi bi-send-fill"></i> <span class="d-none d-sm-inline ms-1">Send</span>';
        }
    }
    
    /**
     * Validate user input
     */
    validateInput(question) {
        if (!question) {
            return {
                valid: false,
                message: 'Please enter a question before sending.'
            };
        }
        
        if (question.length < 3) {
            return {
                valid: false,
                message: 'Your question is too short. Please provide more details.'
            };
        }
        
        if (question.length > 1000) {
            return {
                valid: false,
                message: 'Your question exceeds the maximum length of 1000 characters.'
            };
        }
        
        // Check for common spam patterns
        if (/^(.)\1{10,}$/.test(question)) {
            return {
                valid: false,
                message: 'Please enter a valid question.'
            };
        }
        
        return { valid: true };
    }
    
    /**
     * Update character count
     */
    updateCharCount() {
        const count = this.questionInput.value.length;
        this.charCount.textContent = count;
        
        if (count > 900) {
            this.charCount.classList.add('text-danger');
        } else if (count > 800) {
            this.charCount.classList.add('text-warning');
            this.charCount.classList.remove('text-danger');
        } else {
            this.charCount.classList.remove('text-warning', 'text-danger');
        }
    }
    
    /**
     * Handle keyboard shortcuts
     */
    handleKeyDown(event) {
        // Submit on Ctrl+Enter or Cmd+Enter
        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
            event.preventDefault();
            this.chatForm.dispatchEvent(new Event('submit'));
        }
    }
    
    /**
     * Scroll to bottom of chat
     */
    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }
    
    /**
     * Handle clear chat
     */
    handleClear() {
        if (confirm('Are you sure you want to clear the chat history?')) {
            // Remove all messages except welcome message
            const messages = this.chatMessages.querySelectorAll('.message-wrapper');
            messages.forEach((message, index) => {
                if (index > 0) { // Keep first message (welcome)
                    message.remove();
                }
            });
            
            // Create new session
            sessionStorage.removeItem('chat_session_id');
            this.sessionId = this.getOrCreateSessionId();
            
            this.showAlert('Chat cleared. Starting new session.', 'info', 3000);
        }
    }
    
    /**
     * Load chat history from API
     */
    async loadChatHistory() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/history/${this.sessionId}?limit=3`);
            
            if (!response.ok) {
                console.warn('Failed to load chat history');
                return;
            }
            
            const data = await response.json();
            
            if (data.history && data.history.length > 0) {
                // Display last 3 Q&A pairs
                data.history.reverse().forEach(item => {
                    this.addMessage(item.question, 'user');
                    this.addMessage(item.answer, 'assistant', false, null, {
                        tokens_input: item.tokens_input,
                        tokens_output: item.tokens_output,
                        cost_usd: item.cost_usd,
                        response_time_ms: 0
                    });
                });
                
                this.scrollToBottom();
            }
            
        } catch (error) {
            console.error('Error loading chat history:', error);
            // Don't show error to user, just log it
        }
    }
    
    /**
     * Update status indicator
     */
    updateStatus(online) {
        if (online) {
            this.statusIndicator.className = 'badge bg-success me-2';
            this.statusIndicator.innerHTML = '<i class="bi bi-circle-fill"></i> Online';
        } else {
            this.statusIndicator.className = 'badge bg-danger me-2';
            this.statusIndicator.innerHTML = '<i class="bi bi-circle-fill"></i> Offline';
        }
    }
}

// Initialize chat interface when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.chatInterface = new ChatInterface();
});
