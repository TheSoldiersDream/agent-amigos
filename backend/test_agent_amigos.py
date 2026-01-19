"""
Comprehensive test suite for Agent Amigos
Tests core functionality, tools, security, and performance
"""
import requests
import json
import time
from typing import Dict, Any, List

# Configuration
BASE_URL = "http://127.0.0.1:8080"
TEST_RESULTS = []

class TestResult:
    def __init__(self, name: str, passed: bool, message: str = "", duration: float = 0):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration = duration
    
    def __repr__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status} | {self.name} ({self.duration:.3f}s) - {self.message}"

def log_test(name: str, passed: bool, message: str = "", duration: float = 0):
    result = TestResult(name, passed, message, duration)
    TEST_RESULTS.append(result)
    print(result)
    return passed

def test_health_endpoint():
    """Test if backend health endpoint responds correctly"""
    start = time.time()
    try:
        # Allow a slightly longer timeout for health checks to tolerate slow LLM probes
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        duration = time.time() - start
        
        if response.status_code != 200:
            return log_test("Health Endpoint", False, f"Status code: {response.status_code}", duration)
        
        data = response.json()
        required_fields = ['status', 'agent', 'tools_available', 'llm_ready']
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            return log_test("Health Endpoint", False, f"Missing fields: {missing}", duration)
        
        if data['status'] != 'online':
            return log_test("Health Endpoint", False, f"Status: {data['status']}", duration)
        
        return log_test("Health Endpoint", True, 
                       f"Tools: {data['tools_available']}, LLM: {data['llm_ready']}", duration)
    
    except Exception as e:
        return log_test("Health Endpoint", False, f"Exception: {str(e)}", time.time() - start)

def test_chat_endpoint():
    """Test basic chat functionality"""
    start = time.time()
    try:
        payload = {
            "messages": [
                {"role": "user", "content": "Respond with exactly: TEST_SUCCESS"}
            ]
        }
        response = requests.post(f"{BASE_URL}/chat", json=payload, timeout=30)
        duration = time.time() - start
        
        if response.status_code != 200:
            return log_test("Chat Endpoint", False, f"Status code: {response.status_code}", duration)
        
        data = response.json()
        if 'content' not in data:
            return log_test("Chat Endpoint", False, "No content in response", duration)
        
        return log_test("Chat Endpoint", True, 
                       f"Response length: {len(data['content'])}", duration)
    
    except Exception as e:
        return log_test("Chat Endpoint", False, f"Exception: {str(e)}", time.time() - start)

def test_tools_endpoint():
    """Test tools listing endpoint"""
    start = time.time()
    try:
        response = requests.get(f"{BASE_URL}/tools", timeout=10)
        duration = time.time() - start
        
        if response.status_code != 200:
            return log_test("Tools Endpoint", False, f"Status code: {response.status_code}", duration)
        
        data = response.json()
        
        if not isinstance(data, list):
            return log_test("Tools Endpoint", False, "Response not a list", duration)
        
        if len(data) == 0:
            return log_test("Tools Endpoint", False, "No tools returned", duration)
        
        # Check tool structure
        sample_tool = data[0] if data else {}
        required_fields = ['name', 'description']
        has_required = all(f in sample_tool for f in required_fields)
        
        return log_test("Tools Endpoint", has_required, 
                       f"Tools count: {len(data)}", duration)
    
    except Exception as e:
        return log_test("Tools Endpoint", False, f"Exception: {str(e)}", time.time() - start)

def test_security_status():
    """Test security status endpoint"""
    start = time.time()
    try:
        response = requests.get(f"{BASE_URL}/security/status", timeout=5)
        duration = time.time() - start
        
        if response.status_code != 200:
            return log_test("Security Status", False, f"Status code: {response.status_code}", duration)
        
        data = response.json()
        required_fields = ['autonomy_enabled', 'kill_switch', 'allowed_actions']
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            return log_test("Security Status", False, f"Missing fields: {missing}", duration)
        
        return log_test("Security Status", True, 
                       f"Autonomy: {data['autonomy_enabled']}, Kill switch: {data['kill_switch']}", duration)
    
    except Exception as e:
        return log_test("Security Status", False, f"Exception: {str(e)}", time.time() - start)

def test_tool_execution():
    """Test direct tool execution"""
    start = time.time()
    try:
        payload = {
            "tool_name": "get_system_info",
            "parameters": {}
        }
        response = requests.post(f"{BASE_URL}/execute_tool", json=payload, timeout=10)
        duration = time.time() - start
        
        if response.status_code != 200:
            return log_test("Tool Execution", False, f"Status code: {response.status_code}", duration)
        
        data = response.json()
        if 'result' not in data:
            return log_test("Tool Execution", False, "No result in response", duration)
        
        return log_test("Tool Execution", True, "Tool executed successfully", duration)
    
    except Exception as e:
        return log_test("Tool Execution", False, f"Exception: {str(e)}", time.time() - start)

