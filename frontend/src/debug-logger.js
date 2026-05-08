/**
 * DebugLogger - Centralized logging system for developer debugging
 * Captures all logs in memory instead of browser console
 */

class DebugLogger {
    constructor() {
        this.logs = [];
        this.maxLogs = 500; // Keep last 500 logs
    }

    /**
     * Add a log entry
     */
    _addLog(level, message, data = null) {
        const timestamp = new Date().toISOString();
        const logEntry = {
            timestamp,
            level,
            message,
            data: data ? JSON.stringify(data) : null
        };

        this.logs.push(logEntry);

        // Keep only last maxLogs entries
        if (this.logs.length > this.maxLogs) {
            this.logs.shift();
        }

        // Also log to console in development (can be disabled in production)
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            // Optionally keep console logs for localhost development
            // Comment out these lines to completely hide console logs
            // const consoleMethod = level === 'error' ? console.error : level === 'warn' ? console.warn : console.log;
            // consoleMethod(`[${level.toUpperCase()}]`, message, data || '');
        }
    }

    /**
     * Log info message
     */
    log(message, data = null) {
        this._addLog('info', message, data);
    }

    /**
     * Log info message (alias)
     */
    info(message, data = null) {
        this._addLog('info', message, data);
    }

    /**
     * Log warning message
     */
    warn(message, data = null) {
        this._addLog('warn', message, data);
    }

    /**
     * Log error message
     */
    error(message, data = null) {
        this._addLog('error', message, data);
    }

    /**
     * Get all logs
     */
    getLogs() {
        return [...this.logs]; // Return copy
    }

    /**
     * Clear all logs
     */
    clearLogs() {
        this.logs = [];
    }

    /**
     * Get logs as formatted HTML
     */
    getLogsHTML() {
        return this.logs.map(log => {
            const levelColors = {
                info: '#3B82F6',
                warn: '#F59E0B',
                error: '#EF4444'
            };
            const color = levelColors[log.level] || '#6B7280';
            const time = new Date(log.timestamp).toLocaleTimeString();
            
            return `
                <div class="log-entry log-${log.level}">
                    <span class="log-time">${time}</span>
                    <span class="log-level" style="color: ${color}">[${log.level.toUpperCase()}]</span>
                    <span class="log-message">${log.message}</span>
                    ${log.data ? `<span class="log-data">${log.data}</span>` : ''}
                </div>
            `;
        }).join('');
    }
}

// Create global instance
window.DebugLogger = new DebugLogger();
