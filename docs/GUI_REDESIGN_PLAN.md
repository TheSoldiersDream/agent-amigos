# 🎨 Agent Amigos GUI Redesign Plan

## Problem Statement

The current layout has buttons that overlap and block console windows, creating a cluttered and hard-to-use interface.

---

## Current Issues

1. **Console buttons in header bar** compete for space with Tools dropdown
2. **Floating windows** overlap each other without clear z-index management
3. **No dedicated workspace area** - consoles float over the main chat
4. **Button bar takes horizontal space** needed by windows
5. **Hard to see which consoles are open** when multiple active

---

## 🚀 Proposed Solution: "Cockpit Layout"

### Layout Zones

```
┌─────────────────────────────────────────────────────────────────┐
│  🔒 HEADER BAR (48px) - Logo, Status, User Menu                │
├──────┬──────────────────────────────────────────────────┬──────┤
│      │                                                  │      │
│  S   │                                                  │  R   │
│  I   │                                                  │  I   │
│  D   │           MAIN WORKSPACE AREA                    │  G   │
│  E   │      (Chat, ChalkBoard, Active Console)          │  H   │
│  B   │                                                  │  T   │
│  A   │                                                  │      │
│  R   │                                                  │  P   │
│      │                                                  │  A   │
│ 48px │                                                  │  N   │
│      │                                                  │  E   │
│      │                                                  │  L   │
├──────┴──────────────────────────────────────────────────┴──────┤
│  📊 TASKBAR (40px) - Minimized windows, Quick Status           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. **Header Bar** (48px fixed top)

- Logo + App Name (left)
- Global search (center, optional)
- Status indicators (right)
  - Ollama status
  - Security status
  - User menu

### 2. **Left Sidebar** (48px collapsed, 200px expanded)

- **Tool Icons** (vertical):
  - 💬 Chat
  - 🎨 ChalkBoard
  - 🕷️ Scraper
  - 🌍 Web
  - 🗺️ Maps
  - 📊 Finance
  - 🎬 Media
  - 🎮 Game
  - 📁 Files
  - 📝 Post Creator
- Hover/click expands with labels
- Active tool highlighted
- Tooltips on hover

### 3. **Main Workspace** (flexible)

- **Single Active View** OR **Split View**
- Clean, unobstructed canvas
- Content fills available space
- Tabs at top for multiple open consoles

### 4. **Right Panel** (collapsible, 280px)

- **Context-aware sidebar**:
  - When Chat active → Agent thoughts, history
  - When ChalkBoard active → Layers panel
  - When Scraper active → Saved scrapers
  - When Finance active → Watchlist
- Can be hidden completely

### 5. **Bottom Taskbar** (40px)

- Minimized windows as icons
- Quick status: API connection, memory usage
- Notification area
- Voice toggle

---

## Implementation Phases

### Phase 1: Layout Shell

1. Create `AppShell.jsx` - main layout container
2. Create `Sidebar.jsx` - left navigation
3. Create `WorkspacePanel.jsx` - main content area
4. Create `Taskbar.jsx` - bottom bar

### Phase 2: Console Migration

1. Convert each console to fit new layout
2. Add "maximize", "minimize", "popout" buttons
3. Implement tabbed interface for multiple consoles

### Phase 3: Polish

1. Smooth transitions/animations
2. Keyboard shortcuts (Ctrl+1, Ctrl+2 for consoles)
3. Drag-to-reorder sidebar icons
4. Theme consistency

---

## New State Structure

```javascript
const [layout, setLayout] = useState({
  sidebar: {
    collapsed: false,
    activeItem: "chat",
  },
  workspace: {
    mode: "single", // 'single' | 'split' | 'tabbed'
    activeConsoles: ["chat"],
    tabs: [{ id: "chat", title: "Agent Chat" }],
  },
  rightPanel: {
    visible: true,
    width: 280,
  },
  taskbar: {
    minimized: [], // ['finance', 'scraper']
    notifications: [],
  },
});
```

---

## Component Specs

### Sidebar Button Component

```jsx
<SidebarButton
  icon="🎨"
  label="ChalkBoard"
  active={activeConsole === "chalkboard"}
  onClick={() => openConsole("chalkboard")}
  badge={3} // optional notification count
