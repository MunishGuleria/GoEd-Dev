/**
* ChatbotWidget - Main controller that orchestrates all components
* This is the entry point and public API
* UPDATED: Now properly handles tool_start and tool_end events and uses isolated MainUIManager
*/
(function () {
    'use strict';



    class ChatbotWidget {
        constructor() {
            this.config = null;
            this.sessionManager = null;
            this.apiClient = null;
            this.uiManager = null;
            this.initialized = false;
            this.pollingInterval = null;
            this._currentAbortController = null;
        }



        /**
         * Initialize the chatbot widget
         * @param {Object} userConfig - User configuration
         */
        init(userConfig = {}) {
            if (this.initialized) {
                window.DebugLogger.warn('Chatbot already initialized');
                return;
            }



            // Validate required trialId
            if (!userConfig.trialId && !window.ChatbotConfig.trialId) {
                window.DebugLogger.error('CRITICAL ERROR: Initialization aborted. A valid trialId must be provided in the initialization configuration. Unauthorized widget usage is blocked.');
                return;
            }

            // Merge user config with defaults
            this.config = { ...window.ChatbotConfig, ...userConfig };
            this.config.expiryDays = this.config.sessionExpiryDays;



            // Initialize components
            this.sessionManager = new window.GoEdSessionManager(this.config);
            this.apiClient = new window.GoEdAPIClient(this.config);

            // ==========================================
            // FIX: Using MainUIManager instead of UIManager
            // ==========================================
            this.uiManager = new window.MainUIManager(this.config);



            // Initialize UI
            this.uiManager.init();



            // Set up event listeners
            this._setupEventListeners();



            // Initialize session
            this._initializeSession();



            // Start inactivity polling
            this._startInactivityPolling();



            // Show greeting
            this.uiManager.showGreeting();



            this.initialized = true;
            window.DebugLogger.log('Chatbot widget initialized successfully');
        }



        /**
         * Initialize session (handle returning users and trial mode)
         */
        async _initializeSession() {
            const session = this.sessionManager.getOrCreateSession();

            const isReturning = session.isReturning && session.lead_id;
            const hasTrialId = !!this.config.trialId;

            // If returning user or trial ID is provided, initialize backend session
            if (isReturning || hasTrialId) {
                window.DebugLogger.log('Initializing backend session (returning user or trial mode)');
                await this.apiClient.initSession(session.session_id, session.lead_id || null);

                if (isReturning) {
                    // Reset message count for returning users with lead_id
                    this.sessionManager.resetMessageCount();
                }
            }
        }



        /**
         * Start polling backend for session expiry
         */
        _startInactivityPolling() {
            if (this.pollingInterval) clearInterval(this.pollingInterval);



            this.pollingInterval = setInterval(async () => {
                const session = this.sessionManager.getOrCreateSession();
                const sessionId = session.session_id;
                if (!sessionId) return;



                // Check backend status
                const status = await this.apiClient.checkSessionStatus(sessionId);
                window.DebugLogger.log(`Polling session ${sessionId.substring(0, 16)}... status:`, status);



                // If session expired on backend
                if (status && status.expired === true) {
                    window.DebugLogger.warn('Session expired due to inactivity (detected by polling)');



                    // Stop polling temporarily to prevent multiple triggers
                    clearInterval(this.pollingInterval);



                    // Show expiry message
                    this.uiManager.showExpiryMessage();



                    // Clear local session data
                    const oldLeadId = this.sessionManager.getLeadId();
                    this.sessionManager.resetSession();



                    // Create new session
                    const newSession = this.sessionManager.getOrCreateSession();
                    window.DebugLogger.log(`New session created: ${newSession.session_id}`);



                    // Re-initialize on backend if returning user OR trial mode
                    const hasTrialId = !!this.config.trialId;
                    if (oldLeadId || hasTrialId) {
                        await this.apiClient.initSession(newSession.session_id, oldLeadId || null);
                        window.DebugLogger.log(`Initialized new session on backend (lead: ${oldLeadId}, trial: ${hasTrialId})`);
                    }



                    // Restart polling with new session
                    this._startInactivityPolling();
                }
            }, 60000); // Check every 60 seconds
        }



        /**
         * Setup all event listeners
         */
        _setupEventListeners() {
            // Toggle button
            this.uiManager.toggleButton.addEventListener('click', () => {
                this.uiManager.toggle();
            });



            // Close button
            const closeBtn = this.uiManager.widgetContainer.querySelector('.chatbot-close-btn');
            closeBtn.addEventListener('click', () => {
                this.uiManager.close();
            });



            // Send button
            this.uiManager.sendButton.addEventListener('click', () => {
                this._handleSendMessage();
            });



            // Input field - Enter key
            this.uiManager.inputField.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this._handleSendMessage();
                }
            });



            // Input field - Update activity on typing
            this.uiManager.inputField.addEventListener('input', () => {
                this.sessionManager.updateActivity();
            });
        }



        /**
         * Handle sending a message
         */
        async _handleSendMessage() {
            const message = this.uiManager.getInputValue();



            if (!message) {
                return;
            }



            const session = this.sessionManager.getOrCreateSession();
            const sessionId = session.session_id;



            // Only check session status if:
            // 1. This is a returning user (has lead_id), OR
            // 2. This session has already sent messages before
            const shouldCheckStatus = session.isReturning || this.sessionManager.getMessageCount() > 0;



            if (shouldCheckStatus) {
                window.DebugLogger.log(`Checking session ${sessionId} status...`);
                const status = await this.apiClient.checkSessionStatus(sessionId);
                window.DebugLogger.log('Session status:', status);



                if (status && status.expired === true) {
                    window.DebugLogger.warn('Session expired - creating new session before sending message');



                    // Show expiry message
                    this.uiManager.showExpiryMessage();



                    // Create new session
                    const oldLeadId = this.sessionManager.getLeadId();
                    this.sessionManager.resetSession();
                    const newSession = this.sessionManager.getOrCreateSession();



                    // Re-link lead_id or initialize trial
                    const hasTrialId = !!this.config.trialId;
                    if (oldLeadId || hasTrialId) {
                        await this.apiClient.initSession(newSession.session_id, oldLeadId || null);
                    }



                    // Now continue with the message using new session
                    const newSessionId = newSession.session_id;
                    this._sendMessageToBackend(message, newSessionId);
                    return;
                }
            } else {
                window.DebugLogger.log('Skipping status check for brand new session');
            }



            // Session is valid (or new), send normally
            this._sendMessageToBackend(message, sessionId);
        }



        /**
         * Actually send the message to backend
         */
        async _sendMessageToBackend(message, sessionId) {
            // Abort any in-flight request
            if (this._currentAbortController) {
                this._currentAbortController.abort();
            }
            this._currentAbortController = new AbortController();
            const signal = this._currentAbortController.signal;



            // Increment message count
            this.sessionManager.incrementMessageCount();



            // Add user message to UI
            this.uiManager.addUserMessage(message);
            this.uiManager.clearInput();
            this.uiManager.disableInput();



            // Show typing indicator
            this.uiManager.showTypingIndicator();



            // Update activity
            this.sessionManager.updateActivity();



            await this.apiClient.sendMessage(message, sessionId, {
                onToken: (content, node) => {
                    // Remove typing indicator on first token
                    this.uiManager.hideTypingIndicator();



                    // Start AI message if not started
                    if (!this.uiManager.currentAIMessageElement) {
                        this.uiManager.startAIMessage();
                    }



                    // Append token
                    this.uiManager.appendToAIMessage(content);
                },



                // Handle tool_start events
                onToolStart: (toolName, toolId) => {
                    window.DebugLogger.log(`Tool started: ${toolName}`);
                    // Removed hideTypingIndicator to keep dots visible during tool calls
                },



                // Handle tool_end events
                onToolEnd: (toolName, toolId) => {
                    window.DebugLogger.log(`Tool completed: ${toolName}`);
                },



                onToolResult: (toolName, content) => {
                    window.DebugLogger.log(`Tool ${toolName} executed:`, content);



                    // If check_lead or create_lead was called, user has shared contact info
                    if (toolName === 'check_lead' || toolName === 'create_lead') {
                        // Mark that contact was provided (regardless of found/not_found)
                        this.sessionManager.markContactProvided();



                        // Handle lead capture for successful cases
                        this._handleLeadCapture(content);
                    }
                },



                onComplete: () => {
                    window.DebugLogger.log('Message stream complete');
                    this.uiManager.hideTypingIndicator();
                    this.uiManager.finishAIMessage(() => {
                        this.uiManager.enableInput();
                        this.uiManager.focusInput();
                    });
                    this._currentAbortController = null;
                },



                onError: (error) => {
                    window.DebugLogger.error('Error sending message:', error);
                    this.uiManager.hideTypingIndicator();
                    this.uiManager.showError('Failed to send message. Please try again.');
                    this.uiManager.enableInput();
                    this.uiManager.focusInput();
                    this._currentAbortController = null;
                }
            }, signal);
        }



        /**
         * Handle lead capture from tool results
         * @param {string} toolContent - Tool result content (JSON string)
         */
        _handleLeadCapture(toolContent) {
            try {
                let data = toolContent;



                // Parse JSON string
                if (typeof data === 'string') {
                    data = JSON.parse(data);
                }



                // Handle array format: [{type: 'text', text: '...'}]
                if (Array.isArray(data) && data.length > 0) {
                    const item = data[0];
                    if (item.text && typeof item.text === 'string') {
                        data = JSON.parse(item.text);
                    } else if (typeof item === 'object') {
                        data = item;
                    }
                }



                // Handle single object with text field: {type: 'text', text: '...'}
                if (data.type === 'text' && data.text) {
                    data = JSON.parse(data.text);
                }



                // Check if lead was successfully captured
                if (data.status === 'success' && data.lead_id) {
                    window.DebugLogger.log('Lead captured:', data.lead_id);



                    // Update session with lead info (this also resets message count)
                    this.sessionManager.updateLeadInfo(
                        data.lead_id,
                        data.phone || null,
                        data.email || null,
                        data.name || null
                    );
                } else if (data.status === 'not_found') {
                    window.DebugLogger.log('Contact details provided but lead not found in system');
                    // Contact was provided, just not found - this is fine
                    // contactProvidedInSession is already marked in onToolResult
                }
            } catch (e) {
                // Only log unexpected errors (not "not_found" cases)
                if (!String(toolContent).includes('"status":"not_found"')) {
                    window.DebugLogger.error('Error parsing lead capture data:', { error: e.message, content: toolContent });
                }
            }
        }



        /**
         * Public API: Send message programmatically
         */
        sendMessage(message) {
            if (!this.initialized) {
                window.DebugLogger.error('Widget not initialized');
                return;
            }



            this.uiManager.inputField.value = message;
            this._handleSendMessage();
        }



        /**
         * Public API: Open widget
         */
        open() {
            if (!this.initialized) {
                window.DebugLogger.error('Widget not initialized');
                return;
            }
            this.uiManager.open();
        }



        /**
         * Public API: Close widget
         */
        close() {
            if (!this.initialized) {
                window.DebugLogger.error('Widget not initialized');
                return;
            }
            this.uiManager.close();
        }



        /**
         * Public API: Clear session
         */
        clearSession() {
            if (!this.initialized) {
                window.DebugLogger.error('Widget not initialized');
                return;
            }
            this.sessionManager.clearSession();
            window.DebugLogger.log('Session cleared. Refresh page to start new session.');
        }



        /**
         * Public API: Get session info (for debugging)
         */
        getSessionInfo() {
            if (!this.initialized) {
                window.DebugLogger.error('Widget not initialized');
                return null;
            }



            return {
                session_id: this.sessionManager.getSessionId(),
                lead_id: this.sessionManager.getLeadId(),
                is_returning: this.sessionManager.isReturningUser(),
                message_count: this.sessionManager.getMessageCount()
            };
        }
    }



    // ==========================================
    // CHANGES APPLIED HERE
    // ==========================================

    // Export for global access
    window.ChatbotWidget = ChatbotWidget;

    // Create global instance as mainChatbotWidget
    window.mainChatbotWidget = new ChatbotWidget();



    // Auto-initialize on DOMContentLoaded if config exists
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            if (window.mainChatbotAutoInit) {
                window.mainChatbotWidget.init(window.mainChatbotAutoInit);
            }
        });
    } else {
        // DOM already loaded (script loaded with defer/async or after DOMContentLoaded)
        if (window.mainChatbotAutoInit) {
            window.mainChatbotWidget.init(window.mainChatbotAutoInit);
        }
    }



})();

