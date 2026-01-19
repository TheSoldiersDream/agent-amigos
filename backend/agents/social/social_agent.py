"""High-level social agent wrappers: SocialPlannerAgent and CommentGeneratorAgent."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from .planner import SocialPlanner
from .commenter import SocialCommenter


class SocialPlannerAgent:
    """Agent wrapper that runs daily social plans using the SocialPlanner helper."""

    def __init__(self, planner: Optional[SocialPlanner] = None) -> None:
        self.planner = planner or SocialPlanner()

    def run_daily_plan(self) -> Dict[str, Any]:
        """Return a daily scan plan payload (lightweight, deterministic)."""
        # Default scan targets and objectives as requested
        return {
            "scan_targets": [
                "facebook follow-to-follow groups",
                "music & creator groups",
                "AI discussion posts",
                "veteran reflection posts",
            ],
            "objectives": [
                "find high-engagement threads",
                "identify under-commented posts",
                "prioritise emotional content",
            ],
            "output_required": ["comment ideas", "post ideas", "follow candidates"],
        }


class CommentGeneratorAgent:
    """Generates a short set of comment templates for a given post context."""

    def __init__(self, commenter: Optional[SocialCommenter] = None) -> None:
        self.commenter = commenter or SocialCommenter()

    def generate_comments(self, post_context: str) -> List[Dict[str, str]]:
        comments: List[Dict[str, str]] = []

        for angle in ["emotional", "reflective", "creative"]:
            text = self.commenter.generate_comment(topic=f"{angle} take on {post_context}")
            comments.append(
                {
                    "text": text,
                    "why_it_works": "Adds value, not noise",
                    "follow_up_question": "What led you to this perspective?",
                }
            )

        return comments
