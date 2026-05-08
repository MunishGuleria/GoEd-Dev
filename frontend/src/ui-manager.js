/**
 * MainUIManager - Go Ed AI Edition (Homepage Bot)
 * Professional UI with Robot and Student Icons
 * UPDATED: Fixed DOM query collisions and added unique namespace
 */

class MainUIManager {

    constructor(config) {
        this.config = config;
        this.widgetContainer = null;
        this.messagesContainer = null;
        this.inputField = null;
        this.sendButton = null;
        this.toggleButton = null;
        this.isOpen = false;
        this.currentAIMessageElement = null;

        // Typewriter & Markdown State
        this.typewriterQueue = [];
        this.typewriterTimer = null;
        this.isNetworkStreamDone = false;
        this.currentStreamedText = '';  // Buffer for raw text
        this.typingStartTime = 0;
        this.minTypingMs = 1500;
        this.isTypingVisible = false;
        this.onTypewriterComplete = null;

        // Launcher Bubble State
        this.launcherBubble = null;
        this.currentMessageIndex = 0;
        this.bubbleTimer = null;
    }

    init() {
        this.widgetContainer = this._createWidgetHTML();
        document.body.appendChild(this.widgetContainer);

        // FIX: Strictly query inside THIS widget container to prevent cross-bot collisions
        this.messagesContainer = this.widgetContainer.querySelector('.chatbot-messages');
        this.inputField = this.widgetContainer.querySelector('.chatbot-input');
        this.sendButton = this.widgetContainer.querySelector('.chatbot-send-btn');
        this.toggleButton = this.widgetContainer.querySelector('.chatbot-toggle-btn'); // Changed from document.querySelector
        this.themeToggleBtn = this.widgetContainer.querySelector('.chatbot-theme-toggle');

        if (this.themeToggleBtn) {
            this.themeToggleBtn.addEventListener('click', () => this.toggleTheme());
        }

        this._applyConfig();
        this._setupInputValidation();
        this._initLauncherBubble();
        window.DebugLogger.log('Main UI initialized');
    }

    _setupInputValidation() {
        if (!this.inputField) return;
        
        // Auto-resize logic
        const resizeInput = () => {
            this.inputField.style.height = 'auto';
            const newHeight = Math.min(this.inputField.scrollHeight, 120);
            this.inputField.style.height = newHeight + 'px';
            
            // Add scroll if max height reached
            if (this.inputField.scrollHeight > 120) {
                this.inputField.style.overflowY = 'auto';
            } else {
                this.inputField.style.overflowY = 'hidden';
            }
        };

        this.inputField.addEventListener('input', () => {
            if (this.inputField.value.length > 1000) {
                this.inputField.value = this.inputField.value.substring(0, 1000);
            }
            resizeInput();
        });

        // Also resize on window resize
        window.addEventListener('resize', resizeInput);
        
        // Initial resize
        resizeInput();
    }

    clearMessages() {
        if (this.messagesContainer) {
            this.messagesContainer.innerHTML = '';
        }
    }

    showExpiryMessage(isArchived = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chatbot-message chatbot-message-ai chatbot-system-message';

        if (isArchived) {
            messageDiv.innerHTML = `
                <div class="chatbot-message-avatar">
                    🤖
                </div>
                <div class="chatbot-message-bubble chatbot-expiry-archived">
                    <div class="chatbot-message-content">
                        <strong>💾 Session Archived</strong>

                        Your previous conversation has been saved. A new session has been started. Feel free to continue chatting!
                    </div>
                </div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="chatbot-message-avatar">
                    🤖
                </div>
                <div class="chatbot-message-bubble chatbot-expiry-inactive">
                    <div class="chatbot-message-content">
                        <strong>⏰ Session Expired</strong>

                        Your chat session ended due to inactivity. A new session has been started. Feel free to continue chatting!
                    </div>
                </div>
            `;
        }

        this.messagesContainer.appendChild(messageDiv);
        this._scrollToBottom();

        if (!this.isOpen) {
            this.open();
        }
    }

