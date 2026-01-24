# Game Trainer - Feature Complete Documentation

## Overview

Full-featured game trainer with all standard trainer capabilities for single-player games.

## ✨ Core Features

### 1. Cheat Management System

- **Save/Load Cheat Tables**: Persistent storage per game
- **Cheat Activation**: Toggle cheats on/off with one click
- **Cheat Descriptions**: Label each cheat with name and description
- **Value Freezing**: Lock memory values to prevent changes
- **Hotkey Support**: Assign keyboard shortcuts for quick activation (UI ready, backend integration pending)

### 2. Memory Scanner

- **Value Scanning**: Find int/float values in game memory
- **First & Next Scan**: Narrow down addresses
- **Quick Controls**:
  - **+/-**: Increment/decrement values
  - **Write**: Manually set value
  - **Freeze**: Lock value at current state
  - **+ Cheat**: Save address to cheat list

### 3. Pointer Scanner

- **Multi-Level Scanning**: Find static pointers (up to 5 levels deep)
- **Offset Detection**: Auto-discover pointer paths
- **Permanent Addresses**: Find base+offset combos that survive restarts

### 4. Pattern Scanner (AOB)

- **Byte Pattern Matching**: Find code signatures (e.g., `48 8B ?? 24 ?? FF`)
- **Wildcard Support**: Use `??` for unknown bytes
- **Code Injection Ready**: Locate injection points for advanced mods

### 5. Process Management

- **Auto-Attach**: Select game process from list
- **Process Search**: Filter processes by name
- **Memory Stats**: View process memory usage

## 🎮 Usage Workflow

### Quick Start - God Mode Example

1. **Start Session**
   - Enter game name: "Call to Arms - Gates of Hell"
   - Platform: PC
   - Enable Advanced Memory Tools

2. **Attach to Game**
   - Go to "Memory Tools" tab
   - Search for game process (e.g., "CallToArms")
   - Click to attach

3. **Find Health Address**
   - Note your current health (e.g., 100)
   - Enter `100` in scanner, select `int`, click Scan
   - Take damage in game (e.g., now 75)
   - Enter `75`, click Next Scan
   - Repeat until 1-5 addresses remain

4. **Create God Mode Cheat**
   - Click "+ Cheat" button on found address
   - Name: "God Mode"
   - Description: "Infinite Health"
   - Value: 9999
   - Hotkey: F1 (optional)
   - Click Add

5. **Activate Cheat**
   - Go to "Cheats" tab
   - Click "Activate" on God Mode cheat
   - Health will be frozen at 9999

### Advanced - Pointer Scanning

1. Find dynamic address for a value (e.g., ammo at `0x1A2B3C4D`)
2. Go to Cheats tab → Advanced Scanners → Pointer Scanner
3. Enter target address: `0x1A2B3C4D`
4. Click "Scan Pointers"
5. Results show permanent paths like `[[0x00400000] + 0x1C] + 0x20`
6. Use base address for cheats that survive game restarts

### Pattern Scanning

1. Use debugging tools to find code signature
2. Example: `48 8B 05 ?? ?? ?? ?? 48 89 44 24 ??`
3. Enter pattern in Pattern Scanner
4. Click "Scan Pattern"
5. Results show all matching code locations
6. Use for code injection or function hooking

## 📊 Cheat Table Format

Saved in `trainer_data/cheat_tables/{game_name}.json`:

```json
{
  "game_name": "Call to Arms - Gates of Hell: Ostfront",
  "cheats": [
    {
      "name": "Infinite Health",
      "description": "God mode - prevents health decrease",
      "address": 445350477,
      "pointer_path": null,
      "value_type": "int",
      "frozen_value": 9999,
      "hotkey": "F1",
      "enabled": true
    },
    {
      "name": "Unlimited Ammo",
      "description": "Never run out of ammunition",
      "address": 445350500,
      "value_type": "int",
      "frozen_value": 999,
      "hotkey": "F2",
      "enabled": false
    }
  ]
}
```

## 🔧 Backend API Endpoints

### Cheat Management

- `POST /trainer/cheats/table/load?game_name={name}` - Load cheat table
- `POST /trainer/cheats/table/save` - Save cheat table
- `GET /trainer/cheats/table/list` - List all saved tables
- `POST /trainer/cheats/add` - Add new cheat
- `POST /trainer/cheats/update` - Update existing cheat
- `POST /trainer/cheats/remove?name={name}` - Delete cheat
- `POST /trainer/cheats/toggle?name={name}&enabled={bool}` - Activate/deactivate

