"""FastAPI routes for the scraper engine."""
from __future__ import annotations

import re
from fastapi import APIRouter, HTTPException

from models.scraper_models import (
    AISummaryRequest,
    BatchScrapeRequest,
    DynamicScrapeRequest,
    MonitorRequest,
    ScrapeRequest,
)
from agent_mcp.scraper.ai_extractor import aiextractor
from agent_mcp.scraper.dynamic_scraper import dynamic_scraper
from agent_mcp.scraper.scraper_engine import scraper_engine

router = APIRouter(prefix="/scrape", tags=["scrape"])


@router.post("/url")
def scrape_url(payload: ScrapeRequest):
    return scraper_engine.scrape_url(
        url=str(payload.url),
        selectors=payload.selectors,
        include_text=payload.include_text,
        include_links=payload.include_links,
        include_html=payload.include_html,
        max_links=payload.max_links,
        timeout=payload.timeout,
        headers=payload.headers,
    )


@router.post("/batch")
def scrape_batch(payload: BatchScrapeRequest):
    return scraper_engine.scrape_multiple(
        urls=[str(url) for url in payload.urls],
        selectors=payload.selectors,
        include_text=payload.include_text,
        include_links=payload.include_links,
        include_html=payload.include_html,
        timeout=payload.timeout,
    )


@router.post("/monitor")
def monitor(payload: MonitorRequest):
    return scraper_engine.monitor_webpage(
        url=str(payload.url),
        selectors=payload.selectors,
        include_html=payload.include_html,
        include_links=payload.include_links,
    )


