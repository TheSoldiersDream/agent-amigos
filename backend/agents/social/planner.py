"""Social planner for generating posting schedules and post ideas."""
from __future__ import annotations
from typing import List, Dict
from datetime import datetime, timedelta

class SocialPlanner:
    """Create simple posting plans based on topics and schedule constraints."""

    def __init__(self, default_daily_posts: int = 2):
        self.default_daily_posts = default_daily_posts

    def plan_campaign(self, topics: List[str], days: int = 7) -> List[Dict]:
        """Return a list of planned posts with scheduled timestamps and topic assignment."""
        now = datetime.utcnow()
        posts = []
        for d in range(days):
            date = now + timedelta(days=d)
            for i in range(self.default_daily_posts):
                topic = topics[(d * self.default_daily_posts + i) % len(topics)] if topics else "general"
                posts.append({
                    "scheduled_for": (date + timedelta(hours=9 + i * 3)).isoformat() + "Z",
                    "topic": topic,
                    "platforms": ["twitter", "linkedin"],
                })
        return posts