### Scanning

- `POST /trainer/scan/pointer` - Scan for pointers

  ```json
  {
    "target_address": 445350477,
    "max_offset": 4096,
    "max_depth": 5
  }
  ```

- `POST /trainer/scan/pattern` - Scan for byte patterns
  ```json
  {
    "pattern": "48 8B ?? 24 ?? FF",
    "first_only": false
  }
  ```

### Memory Operations (existing)

- `POST /trainer/attach/pid` - Attach to process
- `POST /trainer/scan/value` - Scan for value
- `POST /trainer/scan/next` - Next scan
- `POST /trainer/write` - Write memory
- `POST /trainer/freeze` - Freeze value
- `POST /trainer/unfreeze` - Unfreeze value

## 🎯 Standard Trainer Features Implemented

✅ **Memory Scanning** - Find int/float values  
✅ **Pointer Scanning** - Find static addresses  
✅ **Pattern Scanning (AOB)** - Find code signatures  
✅ **Value Freezing** - Lock memory values  
✅ **Cheat Tables** - Save/load cheat configurations  
✅ **Cheat Activation** - Toggle cheats on/off  
✅ **Value Controls** - Increment/decrement buttons  
✅ **Address Labeling** - Name and describe cheats  
✅ **Process Attachment** - Auto-attach to games  
⏳ **Hotkey System** - UI ready, global hotkeys pending Windows integration

## 🔐 Security & Ethics

- **Single-Player Focus**: Designed for single-player games only
- **No Online Bypass**: Does not support online/multiplayer games
- **Explicit Consent**: Memory tools disabled by default
- **Developer Tools**: Intended for game testing, modding, and development
- **Educational**: Learn memory manipulation and reverse engineering

## 🚀 Future Enhancements

1. **Global Hotkey System**: Windows keyboard hooks for F1-F12 activation
2. **Code Injection**: Assembly code injection for advanced mods
3. **Lua Scripting**: Custom cheat scripts
4. **Trainer Templates**: Pre-built cheats for popular games
5. **Memory Viewer**: Hex editor for manual inspection
6. **Disassembler**: View game assembly code
7. **Debugger Integration**: Step through game code

## 📝 Example Use Cases

### Game Development

- Test god mode without implementing it
- Spawn items for UI testing
- Skip levels for regression testing
- Modify game state for debugging

### Modding

- Find data structures for mod development
- Locate function addresses for hooks
- Reverse engineer game mechanics
- Create quality-of-life improvements

### Speedrunning Practice

- Practice difficult sections with safety nets
- Test routing with infinite resources
- Learn mechanics with slowed time
- Validate glitch setups

## 🛠️ Technical Architecture

### Frontend (React)

- **GameTrainerConsole.jsx**: Main UI component
- **Tabs**: Session, Analysis, Cheats, Memory Tools, Coach
- **State Management**: React hooks
- **API Client**: Axios for backend communication

### Backend (Python/FastAPI)

- **main.py**: API router with 20+ endpoints
- **cheat_manager.py**: Cheat table persistence
- **pointer_scanner.py**: Multi-level pointer scanning
- **pattern_scanner.py**: AOB pattern matching
- **memory_scanner.py**: Value search engine
- **memory_writer.py**: Read/write/freeze operations

### Storage

- **Cheat Tables**: JSON files in `trainer_data/cheat_tables/`
- **Profiles**: Game configurations in `trainer_data/profiles/`

## 🎓 Learning Resources

### Memory Hacking Basics

1. **Values**: Health, ammo, money are usually int/float
2. **Addresses**: Locations in memory (hex: 0x1A2B3C4D)
3. **Pointers**: Addresses that point to other addresses
4. **AOB**: Array of Bytes - unique code signatures

### Scanning Strategy

1. **First Scan**: Find all addresses with target value
2. **Change Value**: Modify in-game (take damage, spend money)
3. **Next Scan**: Filter to changed addresses
4. **Repeat**: Until 1-10 addresses remain
5. **Test**: Modify each to find correct one

### Pointer Path Example

```
Health: 0x1A2B3C4D (dynamic - changes every restart)
Pointer: [[0x00400000] + 0x1C] + 0x20 (static - always works)
```

## 🏆 Credits

Built by **Agent Amigos** (Darrell Buttigieg)  
Standard trainer features inspired by Cheat Engine, ArtMoney, and classic game trainers.

---

**#darrellbuttigieg #thesoldiersdream**