@router.post("/dynamic")
async def dynamic(payload: DynamicScrapeRequest):
    try:
        return await dynamic_scraper.scrape(
            url=str(payload.url),
            wait_for_selector=payload.wait_for_selector,
            wait_timeout=payload.wait_timeout,
            actions=[action.dict() for action in payload.actions] if payload.actions else None,
            headless=payload.headless,
            viewport=payload.viewport,
            screenshot=payload.screenshot,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/extract")
def ai_extract(payload: AISummaryRequest):
    result = aiextractor.summarize(
        content=payload.content,
        instructions=payload.instructions,
        max_words=payload.max_words,
    )
    return result


# Simple scrape + SEO summary endpoint (user-friendly)
from pydantic import BaseModel, HttpUrl
from typing import Optional, List

class SimpleScrapeRequest(BaseModel):
    url: HttpUrl
    dynamic: Optional[bool] = False
    max_words: Optional[int] = 400

class NewsStory(BaseModel):
    title: str
    snippet: str
    source: Optional[str] = "Unknown"

class MergeNewsRequest(BaseModel):
    stories: List[NewsStory]
    max_words: Optional[int] = 500

@router.post("/merge-news")
def merge_news(payload: MergeNewsRequest):
    """Merge multiple news snippets into a single flowing narrative."""
    if not payload.stories:
        raise HTTPException(status_code=400, detail="No stories provided")
    
    # Format the input for the LLM
    formatted_stories = ""
    for idx, s in enumerate(payload.stories):
        formatted_stories += f"STORY {idx+1}:\nTitle: {s.title}\nSource: {s.source}\nContent: {s.snippet}\n\n"
        
    instructions = (
        "You are a professional news anchor and editor. Your task is to take the provided news snippets "
        "and merge them into one interesting, flowing narrative story. \n\n"
        "Guidelines:\n"
        "1. Create a catchy, overarching headline.\n"
        "2. Write a cohesive narrative that connects related points seamlessly.\n"
        "3. Use transitions like 'Meanwhile', 'In related developments', or 'From a different perspective'.\n"
        "4. Stay factual based only on the provided content.\n"
        "5. Aim for a professional, engaging tone.\n\n"
        "Output format:\n"
        "TITLE: [Your Headline]\n"
        "STORY: [The flowing narrative]\n"
        "SOURCES: [List sources used]\n"
    )
    
    result = aiextractor.summarize(
        content=formatted_stories,
        instructions=instructions,
        max_words=payload.max_words or 500
    )
    
    return result

@router.post("/simple")
def simple_scrape(payload: SimpleScrapeRequest):
    """Scrape a URL (static or dynamic) and return an SEO-optimized article/story

    This endpoint hides scraping complexity and returns a formatted SEO result:
    - Title (H1)
    - Meta description (≤160 chars)
    - Suggested keywords (comma-separated)
    - Suggested social captions (3 short lines)
    - Full SEO article using headings and short paragraphs
    """
    # Choose scraping backend
    if payload.dynamic:
        scraped = dynamic_scraper.scrape_sync(url=str(payload.url), wait_for_selector="body", wait_timeout=10, headless=True)
    else:
        scraped = scraper_engine.scrape_url(url=str(payload.url), include_text=True, include_links=False, include_html=False)

    if not scraped or not scraped.get("success"):
        raise HTTPException(status_code=400, detail=scraped.get("error") or "Failed to scrape URL")

    content = scraped.get("text") or ""
    if not content.strip():
        raise HTTPException(status_code=400, detail="No textual content found on page")

    instructions = (
        "Produce an SEO-optimized article based on the SOURCE CONTENT. Output MUST include:\n"
        "1) Title (H1) on its own line\n"
        "2) Meta description (<=160 chars) on its own line\n"
        "3) Suggested comma-separated keywords on its own line\n"
        "4) Three short social captions (each on its own line)\n"
        "5) A full article using headings (H2/H3) and short paragraphs, up to {max_words} words.\n"
        "Be concise, factual and focused — do NOT add marketing fluff or unrelated commentary."
    ).format(max_words=payload.max_words or 400)

    summary = aiextractor.summarize(content=content, instructions=instructions, max_words=payload.max_words or 400)

    # Graceful fallback if LLM is not configured or fails — produce a simple SEO structure
    if not summary.get("success"):
        err = summary.get("error") or str(summary.get("fallback") or "")
        # Try to build lightweight SEO output from scraped content
        txt = content.strip()
        meta = (scraped.get("metadata") or {}).get("description") if scraped.get("metadata") else None
        title = (scraped.get("metadata") or {}).get("title") or (txt[:80].split("\n")[0])
        # Simple sentence split for captions
        import re
        sents = re.split(r"(?<=[.!?])\s+", txt)
        captions = [sents[i].strip() for i in range(min(3, len(sents)))] if sents else []
        # Simple keywords: top frequent words excluding common stopwords
        stop = set(["the","and","a","to","of","in","is","for","on","that","this","with","as","are","it","was","by","from","or","an","be","at"]) 
        words = re.findall(r"\b[a-zA-Z]{4,}\b", txt.lower())
        freqs = {}
        for w in words:
            if w in stop: continue
            freqs[w] = freqs.get(w,0)+1
        keys = sorted(freqs.items(), key=lambda x: -x[1])[:10]
        keywords = ", ".join([k for k,_ in keys])
        article = (txt[: payload.max_words * 5 ]).strip()

        fallback_summary = {
            "success": True,
            "generated_by": "fallback_simple",
            "title": title or "Untitled",
            "meta_description": (meta or (article[:150] + "..."))[:160],
            "keywords": keywords,
            "social_captions": captions,
            "article": article,
            "error": err,
        }
        return {"success": True, "source": {"url": str(payload.url)}, "summary": fallback_summary}

    return {"success": True, "source": {'url': str(payload.url)}, "summary": summary}

# Comments summarization endpoint
class CommentsRequest(BaseModel):
    comments: List[str]
    max_words: Optional[int] = 150


@router.post("/comments-summary")
def comments_summary(payload: CommentsRequest):
    content = "\n".join([c.strip() for c in payload.comments or [] if c and c.strip()])
    if not content:
        raise HTTPException(status_code=400, detail="No comments provided")

    instructions = (
        "Summarize the following comment list into:\n"
        "1) A concise overall summary (one short paragraph)\n"
        "2) Top 3 themes or points (comma-separated)\n"
        "3) Suggested short reply to post author (1-2 lines)\n"
        "4) Suggested short Facebook caption highlighting the discussion (1-2 lines)\n"
        "5) 3 suggested hashtags\n"
        "Keep it concise and actionable."
    )

    summary = aiextractor.summarize(content=content, instructions=instructions, max_words=payload.max_words or 150)

    if not summary.get("success"):
        # Simple fallback: top words and short constructs
        import re
        words = re.findall(r"\b[a-zA-Z]{4,}\b", content.lower())
        stop = set(["the","and","with","this","that","have","from","your","you","are","for","not","was","but","they","their","what"])
        freqs = {}
        for w in words:
            if w in stop: continue
            freqs[w] = freqs.get(w, 0) + 1
        top = [k for k, _ in sorted(freqs.items(), key=lambda x: -x[1])[:5]]
        summary = {
            "success": True,
            "summary": " ".join((content[:200].split("\n")[0:2])),
            "themes": top,
            "suggested_reply": (content.split("\n")[0])[:200],
            "fb_caption": (content.split("\n")[0])[:140],
            "hashtags": ", ".join(top[:3]),
            "generated_by": "fallback_comments",
        }
        return {"success": True, "result": summary}

    return {"success": True, "result": summary}


# ═══════════════════════════════════════════════════════════════════════════════
# ENHANCED FACEBOOK POST GENERATOR - AI-powered viral content creation
# ═══════════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel
from typing import Optional

class ViralPostRequest(BaseModel):
    """Request model for viral Facebook post generation."""
    content: str  # Scraped/raw content to transform
    topic: Optional[str] = None  # Optional topic override
    style: Optional[str] = "viral"  # viral, professional, casual, promotional
    audience: Optional[str] = "general"  # general, business, tech, youth
    include_emojis: Optional[bool] = True
    include_cta: Optional[bool] = True
    hashtag_count: Optional[int] = 20
    custom_hashtags: Optional[str] = "#darrellbuttigieg #thesoldiersdream"
    region: Optional[str] = "Global"


@router.post("/generate-viral-post")
async def generate_viral_post(payload: ViralPostRequest):
    """
    Generate a viral Facebook post from scraped content using AI.
    
    This endpoint uses Ollama to analyze content and create engaging,
    shareable posts with proper storytelling, hooks, and CTAs.
    """
    import re
    import json
    
    content = payload.content[:5000]  # Limit content size
    
    # Style configurations
    style_guides = {
        "viral": "Create a highly shareable post with curiosity gaps and emotional triggers",
        "professional": "Create a credible, business-appropriate post that's still engaging",
        "casual": "Create a friendly, conversational post like chatting with a friend",
        "promotional": "Create compelling promotional content with benefits and urgency",
        "educational": "Create valuable, educational content that teaches something useful",
        "inspirational": "Create motivational content that inspires action"
    }
    
    audience_guides = {
        "general": "everyday social media users",
        "business": "professionals and entrepreneurs",
        "tech": "tech enthusiasts and developers",
        "youth": "Gen Z and millennials",
        "filipino": "Filipino audience"
    }
    
    # Extract key elements from content
    def extract_facts(text):
        """Extract numbers, names, and quotes from content."""
        numbers = re.findall(r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:\s*(?:%|percent|million|billion|K|M))?\b', text)
        names = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
        quotes = re.findall(r'["""]([^"""]+)["""]', text)
        return {
            "numbers": numbers[:5],
            "names": names[:5],
            "quotes": quotes[:3]
        }
    
    facts = extract_facts(content)
    
    # Build enhanced AI prompt
    emoji_instruction = "Use strategic emojis to enhance key points" if payload.include_emojis else "Do NOT use any emojis"
    cta_instruction = "End with a compelling call-to-action that drives engagement" if payload.include_cta else "End with a memorable closing thought"
    
    facts_context = ""
    if facts["numbers"]:
        facts_context += f"\n- Key numbers found: {', '.join(facts['numbers'][:3])}"
    if facts["names"]:
        facts_context += f"\n- People/entities mentioned: {', '.join(facts['names'][:3])}"
    if facts["quotes"]:
        facts_context += f"\n- Notable quote: \"{facts['quotes'][0][:100]}...\""
    
    # Handle facts context
    default_facts_msg = "\n- Analyze the content to find key facts, numbers, or interesting elements"
    facts_section = facts_context if facts_context else default_facts_msg
    
    viral_prompt = f"""You are an ELITE VIRAL CONTENT STRATEGIST who has created posts reaching millions.

## 📊 SOURCE CONTENT TO TRANSFORM:
\"\"\"
{content}
\"\"\"

## 🎯 KEY FACTS EXTRACTED:{facts_section}

## 📝 POST REQUIREMENTS:
- STYLE: {style_guides.get(payload.style, style_guides['viral'])}
- AUDIENCE: {audience_guides.get(payload.audience, audience_guides['general'])}
- REGION: {payload.region}
- {emoji_instruction}
- {cta_instruction}

## 🔥 CREATE A VIRAL POST WITH:

### THE HOOK (First 2 lines - CRITICAL!)
Use ONE of these proven formulas:
- **Curiosity Gap**: "This changes everything about..."
- **Specific Number**: Lead with a surprising statistic
- **Bold Statement**: Challenge a common belief
- **Question Hook**: "Has anyone else noticed..."
- **Personal Reveal**: "I've been thinking about this all day..."

### THE BODY (2-3 SHORT paragraphs)
- Tell a STORY, don't just inform
- Include SPECIFIC facts from the content
- Use short sentences (mobile-friendly)
- Make it RELATABLE to the reader
- Bridge from the content to why it matters to THEM

### THE CLOSE
{cta_instruction}

### HASHTAGS
Include exactly {payload.hashtag_count} hashtags.
MUST include: {payload.custom_hashtags}

## ⚠️ CRITICAL RULES:
1. Sound HUMAN and AUTHENTIC - not like AI
2. NO generic phrases ("In today's world", "It's worth noting")
3. SPECIFIC > GENERIC (use actual facts)
4. SHORT paragraphs (max 3 sentences)
5. Mobile-first formatting with line breaks
6. Make it SHAREABLE and discussion-worthy

## OUTPUT:
Write ONLY the final Facebook post. Start directly with the hook. No explanations or labels."""

    try:
        # Try Ollama first
        from tools.ollama_tools import ollama_service
        
        result = await ollama_service.generate(
            prompt=viral_prompt,
            task_type="creative_writing",
            temperature=0.85
        )
        
        if result.get("success") and result.get("response"):
            post_text = result["response"]
            
            # Clean up AI response
            post_text = re.sub(r'^(Here\'s|Here is|I\'ve created|Below is|Sure!|Certainly!|Of course!)[\s\S]*?:\s*', '', post_text, flags=re.IGNORECASE)
            post_text = re.sub(r'^(Here\'s your|Your post|The post|Final post)[\s\S]*?:\s*', '', post_text, flags=re.IGNORECASE)
            post_text = re.sub(r'```[\s\S]*?```', '', post_text)
            post_text = re.sub(r'^#{1,3}\s+', '', post_text, flags=re.MULTILINE)
            post_text = re.sub(r'\n{3,}', '\n\n', post_text)
            post_text = post_text.strip()
            
            # Ensure custom hashtags are included
            if payload.custom_hashtags:
                first_tag = payload.custom_hashtags.split()[0]
                if first_tag and first_tag not in post_text:
                    post_text += f"\n\n{payload.custom_hashtags}"
            
            return {
                "success": True,
                "post": post_text,
                "method": "ollama_ai",
                "facts_extracted": facts,
                "style": payload.style,
                "audience": payload.audience
            }
    
    except Exception as e:
        print(f"[VIRAL_POST] Ollama failed: {e}")
    
    # Fallback: Use ai_extractor
    try:
        fallback_result = aiextractor.summarize(
            content=content,
            instructions=viral_prompt,
            max_words=600
        )
        
        if fallback_result.get("success") and fallback_result.get("summary"):
            post_text = fallback_result["summary"]
            
            # Ensure custom hashtags
            if payload.custom_hashtags and payload.custom_hashtags.split()[0] not in post_text:
                post_text += f"\n\n{payload.custom_hashtags}"
            
            return {
                "success": True,
                "post": post_text,
                "method": "ai_extractor_fallback",
                "facts_extracted": facts
            }
    except Exception as e:
        print(f"[VIRAL_POST] AI extractor fallback failed: {e}")
    
    # Final fallback: Template-based generation
    return _generate_template_post(content, payload, facts)


def _generate_template_post(content: str, payload: ViralPostRequest, facts: dict):
    """Generate a post using enhanced templates when AI fails."""
    import random
    
    # Extract best sentences
    sentences = [s.strip() for s in re.split(r'[.!?]+', content) if 20 < len(s.strip()) < 300]
    sentences = [s for s in sentences if not any(x in s.lower() for x in ['cookie', 'privacy', 'javascript', '<!doctype'])]
    
    # Score sentences
    def score_sentence(s):
        score = 0
        if re.search(r'\d', s): score += 3  # Has numbers
        if re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+', s): score += 2  # Has names
        if 50 < len(s) < 200: score += 1  # Good length
        return score
    
    sentences = sorted(sentences, key=score_sentence, reverse=True)
    
    # Build post
    hooks = [
        "📰 This just came across my feed and I HAD to share...",
        "🔥 Everyone needs to see this. Seriously.",
        "👀 I've been thinking about this all day...",
        "💡 This changes how I see things. Here's why:",
        "⚡ Something big is happening and we need to talk about it...",
    ]
    
    ctas = [
        "\n\n💬 What's your take on this? I want to hear your thoughts!",
        "\n\n👇 Does this resonate with you? Let me know below!",
        "\n\n🤔 Agree or disagree? Let's discuss!",
        "\n\n📢 Tag someone who needs to see this!",
    ]
    
    hook = random.choice(hooks) if payload.include_emojis else random.choice(hooks).replace(hooks[0][0], "").strip()
    main = sentences[0] if sentences else content[:200]
    support = sentences[1] if len(sentences) > 1 else ""
    cta = random.choice(ctas) if payload.include_cta else ""
    
    post = f"""{hook}

{main}

{support}
{cta}

{payload.custom_hashtags} #viral #trending #mustread #share #community"""
    
    return {
        "success": True,
        "post": post.strip(),
        "method": "template_fallback",
        "facts_extracted": facts,
        "note": "Generated using templates (AI unavailable)"
    }
