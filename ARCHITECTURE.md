# Agent Amigos (2025 Hybrid Edition) - Architecture Specification

## 1. System Overview
Agent Amigos is a local-first, autonomous desktop assistant designed for Windows. It leverages a hybrid architecture:
- **Frontend**: React + Vite (UI) wrapped in Electron (System Integration).
- **Backend**: Python FastAPI (Agent Logic, LLM Inference, MCP Orchestration).
- **Communication**: REST API + WebSockets (Real-time logs/status).

## 2. Component Structure

### A. Frontend (Electron + React)
- **Window Management**: Electron `main.js` handles system tray, global shortcuts (Ctrl+Alt+A), and window visibility.
- **UI Components**:
  - `Sidebar`: Agent selection (General, Social, Coder).
  - `ChatPanel`: Multi-modal output (Text, Code Blocks, Images).
  - `ActionPanel`: Live log of autonomous actions (file ops, browser clicks).
  - `VoiceControl`: Mic toggle for speech-to-text.
  - `Settings`: API keys, model selection, startup preferences.

### B. Backend (Python FastAPI)
- **API Layer**: Endpoints for chat, command execution, and status.
- **Agent Engine**:
  - `CoreAgent`: Manages context, memory, and planning.
  - `Planner`: Decomposes high-level goals into subtasks.
  - `Executor`: Runs tools and reports results.
- **MCP (Model Context Protocol)**:
  - Standardized interface for tools (File System, Browser, Social Media).
  - `mcp.json`: Registry of available MCP servers.

### C. Data & Persistence
- **Vector DB**: ChromaDB or FAISS for long-term memory (user preferences, past solutions).
- **Logs**: JSONL logs for all actions and LLM traces.
- **Config**: `config.yaml` for user settings.

## 3. Folder Structure
```
AgentAmigos/
├── backend/
│   ├── agent_init.py       # Entry point for the Python backend
│   ├── server.py           # FastAPI server
│   ├── core/
│   │   ├── planner.py      # Task decomposition
│   │   ├── memory.py       # Vector DB wrapper
│   │   └── llm.py          # LLM Interface (vLLM/OpenAI)
│   └── mcp/
│       ├── mcp.json        # MCP Configuration
│       ├── tools.json      # Tool definitions
│       └── server.py       # MCP Server implementation
├── electron/
│   ├── main.js             # Electron main process (System Tray, Windows)
│   └── preload.js          # IPC Bridge
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Main React Component
│   │   ├── components/     # UI Components
│   │   └── hooks/          # Custom hooks (useAgent, useVoice)
│   └── package.json
└── install_startup.bat     # Windows Startup Script
```

## 4. Autonomy Loop
1.  **Trigger**: User input (Text/Voice) or Scheduled Event.
2.  **Plan**: LLM generates a step-by-step plan.
3.  **Execute**: Loop through steps:
    *   Select Tool (MCP).
    *   Execute Tool.
    *   Observe Result.
    *   Self-Correct if needed.
4.  **Response**: Final answer or action confirmation to UI.

## 5. Windows Integration
- **Auto-Start**: Registry key `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
- **System Tray**: Minimize to tray, background listening.
- **Global Hotkey**: `Ctrl+Alt+A` to toggle visibility.