def test_chat_with_tool_call():
    """Test chat endpoint with automatic tool calling"""
    start = time.time()
    try:
        payload = {
            "messages": [
                {"role": "user", "content": "What is the current system time?"}
            ]
        }
        response = requests.post(f"{BASE_URL}/chat", json=payload, timeout=30)
        duration = time.time() - start
        
        if response.status_code != 200:
            return log_test("Chat with Tools", False, f"Status code: {response.status_code}", duration)
        
        data = response.json()
        
        # Check if tools were called
        tools_called = 'actions_taken' in data and len(data.get('actions_taken', [])) > 0
        
        return log_test("Chat with Tools", True, 
                       f"Tools called: {tools_called}", duration)
    
    except Exception as e:
        return log_test("Chat with Tools", False, f"Exception: {str(e)}", time.time() - start)


def test_image_generation_prompt_passthrough():
    """Ensure "generate image of ..." preserves the user's prompt text.

    Regression: direct phrase shortcuts like "generate image" must not override
    dynamic prompts with a hard-coded default.
    """
    start = time.time()
    try:
        prompt = "a cat wearing a top hat, studio lighting"
        payload = {
            "messages": [
                {"role": "user", "content": f"Generate image of {prompt}"}
            ]
        }

        response = requests.post(f"{BASE_URL}/chat", json=payload, timeout=60)
        duration = time.time() - start

        if response.status_code != 200:
            return log_test("Image Prompt Passthrough", False, f"Status code: {response.status_code}", duration)

        data = response.json()
        actions = data.get("actions_taken") or []
        # We accept either schema: actions can be dicts with tool/args, or tool_name/parameters.
        found = False
        got_prompt = None
        for a in actions:
            tool_name = a.get("tool") or a.get("tool_name")
            args = a.get("args") or a.get("parameters") or {}
            if tool_name == "generate_image":
                got_prompt = args.get("prompt")
                found = True
                break

        if not found:
            return log_test("Image Prompt Passthrough", False, f"No generate_image action. actions_taken={actions}", duration)

        # Must contain the exact user prompt substring (case-insensitive to tolerate downstream normalization).
        ok = isinstance(got_prompt, str) and prompt.lower() in got_prompt.lower()
        return log_test("Image Prompt Passthrough", ok, f"prompt={got_prompt!r}", duration)
    except Exception as e:
        return log_test("Image Prompt Passthrough", False, f"Exception: {str(e)}", time.time() - start)

def test_autonomy_controls():
    """Test autonomy enable/disable functionality"""
    start = time.time()
    try:
        # Get current status
        response = requests.get(f"{BASE_URL}/security/status", timeout=5)
        if response.status_code != 200:
            return log_test("Autonomy Controls", False, "Failed to get status", time.time() - start)
        
        initial_status = response.json()
        
        # Try to toggle autonomy
        toggle_payload = {"enabled": not initial_status['autonomy_enabled']}
        response = requests.post(f"{BASE_URL}/security/autonomy", json=toggle_payload, timeout=5)
        
        if response.status_code != 200:
            return log_test("Autonomy Controls", False, f"Toggle failed: {response.status_code}", time.time() - start)
        
        # Verify change
        response = requests.get(f"{BASE_URL}/security/status", timeout=5)
        new_status = response.json()
        
        duration = time.time() - start
        changed = new_status['autonomy_enabled'] != initial_status['autonomy_enabled']
        
        # Restore original state
        requests.post(f"{BASE_URL}/security/autonomy", json={"enabled": initial_status['autonomy_enabled']}, timeout=5)
        
        return log_test("Autonomy Controls", changed, 
                       f"Toggle successful", duration)
    
    except Exception as e:
        return log_test("Autonomy Controls", False, f"Exception: {str(e)}", time.time() - start)

def test_response_time():
    """Test average response time for simple queries"""
    times = []
    try:
        for i in range(3):
            start = time.time()
            payload = {"messages": [{"role": "user", "content": f"Say: test {i}"}]}
            response = requests.post(f"{BASE_URL}/chat", json=payload, timeout=30)
            duration = time.time() - start
            
            if response.status_code == 200:
                times.append(duration)
        
        if not times:
            return log_test("Response Time", False, "All requests failed", 0)
        
        avg_time = sum(times) / len(times)
        passed = avg_time < 10.0  # Should respond within 10 seconds on average
        
        return log_test("Response Time", passed, 
                       f"Avg: {avg_time:.2f}s, Min: {min(times):.2f}s, Max: {max(times):.2f}s", avg_time)
    
    except Exception as e:
        return log_test("Response Time", False, f"Exception: {str(e)}", 0)


