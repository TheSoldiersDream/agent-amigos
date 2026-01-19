# Agent Amigos 2025 - Quick Reference Card

## 🚀 Quick Start (5 Minutes)

### 1️⃣ Install

```bash
cd backend
pip install -r requirements.txt
```

### 2️⃣ Initialize

```bash
python setup_enhancement.py
```

### 3️⃣ Set Up Models (Choose One)

```bash
# Option A: Ollama (Recommended)
ollama pull qwen:70b mistral
ollama serve

# Option B: Cloud APIs
export OPENAI_API_KEY="sk-..."
export GROQ_API_KEY="..."
```

### 4️⃣ Start

```bash
# Terminal 1
python backend/agent_init.py

# Terminal 2
cd frontend && npm run dev
```

### 5️⃣ Open

```
http://localhost:5173
```

---

## 📚 File Structure

```
backend/core/
├── model_manager.py          # 15+ models, routing, stats
├── learning_engine.py        # Memory, skills, patterns
├── adaptive_agent.py         # Multi-strategy reasoning
└── api_endpoints.py          # 17 REST endpoints

frontend/src/components/
├── ModelDashboard.jsx        # Model management UI
├── ModelDashboard.css        # Model styling
├── AgentCapabilities.jsx     # Agent capabilities UI
└── AgentCapabilities.css     # Agent styling

docs/
├── OPENSOURC_AI_ENHANCEMENT.md    # Latest models
├── IMPLEMENTATION_GUIDE.md         # Setup guide
├── ARCHITECTURE_2025.md            # System design
├── ENHANCEMENT_COMPLETE.md         # Summary
└── QUICK_REFERENCE.md             # This file
```

---

## 🎯 Available Models (15+)

### Local (Ollama)

| Model             | Best For          | Speed     |
| ----------------- | ----------------- | --------- |
| **Qwen 2.5 70B**  | Reasoning, Code   | Medium    |
| **Llama 3.3 70B** | General, Balanced | Medium    |
| **Mistral Large** | Fast, Coding      | Fast      |
| **Phi 3.5**       | Lightweight, Edge | Very Fast |

### Cloud APIs

| Provider       | Model       | Best For    |
| -------------- | ----------- | ----------- |
| **OpenAI**     | GPT-4o      | Multimodal  |
| **Groq**       | Llama 3.3   | Ultra-fast  |
| **DeepSeek**   | DeepSeek-V3 | Reasoning   |
| **OpenRouter** | Multiple    | Flexibility |

---

## 💻 API Quick Commands

### Models

```bash
# List all models
curl http://localhost:8000/agent/models/available

# Get best model for task
curl "http://localhost:8000/agent/models/best-for-task?task_type=code"

# Get model stats
curl http://localhost:8000/agent/models/stats
```

### Agents

```bash
# List all agents
curl http://localhost:8000/agent/capabilities

# Get agent details
curl http://localhost:8000/agent/capabilities/CodeAgent

# Execute task
curl -X POST http://localhost:8000/agent/agent/CodeAgent/execute \
  -H "Content-Type: application/json" \
  -d '{"task":"explain recursion"}'
```

### Learning

```bash
# Get learning stats
curl http://localhost:8000/agent/learning/stats

# Submit feedback
curl -X POST http://localhost:8000/agent/learning/feedback \
  -H "Content-Type: application/json" \
  -d '{"interaction_id":"123","feedback":"Great!","rating":5}'
```

### Health

```bash
curl http://localhost:8000/agent/models/health
curl http://localhost:8000/agent/agents/health
```

---

## 🔑 Environment Variables

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4o"

# Groq
export GROQ_API_KEY="..."
export GROQ_MODEL="llama-3.3-70b-versatile"

# Grok (X.AI)
export GROK_API_KEY="..."
export XAI_API_KEY="..."

# DeepSeek
export DEEPSEEK_API_KEY="..."

# OpenRouter
export OPENROUTER_API_KEY="..."

# Local Ollama
export OLLAMA_BASE_URL="http://localhost:11434"
```

---

## 🧪 Test Features

### Test Model Selection

```python
from backend.core.model_manager import get_model_manager

manager = get_model_manager()
model = manager.get_best_model_for_task("code_generation")
print(f"Selected: {model.name}")
```

### Test Learning Engine

```python
from backend.core.learning_engine import get_learning_engine

engine = get_learning_engine()
engine.store_interaction(
    agent_name="TestAgent",
    task="test task",
    input_text="input",
    output_text="output",
    success=True,
    model_used="qwen:70b",
    duration_ms=1000,
    tools_used=["test"]
)
```

### Test Agent Execution

```python
from backend.core.adaptive_agent import get_or_create_agent

