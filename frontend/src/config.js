/**
 * Configuration for the Chatbot Widget
 * 
 * Uses runtime environment variables from window.CHATBOT_ENV (defined in env.js)
 * Falls back to defaults if env.js is not loaded
 */

const DEFAULT_CONFIG = {
    // Backend API - From runtime env or default
    apiUrl: window.CHATBOT_ENV?.API_URL || 'http://localhost:8000',

    // Session management
    sessionExpiryDays: window.CHATBOT_ENV?.SESSION_EXPIRY_DAYS || 7,
    sessionStorageKey: window.CHATBOT_ENV?.SESSION_STORAGE_KEY || 'chatbot_session',

    // UI/UX
    position: window.CHATBOT_ENV?.WIDGET_POSITION || 'bottom-right',
    primaryColor: window.CHATBOT_ENV?.PRIMARY_COLOR || '#667eea',
    theme: window.CHATBOT_ENV?.THEME || 'light',

    // Messages
    placeholder: window.CHATBOT_ENV?.PLACEHOLDER_TEXT || 'Type your message...',
    greeting: window.CHATBOT_ENV?.GREETING_MESSAGE || 'Hi! How can I help you today?',

    // Widget dimensions
    width: window.CHATBOT_ENV?.WIDGET_WIDTH || '500px',
    height: window.CHATBOT_ENV?.WIDGET_HEIGHT || '800px',

    // Launcher Bubble Messages
    launcherMessages: window.CHATBOT_ENV?.LAUNCHER_MESSAGES || [
        "Hey! Need help with admissions?",
        "Have questions about courses?",
        "Chat with Go Ed AI Assistant!"
    ],
    launcherInterval: window.CHATBOT_ENV?.LAUNCHER_INTERVAL || 5000,

    // Position Offsets
    x: window.CHATBOT_ENV?.WIDGET_X || 0,
    y: window.CHATBOT_ENV?.WIDGET_Y || 0,
};

// Export for use in other modules
window.ChatbotConfig = DEFAULT_CONFIG;
