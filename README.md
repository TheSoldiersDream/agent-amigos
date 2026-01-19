# Agent Amigos v3.0 (2025 Hybrid Edition)

This is the **production-grade architecture** for Agent Amigos, featuring a React/Electron frontend and a Python FastAPI backend with MCP support.

## 🎯 Status: Production Ready ✅

**Latest Update**: January 18, 2026  
**Test Coverage**: 100% (8/8 tests passing)  
**Tools Available**: 204  
**Security Score**: 100/100

### Quick Health Check

```powershell
# Start backend
cd backend
python agent_init.py

# In another terminal - Run tests
python backend/test_agent_amigos.py

# View live dashboard
python backend/dashboard.py
```

### Master MCP Registry

Agent Amigos integrates with the **Model Context Protocol (MCP)** to expand its toolset dynamically.

- **Registry**: `backend/agent_mcp/mcp.json`
- **Configured Servers**:
  - `local-system`: Core system automation tools (terminal, filesystem).
  - `github`: Official GitHub MCP server for issue/PR management.

#### Starting the GitHub MCP Standalone

If you need to interact with GitHub explicitly using the agent's token:

```powershell
# Use the VS Code task: "Start GitHub MCP Server"
# OR run manually:
$env:GITHUB_PERSONAL_ACCESS_TOKEN = "your_token_here"; npx -y @modelcontextprotocol/server-github
```

## Directory Structure

- **`backend/`**: The brain of the agent.
  - `agent_init.py`: FastAPI server handling chat and tool execution.
  - `mcp/`: Model Context Protocol configuration and tool definitions.
- **`frontend/`**: The face of the agent.
  - `src/`: React source code (Chat UI, System Status).
  - `package.json`: Dependencies (React, Vite, Electron).
- **`electron/`**: The body of the agent.
  - `main.js`: Handles the application window, system tray, and global hotkeys.

## How to Run

### Prerequisites

- Python 3.10+
- Node.js 18+
- Microsoft Edge or Chrome installed (Selenium will auto-manage the WebDriver)
- Windows desktop unlocked if you expect the agent to drive keyboard/mouse

### Backend (FastAPI) Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt            # core automation + search deps
# Optional heavy media tooling
# pip install -r requirements-media.txt

# Configure an OpenAI-compatible model endpoint
$env:LLM_API_BASE = "http://127.0.0.1:8000/v1"
$env:LLM_MODEL = "mistral-7b-instruct"

python agent_init.py
```

> ✅ The server logs the exact host/port it bound to. Visit `http://127.0.0.1:8080/health` (or the printed port) to verify it’s online and that the LLM endpoint is reachable.

### Frontend (Vite Web UI)

```powershell
cd frontend
cp .env.example .env   # optional – set VITE_AGENT_API_URL if the backend uses a custom URL
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

When the UI loads you’ll see a **connection badge** in the header. Use the **“Change URL”** button there (or edit `frontend/.env`) to point the UI at any reachable backend, even if it had to pick a fallback port.

### Desktop Shell (Electron, optional)

```powershell
cd frontend
npx electron ../electron/main.js
```

### Configure an Open-Source LLM Backend

Agent Amigos talks to any OpenAI-compatible endpoint so you can run fully open-source models (no Ollama required). Set these environment variables before launching `agent_init.py`:

| Variable                | Default                    | Description                                                                                                                                                                     |
| ----------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `LLM_API_BASE`          | `http://localhost:8000/v1` | Base URL of your chat-completions endpoint (vLLM, TGI, LM Studio, etc.).                                                                                                        |
| `LLM_MODEL`             | `mistral-7b-instruct`      | Model identifier exposed by the server.                                                                                                                                         |
| `LLM_API_KEY`           | _empty_                    | Optional bearer token if your server requires auth.                                                                                                                             |
| `LLM_TIMEOUT`           | `120`                      | Timeout (seconds) for each chat call.                                                                                                                                           |
| `AGENT_HOST`            | `127.0.0.1`                | Interface the FastAPI server binds to (use `0.0.0.0` for LAN access).                                                                                                           |
| `AGENT_PORT`            | `8080`                     | Preferred port; the backend automatically falls back to a free port.                                                                                                            |
| `MEDIA_PUBLIC_BASE_URL` | _empty_                    | Public base URL for this backend (used when external services must fetch uploaded media by URL; used for Pollinations-based Img→Img when the source image is an uploaded file). |

