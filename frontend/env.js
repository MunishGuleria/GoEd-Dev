/**
 * Runtime Configuration for Chatbot Widget
 * 
 * IMPORTANT: This file can be edited AFTER deployment without rebuilding!
 * Simply edit the values below and changes take effect on page refresh.
 * 
 * This is useful for:
 * - Changing API URL when moving between environments
 * - Updating theme colors
 * - Modifying default messages
 * - Adjusting session settings
 */

window.CHATBOT_ENV = {
    // Backend API URL - Injected by GitHub Actions from secrets.CHATBOT_API_URL
    // Production: https://zx-edu-ai.centralindia.cloudapp.azure.com/chatbot
    // Auto-detects: /chatbot on current origin in production, localhost:8000 for local dev
    API_URL: (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') ? 'http://localhost:8000' : (window.location.origin + '/chatbot'),

    // Session Configuration
    SESSION_EXPIRY_DAYS: 7,
    SESSION_STORAGE_KEY: 'chatbot_session',

    // UI Theme
    PRIMARY_COLOR: '#667eea',
    THEME: 'light', // 'light' or 'dark'
    WIDGET_POSITION: 'bottom-right', // 'bottom-right' or 'bottom-left'

    // Widget Dimensions
    WIDGET_WIDTH: '500px',
    WIDGET_HEIGHT: '800px',

    // Messages
    GREETING_MESSAGE: 'Hi! How can I help you today?',
    PLACEHOLDER_TEXT: 'Type your message...',
};
