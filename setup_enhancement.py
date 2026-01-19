#!/usr/bin/env python
"""
Quick Start Script for Agent Amigos 2025 Enhancement
Initializes model manager, learning engine, and creates sample agents
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def initialize_systems():
    """Initialize all new systems"""
    
    logger.info("=" * 60)
    logger.info("Agent Amigos 2025 - Open-Source AI Enhancement")
    logger.info("=" * 60)
    
    # Import and initialize model manager
    logger.info("\n[1/4] Initializing Model Manager...")
    try:
        from backend.core.model_manager import get_model_manager
        manager = get_model_manager()
        models = manager.list_models()
        logger.info(f"✓ Model Manager initialized with {len(models)} models")
        logger.info(f"  - Local models: {len([m for m in models if m.local])}")
        logger.info(f"  - Remote models: {len([m for m in models if not m.local])}")
    except Exception as e:
        logger.error(f"✗ Model Manager initialization failed: {e}")
        return False
    
    # Initialize learning engine
    logger.info("\n[2/4] Initializing Learning Engine...")
    try:
        from backend.core.learning_engine import get_learning_engine
        engine = get_learning_engine()
        logger.info("✓ Learning Engine initialized")
        logger.info("  - Storage mode: ChromaDB" if engine.chroma_client else "  - Storage mode: In-memory")
    except Exception as e:
        logger.error(f"✗ Learning Engine initialization failed: {e}")
        return False
    
    # Create sample agents
    logger.info("\n[3/4] Creating Sample Agents...")
    try:
        from backend.core.adaptive_agent import get_or_create_agent
        
        agents_config = [
            ("GeneralAgent", "general"),
            ("CodeAgent", "coding"),
            ("ResearchAgent", "research"),
        ]
        
        for agent_name, agent_type in agents_config:
            agent = get_or_create_agent(agent_name, agent_type=agent_type)
            status = agent.get_agent_status()
            logger.info(f"✓ Created {agent_name} ({agent_type})")
        
        logger.info(f"  - Total agents: {len(agents_config)}")
    except Exception as e:
        logger.error(f"✗ Agent creation failed: {e}")
        return False
    
    # Print available models
    logger.info("\n[4/4] Available Models Summary")
    logger.info("-" * 60)
    
    providers = {}
    for model in models:
        if model.provider not in providers:
            providers[model.provider] = []
        providers[model.provider].append(model.name)
    
    for provider, model_names in sorted(providers.items()):
        logger.info(f"\n{provider.upper()}:")
        for name in model_names:
            logger.info(f"  • {name}")
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ Initialization Complete!")
    logger.info("=" * 60)
    
    logger.info("\n📋 Next Steps:")
    logger.info("1. Review available models above")
    logger.info("2. Set up your preferred LLM provider:")
    logger.info("   - Ollama: Install and run 'ollama serve'")
    logger.info("   - Cloud APIs: Set environment variables (OPENAI_API_KEY, etc.)")
    logger.info("3. Start the backend: python agent_init.py")
    logger.info("4. Add ModelDashboard and AgentCapabilities to App.jsx")
    logger.info("5. Start the frontend: npm run dev")
    logger.info("6. Open http://localhost:5173 in your browser")
    
    logger.info("\n📚 Documentation:")
    logger.info("- OPENSOURCE_AI_ENHANCEMENT.md: Latest OSS models guide")
    logger.info("- IMPLEMENTATION_GUIDE.md: Complete implementation steps")
    
    return True


def print_model_details():
    """Print detailed model information"""
    from backend.core.model_manager import get_model_manager
    
    manager = get_model_manager()
    
    print("\n" + "=" * 80)
    print("DETAILED MODEL INFORMATION")
    print("=" * 80)
    
    models = manager.list_models()
    
    for model in models:
        print(f"\n{model.name}")
        print("-" * 80)
        print(f"  ID: {model.model_id}")
        print(f"  Provider: {model.provider}")
        print(f"  Types: {', '.join([t.value for t in model.types])}")
        print(f"  Context: {model.context_window:,} tokens")
        print(f"  Local: {'Yes' if model.local else 'No (Cloud API)'}")
        print(f"  Functions: {'Yes' if model.supports_function_calling else 'No'}")
        print(f"  Vision: {'Yes' if model.supports_vision else 'No'}")
        print(f"  Success Rate: {model.success_rate:.1%}")
        if model.avg_latency_ms > 0:
            print(f"  Latency: {model.avg_latency_ms:.0f}ms")
        if model.cost_per_1k_input > 0:
            print(f"  Cost: ${model.cost_per_1k_input:.6f}/1K input tokens")
        print(f"  Description: {model.description}")


def test_api_endpoints():
    """Test API endpoints"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing API Endpoints")
    logger.info("=" * 60)
    
    logger.info("\nNote: These endpoints are available when the backend is running:")
    logger.info("\nModel Endpoints:")
    logger.info("  GET  /agent/models/available")
    logger.info("  GET  /agent/models/config")
    logger.info("  GET  /agent/models/best-for-task?task_type=code")
    logger.info("  GET  /agent/models/stats")
    logger.info("  POST /agent/models/select")
    
    logger.info("\nAgent Endpoints:")
    logger.info("  GET  /agent/capabilities")
    logger.info("  GET  /agent/capabilities/{agent_name}")
    logger.info("  POST /agent/agent/{agent_name}/execute")
    
    logger.info("\nLearning Endpoints:")
    logger.info("  GET  /agent/learning/stats")
    logger.info("  POST /agent/learning/feedback")
    logger.info("  GET  /agent/learning/preferences/{user_id}")
    
    logger.info("\nHealth Endpoints:")
    logger.info("  GET  /agent/models/health")
    logger.info("  GET  /agent/agents/health")


def main():
    """Main entry point"""
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "--models":
            print_model_details()
        elif command == "--endpoints":
            test_api_endpoints()
        elif command == "--help":
            print("""
Agent Amigos 2025 Quick Start

Usage: python setup_enhancement.py [command]

Commands:
  (no args)     - Full initialization and setup
  --models      - Show detailed model information
  --endpoints   - List available API endpoints
  --help        - Show this help message

Examples:
  python setup_enhancement.py
  python setup_enhancement.py --models
  python setup_enhancement.py --endpoints
            """)
        else:
            logger.error(f"Unknown command: {command}")
            logger.info("Use --help for available commands")
            sys.exit(1)
    else:
        # Full initialization
        success = initialize_systems()
        if not success:
            sys.exit(1)
        
        # Show additional info
        print_model_details()
        print("\n")
        test_api_endpoints()


if __name__ == "__main__":
    main()