agent = get_or_create_agent("TestAgent")
status = agent.get_agent_status()
print(f"Agent stats: {status}")
```

---

## 📊 Key Metrics to Track

### Per Model

- ✅ Success rate (%)
- ✅ Avg response time (ms)
- ✅ Total interactions
- ✅ Cost (per 1K tokens)

### Per Agent

- ✅ Total interactions
- ✅ Success rate (%)
- ✅ Skills (proficiency %)
- ✅ Most used tools

### Global

- ✅ Best models by task
- ✅ Model rankings
- ✅ Learning efficiency

---

## 🎮 UI Features

### Model Dashboard

- [ ] Sort by success rate
- [ ] Filter by provider
- [ ] View performance metrics
- [ ] See cost analysis
- [ ] Select preferred model

### Agent Capabilities

- [ ] View all agents
- [ ] Check skill levels
- [ ] See success patterns
- [ ] Monitor performance
- [ ] Track learning progress

---

## 🔒 Security Checklist

- ✅ Use environment variables for keys
- ✅ Run models locally with Ollama
- ✅ Enable audit logging
- ✅ Limit agent scopes
- ✅ Rate limit API calls
- ✅ Validate all inputs
- ✅ Use HTTPS in production

---

## 🐛 Troubleshooting

### Issue: Models Not Loading

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Or check API keys
echo $OPENAI_API_KEY
```

### Issue: Memory Issues

```bash
# Use lighter model
# Phi 3.5 (3.8B) instead of Llama (70B)
# or use 8-bit quantization
```

### Issue: ChromaDB Error

```python
# Learning engine auto-falls back to in-memory
# No action needed
```

### Issue: API Rate Limit

```python
# Built-in exponential backoff handles this
# Retries up to 3 times automatically
```

---

## 📖 Documentation Map

| Document                         | Purpose                | Length    |
| -------------------------------- | ---------------------- | --------- |
| **OPENSOURCE_AI_ENHANCEMENT.md** | Latest models research | 200 lines |
| **IMPLEMENTATION_GUIDE.md**      | Setup and deployment   | 400 lines |
| **ARCHITECTURE_2025.md**         | System design          | 300 lines |
| **ENHANCEMENT_COMPLETE.md**      | Project summary        | 500 lines |
| **QUICK_REFERENCE.md**           | This cheat sheet       | 300 lines |

---

## 🎯 Learning System

### How It Works

1. Task executed
2. Result stored in memory
3. Patterns extracted
4. Skills updated
5. Next task uses learned patterns

### User Feedback Loop

```
Task → Execute → User Rates → Learn → Next Task Better
```

---

## 🚀 Next Steps

1. ✅ Install dependencies
2. ✅ Initialize systems
3. ✅ Set up models
4. ✅ Start backend/frontend
5. ✅ Open browser
6. ✅ Select preferred model
7. ✅ Execute tasks
8. ✅ Give feedback
9. ✅ Watch agent improve

---

## 💡 Pro Tips

1. **Start with Qwen 2.5** - Best all-around performance
2. **Use Groq for speed** - Ultra-fast local inference
3. **Enable learning** - Agents improve over time
4. **Monitor dashboard** - Real-time metrics
5. **Try feedback** - Helps agents learn faster
6. **Check patterns** - See what's working
7. **Profile models** - Find best for your tasks

---

## 📞 Key Classes

```python
# Model Management
from backend.core.model_manager import get_model_manager
manager = get_model_manager()

# Learning System
from backend.core.learning_engine import get_learning_engine
engine = get_learning_engine()

# Agent Execution
from backend.core.adaptive_agent import get_or_create_agent
agent = get_or_create_agent("MyAgent")

# API Routes
from backend.core.api_endpoints import router
app.include_router(router)
```

---

## ✨ Feature Highlights

✅ **15+ Models** - Local and cloud  
✅ **Self-Learning** - Improves over time  
✅ **Multi-Strategy** - Different reasoning approaches  
✅ **Real-Time Monitoring** - Live dashboards  
✅ **User Preferences** - Learns what you like  
✅ **Skill Tracking** - See agent development  
✅ **Pattern Learning** - Extract best practices  
✅ **Auto-Selection** - Best model for task

---

## 🎓 Learning Levels

| Level      | Range  | Status      |
| ---------- | ------ | ----------- |
| Expert     | 90%+   | 🟢 Ready    |
| Proficient | 70-89% | 🟡 Good     |
| Learning   | 50-69% | 🟠 Training |
| Developing | <50%   | 🔴 New      |

---

## 📱 Responsive Design

- ✅ Desktop (1920px+)
- ✅ Tablet (768px-1024px)
- ✅ Mobile (320px-767px)
- ✅ Dark theme
- ✅ Touch-friendly

---

## 🔄 Update Frequency

| Component          | Refresh Rate |
| ------------------ | ------------ |
| Model Dashboard    | 5 seconds    |
| Agent Capabilities | 10 seconds   |
| Statistics         | 30 seconds   |
| Learning Stats     | On demand    |

---

## 📦 Dependencies

### Backend (25 packages)

- fastapi, uvicorn, pydantic
- ollama, chromadb, llama-index
- instructor, autogen, crewai
- requests, aiohttp, playwright

### Frontend (1 tool)

- React 18, Axios, CSS3

---

**Version**: 2.0 (2025)  
**Status**: ✅ Production Ready  
**Updated**: December 26, 2025

---

**Need help?** Check the documentation folder or run `python setup_enhancement.py --help`
