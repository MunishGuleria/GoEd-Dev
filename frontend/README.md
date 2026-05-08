# Frontend — Chat Widget

An embeddable JavaScript chat widget that can be dropped into any website with a single `<script>` tag. No framework required — pure vanilla JS + CSS.

---

## How to Build

```bash
cd frontend
node build.js
```

**Output:**
```
build/chatbot-widget.bundle.js   # Unminified (debug)
build/chatbot-widget.min.js      # Minified with terser (production)
```

---

## How to Use

```html
<!-- Drop this on any page -->
<script src="https://your-cdn.com/chatbot-widget.min.js"></script>
<script>
  window.mainChatbotWidget.init({ trialId: "your-trial-uuid" });
</script>
```

The widget auto-injects its own CSS and renders a floating chat button in the bottom-right corner.

---

## File Structure

```
frontend/
├── build.js                    # Build script — bundles JS + CSS into one file
├── env.js                      # API URL configuration (MUST be edited per environment)
├── src/
│   ├── config.js               # Widget configuration constants
│   ├── debug-logger.js         # Debug logging utility
│   ├── session-manager.js      # Session ID generation + persistence
│   ├── api-client.js           # HTTP client for /init-session and /chat (SSE)
│   ├── ui-manager.js           # DOM manipulation — chat UI, messages, forms
│   ├── chatbot-widget.js       # Main entry point — initializes everything
│   └── marked.min.js           # Markdown parser (vendored, no npm)
├── styles/
│   └── widget.css              # All widget styles
├── build/
│   ├── chatbot-widget.bundle.js
│   └── chatbot-widget.min.js
```

---

## How It Works

### Initialization Flow

```
1. env.js sets window.CHATBOT_ENV.API_BASE_URL
2. chatbot-widget.js creates the widget:
   a. Injects CSS into <head>
   b. Renders chat button + chat container
   c. On first open: calls /init-session with trial_user_id
   d. Receives session_id, college metadata, greeting
3. User types message → api-client.js sends to /chat via SSE
4. Response tokens stream in real-time and render as markdown
```

### Session Persistence

- `session_id` is generated once and stored in `sessionStorage`
- Chat history persists while the tab is open (survives inactive state)
- On page refresh: session resets (new session_id, fresh chat)

### API Communication

| Action | Endpoint | Method |
|---|---|---|
| Start session | `/init-session` | POST |
| Send message | `/chat` | POST (SSE stream) |
| Submit form | `/submit-form` | POST |

---

## Configuration

### env.js (MUST edit per environment)

```javascript
window.CHATBOT_ENV = {
    API_BASE_URL: "https://your-api-domain.com"  // No trailing slash
};
```

- **Local dev:** `http://localhost:8000`
- **Production:** `https://api.yourdomain.com`

### Build Process

`build.js` concatenates files in this order:
1. `marked.min.js` — Markdown parser
2. `env.js` — Sets `window.CHATBOT_ENV` (must be early)
3. `config.js` — Constants
4. `debug-logger.js` — Logging
5. `session-manager.js` — Session handling
6. `api-client.js` — API calls
7. `ui-manager.js` — DOM + UI
8. `chatbot-widget.js` — Entry point

CSS is minified and auto-injected via `<style>` tag at runtime.

---

## Key Behaviors

| Behavior | Details |
|---|---|
| **Markdown rendering** | Bot responses are rendered as HTML using `marked.js` |
| **SSE streaming** | Messages appear token-by-token in real-time |
| **Form handling** | Broadcast, Webinar, and Contact forms are built into the widget |
| **Session timeout** | Chat history stays visible after session becomes inactive |
| **Reset on refresh** | Page refresh clears everything and starts a fresh session |

---

## Making Changes

1. Edit files in `src/` or `styles/`
2. Run `node build.js`
3. Deploy `build/chatbot-widget.min.js` to your CDN or static hosting
4. The widget will automatically pick up changes on next page load

> **Important:** Always update `env.js` with the correct `API_BASE_URL` before building for production.