> ℹ️ When `AGENT_PORT` is already taken, Agent Amigos logs the new port in the console so you always know which URL to target.

> 🪄 **Image editing (Img→Img)**: If you upload a source image and want the backend to send it to Pollinations for editing, Pollinations must be able to fetch that image via a public URL. Set `MEDIA_PUBLIC_BASE_URL` to a tunnel/domain that points to your running backend, or paste an external `image_url` in the UI instead. The backend tries `model=kontext` first and (if it fails upstream) automatically falls back to `model=flux`.

Example using a local vLLM server:

```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server --model mistralai/Mistral-7B-Instruct
# In another shell
set LLM_API_BASE=http://localhost:8000/v1
set LLM_MODEL=mistral-7b-instruct
python backend/agent_init.py
```

Example using **Ollama** (after `ollama pull llama3.2`):

```powershell
ollama serve
$env:LLM_API_BASE = "http://127.0.0.1:11434/v1"
$env:LLM_MODEL = "llama3.2"
python backend/agent_init.py
```

The `/health` endpoint now reports `llm_ready` and any connection errors so the frontend can warn you if the model server is unreachable.

If you see an error like `model requires more system memory ... than is available`, the chosen local model doesn't fit in RAM.

- Prefer a smaller model: set `OLLAMA_MODEL=llama3.2` (or `llama3.2:latest`) and restart Ollama.
- Optionally configure automatic retries with smaller models via `OLLAMA_FALLBACK_MODELS` (comma-separated), e.g. `llama3.2,llama3.2:3b,llama3.2:1b`.

### Automation Reliability Checklist

- `pip install -r backend/requirements.txt` installs Selenium, webdriver-manager, DuckDuckGo search, PyAutoGUI, Pillow, psutil, etc. Run this inside the same virtualenv you use for `agent_init.py`.
- The agent leverages Selenium for browser automation. Edge/Chrome must be installed and allowed to download drivers (webdriver-manager handles updates automatically).
- PyAutoGUI requires the Windows desktop to remain unlocked; move the cursor to the top-left corner to trigger its failsafe if needed.
- DuckDuckGo search tools need outbound internet access. If your firewall blocks it, configure a proxy inside `tools/web_tools.py`.

## Features Implemented

- **Architecture**: Full separation of concerns (UI vs Logic).
- **MCP**: `mcp.json` and `tools.json` define the agent's capabilities.
- **Autonomy**: The backend `agent_init.py` contains a mock autonomous loop ready for LLM integration.
- **System Integration**: Electron `main.js` includes System Tray and Global Hotkey (`Ctrl+Alt+A`) logic.

### Email Itinerary Console (local)

Agent Amigos includes a local **Email Itinerary Console** flow: paste an email, parse it into structured segments, and then ask the agent to read it back in chronological order.

Key endpoints:

- `POST /email_monitor/parse_sample` — parse a pasted email (set `autosave=true` to store it)
- `GET /itineraries` — list saved itineraries
- `GET /itineraries/summary?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD` — combined summary
- `GET /itineraries/timeline?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD` — plain-English, smart-sorted timeline (used by the “Read Itiniary” command)

Persistence:

- Saved itineraries are persisted to `backend/data/email_itineraries.json` so they survive backend restarts.
- To remove an itinerary, call `POST /itineraries/{trip_id}/delete` (or delete the JSON file to clear everything).

## Copyright & Disclaimer

**Agent Amigos** is owned and developed by **Darrell Buttigieg**.

Copyright © 2025 Darrell Buttigieg. All Rights Reserved.

**Disclaimer:**
This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages or other liability, whether in an action of contract, tort or otherwise, arising from, out of or in connection with the software or the use or other dealings in the software.
