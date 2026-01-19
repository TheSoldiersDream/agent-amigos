# System Controls & UI Cleanup (Jan 2025)

## 1. Amigos GUI Controls (Hidden by Default)

The floating "Amigos GUI Controls" panel (Model Matrix, Capabilities, etc.) has been hidden to declutter the dashboard.

- **Toggle Hotkey**: `Ctrl + Alt + S`
- **Features**:
  - **CONTROLS Tab**: Toggle Model Matrix, Capabilities, Agent Team, and Autonomy Panel.
  - **SETTINGS Tab**: Configure Backend API URL, Lock/Unlock Layout, Save Layout, and Reset API defaults.
  - **Draggable**: You can still move the panel by dragging the `≡` handle.
  - **Minimized Mode**: Pack the panel into a tiny icon using the `−` button.

## 2. Integrated Settings

The **Settings** icon in the left sidebar now directly toggles the System Controls console and switches to the **SETTINGS** tab for quick access to API configurations.

## 3. Commercial Intelligence & Scraping

- **Autonomous Browsing**: Implemented strictly validated scraping pipelines for commercial data extraction.
- **Market Analysis**: Real-time monitoring of revenue streams and subscriber growth metrics.
- **Data Integrity**: Enforced strict JSON validation on all external data ingestion to prevent hallucination.

## 4. Performance & Security

- **Memory Purged**: Cleared `conversations.json` to ensure a fresh session.
- **Cache Integrity**: Reduced the likelihood of data corruption by enforcing strict JSON validation on ingestion.
