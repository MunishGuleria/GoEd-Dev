/**
 * SessionManager - Handles localStorage-based session persistence
 * Manages session_id, lead_id, and expiry logic
 * 
 * IMPORTANT: Session is cached in memory to prevent regenerating session_id on every call
 */

class SessionManager {
    constructor(config) {
        // Namespace the storage key so different widgets do not share sessions
        this.storageKey = config.sessionStorageKey || 'go_ed_ai_chatbot_session';
        this.expiryDays = config.expiryDays;
        this._cachedSession = null; // In-memory cache to prevent repeated regeneration
    }

    /**
     * Generate a unique session ID using Web Crypto API
     * Format: sess_<uuid>
     */
    generateSessionId() {
        return `sess_${crypto.randomUUID()}`;
    }

    /**
     * Get or create session data (with caching)
     * Returns: { session_id, lead_id, phone, email, name, created_at, last_activity, isReturning }
     *
     * NOTE: lead_id is carried forward from localStorage ONLY as a hint for the backend.
     * The backend (initSession) is responsible for validating the lead still exists.
     * If the backend marks the lead as invalid, clearLeadId() should be called.
     */
    getOrCreateSession() {
        // Return cached session if available
        if (this._cachedSession) {
            return this._cachedSession;
        }

        const stored = localStorage.getItem(this.storageKey);

        if (stored) {
            try {
                const data = JSON.parse(stored);

                // Check if expired
                const lastActivity = new Date(data.last_activity);
                const now = new Date();
                const daysSinceActivity = (now - lastActivity) / (1000 * 60 * 60 * 24);

                if (daysSinceActivity > this.expiryDays) {
                    window.DebugLogger.log('Session expired, creating new session');
                    localStorage.removeItem(this.storageKey);
                    return this._createNewSession();
                }

                // Returning user — new session_id per page load, lead_id carried forward
                // lead_id is treated as UNVERIFIED until initSession confirms it
                const isReturning = data.lead_id !== null;
                const newSession = {
                    ...data,
                    session_id: this.generateSessionId(),
                    last_activity: now.toISOString(),
                    isReturning: isReturning,
                    contactProvidedInSession: false,
                    leadVerified: false, // ← reset verification on every new page load
                };

                this._cachedSession = newSession;
                this._saveToStorage(newSession);

                if (isReturning) {
                    window.DebugLogger.log('Returning user detected, lead_id (unverified):', data.lead_id);
                }
                return newSession;

            } catch (e) {
                window.DebugLogger.error('Error parsing session data:', e);
                return this._createNewSession();
            }
        } else {
            return this._createNewSession();
        }
    }

    /**
     * Create a new session for first-time user
     */
    _createNewSession() {
        const now = new Date().toISOString();
        const newSession = {
            session_id: this.generateSessionId(),
            lead_id: null,
            phone: null,
            email: null,
            name: null,
            created_at: now,
            last_activity: now,
            isReturning: false,
            messageCount: 0,
            contactProvidedInSession: false,
            leadVerified: false,
        };

        this._cachedSession = newSession;
        this._saveToStorage(newSession);
        window.DebugLogger.log('New session created:', newSession.session_id);
        return newSession;
    }

    /**
     * Mark lead as verified by the backend.
     * Called after initSession() confirms the lead exists in Dataverse.
     */
    markLeadVerified() {
        if (this._cachedSession) {
            this._cachedSession.leadVerified = true;
            this._saveToStorage(this._cachedSession);
            window.DebugLogger.log('Lead marked as verified:', this._cachedSession.lead_id);
        }
    }

    /**
     * Clear lead_id from session and localStorage.
     * Called when backend reports the lead no longer exists in Dataverse.
     * This prevents the ghost lead_id from being re-sent on the next page load.
     */
    clearLeadId() {
        if (this._cachedSession) {
            window.DebugLogger.log('Clearing stale lead_id:', this._cachedSession.lead_id);
            this._cachedSession.lead_id = null;
            this._cachedSession.leadVerified = false;
            this._cachedSession.isReturning = false;
            this._saveToStorage(this._cachedSession);
        }
    }

    /**
     * Increment user message count
     */
    incrementMessageCount() {
        if (!this._cachedSession) {
            this.getOrCreateSession();
        }

        if (!this._cachedSession.messageCount) {
            this._cachedSession.messageCount = 0;
        }

        this._cachedSession.messageCount++;
        this._saveToStorage(this._cachedSession);

        return this._cachedSession.messageCount;
    }

    /**
     * Get current message count
     */
    getMessageCount() {
        const session = this.getOrCreateSession();
        return session.messageCount || 0;
    }

    /**
     * Reset message count (call this when lead is captured)
     */
    resetMessageCount() {
        if (this._cachedSession) {
            this._cachedSession.messageCount = 0;
            this._saveToStorage(this._cachedSession);
        }
    }

    /**
     * Mark that contact details were provided in this session
     */
    markContactProvided() {
        if (this._cachedSession) {
            this._cachedSession.contactProvidedInSession = true;
            this._saveToStorage(this._cachedSession);
            window.DebugLogger.log('Contact provided flag set for current session');
        }
    }

    /**
     * Internal: Save session to localStorage without triggering cache invalidation
     */
    _saveToStorage(sessionData) {
        localStorage.setItem(this.storageKey, JSON.stringify(sessionData));
    }

    /**
     * Save/update session data to localStorage and update cache
     */
    saveSession(sessionData) {
        sessionData.last_activity = new Date().toISOString();
        this._cachedSession = sessionData;
        this._saveToStorage(sessionData);
    }

    /**
     * Update session with lead information
     * Called when agent captures user's contact info
     */
    updateLeadInfo(leadId, phone, email, name) {
        if (!this._cachedSession) {
            this.getOrCreateSession();
        }

        this._cachedSession.lead_id = leadId;
        this._cachedSession.leadVerified = true; // freshly created — definitely valid
        this._cachedSession.phone = phone || this._cachedSession.phone;
        this._cachedSession.email = email || this._cachedSession.email;
        this._cachedSession.name = name || this._cachedSession.name;

        this.resetMessageCount();
        this.saveSession(this._cachedSession);
        window.DebugLogger.log('Lead info updated:', { leadId, phone, email, name });
    }

    /**
     * Update activity timestamp (lightweight - no session regeneration)
     */
    updateActivity() {
        if (this._cachedSession) {
            this._cachedSession.last_activity = new Date().toISOString();
            this._saveToStorage(this._cachedSession);
        }
    }

    /**
     * Reset in-memory session cache
     */
    resetSession() {
        this._cachedSession = null;
    }

    /**
     * Clear session data (logout/reset)
     */
    clearSession() {
        this._cachedSession = null;
        localStorage.removeItem(this.storageKey);
        window.DebugLogger.log('Session cleared');
    }

    /**
     * Get current session ID
     */
    getSessionId() {
        const session = this.getOrCreateSession();
        return session.session_id;
    }

    /**
     * Get current lead ID (null if not registered)
     */
    getLeadId() {
        const session = this.getOrCreateSession();
        return session.lead_id;
    }

    /**
     * Check if user is a returning user
     */
    isReturningUser() {
        const session = this.getOrCreateSession();
        return session.isReturning && session.lead_id !== null;
    }
}

// Export for use in other modules
window.GoEdSessionManager = SessionManager;