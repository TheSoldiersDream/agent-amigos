"""Simple content generator for social posts."""
from __future__ import annotations
from typing import Optional

class SocialCommenter:
    """Generate short social copy from a topic and optional template."""

    def __init__(self, default_template: str = "{topic} — Learn more: {link}") -> None:
        self.default_template = default_template

    def generate_comment(self, topic: str, link: Optional[str] = None, template: Optional[str] = None) -> str:
        tpl = template or self.default_template
        return tpl.format(topic=topic, link=(link or ""))
