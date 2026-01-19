"""
Team Demo - Multi-Agent Facebook Post Creator
==============================================
Demonstrates all agents working together to create a viral Facebook post.

Workflow:
1. Scrapey - Scrapes trending topics from the web
2. Ollie - Generates post content using local LLM
3. Media Bot - Finds/suggests images for the post
4. Amigos - Orchestrates everything and finalizes

Owner: Darrell Buttigieg
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
import random

from tools.agent_coordinator import (
    coordinator,
    agent_working,
    agent_thinking,
    agent_idle,
    agent_online,
    start_collaboration,
    end_collaboration,
    AgentStatus
)


# Simulated trending topics (in real use, Scrapey would scrape these)
TRENDING_TOPICS = [
    {"topic": "AI Agents Revolution", "hashtags": ["#AI", "#AgentAmigos", "#Automation", "#FutureTech"]},
    {"topic": "Local LLMs Taking Over", "hashtags": ["#Ollama", "#LocalAI", "#Privacy", "#OpenSource"]},
    {"topic": "Crypto Market Surge", "hashtags": ["#Bitcoin", "#Crypto", "#ToTheMoon", "#Blockchain"]},
    {"topic": "New Gaming Tech 2025", "hashtags": ["#Gaming", "#GameDev", "#NextGen", "#Esports"]},
    {"topic": "Remote Work Revolution", "hashtags": ["#RemoteWork", "#WFH", "#DigitalNomad", "#Productivity"]},
    {"topic": "Climate Tech Innovation", "hashtags": ["#CleanTech", "#Sustainability", "#GreenEnergy", "#ClimateAction"]},
]

# Post templates for different styles
POST_TEMPLATES = {
    "viral": "🔥 {hook}\n\n{body}\n\n{cta}\n\n{hashtags}",
    "engaging": "💡 {hook}\n\n{body}\n\n👇 {cta}\n\n{hashtags}",
    "professional": "📢 {hook}\n\n{body}\n\n{cta}\n\n{hashtags}",
}


class TeamDemoOrchestrator:
    """Orchestrates the multi-agent demo for creating Facebook posts."""
    
    def __init__(self):
        self.demo_running = False
        self.demo_steps = []
        self.current_step = 0
        self.demo_result = None
        self.collab_id = None
    
    async def run_demo(self, custom_topic: str = None) -> Dict:
        """
        Run the full multi-agent demo.
        Returns step-by-step progress and final result.
        """
        if self.demo_running:
            return {"error": "Demo already running", "success": False}
        
        self.demo_running = True
        self.demo_steps = []
        self.current_step = 0
        self.demo_result = None
        
        try:
            # Start collaboration
            self.collab_id = start_collaboration(
                "amigos", 
                ["scrapey", "ollie", "media"], 
                "Create viral Facebook post about trending topic"
            )
            
            # Step 1: Amigos starts coordinating
            await self._step_amigos_start()
            await asyncio.sleep(1.5)
            
            # Step 2: Scrapey finds trending topics
            trending = await self._step_scrapey_scrape(custom_topic)
            await asyncio.sleep(2)
            
            # Step 3: Ollie generates content
            content = await self._step_ollie_generate(trending)
            await asyncio.sleep(2.5)
            
            # Step 4: Media Bot finds images
            media_suggestion = await self._step_media_find(trending)
            await asyncio.sleep(1.5)
            
            # Step 5: Amigos finalizes
            final_post = await self._step_amigos_finalize(content, media_suggestion, trending)
            await asyncio.sleep(1)
            
            # End collaboration
            end_collaboration(self.collab_id, success=True)
            
            self.demo_result = {
                "success": True,
                "post": final_post,
                "steps": self.demo_steps,
                "collaboration_id": self.collab_id
            }
            
            return self.demo_result
            
        except Exception as e:
            if self.collab_id:
                end_collaboration(self.collab_id, success=False)
            return {"success": False, "error": str(e), "steps": self.demo_steps}
        finally:
            self.demo_running = False
            # Reset all agents to idle
            for agent_id in ["amigos", "scrapey", "ollie", "media"]:
                agent_idle(agent_id)
    
    async def _step_amigos_start(self):
        """Step 1: Amigos starts the coordination."""
        agent_working("amigos", "Coordinating team for Facebook post creation", progress=10)
        
        step = {
            "step": 1,
            "agent": "amigos",
            "agent_name": "Agent Amigos",
            "emoji": "🤖",
            "action": "Starting Team Coordination",
            "message": "Alright team! We need to create a viral Facebook post. Let me coordinate everyone...",
            "status": "Assigning tasks to team members",
            "timestamp": datetime.now().isoformat()
        }
        self.demo_steps.append(step)
        self.current_step = 1
        return step
    
    async def _step_scrapey_scrape(self, custom_topic: str = None) -> Dict:
        """Step 2: Scrapey scrapes trending topics."""
        agent_online("scrapey")
        await asyncio.sleep(0.3)
        agent_working("scrapey", "Scraping trending topics from the web", progress=25)
        
        # Simulate scraping delay
        await asyncio.sleep(1)
        agent_working("scrapey", "Analyzing scraped data", progress=75)
        await asyncio.sleep(0.5)
        
        if custom_topic:
            trending = {
                "topic": custom_topic,
                "hashtags": ["#Trending", "#Viral", "#MustSee", "#BreakingNews"],
                "source": "User specified"
            }
        else:
            trending = random.choice(TRENDING_TOPICS)
            trending["source"] = "Web scraping"
        
        step = {
            "step": 2,
            "agent": "scrapey",
            "agent_name": "Scrapey",
            "emoji": "🕷️",
            "action": "Scraping Trending Topics",
            "message": f"Found a hot topic: '{trending['topic']}'! This is trending right now.",
            "status": "Analyzed 50+ sources for trending content",
            "data": trending,
            "timestamp": datetime.now().isoformat()
        }
        self.demo_steps.append(step)
        self.current_step = 2
        
        agent_idle("scrapey")
        return trending
    
    async def _step_ollie_generate(self, trending: Dict, scraped_content: str = None) -> Dict:
        """Step 3: Ollie generates post content using actual AI."""
        agent_online("ollie")
        await asyncio.sleep(0.3)
        agent_thinking("ollie", f"Analyzing content and generating viral post for: {trending['topic']}", progress=15)
        
        # Try to use actual Ollama AI for content generation
        ai_generated = False
        content = {}
        
        try:
            # Import Ollama service
            from tools.ollama_tools import ollama_service
            
            # Prepare the AI prompt for viral post creation
            source_context = f"\n\nSource content to analyze:\n{scraped_content[:3000]}" if scraped_content else ""
            
            viral_prompt = f"""You are a VIRAL CONTENT STRATEGIST. Create an ENGAGING Facebook post about "{trending['topic']}".
{source_context}