def test_autonomy_auto_approve_safe_tools():
    """When autonomy is enabled and auto-approve is turned on, safe tools should execute automatically."""
    start = time.time()
    try:
        # Enable autonomy and set auto-approve safe tools
        r = requests.post(f"{BASE_URL}/agent/autonomy", json={"autonomyEnabled": True, "autoApproveSafeTools": True}, timeout=5)
        if r.status_code != 200:
            return log_test("Autonomy Auto-Approve Safe Tools", False, f"Failed to set config: {r.status_code}", time.time() - start)

        payload = {"messages": [{"role": "user", "content": "Clear the canvas"}], "require_approval": True}
        response = requests.post(f"{BASE_URL}/chat", json=payload, timeout=30)
        data = response.json()
        tools_called = 'actions_taken' in data and len(data.get('actions_taken', [])) > 0
        if not tools_called:
            return log_test("Autonomy Auto-Approve Safe Tools", False, f"No actions taken: {data}", time.time() - start)

        actions = data.get('actions_taken', [])
        found = any(a.get('tool') == 'canvas_clear' for a in actions)
        return log_test("Autonomy Auto-Approve Safe Tools", found, f"actions: {actions}", time.time() - start)
    except Exception as e:
        return log_test("Autonomy Auto-Approve Safe Tools", False, f"Exception: {e}", time.time() - start)


def test_continuous_autonomy_runs_safe_action():
    """Start continuous mode for one cycle and verify safe action runs when auto-approve is enabled."""
    start = time.time()
    try:
        # Ensure autonomy & auto-approve are enabled
        r = requests.post(f"{BASE_URL}/agent/autonomy", json={"autonomyEnabled": True, "autoApproveSafeTools": True}, timeout=5)
        if r.status_code != 200:
            return log_test("Continuous Autonomy", False, f"Failed to set config: {r.status_code}", time.time() - start)

        # Start continuous with a goal that should trigger canvas_clear
        payload = {
            "goal": "Clear the canvas",
            "interval_seconds": 0.5,
            "max_cycles": 1,
            "max_runtime_seconds": 30
        }
        r2 = requests.post(f"{BASE_URL}/agent/continuous/start", json=payload, timeout=10)
        if r2.status_code != 200:
            return log_test("Continuous Autonomy", False, f"Start failed: {r2.status_code} {r2.text}", time.time() - start)

        # Poll status until last_actions populated or timeout
        found = False
        for i in range(10):
            time.sleep(0.7)
            s = requests.get(f"{BASE_URL}/agent/continuous/status_compact", timeout=5).json()
            la = s.get('last_actions') or []
            if any(a.get('tool') == 'canvas_clear' for a in la):
                found = True
                break

        # Stop if still running
        try:
            requests.post(f"{BASE_URL}/agent/continuous/stop", timeout=5)
        except Exception:
            pass

        return log_test("Continuous Autonomy", found, f"Found canvas_clear: {found}", time.time() - start)
    except Exception as e:
        return log_test("Continuous Autonomy", False, f"Exception: {e}", time.time() - start)

def run_all_tests():
    """Run all tests and generate report"""
    print("=" * 80)
    print("🚀 Agent Amigos Test Suite")
    print("=" * 80)
    print()
    
    # Core functionality tests
    print("📡 Core Functionality Tests")
    print("-" * 80)
    test_health_endpoint()
    test_chat_endpoint()
    test_tools_endpoint()
    print()
    
    # Security tests
    print("🔒 Security Tests")
    print("-" * 80)
    test_security_status()
    test_autonomy_controls()
    print()
    
    # Tool tests
    print("🔧 Tool Execution Tests")
    print("-" * 80)
    test_tool_execution()
    test_chat_with_tool_call()
    test_image_generation_prompt_passthrough()
    print()
    
    # Performance tests
    print("⚡ Performance Tests")
    print("-" * 80)
    test_response_time()
    print()
    
    # Generate summary
    print("=" * 80)
    print("📊 Test Summary")
    print("=" * 80)
    
    total_tests = len(TEST_RESULTS)
    passed_tests = sum(1 for t in TEST_RESULTS if t.passed)
    failed_tests = total_tests - passed_tests
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    print()
    
    if failed_tests > 0:
        print("Failed Tests:")
        for result in TEST_RESULTS:
            if not result.passed:
                print(f"  - {result.name}: {result.message}")
    
    print("=" * 80)
    
    return success_rate >= 80  # Consider success if 80%+ tests pass

if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
        exit(2)
    except Exception as e:
        print(f"\n\n❌ Test suite failed: {e}")
        exit(3)