//old
// /**
//  * ChatbotWidget - Main controller that orchestrates all components
//  * This is the entry point and public API
//  * UPDATED: Now properly handles tool_start and tool_end events
//  */

// (function () {
//     'use strict';

//     class ChatbotWidget {
//         constructor() {
//             this.config = null;
//             this.sessionManager = null;
//             this.apiClient = null;
//             this.uiManager = null;
//             this.initialized = false;
//             this.pollingInterval = null;
//             this._currentAbortController = null;
//         }

//         /**
//          * Initialize the chatbot widget
//          * @param {Object} userConfig - User configuration
//          */
//         init(userConfig = {}) {
//             if (this.initialized) {
//                 window.DebugLogger.warn('Chatbot already initialized');
//                 return;
//             }

//             // Merge user config with defaults
//             this.config = { ...window.ChatbotConfig, ...userConfig };
//             this.config.expiryDays = this.config.sessionExpiryDays;

//             // Initialize components
//             this.sessionManager = new window.SessionManager(this.config);
//             this.apiClient = new window.APIClient(this.config);
//             this.uiManager = new window.UIManager(this.config);

//             // Initialize UI
//             this.uiManager.init();

//             // Set up event listeners
//             this._setupEventListeners();

//             // Initialize session
//             this._initializeSession();