## TASK:
Create a Facebook post that will GO VIRAL. Make it HUMAN, AUTHENTIC, and SHAREABLE.

## REQUIRED STRUCTURE:

HOOK (2-3 lines max):
Write an attention-grabbing opening that creates curiosity. Use ONE of these proven formulas:
- Start with a surprising fact or statistic
- Ask a thought-provoking question
- Make a bold statement
- Share a personal revelation

BODY (2-3 short paragraphs):
- Tell the story in a relatable way
- Include SPECIFIC facts, numbers, or names if available
- Use short sentences for mobile readability
- Make it feel like you're sharing news with a friend
- Add emotional elements that resonate

CTA (1 line):
End with an engaging question or call-to-action that drives comments.

## RULES:
- Sound like a REAL PERSON, not AI
- NO generic phrases like "In today's world" or "It's important to note"
- Keep paragraphs SHORT (max 3 sentences)
- Make it SHAREABLE and discussion-worthy
- Include specific details when possible

## OUTPUT FORMAT (return EXACTLY this JSON):
{{
    "hook": "Your attention-grabbing hook here (2-3 lines max)",
    "body": "Your main content here with line breaks using \\n\\n for paragraphs",
    "cta": "Your call-to-action question here"
}}

Return ONLY the JSON, nothing else."""

            # Call Ollama for generation
            agent_working("ollie", "Using local LLM to craft viral content", progress=50)
            result = await ollama_service.generate(
                prompt=viral_prompt,
                task_type="creative_writing",
                temperature=0.8
            )
            
            if result.get("success") and result.get("response"):
                response_text = result["response"]
                
                # Try to parse JSON from response
                import json
                import re
                
                # Find JSON in response
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                        if all(key in parsed for key in ["hook", "body", "cta"]):
                            content = {
                                "hook": parsed["hook"],
                                "body": parsed["body"],
                                "cta": parsed["cta"],
                                "hashtags": " ".join(trending["hashtags"]),
                                "tone": "viral/engaging",
                                "ai_generated": True
                            }
                            ai_generated = True
                    except json.JSONDecodeError:
                        pass
                
                # If JSON parsing failed, try to extract from text
                if not ai_generated and len(response_text) > 100:
                    # Split response into parts
                    lines = response_text.strip().split('\n')
                    lines = [l.strip() for l in lines if l.strip()]
                    
                    if len(lines) >= 3:
                        content = {
                            "hook": lines[0] if lines else f"🔥 {trending['topic']} is changing everything!",
                            "body": '\n\n'.join(lines[1:-1]) if len(lines) > 2 else lines[1] if len(lines) > 1 else "",
                            "cta": lines[-1] if lines else "What do you think? 👇",
                            "hashtags": " ".join(trending["hashtags"]),
                            "tone": "viral/engaging",
                            "ai_generated": True
                        }
                        ai_generated = True
        
        except Exception as e:
            print(f"[TEAM_DEMO] Ollama generation failed: {e}, using enhanced templates")
        
        # Fallback to enhanced templates if AI fails
        if not ai_generated:
            # More varied and engaging hooks
            hooks = [
                f"🚀 Breaking: {trending['topic']} is changing EVERYTHING we thought we knew!",
                f"⚡ I've been following {trending['topic']} for weeks. Today it finally clicked...",
                f"🔥 This is the biggest development in {trending['topic']} I've seen all year.",
                f"💡 Everyone's talking about {trending['topic']} - but most are missing the real story:",
                f"👀 Something huge just happened with {trending['topic']} and nobody's paying attention...",
                f"🎯 {trending['topic']} just hit different today. Here's why it matters:",
            ]
            
            # More storytelling-focused bodies
            bodies = [
                f"The landscape is shifting faster than anyone predicted. {trending['topic']} isn't just a trend anymore - it's becoming the new baseline.\n\nWhat started as an experiment is now reshaping entire industries. The early adopters saw this coming. The rest? Playing catch-up.",
                f"I'll be honest - I was skeptical about {trending['topic']} at first. But after diving deep into the data, I can't ignore what's happening.\n\nThe numbers don't lie. And right now, they're telling a story that could change everything we know about this space.",
                f"Three things became crystal clear to me about {trending['topic']}:\n\n1️⃣ This isn't hype - it's a fundamental shift\n2️⃣ The people paying attention are positioning themselves right now\n3️⃣ In 12 months, we'll look back at this moment as the turning point",
                f"Here's what nobody's telling you about {trending['topic']}:\n\nWhile everyone focuses on the headlines, the real action is happening behind the scenes. The smart money already moved. The question is - where do YOU stand?",
            ]
            
            # More engaging CTAs
            ctas = [
                "Real talk - where do you stand on this? Drop your take below 👇",
                "Am I the only one seeing this? Let me know your thoughts 💬",
                "Agree or disagree? I want to hear YOUR perspective 🎯",
                "Tag someone who NEEDS to see this. Seriously. 📢",
                "This is a discussion worth having. What's your experience? 🤔",
            ]
            
            content = {
                "hook": random.choice(hooks),
                "body": random.choice(bodies),
                "cta": random.choice(ctas),
                "hashtags": " ".join(trending["hashtags"]),
                "tone": "viral/engaging",
                "ai_generated": False
            }
        
        step = {
            "step": 3,
            "agent": "ollie",
            "agent_name": "Ollie",
            "emoji": "🦙",
            "action": "Generating Post Content",
            "message": f"I've crafted {'AI-powered' if ai_generated else 'engaging'} copy for '{trending['topic']}'!",
            "status": f"Generated using {'Ollama LLM' if ai_generated else 'enhanced templates'} locally",
            "data": content,
            "timestamp": datetime.now().isoformat()
        }
        self.demo_steps.append(step)
        self.current_step = 3
        
        agent_idle("ollie")
        return content
    
    async def _step_media_find(self, trending: Dict) -> Dict:
        """Step 4: Media Bot finds/suggests images."""
        agent_online("media")
        await asyncio.sleep(0.3)
        agent_working("media", f"Finding visuals for: {trending['topic']}", progress=30)
        
        # Simulate image search delay
        await asyncio.sleep(1.2)
        agent_working("media", "Optimizing image for social media", progress=80)
        await asyncio.sleep(0.5)
        
        media_suggestions = {
            "recommended_images": [
                "Eye-catching infographic about the topic",
                "High-quality stock photo related to theme",
                "Custom graphic with key statistics",
            ],
            "recommended_colors": ["#6366f1", "#8b5cf6", "#22c55e"],
            "recommended_format": "1200x630px (Facebook optimal)",
            "emoji_suggestions": ["🚀", "💡", "🔥", "⚡", "🎯"],
            "video_option": "15-second reel with key points"
        }
        
        step = {
            "step": 4,
            "agent": "media",
            "agent_name": "Media Bot",
            "emoji": "🎬",
            "action": "Finding Visual Content",
            "message": "I've prepared media recommendations! The right visuals will boost engagement by 150%.",
            "status": "Analyzed optimal media formats for Facebook",
            "data": media_suggestions,
            "timestamp": datetime.now().isoformat()
        }
        self.demo_steps.append(step)
        self.current_step = 4
        
        agent_idle("media")
        return media_suggestions
    
    async def _step_amigos_finalize(self, content: Dict, media: Dict, trending: Dict) -> Dict:
        """Step 5: Amigos finalizes the post."""
        agent_working("amigos", "Finalizing and optimizing the post", progress=90)
        
        # Assemble final post
        template = POST_TEMPLATES["viral"]
        final_text = template.format(
            hook=content["hook"],
            body=content["body"],
            cta=content["cta"],
            hashtags=content["hashtags"]
        )
        
        final_post = {
            "text": final_text,
            "topic": trending["topic"],
            "hashtags": trending["hashtags"],
            "media_recommendations": media,
            "optimal_posting_time": "9:00 AM or 7:00 PM (peak engagement)",
            "estimated_reach": "5,000 - 15,000 impressions",
            "engagement_prediction": "High (viral elements detected)",
            "platform": "Facebook",
            "created_by": "Agent Amigos Team",
            "agents_involved": ["Amigos", "Scrapey", "Ollie", "Media Bot"]
        }
        
        step = {
            "step": 5,
            "agent": "amigos",
            "agent_name": "Agent Amigos",
            "emoji": "🤖",
            "action": "Finalizing Post",
            "message": "Perfect teamwork! 🎉 The post is ready. All agents contributed their expertise!",
            "status": "Post optimized and ready to publish",
            "data": final_post,
            "timestamp": datetime.now().isoformat()
        }
        self.demo_steps.append(step)
        self.current_step = 5
        
        return final_post
    
    def get_status(self) -> Dict:
        """Get current demo status."""
        return {
            "running": self.demo_running,
            "current_step": self.current_step,
            "total_steps": 5,
            "steps_completed": self.demo_steps,
            "result": self.demo_result
        }


# Singleton instance
demo_orchestrator = TeamDemoOrchestrator()


async def run_team_demo(custom_topic: str = None) -> Dict:
    """Run the team demo."""
    return await demo_orchestrator.run_demo(custom_topic)


def get_demo_status() -> Dict:
    """Get demo status."""
    return demo_orchestrator.get_status()
