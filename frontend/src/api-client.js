/**
 * APIClient - Handles all communication with the FastAPI backend
 * Supports streaming responses via NDJSON
 */

class APIClient {
    constructor(config) {
        this.baseUrl = config.apiUrl;
        this.trialId = config.trialId || null;
    }

    /**
     * Send a chat message and handle streaming response
     */
    async sendMessage(query, sessionId, callbacks, externalSignal = null) {
        const { onToken, onToolStart, onToolEnd, onToolResult, onComplete, onError } = callbacks;

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000);

        if (externalSignal) {
            externalSignal.addEventListener('abort', () => controller.abort());
        }

        try {
            const response = await fetch(`${this.baseUrl}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    query, 
                    session_id: sessionId,
                    ...(this.trialId && { trial_user_id: this.trialId })
                }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    window.DebugLogger.log('Stream complete');
                    if (onComplete) onComplete();
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                for (const line of lines) {
                    if (line.trim() === '') continue;

                    try {
                        const data = JSON.parse(line);
                        window.DebugLogger.log('Received chunk:', data);

                        if (data.type === 'token') {
                            if (onToken) onToken(data.content, data.node);
                        } else if (data.type === 'tool_start') {
                            window.DebugLogger.log('Tool started:', data.tool_name);
                            if (onToolStart) onToolStart(data.tool_name, data.tool_id);
                        } else if (data.type === 'tool_end') {
                            window.DebugLogger.log('Tool completed:', data.tool_name);
                            if (onToolEnd) onToolEnd(data.tool_name, data.tool_id);
                        } else if (data.type === 'tool_result') {
                            if (onToolResult) onToolResult(data.tool_name, data.content);
                        } else if (data.type === 'error') {
                            window.DebugLogger.error('Backend error:', data.error);
                            if (onError) onError(new Error(data.error));
                        } else if (data.type === 'done' || data.done) {
                            window.DebugLogger.log('Received done signal');
                            if (onComplete) onComplete();
                        } else {
                            window.DebugLogger.warn('Unknown chunk type:', data.type, data);
                        }

                    } catch (e) {
                        window.DebugLogger.error('Error parsing JSON line:', { line, error: e });
                    }
                }
            }

        } catch (error) {
            if (error.name === 'AbortError') {
                window.DebugLogger.error('Request timed out after 60 seconds');
                if (onError) onError(new Error('Request timed out'));
            } else {
                window.DebugLogger.error('Error sending message:', error);
                if (onError) onError(error);
            }
        }
    }

    /**
     * Check if a session is still active
     */
    async checkSessionStatus(sessionId) {
        try {
            const response = await fetch(`${this.baseUrl}/session/${sessionId}/status`);
            return await response.json();
        } catch (error) {
            window.DebugLogger.error('Status check failed:', error);
            return { expired: false, exists: false };
        }
    }

    /**
     * Initialize session with lead_id for returning users.
     *
     * The backend should validate whether the lead_id actually exists in Dataverse
     * and return: { lead_valid: true/false, lead_id: "..." }
     *
     * If lead_valid === false, we clear the stale lead_id from localStorage
     * so it doesn't get sent again on future page loads.
     *
     * @param {string} sessionId - New session ID
     * @param {string|null} leadId - Existing lead ID from localStorage (may be stale)
     * @param {SessionManager} sessionManager - Passed in so we can clear stale lead if needed
     */
    async initSession(sessionId, leadId, sessionManager = null) {
        try {
            const bodyPayload = { session_id: sessionId, lead_id: leadId };
            
            if (this.trialId) {
                bodyPayload.trial_user_id = this.trialId;
            }

            const response = await fetch(`${this.baseUrl}/session/init`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bodyPayload)
            });

            const data = await response.json();
            window.DebugLogger.log('Session initialized:', data);

            // ── Handle lead validation response from backend ──────────────────
            if (leadId && sessionManager) {
                if (data.lead_valid === false) {
                    // Backend confirmed this lead doesn't exist in Dataverse anymore
                    // Clear it from localStorage so it's never sent again
                    window.DebugLogger.warn(
                        'Lead not found in Dataverse, clearing from localStorage:',
                        leadId
                    );
                    sessionManager.clearLeadId();

                } else if (data.lead_valid === true) {
                    // Backend confirmed lead is valid
                    sessionManager.markLeadVerified();
                    window.DebugLogger.log('Lead verified by backend:', leadId);

                } else {
                    // Backend didn't return lead_valid (older backend version)
                    // Don't clear — assume valid to avoid breaking existing installs
                    window.DebugLogger.log(
                        'Backend did not return lead_valid — assuming lead is valid:', leadId
                    );
                }
            }

            return data;

        } catch (error) {
            window.DebugLogger.error('Error initializing session:', error);
            // Non-critical — don't block the chat
            return null;
        }
    }
}

// Export for use in other modules
window.GoEdAPIClient = APIClient;