//             // Start inactivity polling
//             this._startInactivityPolling();

//             // Show greeting
//             this.uiManager.showGreeting();

//             this.initialized = true;
//             window.DebugLogger.log('Chatbot widget initialized successfully');
//         }

//         /**
//          * Initialize session (handle returning users)
//          */
//         async _initializeSession() {
//             const session = this.sessionManager.getOrCreateSession();

//             // If returning user with lead_id, initialize backend session
//             if (session.isReturning && session.lead_id) {
//                 window.DebugLogger.log('Returning user detected, initializing session with lead_id');
//                 await this.apiClient.initSession(session.session_id, session.lead_id);
//                 // Reset message count for returning users with lead_id
//                 this.sessionManager.resetMessageCount();
//             }
//         }

//         /**
//          * Start polling backend for session expiry
//          */
//         _startInactivityPolling() {
//             if (this.pollingInterval) clearInterval(this.pollingInterval);

//             this.pollingInterval = setInterval(async () => {
//                 const session = this.sessionManager.getOrCreateSession();
//                 const sessionId = session.session_id;
//                 if (!sessionId) return;

//                 // Check backend status
//                 const status = await this.apiClient.checkSessionStatus(sessionId);
//                 window.DebugLogger.log(`Polling session ${sessionId.substring(0, 16)}... status:`, status);

