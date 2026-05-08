# Deployment Guide

## 📦 Deployment Options

### Option 1: CDN Deployment (Recommended)

**Best for:** Production use, multiple websites

1. **Upload files to CDN/Static Hosting:**
   - Azure Blob Storage (with CDN)
   - AWS S3 + CloudFront
   - Cloudflare Pages
   - Vercel
   - Netlify

2. **File structure on CDN:**
   ```
   https://your-cdn.com/
   ├── chatbot-widget.min.css
   ├── config.js
   ├── session-manager.js
   ├── api-client.js
   ├── ui-manager.js
   └── chatbot-widget.js
   ```

3. **Embed on websites:**
   ```html
   <link rel="stylesheet" href="https://your-cdn.com/chatbot-widget.min.css">
   <script src="https://your-cdn.com/config.js"></script>
   <script src="https://your-cdn.com/session-manager.js"></script>
   <script src="https://your-cdn.com/api-client.js"></script>
   <script src="https://your-cdn.com/ui-manager.js"></script>
   <script src="https://your-cdn.com/chatbot-widget.js"></script>
   <script>
     ChatbotWidget.init({
       apiUrl: 'https://your-api.azurewebsites.net'
     });
   </script>
   ```

---

### Option 2: Single Bundle (Advanced)

**Best for:** Minimal HTTP requests, faster load

1. **Create bundled version:**
   ```bash
   # Combine all JS files
   cat src/config.js src/session-manager.js src/api-client.js src/ui-manager.js src/chatbot-widget.js > build/chatbot-widget.js
   
   # Minify
   npx terser build/chatbot-widget.js -o build/chatbot-widget.min.js --compress --mangle
   
   # Minify CSS
   npx csso styles/widget.css -o build/chatbot-widget.min.css
   ```

2. **Upload to CDN:**
   ```
   https://your-cdn.com/
   ├── chatbot-widget.min.css
   └── chatbot-widget.min.js
   ```

3. **Embed (single line):**
   ```html
   <link rel="stylesheet" href="https://your-cdn.com/chatbot-widget.min.css">
   <script src="https://your-cdn.com/chatbot-widget.min.js"></script>
   <script>
     window.ChatbotAutoInit = {
       apiUrl: 'https://your-api.azurewebsites.net'
     };
   </script>
   ```

---

## 🔧 Azure Blob Storage + CDN Setup

### Step 1: Create Storage Account

```bash
# Login to Azure
az login

# Create resource group
az group create --name chatbot-rg --location eastus

# Create storage account
az storage account create \
  --name chatbotstorage123 \
  --resource-group chatbot-rg \
  --location eastus \
  --sku Standard_LRS \
  --kind StorageV2

# Enable static website
az storage blob service-properties update \
  --account-name chatbotstorage123 \
  --static-website \
  --404-document index.html \
  --index-document index.html
```

### Step 2: Upload Files

```bash
# Upload widget files
az storage blob upload-batch \
  --account-name chatbotstorage123 \
  --source ./frontend/src \
  --destination '$web/widget' \
  --pattern "*.js"

az storage blob upload \
  --account-name chatbotstorage123 \
  --file ./frontend/styles/widget.css \
  --container-name '$web' \
  --name widget/widget.css
```

### Step 3: Enable CDN (Optional but Recommended)

```bash
# Create CDN profile
az cdn profile create \
  --resource-group chatbot-rg \
  --name chatbot-cdn \
  --sku Standard_Microsoft

# Create CDN endpoint
az cdn endpoint create \
  --resource-group chatbot-rg \
  --profile-name chatbot-cdn \
  --name chatbot-widget \
  --origin chatbotstorage123.z13.web.core.windows.net \
  --origin-host-header chatbotstorage123.z13.web.core.windows.net
```

### Step 4: CORS Configuration

```bash
# Enable CORS for your website domains
az storage cors add \
  --account-name chatbotstorage123 \
  --services b \
  --methods GET HEAD OPTIONS \
  --origins https://your-college-website.com \
  --allowed-headers '*' \
  --exposed-headers '*' \
  --max-age 3600
```

---

## 🌐 Vercel Deployment (Easiest)

1. **Create `vercel.json`:**
   ```json
   {
     "version": 2,
     "builds": [
       {
         "src": "frontend/**",
         "use": "@vercel/static"
       }
     ],
     "headers": [
       {
         "source": "/src/(.*)",
         "headers": [
           { "key": "Access-Control-Allow-Origin", "value": "*" },
           { "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }
         ]
       }
     ]
   }
   ```

