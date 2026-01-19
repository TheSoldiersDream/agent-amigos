# 🔒 Agent Amigos Security Documentation

**Owner:** Darrell Buttigieg  
**All Rights Reserved**

---

## 🛡️ Security Architecture

Agent Amigos is designed to run **entirely locally** with no external access:

### Local-Only Binding

- **Backend:** `http://127.0.0.1:8080` (localhost only)
- **Frontend:** `http://localhost:5174` (localhost only)
- **No remote connections** are allowed or supported

### CORS Protection

- CORS is restricted to localhost origins only
- No external domains can access the API

---

## 🚀 Production Subscriber-Only Plan

When going live, access must be limited to paid subscribers only. The plan below
provides layered controls (identity, API enforcement, and operational guardrails).

### 1) Identity & Access Control (Required)

- **Frontend gate:** Require sign-in (subscriber account) before exposing the app UI.
- **API gate:** Enforce a server-side token for all non-public endpoints.

**Backend switch:**

- `AMIGOS_SUBSCRIBER_GATING=true`
- `AMIGOS_SUBSCRIBER_TOKEN=<strong-random-token>`

All protected endpoints require `X-Subscriber-Token` (or `Authorization: Bearer <token>`).
Public endpoints remain limited to marketing and public metrics only.

### 2) Transport Security (Required)

- Enforce HTTPS only (TLS) for the API and frontend.
- Redirect all HTTP to HTTPS at the hosting layer.

### 3) Network & Origin Controls (Required)

- Restrict API access to the production frontend origin(s).
- If possible, add IP allowlists for admin access.

### 4) Rate Limiting & Abuse Protection (Recommended)

- Rate-limit authentication and sensitive endpoints.
- Add basic WAF rules for common abuse patterns.

### 5) Audit & Monitoring (Required)

- Log authentication failures and unusual request spikes.
- Track subscriber access with request IDs for incident response.

### 6) Data Handling (Required)

- Store subscriber data encrypted at rest.
- Rotate tokens and keys on a scheduled basis.

---

**Go-live gate:** Do not enable production traffic until the subscriber-only gate
is enabled and validated with a non-subscriber test.

---

## 🔐 Security Checklist

### ✅ Built-In Protections

| Protection                 | Status             |
| -------------------------- | ------------------ |
| Localhost binding          | ✅ Enforced        |
| CORS restriction           | ✅ Enabled         |
| No remote access           | ✅ Verified        |
| Local data storage         | ✅ All files local |
| Sensitive files gitignored | ✅ Configured      |

### 📁 Sensitive Files (Never Commit)

- `.env` files (API keys)
- `*.pem`, `*.key` (certificates)
- `credentials.json`, `secrets.json`
- `*.db`, `*.sqlite` (databases)
- Log files with sensitive data

---

## 🖥️ VS Code Security Settings

Add these to your VS Code `settings.json` for enhanced security:

```json
{
  "security.workspace.trust.enabled": true,
  "security.workspace.trust.untrustedFiles": "prompt",
  "security.allowedUNCHosts": [],
  "remote.downloadExtensionsLocally": true,
  "terminal.integrated.allowWorkspaceConfiguration": false,
  "git.autoRepositoryDetection": "subFolders",
  "files.exclude": {
    "**/.env": true,
    "**/*.pem": true,
    "**/credentials.json": true
  }
}
```

---

## 🚀 Secure Startup Procedure

1. **Start Backend:**

   ```bash
   cd backend
   python agent_init.py
   ```

   Verify: `Running on http://127.0.0.1:8080`

2. **Start Frontend:**

   ```bash
   cd frontend
   npm run dev
   ```

   Verify: `localhost:5174`

3. **Check Security Status:**
   - Click the 🔒 security button in the app header
   - All checks should be ✅ green
   - Review any recommendations

---

## ⚠️ Security Recommendations

### 1. API Keys

- Store API keys in `.env` files
- Never commit API keys to git
- Use environment variables

### 2. Network Security

- Firewall: Block inbound connections to ports 8080, 5174
- Use only on trusted networks
- Disable when not in use

### 3. File Permissions

- Restrict AgentAmigos folder access to your user only
- Don't run as Administrator unless necessary

### 4. Regular Audits

- Click security button regularly
- Review console outputs for anomalies
- Check for unauthorized file access

---

## 🔴 If Security Check Shows Red

If the security indicator turns red:

1. **Stop all services immediately**
2. **Check console for error messages**
3. **Review the security panel recommendations**
4. **Verify no external processes are accessing files**
5. **Restart services after fixing issues**

---

## 📞 Incident Response

If you suspect a security breach:

1. Disconnect from network
2. Stop all Agent Amigos processes
3. Check logs for unauthorized access
4. Rotate any exposed API keys
5. Review file modification timestamps

---

## 🔏 Owner Verification

This installation is owned and secured by:

Darrell Buttigieg

All files, configurations, and data in this project are the property of the owner.
Unauthorized access, copying, or distribution is prohibited.

---

Last Updated: Auto-generated by Agent Amigos Security System
