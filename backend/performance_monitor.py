"""
Performance monitoring and analytics for Agent Amigos
Tracks tool usage, response times, and system health
"""
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from collections import defaultdict

class PerformanceMonitor:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.metrics_file = self.log_dir / "performance_metrics.json"
        self.metrics = self._load_metrics()
        
    def _load_metrics(self) -> Dict:
        """Load existing metrics from disk"""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "tool_usage": defaultdict(int),
            "tool_response_times": defaultdict(list),
            "errors": defaultdict(int),
            "chat_requests": 0,
            "successful_chats": 0,
            "start_time": datetime.now().isoformat()
        }
    
    def _save_metrics(self):
        """Save metrics to disk"""
        # Convert defaultdict to regular dict for JSON serialization
        metrics_copy = {
            "tool_usage": dict(self.metrics["tool_usage"]),
            "tool_response_times": dict(self.metrics["tool_response_times"]),
            "errors": dict(self.metrics["errors"]),
            "chat_requests": self.metrics["chat_requests"],
            "successful_chats": self.metrics["successful_chats"],
            "start_time": self.metrics["start_time"],
            "last_updated": datetime.now().isoformat()
        }
        
        with open(self.metrics_file, 'w') as f:
            json.dump(metrics_copy, f, indent=2)
    
    def record_tool_usage(self, tool_name: str, duration: float, success: bool = True):
        """Record a tool execution"""
        self.metrics["tool_usage"][tool_name] += 1
        self.metrics["tool_response_times"][tool_name].append({
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "success": success
        })
        
        if not success:
            self.metrics["errors"][tool_name] += 1
        
        self._save_metrics()
    
    def record_chat_request(self, success: bool = True):
        """Record a chat request"""
        self.metrics["chat_requests"] += 1
        if success:
            self.metrics["successful_chats"] += 1
        self._save_metrics()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = {
            "total_tool_calls": sum(self.metrics["tool_usage"].values()),
            "total_chat_requests": self.metrics["chat_requests"],
            "success_rate": (self.metrics["successful_chats"] / self.metrics["chat_requests"] * 100) 
                           if self.metrics["chat_requests"] > 0 else 0,
            "top_tools": sorted(
                self.metrics["tool_usage"].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10],
            "error_rate": {},
            "avg_response_times": {}
        }
        
        # Calculate error rates
        for tool, errors in self.metrics["errors"].items():
            total = self.metrics["tool_usage"].get(tool, 0)
            if total > 0:
                stats["error_rate"][tool] = (errors / total * 100)
        
        # Calculate average response times
        for tool, times in self.metrics["tool_response_times"].items():
            if times:
                avg = sum(t["duration"] for t in times) / len(times)
                stats["avg_response_times"][tool] = round(avg, 3)
        
        return stats
    
    def get_tool_analytics(self, tool_name: str) -> Dict[str, Any]:
        """Get detailed analytics for a specific tool"""
        times = self.metrics["tool_response_times"].get(tool_name, [])
        usage_count = self.metrics["tool_usage"].get(tool_name, 0)
        errors = self.metrics["errors"].get(tool_name, 0)
        
        if not times:
            return {
                "tool": tool_name,
                "usage_count": usage_count,
                "error_count": errors,
                "data_available": False
            }
        
        durations = [t["duration"] for t in times]
        successes = sum(1 for t in times if t.get("success", True))
        
        return {
            "tool": tool_name,
            "usage_count": usage_count,
            "total_calls": len(times),
            "successful_calls": successes,
            "error_count": errors,
            "success_rate": (successes / len(times) * 100) if times else 0,
            "avg_response_time": sum(durations) / len(durations),
            "min_response_time": min(durations),
            "max_response_time": max(durations),
            "recent_calls": times[-10:]  # Last 10 calls
        }
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = {
            "tool_usage": defaultdict(int),
            "tool_response_times": defaultdict(list),
            "errors": defaultdict(int),
            "chat_requests": 0,
            "successful_chats": 0,
            "start_time": datetime.now().isoformat()
        }
        self._save_metrics()

# Global instance
monitor = PerformanceMonitor()
