# 🎮 Agent Amigos Game Trainer

**Full-featured memory trainer for single-player games**

## Quick Start

1. **Launch Agent Amigos**

   ```powershell
   cd AgentAmigos
   # Start backend
   .\.venv\Scripts\python.exe backend/agent_init.py
   # In another terminal, start frontend
   cd frontend
   npm run dev
   ```

2. **Open Trainer Console**
   - Click the Game Trainer icon in the UI
   - Or press the hotkey (if configured)

3. **Create Your First Cheat**
   - Enter game name (e.g., "Call to Arms - Gates of Hell")
   - Enable "Advanced Memory Tools"
   - Click "Start Session"
   - Go to "Memory Tools" → Attach to game process
   - Scan for a value (health, ammo, etc.)
   - Click "+ Cheat" to save the address
   - Go to "Cheats" tab → Activate your cheat

## Features

### ⚡ Cheat System

- Save unlimited cheats per game
- Toggle activation with one click
- Assign hotkeys (F1-F12)
- Auto-freeze values

### 🔍 Memory Scanner

- Find any int/float value
- Increment/decrement controls
- Write custom values
- Freeze/unfreeze memory

### 🎯 Pointer Scanner

- Find static pointers (multi-level)
- Permanent addresses
- Auto-detect offsets

### 📝 Pattern Scanner (AOB)

- Byte pattern matching
- Wildcard support (`??`)
- Code signature search

## Example: God Mode

1. **Scan for health**
   - Current health: 100 → Scan
   - Take damage: 75 → Next Scan
   - Repeat until 1-5 addresses

2. **Create cheat**
   - Name: "God Mode"
   - Value: 9999
   - Type: Integer
   - Hotkey: F1

3. **Activate**
   - Go to Cheats tab
   - Click "Activate"
   - Health locked at 9999

## Tabs Overview

### Session

- Declare game and platform
- Start AI trainer session
- Configure memory tools

### Analysis

- AI-powered gameplay analysis
- Performance recommendations
- Strategy suggestions

### Cheats ⭐

- **Cheat list** with activation toggles
- **Add/Edit/Delete** cheats
- **Pointer scanner** for permanent addresses
- **Pattern scanner** for code signatures
- **Save/Load** cheat tables

### Memory Tools

- **Process attachment**
- **Memory scanner**
- **Value freezing**
- **Read/Write memory**

### Coach

- AI gameplay coaching
- Training plans
- Skill improvement tips

## Supported Games

Works with any single-player PC game:

- RTS (Age of Empires, StarCraft, Call to Arms)
- RPG (Elden Ring, Skyrim, Witcher)
- FPS (Single-player campaigns)
- Simulators
- Indie games

**Note**: Designed for single-player only. Does not support online/multiplayer games.

## API Reference

Full documentation: [GAME_TRAINER_DOCUMENTATION.md](GAME_TRAINER_DOCUMENTATION.md)

## Tech Stack

- **Frontend**: React 18, Axios
- **Backend**: Python 3.11, FastAPI
- **Memory**: Windows API (ReadProcessMemory, WriteProcessMemory)
- **Storage**: JSON-based cheat tables

## File Locations

- **Cheat Tables**: `trainer_data/cheat_tables/{game_name}.json`
- **Profiles**: `trainer_data/profiles/`
- **Logs**: `backend/logs/trainer.log`

## Common Patterns

### Find Health

1. Note current HP
2. Scan for value
3. Take damage
4. Next scan with new HP
5. Repeat 2-3 times

### Find Money

1. Note current cash
2. Scan for value
3. Buy/sell item
4. Next scan with new amount
5. Repeat until found

### Find Ammo

1. Note current ammo count
2. Scan for value
3. Fire weapon
4. Next scan with new count
5. Freeze at 999

## Troubleshooting

**"No process attached"**

- Make sure game is running
- Search for process by name
- Try administrator privileges

**"Scan found 0 addresses"**

- Check value type (int vs float)
- Try searching for exact value
- Game might use unusual data types

**"Failed to write memory"**

- Run as administrator
- Check if game has anti-cheat
- Verify address is correct

## Safety

✅ **Safe for single-player games**  
✅ **No online game support**  
✅ **Educational purposes**  
✅ **Developer testing tools**  
❌ **Do not use for multiplayer**  
❌ **No anti-cheat bypass**

## Credits

**Agent Amigos** by Darrell Buttigieg  
Inspired by: Cheat Engine, ArtMoney, GameConqueror

#darrellbuttigieg #thesoldiersdream

---

**License**: For single-player game testing and development only.