/>
```

### Workspace Panel Props

```jsx
<WorkspacePanel
  consoles={activeConsoles}
  mode={workspaceMode}
  onMinimize={(id) => minimizeConsole(id)}
  onMaximize={(id) => maximizeConsole(id)}
  onClose={(id) => closeConsole(id)}
  onTabChange={(id) => setActiveTab(id)}
/>
```

---

## Z-Index Hierarchy (Fixed)

```
1    - Main content
100  - Sidebar
200  - Taskbar
300  - Right panel
500  - Floating windows (when popped out)
800  - Modals
900  - Tooltips
1000 - Dropdowns/Menus
9999 - Critical alerts
```

---

## Keyboard Shortcuts

| Shortcut       | Action                  |
| -------------- | ----------------------- |
| `Ctrl+B`       | Toggle sidebar          |
| `Ctrl+1-9`     | Quick open console 1-9  |
| `Ctrl+\``      | Toggle ChalkBoard       |
| `Ctrl+Shift+M` | Minimize current        |
| `Esc`          | Close active modal/menu |
| `Ctrl+Tab`     | Cycle tabs              |

---

## Migration Steps

1. **Don't break existing code** - build new layout alongside current
2. **Feature flag** - `useNewLayout` toggle in settings
3. **Gradual migration** - one console at a time
4. **User testing** - get feedback before full switch

---

## CSS Framework

Using CSS Grid + Flexbox:

```css
.app-shell {
  display: grid;
  grid-template-areas:
    "header header header"
    "sidebar workspace rightpanel"
    "taskbar taskbar taskbar";
  grid-template-columns: auto 1fr auto;
  grid-template-rows: 48px 1fr 40px;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  grid-area: sidebar;
}
.workspace {
  grid-area: workspace;
}
.rightpanel {
  grid-area: rightpanel;
}
.header {
  grid-area: header;
}
.taskbar {
  grid-area: taskbar;
}
```

---

## Timeline Estimate

| Phase               | Effort    | Priority |
| ------------------- | --------- | -------- |
| Layout Shell        | 2-3 hours | High     |
| Sidebar             | 1-2 hours | High     |
| Workspace Panel     | 2-3 hours | High     |
| Taskbar             | 1 hour    | Medium   |
| Console Migration   | 3-4 hours | Medium   |
| Polish & Animations | 2 hours   | Low      |

**Total: ~12-15 hours**

---

## Alternative: Quick Fix (Less Work)

If full redesign is too much, a **quick fix**:

1. **Move console buttons to a collapsible left strip** (not in header)
2. **Add z-index manager** - bring clicked window to front
3. **Snap-to-edge** - windows snap to screen edges
4. **Auto-arrange** - button to tile all open windows

Quick fix: ~3-4 hours

---

## Recommendation

Start with **Quick Fix** to solve immediate problems, then implement full **Cockpit Layout** as a v2 update.

---

## Visual Reference

```
BEFORE (Current):
┌──────────────────────────────────────────┐
│ [Btn][Btn][Btn][Btn]    [Tools▼][🔒]    │ ← Crowded header
├──────────────────────────────────────────┤
│  ┌────────┐  ┌────────┐                  │
│  │Console1│  │Console2│ (overlapping)    │
│  │   ▓▓▓▓ │  └────────┘                  │
│  └────────┘                              │
│       ┌─────────────────────┐            │
│       │    CHAT WINDOW      │            │
│       └─────────────────────┘            │
└──────────────────────────────────────────┘

AFTER (Redesign):
┌──────────────────────────────────────────┐
│ Agent Amigos          [🔍]    [🔒][👤]  │ ← Clean header
├────┬─────────────────────────────┬───────┤
│ 💬 │  ┌─[Chat]─[Finance]─────┐   │Layers │
│ 🎨 │  │                      │   │───────│
│ 🕷️ │  │    Active Console    │   │ BG    │
│ 🌍 │  │    (Full Space)      │   │ FG    │
│ 📊 │  │                      │   │ CAD   │
│ 🎬 │  └──────────────────────┘   │       │
├────┴─────────────────────────────┴───────┤
│ [💬 Chat] [📊 Finance]     🟢 Connected │ ← Taskbar
└──────────────────────────────────────────┘
```

---

**Ready to implement?** Let me know if you want to proceed with:

- A) **Quick Fix** (3-4 hours)
- B) **Full Cockpit Layout** (12-15 hours)
- C) **Modified plan** (tell me your preferences)
