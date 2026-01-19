# OpenWork Integration for Agent Amigos

OpenWork has been successfully integrated into Agent Amigos! This provides a powerful "Claude Work" style workflow system for knowledge workers, powered by OpenCode under the hood.

## What is OpenWork?

OpenWork is an extensible, open-source agentic workflow system that:

- Runs OpenCode locally on your computer OR connects to remote OpenCode servers
- Provides a clean, guided workflow interface
- Tracks task progress with live execution plans
- Manages permissions for privileged operations
- Supports reusable templates and installable skills

## Features Integrated

### 1. **Backend Integration** (`backend/openwork_integration.py`)

- `OpenWorkManager` - Central management for sessions and workspaces
- `OpenWorkSession` - Track individual workflow sessions with todos, messages, and permissions
- OpenCode server lifecycle management (start/stop)
- Workspace and skill management
- Session persistence and history

### 2. **API Endpoints** (`backend/agent_init.py`)

All endpoints are prefixed with `/openwork`:

#### Server Management

- `GET /openwork/status` - Check if OpenCode server is running
- `POST /openwork/server/start` - Start OpenCode server for a workspace
- `POST /openwork/server/stop` - Stop the OpenCode server

#### Session Management

- `POST /openwork/sessions` - Create a new workflow session
- `GET /openwork/sessions` - List all active sessions
- `GET /openwork/sessions/{id}` - Get session details
- `POST /openwork/sessions/{id}/close` - Close a session
- `DELETE /openwork/sessions/{id}` - Delete a session

#### Task & Communication

- `POST /openwork/sessions/{id}/todos` - Add a todo to session
- `PUT /openwork/sessions/{id}/todos/{todo_id}` - Update a todo
- `POST /openwork/sessions/{id}/messages` - Add a message to session

#### Permissions

- `POST /openwork/sessions/{id}/permissions` - Request a permission
- `POST /openwork/sessions/{id}/permissions/{perm_id}/respond` - Respond to permission request

#### Workspace Management

- `GET /openwork/workspaces` - List available workspaces
- `GET /openwork/workspaces/{path}/skills` - Get installed skills for a workspace

### 3. **Frontend Console** (`frontend/src/components/OpenWorkConsole.jsx`)

A beautiful React interface featuring:

- Live server status monitoring
- Workspace selection dropdown
- Session creation and management
- Real-time todo tracking
- Message history display
- Auto-refresh every 5 seconds

### 4. **Navigation Integration**

- Added to Sidebar with 🔧 icon
- Detachable window support
- Accessible via "OpenWork" button in left sidebar

## How to Use

### Prerequisites

1. Install OpenCode CLI: https://github.com/different-ai/opencode
2. Ensure OpenCode is available in your PATH
3. Make sure Agent Amigos backend is running on port 65252

### Getting Started

1. **Start Agent Amigos** (if not already running):

   ```bash
   launch amigos
   ```

2. **Open OpenWork Console**:
   - Click the 🔧 **OpenWork** button in the left sidebar
   - Or detach it to a standalone window

3. **Select a Workspace**:
   - Choose from the workspace dropdown
   - The current Agent Amigos workspace is preselected

4. **Start the OpenCode Server** (if needed):
   - Click "Start Server" button
   - Wait for the server to initialize
   - Status will change to "● Running"

5. **Create a Session**:
   - Enter a task description in the "New Session" textarea
   - Click "Create Session"
   - The session will appear in the sessions list

6. **Monitor Progress**:
   - Click on a session to view details
   - Watch todos update in real-time
   - Review messages and permissions
   - Close sessions when complete

## Architecture

```
┌─────────────────────────────────────────┐
│        Agent Amigos Frontend            │
│    (OpenWorkConsole Component)          │
└──────────────┬──────────────────────────┘
               │ HTTP/REST
               ▼
┌─────────────────────────────────────────┐
│      Agent Amigos Backend (FastAPI)     │
│     /openwork/* API endpoints           │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│     OpenWorkManager                     │
│  (Session & Workspace Management)       │
└──────────────┬──────────────────────────┘
               │ Process Management
               ▼
┌─────────────────────────────────────────┐
│    OpenCode Server (Local Process)      │
│    Running in workspace directory       │
└─────────────────────────────────────────┘
```

## Files Modified/Created

### Created Files:

- `backend/openwork_integration.py` - Core integration logic
- `frontend/src/components/OpenWorkConsole.jsx` - React UI component
- `OPENWORK_INTEGRATION.md` - This documentation

### Modified Files:

- `backend/agent_init.py` - Added OpenWork API endpoints
- `frontend/src/App.jsx` - Added OpenWork import and routing
- `frontend/src/components/Sidebar.jsx` - Added OpenWork to navigation

## Configuration

No additional configuration needed! OpenWork will:

- Use the current Agent Amigos workspace by default
- Start OpenCode server on an available port (default: 8765)
- Store session data in memory (persists during backend runtime)

## Workflow Templates

Starter OpenWork workflow templates are available in:

- `templates/openwork/`

Included templates:

- `bugfix-triage.md`
- `feature-implementation.md`
- `integration-workflow.md`
- `research-synthesis.md`
- `qa-validation.md`

Use them as session prompts or copy sections into new OpenWork sessions to keep workflows consistent.

## Future Enhancements

Potential improvements for the integration:

1. **Persistent Session Storage** - Save sessions to disk
2. **SSE Streaming** - Real-time event streaming from OpenCode
3. **Skill Management UI** - Install/manage OpenCode skills from the UI
4. **Template UI/Selector** - Browse and apply templates from the console
5. **Multi-Workspace Support** - Switch between multiple workspaces
6. **Remote Server Connection** - Connect to remote OpenCode servers
7. **Advanced Permissions** - Rich permission request UI

## Troubleshooting

### OpenCode Not Found

**Problem**: "OpenCode CLI not found" error when starting server

**Solution**:

1. Install OpenCode: `npm install -g opencode-cli`
2. Or download from: [https://github.com/different-ai/opencode](https://github.com/different-ai/opencode)
3. Verify installation: `opencode --version`

### Server Won't Start

**Problem**: Server fails to start

**Solutions**:

- Check if port 8765 is already in use
- Verify workspace path is valid
- Check OpenCode installation: `opencode serve --help`

### Sessions Not Updating

**Problem**: Session list or details not refreshing

**Solutions**:

- The console auto-refreshes every 5 seconds
- Click "Refresh" manually if needed
- Check browser console for errors
- Verify backend is running on port 65252

## Learn More

- **OpenWork Project**: [https://github.com/different-ai/openwork](https://github.com/different-ai/openwork)
- **OpenCode Documentation**: [https://github.com/different-ai/opencode](https://github.com/different-ai/opencode)
- **Agent Amigos Architecture**: See `ARCHITECTURE_2025.md`

## Credits

- **OpenWork** by different-ai team
- **OpenCode** AI coding assistant
- **Integration** by Agent Amigos development team

---

**Status**: ✅ Fully Integrated & Ready to Use

The OpenWork integration brings professional agentic workflow capabilities to Agent Amigos, making it easier than ever to manage complex, multi-step AI-powered tasks!
