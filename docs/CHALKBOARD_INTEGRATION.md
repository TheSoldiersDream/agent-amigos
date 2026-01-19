# 🧠🎨 Agent Amigos Chalk Board - Integration Guide

## Quick Start

### 1. Frontend Integration (App.jsx)

Add these imports to the top of your `App.jsx`:

```jsx
import { useState } from "react";
import ChalkBoardPanel from "./components/ChalkBoard";
```

### 2. Add State Variable

In your App component, add:

```jsx
const [chalkBoardOpen, setChalkBoardOpen] = useState(false);
```

### 3. Add Toggle Button to Your Tools Menu

In your "🛠️ Tools" dropdown menu, add:

```jsx
<button
  className="dropdown-item"
  onClick={() => setChalkBoardOpen(!chalkBoardOpen)}
>
  🎨 Chalk Board
</button>
```

### 4. Render the ChalkBoard Panel

Add this at the end of your App component's return, just before the closing fragment/div:

```jsx
{
  chalkBoardOpen && (
    <ChalkBoardPanel
      onClose={() => setChalkBoardOpen(false)}
      onAgentCommand={(cmd) => {
        // Optional: Send commands to your agent
        console.log("ChalkBoard command:", cmd);
      }}
    />
  );
}
```

---

## Backend Integration (agent_init.py or main.py)

### 1. Import the Router

```python
from chalkboard import chalkboard_router
```

### 2. Include the Router

```python
app.include_router(chalkboard_router, prefix="/chalkboard", tags=["chalkboard"])
```

### 3. Optional: Register MCP Tools

If you have an MCP server setup:

```python
from chalkboard import register_mcp_tools, chalkboard_controller

# Register ChalkBoard tools with your MCP server
register_mcp_tools(mcp_server)

# Or manually get tool definitions
tools = chalkboard_controller.get_mcp_tools()
```

---

## Full App.jsx Example (if starting fresh)

```jsx
import React, { useState, useRef, useEffect } from "react";
import ChalkBoardPanel from "./components/ChalkBoard";
import "./App.css";

function App() {
  // ... your existing state ...
  const [chalkBoardOpen, setChalkBoardOpen] = useState(false);
  const [toolsMenuOpen, setToolsMenuOpen] = useState(false);

  // Handle ChalkBoard agent commands
  const handleChalkBoardCommand = (command) => {
    console.log("ChalkBoard agent command:", command);
    // Integrate with your agent system here
  };

  return (
    <div className="app-container">
      {/* Header with Tools Menu */}
      <header className="app-header">
        <h1>🤖 Agent Amigos</h1>

        <div className="tools-menu-container">
          <button
            className="tools-menu-button"
            onClick={() => setToolsMenuOpen(!toolsMenuOpen)}
          >
            🛠️ Tools
          </button>

          {toolsMenuOpen && (
            <div className="tools-dropdown">
              <button onClick={() => setChalkBoardOpen(!chalkBoardOpen)}>
                🎨 Chalk Board {chalkBoardOpen ? "✓" : ""}
              </button>
              {/* ... other tools ... */}
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="app-main">{/* Your chat/agent interface */}</main>

      {/* ChalkBoard Panel (floating) */}
      {chalkBoardOpen && (
        <ChalkBoardPanel
          onClose={() => setChalkBoardOpen(false)}
          onAgentCommand={handleChalkBoardCommand}
        />
      )}
    </div>
  );
}

export default App;
```

---

## API Endpoints

The ChalkBoard backend provides these endpoints at `/chalkboard`:

### Sessions

- `POST /session` - Create new session
- `GET /session/{id}` - Get session
- `DELETE /session/{id}` - Delete session
- `PATCH /session/{id}` - Update session

### Objects

- `POST /session/{id}/objects` - Add object
- `GET /session/{id}/objects/{obj_id}` - Get object
- `PUT /session/{id}/objects/{obj_id}` - Update object
- `DELETE /session/{id}/objects/{obj_id}` - Delete object

### Layers

- `POST /session/{id}/layers` - Add layer
- `PUT /session/{id}/layers/{layer_id}` - Update layer
- `DELETE /session/{id}/layers/{layer_id}` - Delete layer

### History

- `POST /session/{id}/undo` - Undo
- `POST /session/{id}/redo` - Redo
- `GET /session/{id}/history` - Get history

### Agent Integration

- `POST /agent/command` - Execute agent draw command
- `GET /agent/queue` - Get pending commands
- `GET /agent/pending/{id}` - Get pending commands for session