2. **Deploy:**
   ```bash
   npm install -g vercel
   cd frontend
   vercel
   ```

3. **Your files will be at:**
   ```
   https://your-project.vercel.app/src/chatbot-widget.js
   https://your-project.vercel.app/styles/widget.css
   ```

---

## 🧪 Testing Before Production

### Test Checklist

- [ ] **Local Testing**
  ```bash
  # Open frontend/index.html in browser
  # Or use VS Code Live Server
  ```

- [ ] **Backend Connection**
  ```bash
  # Ensure FastAPI is running
  cd chatbot
  python main.py
  ```

- [ ] **Test Scenarios:**
  - [ ] Send 3 messages without providing contact
  - [ ] Provide phone number on 4th message
  - [ ] Verify lead_id stored in localStorage
  - [ ] Refresh page - session should persist
  - [ ] Clear localStorage - session resets
  - [ ] Test on mobile (responsive design)
  - [ ] Test dark mode

### Browser DevTools Checklist

```javascript
// In browser console:

// 1. Check session
ChatbotWidget.getSessionInfo()

// 2. Check localStorage
JSON.parse(localStorage.getItem('chatbot_session'))

// 3. Clear session
ChatbotWidget.clearSession()

// 4. Send test message
ChatbotWidget.sendMessage('What MBA courses do you have?')
```

---

## 🔐 Security Considerations

### 1. CORS Configuration
Ensure your FastAPI backend allows requests from widget domain:

```python
# In chatbot/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-college-website.com",
        "https://your-cdn.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. Content Security Policy

Add to your website's CSP headers:
```
Content-Security-Policy: 
  script-src 'self' https://your-cdn.com;
  style-src 'self' https://your-cdn.com;
  connect-src 'self' https://your-api.azurewebsites.net;
```

### 3. Rate Limiting

Consider adding rate limiting to prevent abuse:
```python
# In FastAPI
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/chat")
@limiter.limit("20/minute")
async def chat(request: Request, payload: ChatRequest):
    ...
```

---

## 📊 Monitoring

### Analytics to Track

1. **Widget Usage:**
   - Number of sessions per day
   - Messages per session
   - Lead capture rate

2. **Add to widget (Google Analytics):**
   ```javascript
   // In chatbot-widget.js, after init
   gtag('event', 'chatbot_opened', {
     'event_category': 'chatbot',
     'event_label': 'widget_opened'
   });
   ```

3. **Backend Monitoring:**
   - Monitor `/chat` endpoint latency
   - Track lead creation success rate
   - Monitor Redis memory usage

---

## 🔄 Update Process

When you need to update the widget:

1. **Make changes** to source files
2. **Test locally** with index.html
3. **Bundle** (if using single file approach)
4. **Upload** new version to CDN
5. **Versioning** (recommended):
   ```
   https://your-cdn.com/v1/chatbot-widget.js
   https://your-cdn.com/v2/chatbot-widget.js
   ```

6. **Cache busting:**
   ```html
   <script src="https://your-cdn.com/chatbot-widget.js?v=2.0.1"></script>
   ```

---

## 📱 Performance Optimization

### 1. Lazy Loading

Load widget only when needed:
```html
<script>
  // Load widget when user scrolls or after 3 seconds
  setTimeout(() => {
    const script = document.createElement('script');
    script.src = 'https://your-cdn.com/chatbot-widget.min.js';
    document.body.appendChild(script);
  }, 3000);
</script>
```

### 2. Preconnect to API

```html
<link rel="preconnect" href="https://your-api.azurewebsites.net">
```

### 3. Resource Hints

```html
<link rel="dns-prefetch" href="//your-cdn.com">
<link rel="preload" href="https://your-cdn.com/chatbot-widget.min.js" as="script">
```

---

## ✅ Production Checklist

Before going live:

- [ ] FastAPI backend deployed and accessible
- [ ] MCP server running
- [ ] Archive worker running
- [ ] Widget files uploaded to CDN
- [ ] CORS configured correctly
- [ ] Test on production website
- [ ] Test on mobile devices
- [ ] Monitor backend logs for errors
- [ ] Set up analytics
- [ ] Document embedding instructions for marketing team
