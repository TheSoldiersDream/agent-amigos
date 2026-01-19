"""Adapter to expose SocialPlannerAgent via the planner module import path."""
from __future__ import annotations
from .social_agent import SocialPlannerAgent

# Expose class as expected by older import paths
__all__ = ["SocialPlannerAgent"]