//                 // If session expired on backend
//                 if (status && status.expired === true) {
//                     window.DebugLogger.warn('Session expired due to inactivity (detected by polling)');

//                     // Stop polling temporarily to prevent multiple triggers
//                     clearInterval(this.pollingInterval);

//                     // Clear old messages from UI
//                     this.uiManager.clearMessages();

//                     // Show expiry message
//                     this.uiManager.showExpiryMessage();

//                     // Clear local session data
//                     const oldLeadId = this.sessionManager.getLeadId();
//                     this.sessionManager.resetSession();

//                     // Create new session
//                     const newSession = this.sessionManager.getOrCreateSession();
//                     window.DebugLogger.log(`New session created: ${newSession.session_id}`);

//                     // Re-initialize on backend with old lead_id if exists
//                     if (oldLeadId) {
//                         await this.apiClient.initSession(newSession.session_id, oldLeadId);
//                         window.DebugLogger.log(`Linked old lead_id ${oldLeadId} to new session`);
//                     }

//                     // Restart polling with new session
//                     this._startInactivityPolling();
//                 }
//             }, 60000); // Check every 60 seconds
//         }

//         /**
//          * Setup all event listeners
//          */
//         _setupEventListeners() {
//             // Toggle button
//             this.uiManager.toggleButton.addEventListener('click', () => {
//                 this.uiManager.toggle();
//             });

//             // Close button
//             const closeBtn = this.uiManager.widgetContainer.querySelector('.chatbot-close-btn');
//             closeBtn.addEventListener('click', () => {
//                 this.uiManager.close();
//             });

//             // Send button
//             this.uiManager.sendButton.addEventListener('click', () => {
//                 this._handleSendMessage();
//             });

//             // Input field - Enter key
//             this.uiManager.inputField.addEventListener('keypress', (e) => {
//                 if (e.key === 'Enter' && !e.shiftKey) {
//                     e.preventDefault();
//                     this._handleSendMessage();
//                 }
//             });