### Export

- `POST /export` - Export canvas (PNG, SVG, PDF, DXF, JSON)

### Templates

- `POST /templates/floor-plan` - Generate floor plan
- `POST /templates/flowchart` - Generate flowchart

---

## ChalkBoard Modes

| Mode    | Icon | Purpose                           |
| ------- | ---- | --------------------------------- |
| SKETCH  | ✏️   | Freehand drawing, artistic work   |
| DIAGRAM | 📊   | Flowcharts, mind maps, org charts |
| CAD     | 📐   | Floor plans, technical drawings   |
| MEDIA   | 🖼️   | Images, videos, media placement   |
| TEXT    | 📝   | Poetry, stories, text art         |

---

## Drawing Tools

| Tool      | Description             |
| --------- | ----------------------- |
| SELECT    | Select and move objects |
| PEN       | Freehand thin line      |
| BRUSH     | Freehand thick brush    |
| ERASER    | Erase objects           |
| LINE      | Straight line           |
| RECTANGLE | Rectangle shape         |
| ELLIPSE   | Circle/ellipse          |
| ARROW     | Arrow connector         |
| TEXT      | Text label              |
| IMAGE     | Insert image            |
| WALL      | CAD wall (thick line)   |
| DOOR      | CAD door with swing     |
| WINDOW    | CAD window              |
| DIMENSION | CAD dimension line      |

---

## Agent Command Examples

### Draw a Floor Plan

```javascript
await fetch("/chalkboard/agent/command", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    session_id: "my-session",
    command_type: "floor_plan",
    parameters: {
      rooms: [
        { name: "Living Room", width: 20, height: 15, x: 0, y: 0 },
        { name: "Kitchen", width: 12, height: 12, x: 20, y: 0 },
        { name: "Bedroom", width: 14, height: 12, x: 0, y: 15 },
      ],
    },
    thought: "Creating a 3-room floor plan",
  }),
});
```

### Generate a Flowchart

```javascript
await fetch("/chalkboard/agent/command", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    session_id: "my-session",
    command_type: "flowchart",
    parameters: {
      nodes: [
        { id: "start", label: "Start", type: "start" },
        { id: "process1", label: "Process Data", type: "process" },
        { id: "decision", label: "Valid?", type: "decision" },
        { id: "end", label: "End", type: "end" },
      ],
      connections: [
        { from_id: "start", to_id: "process1" },
        { from_id: "process1", to_id: "decision" },
        { from_id: "decision", to_id: "end", label: "Yes" },
      ],
    },
    thought: "Creating validation flowchart",
  }),
});
```

### Render a Poem

```javascript
await fetch("/chalkboard/agent/command", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    session_id: "my-session",
    command_type: "poem",
    parameters: {
      title: "Digital Dreams",
      lines: [
        "In silicon valleys deep,",
        "Where algorithms softly creep,",
        "A canvas waits for thoughts to bloom,",
        "And chase away the digital gloom.",
      ],
      style: "classic",
    },
    thought: "Rendering poem with classic typography",
  }),
});
```

---

## Keyboard Shortcuts

| Shortcut | Action          |
| -------- | --------------- |
| Ctrl+Z   | Undo            |
| Ctrl+Y   | Redo            |
| V        | Select tool     |
| P        | Pen tool        |
| B        | Brush tool      |
| E        | Eraser          |
| L        | Line tool       |
| R        | Rectangle       |
| O        | Ellipse         |
| A        | Arrow           |
| T        | Text            |
| Delete   | Delete selected |

---

## CSS Styling

The ChalkBoard uses these CSS custom properties (add to your global CSS):

```css
:root {
  --chalkboard-bg: #1e1e2e;
  --chalkboard-surface: #2d2d3d;
  --chalkboard-border: #3d3d5c;
  --chalkboard-text: #e0e0e0;
  --chalkboard-accent: #7c3aed;

  --mode-sketch: #ec4899;
  --mode-diagram: #a855f7;
  --mode-cad: #06b6d4;
  --mode-media: #f59e0b;
  --mode-text: #22c55e;
}
```

---

## Future Enhancements

- [ ] Voice commands integration
- [ ] Real-time collaboration (WebSocket)
- [ ] AR/VR canvas projection
- [ ] Multi-agent collaborative drawing
- [ ] AI-assisted shape recognition
- [ ] Smart snapping and alignment
- [ ] Template library expansion
- [ ] Animation timeline

---

**Happy Drawing! 🎨✨**
