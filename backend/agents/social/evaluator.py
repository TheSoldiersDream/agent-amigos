"""Engagement evaluator for social posts."""
from __future__ import annotations
from typing import List, Dict, Any

class EngagementEvaluatorAgent:
    """Evaluate engagement results and generate simple insights."""

    def evaluate(self, results: List[Dict[str, Any]]) -> List[str]:
        insights: List[str] = []

        for item in results:
            try:
                replies = int(item.get("replies", 0))
            except Exception:
                replies = 0
            if replies == 0:
                insights.append("Rewrite with stronger emotional hook")
            else:
                insights.append("Expand conversation")

        return insights