    showError(message) {
        if (!this.messagesContainer) return;

        const errorDiv = document.createElement('div');
        errorDiv.className = 'chatbot-message chatbot-message-ai';
        errorDiv.innerHTML = `
            <div class="chatbot-message-avatar">
                🤖
            </div>
            <div class="chatbot-message-bubble chatbot-error-bubble">
                <div class="chatbot-message-content chatbot-error-text">
                    ${this._escapeHtml(message)}
                </div>
            </div>
        `;

        this.messagesContainer.appendChild(errorDiv);
        this._scrollToBottom();
    }

    _createWidgetHTML() {
        const container = document.createElement('div');
        container.id = 'main-chatbot-widget-container'; // UNIQUE ID for the homepage bot
        container.className = 'chatbot-widget-container';
        container.innerHTML = `
            <div class="chatbot-launcher-bubble" style="display: none;">
                <span class="bubble-icon">💬</span>
                <span class="bubble-text"></span>
            </div>

            <button class="chatbot-toggle-btn" aria-label="Toggle chat">
                <svg class="chatbot-icon-open" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2ZM20 16H6L4 18V4H20V16ZM7 9H9V11H7V9ZM11 9H13V11H11V9ZM15 9H17V11H15V9Z"/>
                </svg>
                <svg class="chatbot-icon-close" viewBox="0 0 24 24" fill="currentColor" style="display:none;">
                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41Z"/>
                </svg>
            </button>

            <div class="chatbot-widget" style="display: none;">
                <div class="chatbot-header">
                    <div class="chatbot-header-content">
                        <div class="chatbot-avatar">
                            🤖
                        </div>
                        <div class="chatbot-header-text">
                            <div class="chatbot-title">Go Ed AI Assistant</div>
                            <div class="chatbot-status">
                                <span class="chatbot-status-dot"></span>
                                Online
                            </div>
                        </div>
                    </div>
                    <div class="chatbot-header-actions">
                        <button class="chatbot-header-btn chatbot-theme-toggle" aria-label="Toggle dark mode">
                            <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: none;">
                                <circle cx="12" cy="12" r="5"></circle>
                                <line x1="12" y1="1" x2="12" y2="3"></line>
                                <line x1="12" y1="21" x2="12" y2="23"></line>
                                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                                <line x1="1" y1="12" x2="3" y2="12"></line>
                                <line x1="21" y1="12" x2="23" y2="12"></line>
                                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
                            </svg>
                            <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
                            </svg>
                        </button>
                        <button class="chatbot-header-btn chatbot-close-btn" aria-label="Close chat">
                            <svg viewBox="0 0 24 24" fill="currentColor">
                                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41Z"/>
                            </svg>
                        </button>
                    </div>
                </div>

                <div class="chatbot-messages"></div>

                <div class="chatbot-input-area">
                    <textarea
                        class="chatbot-input"
                        placeholder="${this.config.placeholder}"
                        aria-label="Type your message"
                        maxlength="1000"
                        rows="1"
                    ></textarea>
                    <button class="chatbot-send-btn" aria-label="Send message">
                        <svg viewBox="0 0 24 24" fill="currentColor">
                            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                        </svg>
                    </button>
                </div>

                <div class="chatbot-footer">
                    <span class="chatbot-powered-by">Powered by Go Ed AI</span>
                </div>
            </div>
        `;
        return container;
    }

    _applyConfig() {
        const widget = this.widgetContainer.querySelector('.chatbot-widget');

        // CHECK FOR MOBILE VIEW (768px threshold)
        // If on mobile, we skip applying fixed width/height/offsets 
        // and let the CSS media queries take over fully.
        const isMobile = window.innerWidth <= 768;

        if (!isMobile) {
            // Apply position and offsets only for desktop
            const defaultMargin = 30;
            const xOffset = parseInt(this.config.x) || 0;
            const yOffset = parseInt(this.config.y) || 0;

            if (this.config.position === 'bottom-left') {
                this.widgetContainer.style.left = `${defaultMargin + xOffset}px`;
                this.widgetContainer.style.right = 'auto';
            } else {
                this.widgetContainer.style.right = `${defaultMargin + xOffset}px`;
                this.widgetContainer.style.left = 'auto';
            }

            // Apply vertical offset
            this.widgetContainer.style.bottom = `${defaultMargin + yOffset}px`;
            
            // Apply fixed dimensions
            widget.style.width = this.config.width || '400px';
            widget.style.height = this.config.height || '640px';
        } else {
            // Clear any potential inline styles on mobile to ensure CSS wins
            this.widgetContainer.style.left = '';
            this.widgetContainer.style.right = '';
            this.widgetContainer.style.bottom = '';
            widget.style.width = '';
            widget.style.height = '';
        }

        const root = document.documentElement;
        root.style.setProperty('--cb-color-primary', this.config.primaryColor);

        this._initTheme();
    }

    addUserMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chatbot-message chatbot-message-user';
        messageDiv.innerHTML = `
            <div class="chatbot-message-avatar" style="background: linear-gradient(135deg, #6366F1, #8B5CF6);">
                🎓
            </div>
            <div class="chatbot-message-content">${this._escapeHtml(text)}</div>
        `;

        this.messagesContainer.appendChild(messageDiv);
        this._scrollToBottom();
    }

    startAIMessage() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chatbot-message chatbot-message-ai';
        messageDiv.innerHTML = `
            <div class="chatbot-message-avatar">
                🤖
            </div>
            <div class="chatbot-message-bubble">
                <div class="chatbot-message-content"></div>
            </div>
        `;

        this.messagesContainer.appendChild(messageDiv);
        this.currentAIMessageElement = messageDiv.querySelector('.chatbot-message-content');
        this._scrollToBottom();

        // Reset typewriter state
        this.typewriterQueue = [];
        this.currentStreamedText = '';
        this.isNetworkStreamDone = false;

        this._startTypewriterLoop();

        return this.currentAIMessageElement;
    }

    appendToAIMessage(token) {
        if (token) {
            const chars = token.split('');
            this.typewriterQueue.push(...chars);
        }
    }

    finishAIMessage(callback = null) {
        this.isNetworkStreamDone = true;
        this.onTypewriterComplete = callback;
    }

    // --- Typewriter Loop ---
    _startTypewriterLoop() {
        if (this.typewriterTimer) clearInterval(this.typewriterTimer);

        this.typewriterTimer = setInterval(() => {
            // Smart Delay: pause typewriter while typing indicator is visible
            if (this.isTypingVisible) return;

            // Adaptive speed: process more chars when queue is large
            const queueLen = this.typewriterQueue.length;
            const charsPerTick = queueLen > 200 ? 5 : queueLen > 100 ? 3 : 1;

            let changed = false;
            for (let i = 0; i < charsPerTick && this.typewriterQueue.length > 0; i++) {
                this.currentStreamedText += this.typewriterQueue.shift();
                changed = true;
            }

            if (changed && this.currentAIMessageElement) {
                this.currentAIMessageElement.innerHTML = this._parseMarkdown(this.currentStreamedText);
                this._scrollToBottom();
            }
            else if (!changed && this.isNetworkStreamDone) {
                clearInterval(this.typewriterTimer);
                this.currentAIMessageElement = null;
                
                // Trigger callback if typewriter is finished
                if (typeof this.onTypewriterComplete === 'function') {
                    this.onTypewriterComplete();
                    this.onTypewriterComplete = null;
                }
            }
        }, 15); // 15ms per tick
    }

    // --- Markdown Parser (powered by marked.js) ---
    _parseMarkdown(text) {
        if (!text) return '';
        return marked.parse(text, { breaks: true, gfm: true });
    }

    showTypingIndicator() {
        this.isTypingVisible = true;
        this.typingStartTime = Date.now();
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chatbot-typing-indicator';
        typingDiv.innerHTML = `
            <div class="chatbot-message-avatar">
                🤖
            </div>
            <div class="chatbot-typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        typingDiv.id = 'main-chatbot-typing'; // UNIQUE ID
        this.messagesContainer.appendChild(typingDiv);
        this._scrollToBottom();
    }

    hideTypingIndicator() {
        const elapsed = Date.now() - this.typingStartTime;
        const remaining = this.minTypingMs - elapsed;

        if (remaining > 0) {
            setTimeout(() => this._forceHideIndicator(), remaining);
        } else {
            this._forceHideIndicator();
        }
    }

    _forceHideIndicator() {
        const typingDiv = document.getElementById('main-chatbot-typing');
        if (typingDiv) {
            typingDiv.remove();
        }
        this.isTypingVisible = false;
    }

    showGreeting() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chatbot-message chatbot-message-ai chatbot-greeting';
        messageDiv.innerHTML = `
            <div class="chatbot-message-avatar">
                🤖
            </div>
            <div class="chatbot-message-bubble">
                <div class="chatbot-message-content">${this._escapeHtml(this.config.greeting)}</div>
            </div>
        `;

        this.messagesContainer.appendChild(messageDiv);
    }

    clearInput() {
        this.inputField.value = '';
        this.inputField.style.height = 'auto';
        this.inputField.style.overflowY = 'hidden';
    }

    getInputValue() {
        const val = this.inputField.value.trim();
        return val.length > 1000 ? val.substring(0, 1000) : val;
    }

    focusInput() {
        this.inputField.focus();
    }

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        const widget = this.widgetContainer.querySelector('.chatbot-widget');
        const iconOpen = this.toggleButton.querySelector('.chatbot-icon-open');
        const iconClose = this.toggleButton.querySelector('.chatbot-icon-close');

        widget.style.display = 'flex';
        this.widgetContainer.classList.add('is-open'); // Added for responsive styling
        iconOpen.style.display = 'none';
        iconClose.style.display = 'block';
        this.isOpen = true;

        this.focusInput();

        // Hide launcher bubble when widget is open
        this._hideLauncherBubble();
    }

    close() {
        const widget = this.widgetContainer.querySelector('.chatbot-widget');
        const iconOpen = this.toggleButton.querySelector('.chatbot-icon-open');
        const iconClose = this.toggleButton.querySelector('.chatbot-icon-close');

        widget.style.display = 'none';
        this.widgetContainer.classList.remove('is-open'); // Added for responsive styling
        iconOpen.style.display = 'block';
        iconClose.style.display = 'none';
        this.isOpen = false;

        // Show launcher bubble when widget is closed
        this._showLauncherBubble();
    }

    _scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    disableInput() {
        this.inputField.disabled = true;
        this.sendButton.disabled = true;
    }

    enableInput() {
        this.inputField.disabled = false;
        this.sendButton.disabled = false;
    }

    _initTheme() {
        const savedTheme = localStorage.getItem('main-chatbot-theme');
        const widget = this.widgetContainer.querySelector('.chatbot-widget');

        if (savedTheme === 'dark' || (!savedTheme && this.config.theme === 'dark')) {
            this._setTheme('dark');
        } else {
            this._setTheme('light');
        }
    }

    toggleTheme() {
        const widget = this.widgetContainer.querySelector('.chatbot-widget');
        const isDark = widget.classList.contains('chatbot-dark-theme');
        this._setTheme(isDark ? 'light' : 'dark');
    }

    _setTheme(theme) {
        const widget = this.widgetContainer.querySelector('.chatbot-widget');
        const sunIcon = this.widgetContainer.querySelector('.icon-sun');
        const moonIcon = this.widgetContainer.querySelector('.icon-moon');

        if (theme === 'dark') {
            widget.classList.add('chatbot-dark-theme');
            sunIcon.style.display = 'block';
            moonIcon.style.display = 'none';
            localStorage.setItem('main-chatbot-theme', 'dark');
        } else {
            widget.classList.remove('chatbot-dark-theme');
            sunIcon.style.display = 'none';
            moonIcon.style.display = 'block';
            localStorage.setItem('main-chatbot-theme', 'light');
        }
    }

    // --- Launcher Bubble Methods ---

    _initLauncherBubble() {
        this.launcherBubble = this.widgetContainer.querySelector('.chatbot-launcher-bubble');
        if (!this.launcherBubble || !this.config.launcherMessages || this.config.launcherMessages.length === 0) return;

        // Show the first message
        this._showLauncherBubble();

        // Start cycling
        this._startBubbleCycle();
    }

    _showLauncherBubble() {
        if (!this.launcherBubble || this.isOpen) return;

        const messages = this.config.launcherMessages;
        if (!messages || messages.length === 0) return;

        const textSpan = this.launcherBubble.querySelector('.bubble-text');
        textSpan.textContent = messages[this.currentMessageIndex];

        this.launcherBubble.style.display = 'flex';
        this.launcherBubble.classList.remove('hiding');
        this.launcherBubble.classList.add('showing');
    }

    _hideLauncherBubble() {
        if (!this.launcherBubble) return;
        this.launcherBubble.classList.add('hiding');
        setTimeout(() => {
            if (this.launcherBubble.classList.contains('hiding')) {
                this.launcherBubble.style.display = 'none';
            }
        }, 300);
    }

    _startBubbleCycle() {
        if (this.bubbleTimer) clearInterval(this.bubbleTimer);
        
        const interval = this.config.launcherInterval || 5000;
        const messages = this.config.launcherMessages;

        if (!messages || messages.length <= 1) return;

        this.bubbleTimer = setInterval(() => {
            if (this.isOpen) return;

            // Transition out
            this.launcherBubble.classList.add('hiding');

            setTimeout(() => {
                // Change message
                this.currentMessageIndex = (this.currentMessageIndex + 1) % messages.length;
                const textSpan = this.launcherBubble.querySelector('.bubble-text');
                textSpan.textContent = messages[this.currentMessageIndex];

                // Transition in
                this.launcherBubble.classList.remove('hiding');
                this.launcherBubble.classList.add('showing');
            }, 300);
        }, interval);
    }
}

// EXPORT AS MainUIManager
window.MainUIManager = MainUIManager;

// old
// /**
//  * UIManager - Go Ed AI Edition
//  * Professional UI with Robot and Student Icons
//  */

// class UIManager {

//     constructor(config) {
//         this.config = config;
//         this.widgetContainer = null;
//         this.messagesContainer = null;
//         this.inputField = null;
//         this.sendButton = null;
//         this.toggleButton = null;
//         this.isOpen = false;
//         this.currentAIMessageElement = null;

//         // Typewriter & Markdown State
//         this.typewriterQueue = [];
//         this.typewriterTimer = null;
//         this.isNetworkStreamDone = false;
//         this.currentStreamedText = '';  // Buffer for raw text
//         this.typingStartTime = 0;
//         this.minTypingMs = 1500;
//         this.isTypingVisible = false;
//     }

//     init() {
//         this.widgetContainer = this._createWidgetHTML();
//         document.body.appendChild(this.widgetContainer);

//         this.messagesContainer = this.widgetContainer.querySelector('.chatbot-messages');
//         this.inputField = this.widgetContainer.querySelector('.chatbot-input');
//         this.sendButton = this.widgetContainer.querySelector('.chatbot-send-btn');
//         this.toggleButton = document.querySelector('.chatbot-toggle-btn');
//         this.themeToggleBtn = this.widgetContainer.querySelector('.chatbot-theme-toggle');

//         if (this.themeToggleBtn) {
//             this.themeToggleBtn.addEventListener('click', () => this.toggleTheme());
//         }

//         this._applyConfig();
//         window.DebugLogger.log('UI initialized');
//     }

//     clearMessages() {
//         if (this.messagesContainer) {
//             this.messagesContainer.innerHTML = '';
//         }
//     }

//     showExpiryMessage(isArchived = false) {
//         const messageDiv = document.createElement('div');
//         messageDiv.className = 'chatbot-message chatbot-message-ai chatbot-system-message';

//         if (isArchived) {
//             messageDiv.innerHTML = `
//                 <div class="chatbot-message-avatar">
//                     🤖
//                 </div>
//                 <div class="chatbot-message-bubble chatbot-expiry-archived">
//                     <div class="chatbot-message-content">
//                         <strong>💾 Session Archived</strong><br>
//                         Your previous conversation has been saved. A new session has been started. Feel free to continue chatting!
//                     </div>
//                 </div>
//             `;
//         } else {
//             messageDiv.innerHTML = `
//                 <div class="chatbot-message-avatar">
//                     🤖
//                 </div>
//                 <div class="chatbot-message-bubble chatbot-expiry-inactive">
//                     <div class="chatbot-message-content">
//                         <strong>⏰ Session Expired</strong><br>
//                         Your chat session ended due to inactivity. A new session has been started. Feel free to continue chatting!
//                     </div>
//                 </div>
//             `;
//         }

//         this.messagesContainer.appendChild(messageDiv);
//         this._scrollToBottom();

//         if (!this.isOpen) {
//             this.open();
//         }
//     }

//     showError(message) {
//         if (!this.messagesContainer) return;

//         const errorDiv = document.createElement('div');
//         errorDiv.className = 'chatbot-message chatbot-message-ai';
//         errorDiv.innerHTML = `
//             <div class="chatbot-message-avatar">
//                 🤖
//             </div>
//             <div class="chatbot-message-bubble chatbot-error-bubble">
//                 <div class="chatbot-message-content chatbot-error-text">
//                     ${this._escapeHtml(message)}
//                 </div>
//             </div>
//         `;

//         this.messagesContainer.appendChild(errorDiv);
//         this._scrollToBottom();
//     }

//     _createWidgetHTML() {
//         const container = document.createElement('div');
//         container.className = 'chatbot-widget-container';
//         container.innerHTML = `
//             <!-- Toggle Button with Chat Icon -->
//             <button class="chatbot-toggle-btn" aria-label="Toggle chat">
//                 <svg class="chatbot-icon-open" viewBox="0 0 24 24" fill="currentColor">
//                     <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2ZM20 16H6L4 18V4H20V16ZM7 9H9V11H7V9ZM11 9H13V11H11V9ZM15 9H17V11H15V9Z"/>
//                 </svg>
//                 <svg class="chatbot-icon-close" viewBox="0 0 24 24" fill="currentColor" style="display:none;">
//                     <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41Z"/>
//                 </svg>
//             </button>

//             <!-- Main Widget -->
//             <div class="chatbot-widget" style="display: none;">
//                 <!-- Header -->
//                 <div class="chatbot-header">
//                     <div class="chatbot-header-content">
//                         <div class="chatbot-avatar">
//                             🤖
//                         </div>
//                         <div class="chatbot-header-text">
//                             <div class="chatbot-title">Go Ed AI Assistant</div>
//                             <div class="chatbot-status">
//                                 <span class="chatbot-status-dot"></span>
//                                 Online
//                             </div>
//                         </div>
//                     </div>
//                     <div class="chatbot-header-actions">
//                         <button class="chatbot-header-btn chatbot-theme-toggle" aria-label="Toggle dark mode">
//                             <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: none;">
//                                 <circle cx="12" cy="12" r="5"></circle>
//                                 <line x1="12" y1="1" x2="12" y2="3"></line>
//                                 <line x1="12" y1="21" x2="12" y2="23"></line>
//                                 <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
//                                 <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
//                                 <line x1="1" y1="12" x2="3" y2="12"></line>
//                                 <line x1="21" y1="12" x2="23" y2="12"></line>
//                                 <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
//                                 <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
//                             </svg>
//                             <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
//                                 <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
//                             </svg>
//                         </button>
//                         <button class="chatbot-header-btn chatbot-close-btn" aria-label="Close chat">
//                             <svg viewBox="0 0 24 24" fill="currentColor">
//                                 <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41Z"/>
//                             </svg>
//                         </button>
//                     </div>
//                 </div>

//                 <!-- Messages Area -->
//                 <div class="chatbot-messages"></div>

//                 <!-- Input Area -->
//                 <div class="chatbot-input-area">
//                     <input
//                         type="text"
//                         class="chatbot-input"
//                         placeholder="${this.config.placeholder}"
//                         aria-label="Type your message"
//                     />
//                     <button class="chatbot-send-btn" aria-label="Send message">
//                         <svg viewBox="0 0 24 24" fill="currentColor">
//                             <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
//                         </svg>
//                     </button>
//                 </div>

//                 <!-- Footer -->
//                 <div class="chatbot-footer">
//                     <span class="chatbot-powered-by">Powered by Go Ed AI</span>
//                 </div>
//             </div>
//         `;
//         return container;
//     }

//     _applyConfig() {
//         const widget = this.widgetContainer.querySelector('.chatbot-widget');

//         if (this.config.position === 'bottom-left') {
//             this.widgetContainer.style.left = '24px';
//             this.widgetContainer.style.right = 'auto';
//         }

//         const root = document.documentElement;
//         root.style.setProperty('--cb-color-primary', this.config.primaryColor);

//         this._initTheme();

//         widget.style.width = this.config.width || '400px';
//         widget.style.height = this.config.height || '640px';
//     }

//     addUserMessage(text) {
//         const messageDiv = document.createElement('div');
//         messageDiv.className = 'chatbot-message chatbot-message-user';
//         messageDiv.innerHTML = `
//             <div class="chatbot-message-avatar" style="background: linear-gradient(135deg, #6366F1, #8B5CF6);">
//                 🎓
//             </div>
//             <div class="chatbot-message-content">${this._escapeHtml(text)}</div>
//         `;

//         this.messagesContainer.appendChild(messageDiv);
//         this._scrollToBottom();
//     }

//     startAIMessage() {
//         const messageDiv = document.createElement('div');
//         messageDiv.className = 'chatbot-message chatbot-message-ai';
//         messageDiv.innerHTML = `
//             <div class="chatbot-message-avatar">
//                 🤖
//             </div>
//             <div class="chatbot-message-bubble">
//                 <div class="chatbot-message-content"></div>
//             </div>
//         `;

//         this.messagesContainer.appendChild(messageDiv);
//         this.currentAIMessageElement = messageDiv.querySelector('.chatbot-message-content');
//         this._scrollToBottom();

//         // Reset typewriter state
//         this.typewriterQueue = [];
//         this.currentStreamedText = '';
//         this.isNetworkStreamDone = false;

//         this._startTypewriterLoop();

//         return this.currentAIMessageElement;
//     }

//     appendToAIMessage(token) {
//         if (token) {
//             const chars = token.split('');
//             this.typewriterQueue.push(...chars);
//         }
//     }

//     finishAIMessage() {
//         this.isNetworkStreamDone = true;
//     }

//     // --- Typewriter Loop ---
//     _startTypewriterLoop() {
//         if (this.typewriterTimer) clearInterval(this.typewriterTimer);

//         this.typewriterTimer = setInterval(() => {
//             // Smart Delay: pause typewriter while typing indicator is visible
//             if (this.isTypingVisible) return;

//             // Adaptive speed: process more chars when queue is large
//             const queueLen = this.typewriterQueue.length;
//             const charsPerTick = queueLen > 200 ? 5 : queueLen > 100 ? 3 : 1;

//             let changed = false;
//             for (let i = 0; i < charsPerTick && this.typewriterQueue.length > 0; i++) {
//                 this.currentStreamedText += this.typewriterQueue.shift();
//                 changed = true;
//             }

//             if (changed && this.currentAIMessageElement) {
//                 this.currentAIMessageElement.innerHTML = this._parseMarkdown(this.currentStreamedText);
//                 this._scrollToBottom();
//             }
//             else if (!changed && this.isNetworkStreamDone) {
//                 clearInterval(this.typewriterTimer);
//                 this.currentAIMessageElement = null;
//             }
//         }, 15); // 15ms per tick
//     }

//     // --- Markdown Parser (powered by marked.js) ---
//     _parseMarkdown(text) {
//         if (!text) return '';
//         return marked.parse(text, { breaks: true, gfm: true });
//     }

//     showTypingIndicator() {
//         this.isTypingVisible = true;
//         this.typingStartTime = Date.now();
//         const typingDiv = document.createElement('div');
//         typingDiv.className = 'chatbot-typing-indicator';
//         typingDiv.innerHTML = `
//             <div class="chatbot-message-avatar">
//                 🤖
//             </div>
//             <div class="chatbot-typing-dots">
//                 <span></span>
//                 <span></span>
//                 <span></span>
//             </div>
//         `;
//         typingDiv.id = 'chatbot-typing';
//         this.messagesContainer.appendChild(typingDiv);
//         this._scrollToBottom();
//     }

//     hideTypingIndicator() {
//         const elapsed = Date.now() - this.typingStartTime;
//         const remaining = this.minTypingMs - elapsed;

//         if (remaining > 0) {
//             setTimeout(() => this._forceHideIndicator(), remaining);
//         } else {
//             this._forceHideIndicator();
//         }
//     }

//     _forceHideIndicator() {
//         const typingDiv = document.getElementById('chatbot-typing');
//         if (typingDiv) {
//             typingDiv.remove();
//         }
//         this.isTypingVisible = false;
//     }

//     showGreeting() {
//         const messageDiv = document.createElement('div');
//         messageDiv.className = 'chatbot-message chatbot-message-ai chatbot-greeting';
//         messageDiv.innerHTML = `
//             <div class="chatbot-message-avatar">
//                 🤖
//             </div>
//             <div class="chatbot-message-bubble">
//                 <div class="chatbot-message-content">${this._escapeHtml(this.config.greeting)}</div>
//             </div>
//         `;

//         this.messagesContainer.appendChild(messageDiv);
//     }

//     clearInput() {
//         this.inputField.value = '';
//     }

//     getInputValue() {
//         return this.inputField.value.trim();
//     }

//     focusInput() {
//         this.inputField.focus();
//     }

//     toggle() {
//         if (this.isOpen) {
//             this.close();
//         } else {
//             this.open();
//         }
//     }

//     open() {
//         const widget = this.widgetContainer.querySelector('.chatbot-widget');
//         const iconOpen = this.toggleButton.querySelector('.chatbot-icon-open');
//         const iconClose = this.toggleButton.querySelector('.chatbot-icon-close');

//         widget.style.display = 'flex';
//         iconOpen.style.display = 'none';
//         iconClose.style.display = 'block';
//         this.isOpen = true;

//         this.focusInput();
//     }

//     close() {
//         const widget = this.widgetContainer.querySelector('.chatbot-widget');
//         const iconOpen = this.toggleButton.querySelector('.chatbot-icon-open');
//         const iconClose = this.toggleButton.querySelector('.chatbot-icon-close');

//         widget.style.display = 'none';
//         iconOpen.style.display = 'block';
//         iconClose.style.display = 'none';
//         this.isOpen = false;
//     }

//     _scrollToBottom() {
//         this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
//     }

//     _escapeHtml(text) {
//         const div = document.createElement('div');
//         div.textContent = text;
//         return div.innerHTML;
//     }

//     disableInput() {
//         this.inputField.disabled = true;
//         this.sendButton.disabled = true;
//     }

//     enableInput() {
//         this.inputField.disabled = false;
//         this.sendButton.disabled = false;
//     }

//     _initTheme() {
//         const savedTheme = localStorage.getItem('chatbot-theme');
//         const widget = this.widgetContainer.querySelector('.chatbot-widget');

//         if (savedTheme === 'dark' || (!savedTheme && this.config.theme === 'dark')) {
//             this._setTheme('dark');
//         } else {
//             this._setTheme('light');
//         }
//     }

//     toggleTheme() {
//         const widget = this.widgetContainer.querySelector('.chatbot-widget');
//         const isDark = widget.classList.contains('chatbot-dark-theme');
//         this._setTheme(isDark ? 'light' : 'dark');
//     }

//     _setTheme(theme) {
//         const widget = this.widgetContainer.querySelector('.chatbot-widget');
//         const sunIcon = this.widgetContainer.querySelector('.icon-sun');
//         const moonIcon = this.widgetContainer.querySelector('.icon-moon');

//         if (theme === 'dark') {
//             widget.classList.add('chatbot-dark-theme');
//             sunIcon.style.display = 'block';
//             moonIcon.style.display = 'none';
//             localStorage.setItem('chatbot-theme', 'dark');
//         } else {
//             widget.classList.remove('chatbot-dark-theme');
//             sunIcon.style.display = 'none';
//             moonIcon.style.display = 'block';
//             localStorage.setItem('chatbot-theme', 'light');
//         }
//     }
// }

// window.UIManager = UIManager;