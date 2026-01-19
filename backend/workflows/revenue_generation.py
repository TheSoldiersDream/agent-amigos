"""
Revenue Generation Workflows for Agent Amigos AI Company
Real revenue-generating tasks that the AI company executes
"""
from typing import Dict, List, Any
from datetime import datetime, timedelta


class RevenueWorkflows:
    """Real revenue-generating workflows for the AI company"""
    
    @staticmethod
    def get_revenue_tasks() -> List[Dict[str, Any]]:
        """Return real, actionable revenue-generating tasks"""
        now = datetime.now()
        
        return [
            {
                "id": "revenue-content-linkedin",
                "title": "Create LinkedIn thought leadership post about AI automation",
                "description": "Write and publish a LinkedIn post showcasing Agent Amigos capabilities with #darrellbuttigieg #thesoldiersdream",
                "owner": "Marketing",
                "owner_id": "media",
                "status": "pending",
                "ai_validated": True,
                "validation_note": "ai-best-outcome",
                "scheduled_for": (now + timedelta(hours=2)).isoformat(),
                "source": "revenue-generation",
                "tags": ["content", "linkedin", "revenue"],
                "kpi_impact": "brand_awareness",
                "estimated_reach": 5000,
            },
            {
                "id": "revenue-outreach-github",
                "title": "Identify and reach out to 10 GitHub repos that need automation",
                "description": "Find Python/JS projects with repetitive tasks and offer Agent Amigos as solution",
                "owner": "CEO Agent",
                "owner_id": "ceo",
                "status": "pending",
                "ai_validated": True,
                "validation_note": "ai-best-outcome",
                "scheduled_for": (now + timedelta(hours=4)).isoformat(),
                "source": "revenue-generation",
                "tags": ["outreach", "leads", "revenue"],
                "kpi_impact": "lead_generation",
                "target_leads": 10,
            },
            {
                "id": "revenue-landing-page",
                "title": "Build landing page with CTA for Agent Amigos Pro",
                "description": "Create conversion-optimized landing page with high-quality screenshots, pricing, and email capture",
                "owner": "Workflow Operations",
                "owner_id": "ops",
                "status": "pending",
                "ai_validated": True,
                "validation_note": "ai-best-outcome",
                "scheduled_for": (now + timedelta(hours=8)).isoformat(),
                "source": "revenue-generation",
                "tags": ["website", "conversion", "revenue"],
                "kpi_impact": "lead_generation",
            },
            {
                "id": "revenue-reddit-engagement",
                "title": "Engage in 5 relevant Reddit threads about AI automation",
                "description": "Provide value in r/learnprogramming, r/automation, r/productivity with subtle Agent Amigos mentions",
                "owner": "Marketing",
                "owner_id": "media",
                "status": "pending",
                "ai_validated": True,
                "validation_note": "ai-best-outcome",
                "scheduled_for": (now + timedelta(hours=3)).isoformat(),
                "source": "revenue-generation",
                "tags": ["reddit", "community", "revenue"],
                "kpi_impact": "brand_awareness",
                "target_communities": ["learnprogramming", "automation", "productivity"],
            },
            {
                "id": "revenue-feature-showcase",
                "title": "Create feature comparison: Agent Amigos vs manual workflows",
                "description": "Quantify time saved, ROI, and productivity gains with real metrics",
                "owner": "AI Strategy",
                "owner_id": "amigos",
                "status": "pending",
                "ai_validated": True,
                "validation_note": "ai-best-outcome",
                "scheduled_for": (now + timedelta(hours=5)).isoformat(),
                "source": "revenue-generation",
                "tags": ["analysis", "roi", "revenue"],
                "kpi_impact": "value_proposition",
            },
            {
                "id": "revenue-email-campaign",
                "title": "Draft email sequence for trial users (5 emails)",
                "description": "Nurture sequence: Welcome → Feature tour → Use cases → Success stories → Upgrade CTA",
                "owner": "Marketing",
                "owner_id": "media",
                "status": "pending",
                "ai_validated": True,
                "validation_note": "ai-best-outcome",
                "scheduled_for": (now + timedelta(hours=7)).isoformat(),
                "source": "revenue-generation",
                "tags": ["email", "nurture", "revenue"],
                "kpi_impact": "conversion_rate",
                "email_count": 5,
            },
            {
                "id": "revenue-partnership-list",
                "title": "Identify 20 potential integration partners",
                "description": "Find complementary tools (Zapier, n8n, Make) for partnership opportunities",
                "owner": "CEO Agent",
                "owner_id": "ceo",
                "status": "pending",
                "ai_validated": True,
                "validation_note": "ai-best-outcome",
                "scheduled_for": (now + timedelta(hours=9)).isoformat(),
                "source": "revenue-generation",
                "tags": ["partnerships", "integrations", "revenue"],
                "kpi_impact": "distribution_channels",
                "target_partners": 20,
            },
            {
                "id": "revenue-testimonial-collection",
                "title": "Reach out to 10 users for testimonials and case studies",
                "description": "Collect success stories to build social proof and conversion assets",
                "owner": "Marketing",
                "owner_id": "media",
                "status": "pending",
                "ai_validated": True,
                "validation_note": "ai-best-outcome",
                "scheduled_for": (now + timedelta(hours=10)).isoformat(),
                "source": "revenue-generation",
                "tags": ["testimonials", "social-proof", "revenue"],
                "kpi_impact": "conversion_rate",
                "target_testimonials": 10,
            },
        ]
    
    @staticmethod
    def get_kpi_definitions() -> Dict[str, Any]:
        """Define trackable KPIs for the AI company"""
        return {
            "lead_generation": {
                "name": "Lead Generation",
                "metric": "leads_per_week",
                "target": 50,
                "current": 0,
                "unit": "leads",
            },
            "brand_awareness": {
                "name": "Brand Awareness",
                "metric": "social_reach",
                "target": 10000,
                "current": 0,
                "unit": "impressions",
            },
            "conversion_rate": {
                "name": "Trial to Paid Conversion",
                "metric": "conversion_percentage",
                "target": 15,
                "current": 0,
                "unit": "percent",
            },
            "revenue_model": {
                "name": "Monthly Recurring Revenue",
                "metric": "mrr",
                "target": 10000,
                "current": 0,
                "unit": "USD",
            },
            "value_proposition": {
                "name": "Time Saved Per User",
                "metric": "hours_saved_per_month",
                "target": 20,
                "current": 0,
                "unit": "hours",
            },
            "distribution_channels": {
                "name": "Active Distribution Partners",
                "metric": "active_partners",
                "target": 5,
                "current": 0,
                "unit": "partners",
            },
        }