//             // Input field - Update activity on typing
//             this.uiManager.inputField.addEventListener('input', () => {
//                 this.sessionManager.updateActivity();
//             });
//         }

//         /**
//          * Handle sending a message
//          */
//         async _handleSendMessage() {
//             const message = this.uiManager.getInputValue();

//             if (!message) {
//                 return;
//             }

//             const session = this.sessionManager.getOrCreateSession();
//             const sessionId = session.session_id;

//             // Only check session status if:
//             // 1. This is a returning user (has lead_id), OR
//             // 2. This session has already sent messages before
//             const shouldCheckStatus = session.isReturning || this.sessionManager.getMessageCount() > 0;

//             if (shouldCheckStatus) {
//                 window.DebugLogger.log(`Checking session ${sessionId} status...`);
//                 const status = await this.apiClient.checkSessionStatus(sessionId);
//                 window.DebugLogger.log('Session status:', status);

//                 if (status && status.expired === true) {
//                     window.DebugLogger.warn('Session expired - creating new session before sending message');

//                     // Clear old messages
//                     this.uiManager.clearMessages();

//                     // Show expiry message
//                     this.uiManager.showExpiryMessage();

//                     // Create new session
//                     const oldLeadId = this.sessionManager.getLeadId();
//                     this.sessionManager.resetSession();
//                     const newSession = this.sessionManager.getOrCreateSession();

//                     // Re-link lead_id
//                     if (oldLeadId) {
//                         await this.apiClient.initSession(newSession.session_id, oldLeadId);
//                     }

//                     // Now continue with the message using new session
//                     const newSessionId = newSession.session_id;
//                     this._sendMessageToBackend(message, newSessionId);
//                     return;
//                 }
//             } else {
//                 window.DebugLogger.log('Skipping status check for brand new session');
//             }

//             // Session is valid (or new), send normally
//             this._sendMessageToBackend(message, sessionId);
//         }

//         /**
//          * Actually send the message to backend
//          */
//         async _sendMessageToBackend(message, sessionId) {
//             // Abort any in-flight request
//             if (this._currentAbortController) {
//                 this._currentAbortController.abort();
//             }
//             this._currentAbortController = new AbortController();
//             const signal = this._currentAbortController.signal;

//             // Increment message count
//             this.sessionManager.incrementMessageCount();

//             // Add user message to UI
//             this.uiManager.addUserMessage(message);
//             this.uiManager.clearInput();
//             this.uiManager.disableInput();

//             // Show typing indicator
//             this.uiManager.showTypingIndicator();

//             // Update activity
//             this.sessionManager.updateActivity();

//             await this.apiClient.sendMessage(message, sessionId, {
//                 onToken: (content, node) => {
//                     // Remove typing indicator on first token
//                     this.uiManager.hideTypingIndicator();

//                     // Start AI message if not started
//                     if (!this.uiManager.currentAIMessageElement) {
//                         this.uiManager.startAIMessage();
//                     }

//                     // Append token
//                     this.uiManager.appendToAIMessage(content);
//                 },

//                 // Handle tool_start events
//                 onToolStart: (toolName, toolId) => {
//                     window.DebugLogger.log(`Tool started: ${toolName}`);
//                     this.uiManager.hideTypingIndicator();
//                 },

//                 // Handle tool_end events
//                 onToolEnd: (toolName, toolId) => {
//                     window.DebugLogger.log(`Tool completed: ${toolName}`);
//                 },

//                 onToolResult: (toolName, content) => {
//                     window.DebugLogger.log(`Tool ${toolName} executed:`, content);

//                     // If check_lead or create_lead was called, user has shared contact info
//                     if (toolName === 'check_lead' || toolName === 'create_lead') {
//                         // Mark that contact was provided (regardless of found/not_found)
//                         this.sessionManager.markContactProvided();

//                         // Handle lead capture for successful cases
//                         this._handleLeadCapture(content);
//                     }
//                 },

//                 onComplete: () => {
//                     window.DebugLogger.log('Message stream complete');
//                     this.uiManager.hideTypingIndicator();
//                     this.uiManager.finishAIMessage();
//                     this.uiManager.enableInput();
//                     this.uiManager.focusInput();
//                     this._currentAbortController = null;
//                 },

//                 onError: (error) => {
//                     window.DebugLogger.error('Error sending message:', error);
//                     this.uiManager.hideTypingIndicator();
//                     this.uiManager.showError('Failed to send message. Please try again.');
//                     this.uiManager.enableInput();
//                     this.uiManager.focusInput();
//                     this._currentAbortController = null;
//                 }
//             }, signal);
//         }

//         /**
//          * Handle lead capture from tool results
//          * @param {string} toolContent - Tool result content (JSON string)
//          */
//         _handleLeadCapture(toolContent) {
//             try {
//                 let data = toolContent;

//                 // Parse JSON string
//                 if (typeof data === 'string') {
//                     data = JSON.parse(data);
//                 }

//                 // Handle array format: [{type: 'text', text: '...'}]
//                 if (Array.isArray(data) && data.length > 0) {
//                     const item = data[0];
//                     if (item.text && typeof item.text === 'string') {
//                         data = JSON.parse(item.text);
//                     } else if (typeof item === 'object') {
//                         data = item;
//                     }
//                 }

//                 // Handle single object with text field: {type: 'text', text: '...'}
//                 if (data.type === 'text' && data.text) {
//                     data = JSON.parse(data.text);
//                 }

//                 // Check if lead was successfully captured
//                 if (data.status === 'success' && data.lead_id) {
//                     window.DebugLogger.log('Lead captured:', data.lead_id);

//                     // Update session with lead info (this also resets message count)
//                     this.sessionManager.updateLeadInfo(
//                         data.lead_id,
//                         data.phone || null,
//                         data.email || null,
//                         data.name || null
//                     );
//                 } else if (data.status === 'not_found') {
//                     window.DebugLogger.log('Contact details provided but lead not found in system');
//                     // Contact was provided, just not found - this is fine
//                     // contactProvidedInSession is already marked in onToolResult
//                 }
//             } catch (e) {
//                 // Only log unexpected errors (not "not_found" cases)
//                 if (!String(toolContent).includes('"status":"not_found"')) {
//                     window.DebugLogger.error('Error parsing lead capture data:', { error: e.message, content: toolContent });
//                 }
//             }
//         }

//         /**
//          * Public API: Send message programmatically
//          */
//         sendMessage(message) {
//             if (!this.initialized) {
//                 window.DebugLogger.error('Widget not initialized');
//                 return;
//             }

//             this.uiManager.inputField.value = message;
//             this._handleSendMessage();
//         }

//         /**
//          * Public API: Open widget
//          */
//         open() {
//             if (!this.initialized) {
//                 window.DebugLogger.error('Widget not initialized');
//                 return;
//             }
//             this.uiManager.open();
//         }

//         /**
//          * Public API: Close widget
//          */
//         close() {
//             if (!this.initialized) {
//                 window.DebugLogger.error('Widget not initialized');
//                 return;
//             }
//             this.uiManager.close();
//         }

//         /**
//          * Public API: Clear session
//          */
//         clearSession() {
//             if (!this.initialized) {
//                 window.DebugLogger.error('Widget not initialized');
//                 return;
//             }
//             this.sessionManager.clearSession();
//             window.DebugLogger.log('Session cleared. Refresh page to start new session.');
//         }

//         /**
//          * Public API: Get session info (for debugging)
//          */
//         getSessionInfo() {
//             if (!this.initialized) {
//                 window.DebugLogger.error('Widget not initialized');
//                 return null;
//             }

//             return {
//                 session_id: this.sessionManager.getSessionId(),
//                 lead_id: this.sessionManager.getLeadId(),
//                 is_returning: this.sessionManager.isReturningUser(),
//                 message_count: this.sessionManager.getMessageCount()
//             };
//         }
//     }

//     // Create global instance
//     window.ChatbotWidget = new ChatbotWidget();

//     // Auto-initialize on DOMContentLoaded if config exists
//     if (document.readyState === 'loading') {
//         document.addEventListener('DOMContentLoaded', () => {
//             if (window.ChatbotAutoInit) {
//                 window.ChatbotWidget.init(window.ChatbotAutoInit);
//             }
//         });
//     } else {
//         // DOM already loaded (script loaded with defer/async or after DOMContentLoaded)
//         if (window.ChatbotAutoInit) {
//             window.ChatbotWidget.init(window.ChatbotAutoInit);
//         }
//     }

// })();
