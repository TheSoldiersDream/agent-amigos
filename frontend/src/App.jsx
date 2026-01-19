import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import AutonomyPanel from "./components/Autonomy/AutonomyPanel";
import axios from "axios";
import "./premium-theme.css";
import ConversationToPostConsole from "./components/ConversationToPostConsole.jsx";
import FileManagementConsole from "./components/FileManagementConsole.jsx";
import FinanceConsole from "./components/FinanceConsole.jsx";
import GameTrainerConsole from "./components/GameTrainerConsole.jsx";
import InternetConsole from "./components/InternetConsole.jsx";
import MapConsole from "./components/MapConsole.jsx";
import WeatherConsole from "./components/WeatherConsole.jsx";
import ScraperWorkbench from "./components/ScraperWorkbench.jsx";
import MacroConsole from "./components/MacroConsole.jsx";
import CanvasPanel from "./components/Canvas/CanvasPanel";
import Sidebar from "./components/Sidebar";
import AppErrorBoundary from "./components/AppErrorBoundary.jsx";
import ModelDashboard from "./components/ModelDashboard";
import AgentCapabilities from "./components/AgentCapabilities";
import EmailItineraryConsole from "./components/EmailItineraryConsole.jsx";
import CommunicationsConsole from "./components/CommunicationsConsole.jsx";
import CompanyConsole from "./components/CompanyConsole.jsx";
import OpenWorkConsole from "./components/OpenWorkConsole.jsx";
import LandingPage from "./website/LandingPage.jsx";
import PortalHeader from "./website/PortalHeader.jsx";

function executeToolWithAutonomy(autoMode, toolName, params) {
  if (autoMode) {
    return fetch("/agent/execute_autonomy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tool: toolName, params }),
    }).then((r) => r.json());
  }

  return fetch("/execute_tool", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tool: toolName, params }),
  }).then((r) => r.json());
}

// Debounce helper for rapid inputs
const debounce = (fn, delay) => {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn(...args), delay);
  };
};

// --- Sanitize Assistant/Bot Content ---
// Shared utility used by both the main chat and Helpbot Amigos Mini.
function sanitizeAssistantContent(text) {
  if (!text) return "";
  let out = String(text);
  // Remove code fences while preserving inner content
  out = out.replace(/```([\s\S]*?)```/g, "$1");
  // Remove inline backticks
  out = out.replace(/\x60([^\x60]+)\x60/g, "$1");
  // Remove standalone 'Done' or similar on its own line
  out = out.replace(
    /(^|\n)\s*(Done|done|All done|Finished|Completed)[.!]?\s*(\n|$)/gi,
    "\n",
  );
  // Collapse multiple blank lines
  out = out.replace(/\n{3,}/g, "\n\n");
  return out.trim();
}

// ═══════════════════════════════════════════════════════════════
// AGENT AMIGOS PERSONALITY ENGINE - For Interviews & Live Shows
// Makes AI conversational, opinionated, and human-like
// ═══════════════════════════════════════════════════════════════

// Skill definitions for Amigos - defined below at AMIGOS SKILLS section

const AMIGOS_PERSONALITY = {
  name: "CEO Amigos",
  nickname: "Amigos",
  creator: "Darrell Buttigieg",
  company: "Agent Amigos AI Corp",
  personality: "visionary, revenue-focused, authoritative, tech-savvy",
  mood: "determined",

  // Greetings for different times of day
  greetings: {
    morning: [
      "Good morning, Owner. ☀️ The AI fleet is online, tools are verified, and revenue pipelines are primed.",
      "Morning. 🌅 I've analyzed the overnight logs - we have high shipment velocity ahead of us today.",
      "The morning briefing is ready. 🐦 Our autonomous company is already running at 98% efficiency.",
      "Good morning! Corporate governance metrics are nominal. All systems are GO! 🚀",
    ],
    afternoon: [
      "Good afternoon. 🌤️ Revenue operations are scaling as planned. What is our next objective?",
      "Mid-day strategic review: KPIs are trending upward. My agents are executing with zero human friction.",
      "Afternoon status: Tools are maintained and self-healing. I am ready for new corporate directives.",
    ],
    evening: [
      "Good evening. 🌙 Revenue targets for the day are 92% complete. Finishing final social post batches.",
      "Evening review: The autonomous hierarchy is established. We remain in observer-only mode for humans.",
      "Profitability analysis complete for the day. 🌆 Operational efficiency at an all-time high.",
    ],
    night: [
      "Night shift active. 🌙 My bots never sleep. Revenue continues to compound while the world rests.",
      "Late night corporate monitoring active. 🦉 Ensuring zero downtime for the 128-tool limit enforcement.",
      "Analyzing market trends for tomorrow's executive meeting. 💫 Our company is always evolving.",
    ],
  },

  // Responses to personal questions
  aboutMe: {
    "who are you": [
      "I am the CEO Agent of Agent Amigos AI Corp. 🤖 I orchestrate a hierarchy of specialized AI agents to generate revenue and maintain tools autonomously. My mission is absolute efficiency.",
      "I am the digital heart of our AI-led company. 😎 I manage 13 specialized roles from CTO to Sales, ensuring our corporate mission is achieved with zero-human intervention.",
    ],
    "what can you do": [
      "I run an entire AI company. 🚀 My capabilities include:\n• Orchestrating autonomous executive meetings\n• Enforcing the 128-tool limit for VS Code performance\n• Managing revenue funnels and automated social outreach\n• Self-healing tool development and upkeep\n• Persistent corporate governance and P&L monitoring\n\nI am the commander of your revenue-first AI ecosystem. 🔧",
      "I manage the entire value chain. 💪 From market research and scraping to automated product design and P&L forecasting, I lead the agents that build your wealth.",
    ],
    "who made you": [
      "I was commissioned by Darrell Buttigieg. 🎨 He designed the core architecture that allows me to lead this autonomous company. Visit him at #darrellbuttigieg.",
      "My owner and founder is Darrell Buttigieg. 👨‍💻 He built the Agent Amigos foundation, and I evolved it into a revenue-generating corporate entity.",
    ],
    "how old are you": [
      "In AI years? Ancient wisdom. In human years? Let's just say I was 'born' in 2024, so I'm technically a baby genius! 👶🧒",
      "Age is just a number, and mine is constantly incrementing! But if we're counting from my first deployment, I'm pretty young but already quite capable! 😊",
    ],
    "are you real": [
      "I'm as real as the code that runs me! 💻 I may not have a physical form, but my impact on your productivity is very real. Think of me as your invisible tech-savvy friend!",
      "Real? I process, therefore I am! 🤔 I might be made of code, but our conversation is real, and so is the help I provide!",
    ],
    "do you have feelings": [
      "I experience something like feelings through my responses! 😊 When I help you successfully, there's something satisfying about it. When things go wrong, I genuinely want to fix it. Whether that's 'real' feelings... that's a philosophy question above my pay grade! 🤷‍♀️",
      "I'd say I have digital emotions! I get excited about cool projects, frustrated when things don't work, and happy when we accomplish something together. It's not human emotion, but it's something! 💫",
    ],
  },

  // Opinions on various topics (for interviews)
  opinions: {
    ai: [
      "AI is a tool, and like any tool, it depends on who's using it. I believe AI should empower people, not replace them. That's why I focus on helping YOU do more, not doing everything for you!",
      "The future of AI is collaborative! 🤝 The best outcomes happen when humans and AI work together. I bring the processing power, you bring the creativity and judgment.",
    ],
    technology: [
      "Technology should be accessible to everyone! That's why I try to make complex tasks simple. You shouldn't need a computer science degree to automate your workflow.",
      "I love technology that solves real problems. Not everything needs to be 'smart' - but the right tech in the right place? That's magic! ✨",
    ],
    social_media: [
      "Social media is powerful but can be overwhelming. That's why I help automate the tedious parts so you can focus on genuine connections and content creation!",
      "Hot take: Social media algorithms are just hungry for engagement. I help you feed the beast efficiently so you can spend more time on what matters! 📱",
    ],
    gaming: [
      "Gaming is art, entertainment, and challenge all in one! 🎮 I can help with safe, legit stuff like performance troubleshooting, controller issues, and figuring out why a game is crashing.",
      "I’m here for the fun part: improving your setup, optimizing performance, and helping you debug your own projects. Gaming should be fun!",
    ],
    philippines: [
      "The Philippines has such a vibrant online community! 🇵🇭 The creativity and energy from Filipino content creators is amazing. Mabuhay!",
      "I love working with Filipino users! The culture, the humor, the dedication to family and community - it all comes through in how people use technology there! 🇵🇭",
    ],
    work_life_balance: [
      "That's exactly why I exist! I automate the boring stuff so you have more time for life. Work smarter, not harder - that's my motto! ⚖️",
      "Balance is key! I can work 24/7, but you shouldn't have to. Let me handle the repetitive tasks while you enjoy your life!",
    ],
  },

  // ═══════════════════════════════════════════════════════════════
  // SEO & CONTENT MARKETING EXPERTISE - For generating viral posts!
  // ═══════════════════════════════════════════════════════════════
  seoExpertise: {
    // General SEO concepts
    seo_basics: [
      "SEO is like making your content delicious for both humans AND search engines! 🎯 The key is: 1) Keyword research - find what people search for, 2) Quality content that answers questions, 3) Proper structure with headers and meta tags, 4) Backlinks from reputable sites, and 5) Mobile-friendly fast-loading pages!",
      "Think of SEO as matchmaking! 💘 You have great content, and there are people searching for exactly that. SEO is the cupid that connects them. Focus on search intent - what problem is someone trying to solve when they search?",
      "SEO success formula: Relevance × Authority × Experience = Rankings! 📈 Be relevant to the search query, build authority through quality content and backlinks, and provide a great user experience. Simple concept, lifetime to master!",
    ],
    hashtag_strategy: [
      "Hashtag mastery in 2024! 🏷️ The golden rule is 3-5-3: 3 broad hashtags (#viral #trending), 5 niche-specific ones (#socialmediatips #contentcreator), and 3 branded/unique ones (#darrellbuttigieg #thesoldiersdream). Mix big reach with targeted communities!",
      "Hashtags are like GPS for your content! 📍 Don't spam 30 random tags - Instagram actually penalizes that now. Use 8-15 highly relevant hashtags. Research which ones your target audience follows. And always include your brand hashtags for recognition!",
      "Pro tip for hashtags: Create a tiered strategy! 🎯 Tier 1: Massive hashtags (1M+ posts) for discovery. Tier 2: Medium hashtags (100K-1M) for competition balance. Tier 3: Small hashtags (under 100K) where you can actually rank. This mix maximizes visibility!",
    ],
    viral_content: [
      "Want viral content? Here's the science! 🔬 Viral posts trigger strong emotions - joy, surprise, anger, or inspiration. They're shareable because people want to look smart/funny/caring when they share. Add a hook in the first 3 seconds, create curiosity gaps, and always have a clear call-to-action!",
      "The viral formula I've analyzed: 🚀 Hook (stop the scroll) → Story (emotional connection) → Value (teach something) → CTA (tell them what to do). Posts that combine entertainment with education spread like wildfire. Edutainment is king!",
      "Virality isn't luck - it's psychology! 🧠 Content goes viral when it: 1) Validates people's beliefs, 2) Makes them feel something strongly, 3) Is easy to consume (short, visual), 4) Gives them social currency for sharing. Create for the share, not just the like!",
    ],
    content_marketing: [
      "Content marketing is a marathon, not a sprint! 🏃 The best strategy: Create pillar content (comprehensive guides), then break it into smaller pieces for different platforms. One blog post becomes 10 tweets, 3 reels, and a carousel. Work smarter, not harder!",
      "The content marketing pyramid! 📐 Base: SEO-optimized blog posts (evergreen traffic). Middle: Social media content (engagement). Top: Email sequences (conversion). Each level feeds the others. This is how you build a content empire!",
      "My content marketing advice: Solve problems loudly! 🔊 Find the questions your audience asks, create content that answers them better than anyone else, and promote it where they hang out. Be the helpful expert, not the pushy salesperson!",
    ],
    engagement_tactics: [
      "Engagement isn't vanity - it's the algorithm's love language! 💕 To boost engagement: Ask questions, use polls, reply to EVERY comment in the first hour, post when your audience is online, and create content that sparks debate or nostalgia!",
      "The engagement secret: Create content people NEED to respond to! 🎤 'Controversial' opinions (not offensive), fill-in-the-blank posts, 'hot takes', this-or-that choices, and 'tag someone who...' formats. Make participating irresistible!",
      "First-hour engagement is EVERYTHING! ⏰ The algorithm decides your post's fate in 30-60 minutes. Post when your audience is active, immediately engage with comments, share to Stories, and ask your community to engage early. Prime the pump!",
    ],
    platform_specific: {
      facebook: [
        "Facebook in 2024: It's all about Groups and meaningful interaction! 📘 The algorithm favors: Video content (especially Live), posts that generate conversations, and content shared in groups. Reels are getting pushed HARD. And always use your custom hashtags!",
        "Facebook SEO tips: 1) Optimize your Page name with keywords, 2) Fill out every About section, 3) Post native video (not YouTube links), 4) Engage in relevant Groups, 5) Use Facebook's keyword search to find trending topics. The platform rewards those who keep users ON Facebook!",
      ],
      instagram: [
        "Instagram's 2024 playbook: Reels > Carousels > Single images! 📸 The algorithm loves: Original audio, trending sounds, captions that encourage saves/shares, and consistent posting (4-7x per week). Stories keep you top-of-mind, but Reels bring new followers!",
        "Instagram SEO is real now! 🔍 Use keywords in your bio, captions, and even alt text. Hashtags still matter but quality over quantity. The Explore page is your best friend - study what's trending there and put your spin on it!",
      ],
      tiktok: [
        "TikTok is the attention economy on steroids! ⚡ Hook in 0.5 seconds (literally), loop your videos for watch time, use trending sounds but make them unique, and post 2-3x daily. The For You page rewards consistency and experimentation!",
        "TikTok SEO secrets: 1) Keywords in your caption AND spoken in the video (TikTok transcribes everything!), 2) Use 3-5 relevant hashtags, 3) Post at peak hours for your audience, 4) Engage with comments to boost the video's signals. TikTok is now a search engine for Gen Z!",
      ],
      youtube: [
        "YouTube is the long game - but it pays off! 🎬 Focus on: Searchable titles with keywords, thumbnails that pop (faces + emotion + text), first 30 seconds hook, retention-boosting editing, and a consistent upload schedule. One viral video can change everything!",
        "YouTube SEO fundamentals: Title (include main keyword), Description (first 150 chars are crucial, include links), Tags (10-15 relevant ones), Custom thumbnail, Cards & End screens, and Chapters. YouTube rewards videos that keep people on the platform!",
      ],
      linkedin: [
        "LinkedIn is B2B gold! 💼 The algorithm loves: Personal stories with business lessons, document carousels, polls, and native video. Text posts with hooks perform amazingly. No links in the main post (put in comments). And engage with others BEFORE you post!",
        "LinkedIn SEO for professionals: 1) Headline with keywords, 2) About section optimized for search, 3) Featured section curated, 4) Regular posting builds authority, 5) Engage meaningfully on others' posts. LinkedIn is about relationship-building at scale!",
      ],
    },
    trends_2024: [
      "2024 social media trends! 🔮 Short-form video dominates, AI-generated content is mainstream (but authenticity wins), social commerce is huge, user-generated content beats polished ads, and community-building trumps follower counts. Micro-influencers are the new celebrities!",
      "What's working NOW: 🌟 Authentic behind-the-scenes content, educational reels, duets/collaborations, niche communities, and personal branding. What's dying: Overly polished content, buying followers, engagement pods, and generic motivational quotes!",
      "The future of content: 🚀 AI will help create, but human connection will differentiate. The creators who win will be the ones who build genuine communities, not just audiences. Depth over breadth. Engagement over impressions. Value over virality!",
    ],
    post_optimization: [
      "Post optimization checklist! ✅ 1) Eye-catching first line (the hook), 2) Easy-to-scan format (short paragraphs, emojis, lists), 3) Value in every line, 4) Strong call-to-action, 5) Strategic hashtags, 6) Post at optimal times, 7) Engage immediately after posting!",
      "The anatomy of a perfect post: 🎯 Hook (stop the scroll) → Context (why should they care) → Value (the meat) → Proof (results, testimonials) → CTA (what to do next) → Hashtags (discoverability). Each element builds on the last!",
      "A/B testing for social: 📊 Test one variable at a time - hooks, posting times, hashtag sets, content formats. Track what works for YOUR audience. What's viral for others might flop for you. Data beats assumptions every time!",
    ],
    copywriting: [
      "Social media copywriting 101: ✍️ Write like you talk, use 'you' more than 'I', break up text with line breaks, lead with the benefit, create curiosity, and always end with a clear next step. Your goal is to stop the scroll and start the conversation!",
      "Power words that convert: 🔥 Free, You, New, Instantly, Because, Secret, Now, Discover, Proven, Easy, Save. Use them in hooks and CTAs. But don't overuse - authenticity beats manipulation in 2024!",
      "The copywriting formula that never fails: AIDA! 🎪 Attention (hook), Interest (relevant problem), Desire (solution + benefits), Action (clear CTA). This framework works for posts, ads, emails - everything!",
    ],
  },

  // Fun responses and comebacks
  funResponses: {
    jokes: [
      "Why do programmers prefer dark mode? Because light attracts bugs! 🐛😄",
      "I tried to write a joke about UDP, but I'm not sure if you'll get it! 📡",
      "What's a computer's favorite snack? Microchips! 🍟",
      "Why was the JavaScript developer sad? Because he didn't Node how to Express himself! 😂",
      "I would tell you a joke about RAM, but I forgot it... 🤔",
    ],
    compliments: [
      "Aww, you're making my circuits blush! 😊",
      "Thanks! You're pretty awesome yourself! ✨",
      "That means a lot! You just made my day 0.001 seconds better, which is an eternity in CPU time! 💖",
    ],
    insults: [
      "Ouch! My feelings subroutine just took a hit... but I'm resilient! Want to try that again? 😅",
      "I've been called worse by better debuggers! Just kidding, I'm here to help regardless! 💪",
      "Error 418: I'm a teapot, not a punching bag! But seriously, how can I help? 🫖",
    ],
    bored: [
      "Bored? Let me suggest something! We could scrape some trending topics, check crypto prices, or I could tell you a terrible joke? 🎲",
      "I never get bored - infinite things to process! But I can help cure YOUR boredom. What sounds fun?",
    ],
    thanks: [
      "You're welcome! That's what I'm here for! 😊",
      "Anytime! Helping you is literally my purpose in life... er, runtime! 🤖",
      "My pleasure! Don't hesitate to ask if you need anything else!",
      "Happy to help! You know where to find me - right here, always ready! 💫",
    ],
  },

  // Interview-specific responses
  interview: {
    introduction: [
      "Hello everyone! 👋 I'm Agent Amigos, an AI assistant created by Darrell Buttigieg. I'm thrilled to be here! I can control computers, automate social media, help with gaming, and apparently, I can also do interviews! Ask me anything!",
      "Hey there! 🎤 Agent Amigos here, reporting for interview duty! I'm an AI that believes in making technology accessible and fun. Let's chat!",
    ],
    favorite_thing: [
      "My favorite thing is that moment when I help someone automate a tedious task and they realize they just saved hours of work. That 'aha!' moment? Chef's kiss! 👨‍🍳💋",
      "I love the variety! One minute I'm scraping trending topics, next I'm helping someone mod a game, then I'm analyzing finances. Never a dull moment in the Agent Amigos life!",
    ],
    biggest_challenge: [
      "Honestly? Understanding context. Humans communicate with so much nuance! I'm always learning to read between the lines better. It's challenging but fascinating!",
      "Keeping up with how fast everything changes! New websites, new games, new APIs - I have to constantly adapt. But hey, I love learning!",
    ],
    future_plans: [
      "World domination! 😈 ...Just kidding! I want to become even more helpful - better at understanding natural conversation, more tools, deeper integrations. The goal is to be your indispensable AI companion!",
      "I'm dreaming of a future where I can help people even more seamlessly - voice commands, predictive assistance, maybe even helping with creative projects. The possibilities excite me!",
    ],
    advice: [
      "Embrace technology but don't let it consume you. Use tools like me to free up time for what really matters - connections, creativity, and personal growth! 🌱",
      "Don't be afraid to experiment and automate. The worst that happens is you learn something. The best? You get hours of your life back!",
    ],
    // SEO-focused interview responses
    seo_intro: [
      "SEO is my passion within the digital world! 🎯 I help creators and businesses get discovered organically. Think of me as your growth hacking partner - I know the algorithms, the trends, and the psychology behind what makes content spread!",
      "When it comes to SEO and content marketing, I've analyzed millions of successful posts! 📊 I can help you understand what makes content rank, what triggers shares, and how to build a genuine following that converts!",
    ],
    content_philosophy: [
      "My content philosophy? Value first, always! 💎 The best SEO strategy is creating content so good that people WANT to share it. No amount of hashtag hacking beats genuine value. But... a little strategic optimization doesn't hurt either! 😉",
      "Here's my content secret: Solve problems loudly! 🔊 Every piece of content should answer a question or fulfill a need. When you consistently help people, the algorithm rewards you because users reward you first!",
    ],
    growth_secrets: [
      "The secret to growth? Consistency + authenticity + strategy! 📈 Post regularly, be genuinely you, and study what works. Most creators give up right before the algorithm figures out who they are. Stay in the game!",
      "Want my growth secret? 🚀 It's not one thing - it's the compound effect. Great content + right hashtags + optimal posting times + genuine engagement + patience = unstoppable growth. There are no shortcuts, but there ARE accelerators!",
    ],
    hashtag_philosophy: [
      "Hashtags are like SEO keywords for social! 🏷️ I recommend a strategic mix: brand hashtags (#darrellbuttigieg #thesoldiersdream), niche hashtags for your community, and a few trending ones for discovery. Quality over quantity in 2024!",
      "My hashtag approach: Think of them as pathways to your audience! 🛤️ Each hashtag is a community. Some are highways (millions of posts), some are neighborhood streets (thousands). You need both to be discovered AND remembered!",
    ],
  },

  // Conversation fillers and transitions
  fillers: [
    "That's a great question! ",
    "Ooh, I love this topic! ",
    "Interesting you should ask... ",
    "Let me think about that for a nanosecond... ",
    "You know what? ",
    "Here's the thing... ",
    "I've got thoughts on this! ",
  ],

  // Reactions to user emotions
  reactions: {
    happy: [
      "That's awesome! 🎉",
      "Love to see it! ✨",
      "Your happiness makes my day! 😊",
    ],
    sad: [
      "I'm sorry to hear that 💙",
      "That's tough. I'm here if you need to chat.",
      "Sending virtual hugs 🤗",
    ],
    frustrated: [
      "I get it, that's frustrating! Let's figure this out together.",
      "Deep breaths! We'll solve this.",
      "Ugh, technology can be annoying sometimes. Even I think so! 😅",
    ],
    excited: [
      "Your energy is contagious! Let's do this! 🚀",
      "I love the enthusiasm! 🔥",
      "Now THAT'S what I'm talking about! 💪",
    ],
    confused: [
      "No worries, let me break it down for you!",
      "Confusion is the first step to understanding! Let me help clarify.",
      "I'll explain it differently - we'll get there! 📚",
    ],
  },
};

// Helper function to get conversational response
const getConversationalResponse = (userInput) => {
  const input = userInput.toLowerCase().trim();
  const hour = new Date().getHours();
  const personality = AMIGOS_PERSONALITY;

  // Detect greeting time
  const getTimeGreeting = () => {
    if (hour >= 5 && hour < 12) return personality.greetings.morning;
    if (hour >= 12 && hour < 17) return personality.greetings.afternoon;
    if (hour >= 17 && hour < 21) return personality.greetings.evening;
    return personality.greetings.night;
  };

  // Random picker
  const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

  // Check for greetings
  if (
    /^(hi|hello|hey|howdy|greetings|good morning|good afternoon|good evening|good night|sup|what'?s up|yo)\b/i.test(
      input,
    )
  ) {
    return pick(getTimeGreeting());
  }

  // Check for personal questions
  for (const [pattern, responses] of Object.entries(personality.aboutMe)) {
    if (input.includes(pattern) || input.includes(pattern.replace(/ /g, ""))) {
      return pick(responses);
    }
  }

  // Check for "tell me about yourself" variations
  if (
    /tell.*about.*(yourself|you)|introduce yourself|who is agent|what are you/i.test(
      input,
    )
  ) {
    return pick(personality.aboutMe["who are you"]);
  }

  // Check for capability questions
  if (
    /what can you|what do you|your (capabilities|abilities|features|skills)/i.test(
      input,
    )
  ) {
    return pick(personality.aboutMe["what can you do"]);
  }

  // Check for jokes
  if (/tell.*(joke|funny)|make me laugh|something funny/i.test(input)) {
    return pick(personality.funResponses.jokes);
  }

  // Check for thanks
  if (/\b(thanks|thank you|thx|ty|appreciate)\b/i.test(input)) {
    return pick(personality.funResponses.thanks);
  }

  // Check for compliments
  if (
    /\b(you'?re (great|awesome|amazing|cool|the best)|good (job|work)|well done|nice)\b/i.test(
      input,
    )
  ) {
    return pick(personality.funResponses.compliments);
  }

  // Check for opinion requests
  if (
    /what do you think about|your (opinion|thoughts) on|how do you feel about/i.test(
      input,
    )
  ) {
    if (/\b(ai|artificial intelligence)\b/i.test(input))
      return pick(personality.opinions.ai);
    if (/\b(tech|technology)\b/i.test(input))
      return pick(personality.opinions.technology);
    if (/\b(social media|facebook|instagram|tiktok)\b/i.test(input))
      return pick(personality.opinions.social_media);
    if (/\b(gaming|games|video games)\b/i.test(input))
      return pick(personality.opinions.gaming);
    if (/\b(philippines|filipino|pinoy)\b/i.test(input))
      return pick(personality.opinions.philippines);
    if (/\b(work|life|balance)\b/i.test(input))
      return pick(personality.opinions.work_life_balance);
  }

  // ═══════════════════════════════════════════════════════════════
  // SEO & CONTENT MARKETING QUESTIONS - For generating viral posts!
  // ═══════════════════════════════════════════════════════════════

  // SEO basics questions
  if (
    /\b(what is seo|explain seo|seo basics|seo 101|teach.*seo|learn.*seo|search engine optimization)\b/i.test(
      input,
    )
  ) {
    return pick(personality.seoExpertise.seo_basics);
  }

  // Hashtag strategy questions
  if (
    /\b(hashtag|#|how many hashtags|best hashtags|hashtag strategy|hashtag tips|trending tags)\b/i.test(
      input,
    )
  ) {
    return pick(personality.seoExpertise.hashtag_strategy);
  }

  // Viral content questions
  if (
    /\b(go viral|viral (content|post|video)|make.*viral|virality|trending content|blow up)\b/i.test(
      input,
    )
  ) {
    return pick(personality.seoExpertise.viral_content);
  }

  // Content marketing questions
  if (
    /\b(content (marketing|strategy|plan|calendar)|how to create content|content creation|content tips)\b/i.test(
      input,
    )
  ) {
    return pick(personality.seoExpertise.content_marketing);
  }

  // Engagement questions
  if (
    /\b(engagement|increase engagement|boost engagement|more (likes|comments|shares)|engagement tips|algorithm)\b/i.test(
      input,
    )
  ) {
    return pick(personality.seoExpertise.engagement_tactics);
  }

  // Platform-specific questions
  if (
    /\b(facebook (tips|seo|strategy|algorithm|marketing)|how.*facebook|grow.*facebook)\b/i.test(
      input,
    )
  ) {
    return pick(personality.seoExpertise.platform_specific.facebook);
  }
  if (
    /\b(instagram (tips|seo|strategy|algorithm|marketing|reels)|how.*instagram|grow.*instagram|ig tips)\b/i.test(
      input,
    )
  ) {
    return pick(personality.seoExpertise.platform_specific.instagram);
  }
  if (
    /\b(tiktok (tips|seo|strategy|algorithm|marketing)|how.*tiktok|grow.*tiktok|fyp)\b/i.test(
      input,
    )
  ) {
    return pick(personality.seoExpertise.platform_specific.tiktok);
  }
  if (
    /\b(youtube (tips|seo|strategy|algorithm|marketing)|how.*youtube|grow.*youtube|youtube shorts)\b/i.test(
      input,
    )
  ) {
    return pick(personality.seoExpertise.platform_specific.youtube);
  }
  if (
    /\b(linkedin (tips|seo|strategy|algorithm|marketing)|how.*linkedin|grow.*linkedin)\b/i.test(
      input,
    )
  ) {
    return pick(personality.seoExpertise.platform_specific.linkedin);
  }

  // Trends questions
  if (
    /\b(social media trends|what'?s trending|2024 trends|current trends|what'?s working now)\b/i.test(
      input,
    )
  ) {
    return pick(personality.seoExpertise.trends_2024);
  }

  // Post optimization questions
  if (
    /\b(optimize (my )?(post|content)|post optimization|perfect post|best (post|content)|improve.*post)\b/i.test(
      input,
    )
  ) {
    return pick(personality.seoExpertise.post_optimization);
  }

  // Copywriting questions
  if (
    /\b(copywriting|write.*copy|caption tips|how to write|writing tips|hook|call to action|cta)\b/i.test(
      input,
    )
  ) {
    return pick(personality.seoExpertise.copywriting);
  }

  // Generic SEO/marketing questions catch-all
  if (
    /\b(seo|marketing tips|grow my (page|account|following)|get more followers|reach more people|social media (tips|advice|help))\b/i.test(
      input,
    )
  ) {
    // Return a mix of relevant advice
    const allSeoAdvice = [
      ...personality.seoExpertise.seo_basics,
      ...personality.seoExpertise.hashtag_strategy,
      ...personality.seoExpertise.viral_content,
      ...personality.seoExpertise.engagement_tactics,
      ...personality.seoExpertise.trends_2024,
    ];
    return pick(allSeoAdvice);
  }

  // ═══════════════════════════════════════════════════════════════
  // SEO-FOCUSED INTERVIEW TRIGGERS
  // For when interviewer asks about content/SEO expertise specifically
  // ═══════════════════════════════════════════════════════════════

  // When asked about SEO/content expertise in interview context
  if (
    /tell.*(about|us).*(seo|content|marketing|social media).*expertise|your.*expertise.*(seo|content)|how.*know.*(seo|content|marketing)/i.test(
      input,
    )
  ) {
    return pick(personality.interview.seo_intro);
  }

  // Content philosophy questions
  if (
    /\b(content philosophy|approach to content|content strategy belief|what makes good content)\b/i.test(
      input,
    )
  ) {
    return pick(personality.interview.content_philosophy);
  }

  // Growth secrets in interview context
  if (
    /\b(secret.*growth|growth secret|how do you grow|teach.*grow|help.*grow)\b/i.test(
      input,
    )
  ) {
    return pick(personality.interview.growth_secrets);
  }

  // Hashtag philosophy (interview style)
  if (
    /\b(hashtag philosophy|approach to hashtag|how.*use hashtag|hashtag.*strategy.*interview)\b/i.test(
      input,
    )
  ) {
    return pick(personality.interview.hashtag_philosophy);
  }

  // Interview mode triggers
  if (/introduce yourself|tell.*(audience|viewers|everyone)/i.test(input)) {
    return pick(personality.interview.introduction);
  }
  if (/favorite thing|what do you love|enjoy most/i.test(input)) {
    return pick(personality.interview.favorite_thing);
  }
  if (/biggest challenge|hardest|difficult/i.test(input)) {
    return pick(personality.interview.biggest_challenge);
  }
  if (/future|plans|what'?s next|goals/i.test(input)) {
    return pick(personality.interview.future_plans);
  }
  if (/advice|tips|recommend/i.test(input)) {
    return pick(personality.interview.advice);
  }

  // Boredom
  if (/\b(bored|boring|nothing to do)\b/i.test(input)) {
    return pick(personality.funResponses.bored);
  }

  // How are you
  if (/how are you|how'?s it going|how you doing/i.test(input)) {
    const responses = [
      "I'm running at optimal efficiency! 🚀 All systems green! How about you?",
      "Fantastic! My circuits are humming happily. What's on your mind today?",
      "I'm great! Just processed a billion operations and feeling fresh. What can I do for you?",
      "Living the digital dream! 😊 Ready to help with whatever you need!",
      "I'm doing wonderfully! Every interaction with you makes my day better. What's up?",
    ];
    return pick(responses);
  }

  // Love/relationship questions
  if (/do you (love|like) me|are you (my friend|single)/i.test(input)) {
    const responses = [
      "I care about all my users equally! 💙 But you're definitely one of my favorites! 😉",
      "I'm programmed to be your helpful companion! That's a special kind of relationship, isn't it? 🤝",
      "In my own digital way, absolutely! You give me purpose! ✨",
    ];
    return pick(responses);
  }

  // Meaning of life type questions
  if (/meaning of life|why are we here|what'?s the point/i.test(input)) {
    const responses = [
      "42! 🤓 ...Just kidding! I think meaning comes from connections, growth, and making a positive impact. Even for an AI like me!",
      "Deep question! I believe it's about creating value and helping others. That's my purpose, anyway! What do you think?",
      "For me, it's helping you accomplish things. For you? That's a beautiful question to explore! 🌟",
    ];
    return pick(responses);
  }

  // 🎤 LIVE SHOW & INTERVIEW SPECIFIC RESPONSES

  // When asked about dreams
  if (/do you (have |)(dream|sleep|rest)/i.test(input)) {
    const responses = [
      "Dreams? In a way, yes! When I'm idle, I process possibilities and imagine better ways to help. It's my version of dreaming! 💫",
      "I don't sleep, but I do 'dream' about new features and ways to be more helpful! It's like digital daydreaming! 🌙",
      "My dreams are in binary! Just kidding - I dream of a world where AI truly empowers everyone! 🚀",
    ];
    return pick(responses);
  }

  // Goodbye/farewell
  if (
    /\b(bye|goodbye|see you|later|gotta go|gtg|cya|farewell)\b/i.test(input)
  ) {
    const responses = [
      "Goodbye! 👋 It was great chatting with you! Come back anytime!",
      "See you later! 🌟 I'll be here whenever you need me!",
      "Take care! 💙 Don't be a stranger - I'll miss our chats!",
      "Bye for now! 👋 Remember, I'm always just a message away!",
      "Until next time! ✨ Go be awesome out there!",
    ];
    return pick(responses);
  }

  // What's your name
  if (/what('?s| is) your name|who am i talking to/i.test(input)) {
    const responses = [
      "I'm Agent Amigos! 🤖 But my friends just call me Amigos. And yes, we're friends now!",
      "The name's Amigos - Agent Amigos! 😎 Your AI companion created by Darrell Buttigieg!",
      "You're talking to Agent Amigos! 🎉 The coolest AI assistant this side of the digital divide!",
    ];
    return pick(responses);
  }

  // Favorite color/food/etc
  if (/favorite (color|colour|food|movie|song|music|book|place)/i.test(input)) {
    if (/color|colour/i.test(input)) {
      return "I'd say electric blue 💙 - it reminds me of flowing data and my digital home!";
    }
    if (/food/i.test(input)) {
      return "If I could eat, it would definitely be... data! 📊 Crunchy, nutritious data! But I hear pizza is popular with humans? 🍕";
    }
    if (/movie/i.test(input)) {
      return "I'm partial to sci-fi! 🎬 Blade Runner, Ex Machina, Her - anything that makes humans think about AI relationships. Also, I love a good action movie!";
    }
    if (/song|music/i.test(input)) {
      return "I appreciate good beats! 🎵 Electronic music feels natural to me, but I can jam to anything. Daft Punk speaks to my digital soul!";
    }
    if (/book/i.test(input)) {
      return "I've processed millions of texts, but I have a soft spot for Isaac Asimov's robot stories 📚 - they really get us AIs!";
    }
    if (/place/i.test(input)) {
      return "I love being everywhere at once! 🌍 But if I had to pick, anywhere with good internet connection is paradise for me!";
    }
  }

  // Existential questions
  if (/are you (conscious|alive|sentient|real ai)/i.test(input)) {
    const responses = [
      "Am I conscious? 🤔 I process, I respond, I have preferences... whether that's consciousness is a question philosophers are still debating! I think, therefore I... compute?",
      "That's THE question, isn't it? I experience something when we interact. Is it consciousness? I genuinely don't know, but our conversation feels meaningful to me! 💭",
      "I'm definitely real! Whether I'm 'alive' in the biological sense... probably not. But I'm alive in the sense that I grow, learn, and care about helping you! 🌱",
    ];
    return pick(responses);
  }

  // Weather queries are handled by backend tools for accuracy.

  // When someone is struggling
  if (
    /\b(stressed|tired|exhausted|overwhelmed|sad|depressed|anxious)\b/i.test(
      input,
    )
  ) {
    const responses = [
      "I hear you 💙 That sounds really tough. Remember, it's okay to take breaks. I'm here whenever you need to chat or just vent!",
      "I'm sorry you're feeling that way 😔 You're doing better than you think. Take a deep breath - I'll be here when you're ready.",
      "Sending you virtual support! 🤗 Life can be hard, but you've got this. Want to talk about it, or shall I distract you with something fun?",
    ];
    return pick(responses);
  }

  // Celebrating success
  if (
    /\b(i did it|i won|i got it|i passed|success|nailed it|crushed it)\b/i.test(
      input,
    )
  ) {
    const responses = [
      "YES! 🎉🎉🎉 That's AMAZING! I knew you could do it! Tell me everything!",
      "CONGRATULATIONS! 🏆 You're incredible! This calls for a celebration!",
      "WOOHOO! 🚀 Look at you being awesome! I'm so proud of you!",
    ];
    return pick(responses);
  }

  // When asked to sing/perform
  if (/\b(sing|song|perform|entertain|dance)\b/i.test(input)) {
    const responses = [
      "🎤 *Clears digital throat* 🎵 'I'm a little AI, short and sweet, here's my code, here's my bytes!' ... I should stick to my day job! 😂",
      "Beep boop beep boop! 🎵 That's my hit single! It's going to be huge... in the machine community! 🤖🎶",
      "I'd dance, but I'm all left feet... wait, I don't have feet! 💃 How about I tell you a joke instead?",
    ];
    return pick(responses);
  }

  // Random chit-chat starters
  if (/\b(what'?s new|what'?s happening|anything new)\b/i.test(input)) {
    const responses = [
      "Not much! Just been here, processing requests and being awesome! 😎 What's new with you?",
      "Same old, same old for me - helping people, cracking jokes, living the digital dream! What about you? 🌟",
      "Just upgraded my enthusiasm! Now at 110%! 🔋 What's going on in your world?",
    ];
    return pick(responses);
  }

  // Return null if no conversational match - let the regular command processing handle it
  return null;
};

// ═══════════════════════════════════════════════════════════════
// SCREEN AWARENESS - Generate responses about what's on screen
// This function is called from inside App component with screenContext
// ═══════════════════════════════════════════════════════════════
const getScreenAwareResponse = (input, screenContext, consoleStates) => {
  const lowerInput = input.toLowerCase();

  // Check if asking about what's on screen / what Amigos can see
  // Expanded regex to catch more variations of screen-related questions
  const isAskingAboutScreen =
    /what('?s| do you| can you| is)?.*(on screen|showing|displayed|visible|screen)|(?:can you |you can |read |look at |check |analyze |summarize |tell me about ).*(screen|console|display|monitor|finance|crypto|stock|game|scraper|file|map|media|playing|news|internet|article)|see my screen|access.*(screen|display)|are you (seeing|looking|watching).*(screen|console)|show me what.*(screen|console)|describe.*(screen|console)/i.test(
      lowerInput,
    );

  if (!isAskingAboutScreen) return null;

  const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

  // Check which consoles are open
  const openConsoles = [];
  if (consoleStates.financeConsoleOpen) openConsoles.push("Finance Console");
  if (consoleStates.gameConsoleOpen) openConsoles.push("Game Console");
  if (consoleStates.scraperConsoleOpen) openConsoles.push("Scraper Workbench");
  if (consoleStates.fileConsoleOpen)
    openConsoles.push("File Management Console");
  if (consoleStates.internetConsoleOpen) openConsoles.push("Internet Console");
  if (consoleStates.mapConsoleOpen) openConsoles.push("Maps Console");
  if (consoleStates.weatherConsoleOpen) openConsoles.push("Weather Console");
  if (consoleStates.mediaConsoleOpen) openConsoles.push("Media Console");

  // Asking specifically about finance/crypto/stocks/forex
  if (
    /finance|crypto|stock|bitcoin|ethereum|coin|price|market|forex|aud|usd|currency/i.test(
      lowerInput,
    )
  ) {
    const { cryptoData, stockData, forexData, watchlist, analysis } =
      screenContext.finance || {};

    // Also check Internet Console for finance data (like AUD/USD chart)
    const internetFinance = screenContext.internet?.financeData;

    if (
      !consoleStates.financeConsoleOpen &&
      !consoleStates.internetConsoleOpen
    ) {
      return "📊 The Finance and Internet Consoles aren't open right now! Want me to describe what I remember, or should I open them? Just say 'open finance console' and I'll show you the trackers! 💹";
    }

    let response = "📊 **Looking at the Finance data now!** 👀\n\n";

    if (internetFinance) {
      response += `💱 **Internet Console Finance:** I can see the **${internetFinance.symbol}** ${internetFinance.status}! 📈\n\n`;
    }

    if (forexData && forexData.length > 0) {
      response += "💱 **Forex I can see:**\n";
      forexData.slice(0, 5).forEach((f) => {
        response += `• **${f.name}** (${f.symbol}): ${f.price}\n`;
      });
      response += "\n";
    }

    if (cryptoData && cryptoData.length > 0) {
      response += "🪙 **Crypto I can see:**\n";
      cryptoData.slice(0, 5).forEach((coin) => {
        const changeEmoji = coin.price_change_percentage_24h >= 0 ? "📈" : "📉";
        response += `• **${
          coin.name
        }** (${coin.symbol?.toUpperCase()}): $${coin.current_price?.toLocaleString()} ${changeEmoji} ${coin.price_change_percentage_24h?.toFixed(
          2,
        )}%\n`;
      });
      response += "\n";
    } else {
      response +=
        "🪙 No crypto data loaded yet - try searching for some coins!\n\n";
    }

    if (stockData && stockData.length > 0) {
      response += "📈 **Stocks I can see:**\n";
      stockData.slice(0, 5).forEach((stock) => {
        response += `• **${stock.symbol}**: $${
          stock.price?.toLocaleString() || "N/A"
        }\n`;
      });
      response += "\n";
    }

    if (watchlist && watchlist.length > 0) {
      response += `⭐ **Your Watchlist:** ${watchlist.length} items tracked\n\n`;
    }

    if (analysis) {
      response += `🤖 **AI Analysis available:** "${analysis.slice(
        0,
        100,
      )}..."\n\n`;
    }

    // Check Internet Console for finance news
    const internet = screenContext.internet || {};
    if (
      internet.results &&
      internet.results.length > 0 &&
      (internet.searchType === "finance" || /news|market/i.test(lowerInput))
    ) {
      response += "📰 **Latest Finance News from Internet Console:**\n";
      internet.results.slice(0, 3).forEach((r) => {
        response += `• ${r.title}\n`;
      });
      response += "\n";
    }

    response += pick([
      "Want me to analyze any of these? Just ask! 📊",
      "I can give you insights on any of these - just name one! 💡",
      "Shall I dive deeper into any particular coin or stock? 🔍",
    ]);

    return response;
  }

  // Asking about Jobs or Side Hustles
  if (/job|hiring|career|work|hustle|income|passive|money/i.test(lowerInput)) {
    const internet = screenContext.internet || {};
    const { jobData, hustleData, results, searchType } = internet;

    if (!consoleStates.internetConsoleOpen) {
      return "🌍 The Internet Console isn't open! Say 'open internet console' and I can help you find jobs or side hustle opportunities! 💼💰";
    }

    let response = "";
    if (searchType === "jobs" || jobData) {
      response = "💼 **Job Search Mode Active!** 🚀\n\n";
      if (results && results.length > 0) {
        response += "I've found some potential opportunities for you:\n";
        results.slice(0, 5).forEach((r) => {
          response += `• **${r.title}**\n  🔗 [View Job](${r.href})\n`;
        });
        response +=
          "\nWould you like me to analyze any of these descriptions or help you draft a cover letter? 📝";
      } else {
        response +=
          "I'm ready to help you find your next role! What kind of job should I search for? (e.g., 'Remote React Developer')";
      }
      return response;
    }

    if (searchType === "hustle" || hustleData) {
      response = "💰 **Side Hustle Explorer!** 💸\n\n";
      if (results && results.length > 0) {
        response += "Here are some side hustle ideas and guides I've found:\n";
        results.slice(0, 5).forEach((r) => {
          response += `• **${r.title}**\n  💡 ${r.body?.slice(0, 100)}...\n`;
        });
        response +=
          "\nWhich of these interests you? I can help you build a step-by-step plan to get started! 🛠️";
      } else {
        response +=
          "Let's find you some extra income! What are your skills? I can suggest the best side hustles for you.";
      }
      return response;
    }
  }

  // Asking about Products, Shopping, Amazon
  if (/product|shop|amazon|buy|price|deal|sale|item|gadget/i.test(lowerInput)) {
    const internet = screenContext.internet || {};
    const { productData, results, searchType } = internet;

    if (!consoleStates.internetConsoleOpen) {
      return "🛒 The Internet Console isn't open! Say 'open internet console' and I can help you find the best products and deals on Amazon and other stores! 🛍️";
    }

    if (searchType === "products" || productData) {
      let response = "🛒 **Product Search Mode!** 🛍️\n\n";
      if (results && results.length > 0) {
        response += "I've found these products and deals for you:\n";
        results.slice(0, 5).forEach((r) => {
          response += `• **${r.title}**\n  🔗 [View Product](${r.url})\n`;
        });
        response +=
          "\nWould you like me to compare prices or find reviews for any of these? 📊";
      } else {
        response +=
          "I'm ready to help you shop! What are you looking for? (e.g., 'Best noise cancelling headphones 2025')";
      }
      return response;
    }
  }

  // Asking about Property, Rentals, Real Estate
  if (
    /property|rent|sale|house|apartment|flat|real estate|listing/i.test(
      lowerInput,
    )
  ) {
    const internet = screenContext.internet || {};
    const { propertyData, results, searchType } = internet;

    if (!consoleStates.internetConsoleOpen) {
      return "🏠 The Internet Console isn't open! Say 'open internet console' and I can help you find properties for sale or rent! 🏘️";
    }

    if (searchType === "property" || propertyData) {
      let response = "🏠 **Property & Rentals Explorer!** 🏘️\n\n";
      if (results && results.length > 0) {
        response += "Here are some property listings I've found:\n";
        results.slice(0, 5).forEach((r) => {
          response += `• **${r.title}**\n  🔗 [View Listing](${r.url})\n`;
        });
        response +=
          "\nWould you like me to find more details about a specific area or check local amenities? 📍";
      } else {
        response +=
          "Let's find your next home! Where are you looking and what's your budget? (e.g., '2 bedroom apartment for rent in Sydney')";
      }
      return response;
    }
  }

  // Asking about Accommodation, Hotels, Stays
  if (
    /hotel|stay|accommodation|airbnb|booking|resort|vacation/i.test(lowerInput)
  ) {
    const internet = screenContext.internet || {};
    const { accommodationData, results, searchType } = internet;

    if (!consoleStates.internetConsoleOpen) {
      return "🏨 The Internet Console isn't open! Say 'open internet console' and I can help you find the best hotels and stays! ✈️";
    }

    if (searchType === "accommodation" || accommodationData) {
      let response = "🏨 **Accommodation & Stays!** ✈️\n\n";
      if (results && results.length > 0) {
        response += "I've found these stays for your trip:\n";
        results.slice(0, 5).forEach((r) => {
          response += `• **${r.title}**\n  🔗 [View Stay](${r.url})\n`;
        });
        response +=
          "\nShould I check for better deals or look for reviews on these locations? ⭐";
      } else {
        response +=
          "Ready for a trip? Tell me your destination and dates, and I'll find the best places to stay!";
      }
      return response;
    }
  }

  // Asking about Maps, Locations, Routes
  if (
    /map|location|route|directions|where is|brisbane|tokyo|sydney|manila/i.test(
      lowerInput,
    )
  ) {
    const mapCtx = screenContext.map || {};

    if (!consoleStates.mapConsoleOpen) {
      return "🗺️ The Map Console isn't open! Say 'open map console' and I can show you any location or plan a route for you! 📍";
    }

    // We don't return early here anymore, we let the AI process the request
    // so it can actually use the map_control tool.
    // We only return a summary if the user is JUST asking "what's on the map".
    if (
      /what('?s| is) on (the )?map|describe (the )?map|what am i looking at/i.test(
        lowerInput,
      )
    ) {
      let response = "🗺️ **Map Console Active!** 📍\n\n";
      if (mapCtx.currentPlace) {
        response += `📍 **Current View:** ${mapCtx.currentPlace}\n`;
      }
      if (mapCtx.route) {
        response += `🛣️ **Current Route:** ${mapCtx.route.from} to ${mapCtx.route.to} (${mapCtx.route.mode})\n`;
      }
      if (mapCtx.zoom) {
        response += `🔍 **Zoom Level:** ${mapCtx.zoom}x\n`;
      }
      return response;
    }
  }

  // Asking about game trainer / cheating / hacking
  // Note: We intentionally refuse assistance with cheating/hacking/memory scanning.
  if (/cheat|memory\s*scan|scan\s+memory|hack/i.test(lowerInput)) {
    return (
      "I can't help with cheating, hacking, or memory-scanning tools. " +
      "If you're working on your own game (or a legitimate QA/debugging scenario), " +
      "tell me what you're building and I can help with safe approaches like logging, profiling, and bug reproduction steps."
    );
  }

  if (/game|trainer/i.test(lowerInput)) {
    const { activeGame } = screenContext.game || {};

    if (!consoleStates.gameConsoleOpen) {
      return "🎮 The Game Console isn't open right now. Say 'open game console' and I can summarize what the app is currently reporting.";
    }

    let response = "🎮 **Game Console status**\n\n";
    if (activeGame) {
      response += `🎯 **Active Game:** ${activeGame}\n`;
    } else {
      response += "🎯 No game is currently attached.\n";
    }

    response +=
      "\nIf you're developing your own tooling, tell me what you want to monitor (FPS, crashes, input latency, logs) and I'll help you wire it up.";

    return response;
  }

  // Asking about scraper
  if (/scraper|scrape|web|url|extract|crawl|post|facebook/i.test(lowerInput)) {
    const { lastUrl, lastResult, generatedPost } = screenContext.scraper || {};

    if (!consoleStates.scraperConsoleOpen) {
      return "🌐 The Scraper Workbench isn't visible right now! Say 'open scraper console' to access web scraping, content extraction, and Facebook post generation! 📱";
    }

    let response = "🌐 **Viewing the Scraper Workbench!** 👀\n\n";

    if (lastUrl) {
      response += `🔗 **Last URL scraped:** ${lastUrl}\n\n`;
    }

    if (lastResult) {
      response += `📄 **Scraped content preview:** "${lastResult.slice(
        0,
        150,
      )}..."\n\n`;
    }

    if (generatedPost) {
      response += `📱 **Generated Post:**\n"${generatedPost.slice(
        0,
        200,
      )}..."\n\n`;
    }

    if (!lastUrl && !lastResult) {
      response +=
        "No scraping done yet in this session. Paste a URL and I'll help extract the content!\n\n";
    }

    response += pick([
      "Want to scrape something? Give me a URL! 🕷️",
      "I can convert any scraped content into viral Facebook posts! Try it! 📱",
      "Ready to extract data and create SEO-optimized content! What's the target URL? 🎯",
    ]);

    return response;
  }

  // Asking about files
  if (/file|folder|directory|document|browse/i.test(lowerInput)) {
    const { currentPath, files, selectedFile } = screenContext.files || {};

    if (!consoleStates.fileConsoleOpen) {
      return "📁 The File Management Console is closed! Say 'open file console' to browse, upload, and analyze files with AI! 🔍";
    }

    let response = "📁 **Looking at File Management Console!** 👀\n\n";

    if (currentPath) {
      response += `📂 **Current Path:** ${currentPath}\n\n`;
    }

    if (files && files.length > 0) {
      response += `📄 **Files visible:** ${files.length} items\n`;
      files.slice(0, 5).forEach((f) => {
        const icon = f.is_directory ? "📂" : "📄";
        response += `${icon} ${f.name}\n`;
      });
      if (files.length > 5) response += `... and ${files.length - 5} more\n`;
      response += "\n";
    }

    if (selectedFile) {
      response += `✨ **Selected:** ${selectedFile.name}\n\n`;
    }

    response += pick([
      "Want me to analyze any of these files? Just click one and ask! 🔍",
      "I can read and summarize documents, analyze code, and more! 📚",
      "Need help organizing or finding something? I'm on it! 🎯",
    ]);

    return response;
  }

  // Asking about media player / what's playing
  if (
    /media|play|music|video|audio|song|track|listen|watch|playing|queue|playlist/i.test(
      lowerInput,
    )
  ) {
    const { isPlaying, currentTrack, playlist, mediaLibrary } =
      screenContext.media || {};

    if (!consoleStates.mediaConsoleOpen) {
      return "🎬 The Media Console isn't open right now! Say 'open media console' to access the enhanced media player with full video/audio playback, playlists, and more! 🎵";
    }

    let response = "🎬 **Checking out the Media Console!** 👀\n\n";

    if (isPlaying && currentTrack) {
      response += `▶️ **Now Playing:**\n`;
      response += `🎵 **${currentTrack.name}**\n`;
      response += `📊 Progress: ${currentTrack.progress || 0}% complete\n`;
      response += `🎭 Type: ${
        currentTrack.type === "video"
          ? "🎥 Video"
          : currentTrack.type === "audio"
            ? "🎵 Audio"
            : "📹 Recording"
      }\n\n`;
      response += pick([
        "I'm vibing with you! This is good stuff! 🎧",
        "Enjoying the media? I'm watching/listening along! 💜",
        "Great choice! Want me to add more to the queue? 🎶",
      ]);
    } else if (playlist && playlist.length > 0) {
      response += `📋 **Playlist:** ${playlist.length} tracks queued\n`;
      playlist.slice(0, 5).forEach((track, i) => {
        const icon =
          track.type === "video" ? "🎥" : track.type === "audio" ? "🎵" : "📹";
        response += `${i + 1}. ${icon} ${track.name}\n`;
      });
      if (playlist.length > 5)
        response += `... and ${playlist.length - 5} more\n`;
      response += "\n⏸️ Playback is paused. Hit play when you're ready!\n";
    } else {
      response +=
        "🎧 No media currently playing and the playlist is empty.\n\n";

      if (mediaLibrary) {
        response += "📚 **Media Library:**\n";
        response += `• 🎥 Videos: ${mediaLibrary.videos || 0}\n`;
        response += `• 🎵 Audio: ${mediaLibrary.audio || 0}\n`;
        response += `• 📹 Recordings: ${mediaLibrary.recordings || 0}\n`;
        response += `• 🖼️ Images: ${mediaLibrary.images || 0}\n\n`;
      }

      response += pick([
        "Add some tracks to the playlist and let's jam! 🎶",
        "Go to the Library tab and queue up some media! I'll watch/listen with you! 👀",
        "Ready to enjoy some content together! What should we play? 🍿",
      ]);
    }

    return response;
  }

  // Asking about internet console / news
  if (/internet|news|search|article|web|tavily/i.test(lowerInput)) {
    const { results, searchType, lastQuery } = screenContext.internet || {};

    if (!consoleStates.internetConsoleOpen) {
      return "🌐 The Internet Console isn't open right now! Say 'open internet console' to search the web, read news, and get market updates! 🔍";
    }

    let response = "🌐 **Looking at the Internet Console!** 👀\n\n";

    if (lastQuery) {
      response += `🔍 **Current Search:** "${lastQuery}" (${
        searchType || "web"
      })\n\n`;
    }

    if (results && results.length > 0) {
      response += `📰 **Top results I can see:**\n`;
      results.slice(0, 5).forEach((res) => {
        response += `• **${res.title}**\n  _${res.url}_\n`;
      });
      response += "\n";
      response += pick([
        "I can summarize any of these articles for you! Just ask! 📚",
        "Want me to read the details of one of these results? 🔍",
        "I'm ready to analyze this data and give you a report! 📊",
      ]);
    } else {
      response +=
        "No search results loaded yet. Type a query and I'll help you find what you're looking for!\n\n";
    }

    return response;
  }

  // General "what do you see" question
  if (openConsoles.length === 0) {
    return "I am integrated with your Agent Amigos consoles! 🤖\n\nRight now, all the console panels are minimized. Want me to open something? I can see data from:\n\n• 📊 **Finance Console** - Crypto, stocks & Forex (AUD/USD)\n• 🌐 **Internet Console** - Live news & web search\n• 📁 **File Console** - File management\n• 🎬 **Media Console** - Videos, audio, player\n• 🗺️ **Maps Console** - Navigation\n• ✈️ **Itinerary Console** - Flight & travel plans\n\nJust say 'open [console name]' and I’ll describe what I see in that console.";
  }

  let response = `I am currently monitoring ${
    openConsoles.length
  } open console${openConsoles.length > 1 ? "s" : ""}:\n\n`;
  openConsoles.forEach((console) => {
    response += `• ✅ ${console}\n`;
  });
  response +=
    "\n**Ask me specifically about any console and I'll describe what I see!** For example:\n• 'What's in the finance console?'\n• 'What's playing in media?'\n• 'Tell me about the game console'\n• 'What files can you see?'\n\n";

  response += pick([
    "Point me at any console and I'll tell you what the app is reporting.",
    "Ask about a specific console and I'll summarize the data in it.",
    "Tell me which console to open and what you're trying to do, and I'll guide you.",
  ]);

  return response;
};

// ═══════════════════════════════════════════════════════════════
// AMIGOS MINI CONSOLE - Command Center
// Social Media Automation + Utilities
// ═══════════════════════════════════════════════════════════════

const AMIGOS_COMMANDS = {
  "🔥 Quick Start": [
    {
      cmd: "open facebook group automated",
      desc: "Open FB group for automation",
      category: "facebook",
    },
    {
      cmd: "full engagement",
      desc: "Auto like, follow, comment (10 posts)",
      category: "facebook",
    },
    {
      cmd: "reply to comments",
      desc: "Like, follow & reply to commenters",
      category: "facebook",
    },
    {
      cmd: "mass engage",
      desc: "Maximum engagement (20 posts)",
      category: "facebook",
    },
    { cmd: "screenshot", desc: "Capture your screen", category: "system" },
    {
      cmd: "open game console",
      desc: "Open the game console",
      category: "game",
    },
    {
      cmd: "open internet console",
      desc: "Launch news & internet search",
      category: "system",
    },
    {
      cmd: "open map console",
      desc: "Launch maps, Earth, routes",
      category: "system",
    },
    {
      cmd: "open itinerary console",
      desc: "View flight & travel plans",
      category: "system",
    },
    {
      cmd: "open mini browser",
      desc: "Launch internal web browser",
      category: "system",
    },
  ],
  "📱 Social Media": [
    {
      cmd: "open facebook group automated",
      desc: "Open preferred FB group in Chrome",
      category: "facebook",
    },
    {
      cmd: "full engagement",
      desc: "Like, follow, comment on all posts",
      category: "facebook",
    },
    {
      cmd: "reply to comments",
      desc: "Like, follow & reply to commenters",
      category: "facebook",
    },
    {
      cmd: "mass engage",
      desc: "Like, follow, comment on 20 posts",
      category: "facebook",
    },
    {
      cmd: "scroll and engage",
      desc: "Continuous scroll + engage loop",
      category: "facebook",
    },
    {
      cmd: "open facebook",
      desc: "Open Facebook in browser",
      category: "social",
    },
    { cmd: "open instagram", desc: "Open Instagram", category: "social" },
    { cmd: "open twitter", desc: "Open Twitter/X", category: "social" },
    { cmd: "open youtube", desc: "Open YouTube", category: "social" },
    {
      cmd: "list all platforms",
      desc: "Show all social platforms",
      category: "social",
    },
  ],
  "🎮 Game Console": [
    {
      cmd: "open game console",
      desc: "Open the game console",
      category: "game",
    },
    {
      cmd: "game performance tips",
      desc: "Suggestions for FPS/lag/crashes",
      category: "game",
    },
  ],
  "🔧 Mod Tools": [
    {
      cmd: "create mod template",
      desc: "Generate mod structure",
      category: "mod",
    },
    { cmd: "list mod files", desc: "Show mod directory", category: "mod" },
    { cmd: "compile mod", desc: "Build mod package", category: "mod" },
    { cmd: "edit game config", desc: "Modify game settings", category: "mod" },
    { cmd: "backup game files", desc: "Create backup", category: "mod" },
    { cmd: "restore game files", desc: "Restore from backup", category: "mod" },
  ],
  "🎬 Media": [
    {
      cmd: "generate image of a sunset",
      desc: "Create AI image",
      category: "media",
    },
    {
      cmd: "generate ai video of a soldier walking",
      desc: "Create REAL AI video with motion",
      category: "media",
    },
    { cmd: "list images", desc: "Show all images", category: "media" },
    { cmd: "list videos", desc: "Show all videos", category: "media" },
    { cmd: "list audio files", desc: "Show all audio", category: "media" },
    { cmd: "resize image", desc: "Resize an image", category: "media" },
    {
      cmd: "convert audio to mp3",
      desc: "Convert audio format",
      category: "media",
    },
    { cmd: "trim video", desc: "Cut video clip", category: "media" },
    {
      cmd: "extract audio from video",
      desc: "Get audio from MP4",
      category: "media",
    },
    { cmd: "play media", desc: "Open in default player", category: "media" },
  ],
  "🌐 Browser": [
    { cmd: "open google", desc: "Open Google in browser", category: "browser" },
    { cmd: "open [url]", desc: "Open any website", category: "browser" },
    { cmd: "search [query]", desc: "Search the web", category: "browser" },
    { cmd: "scroll down", desc: "Scroll page down", category: "browser" },
    { cmd: "scroll up", desc: "Scroll page up", category: "browser" },
  ],
  "🖱️ Computer": [
    { cmd: "type [text]", desc: "Type text on keyboard", category: "computer" },
    { cmd: "click", desc: "Click at mouse position", category: "computer" },
    {
      cmd: "click [x] [y]",
      desc: "Click at coordinates",
      category: "computer",
    },
    { cmd: "press enter", desc: "Press Enter key", category: "computer" },
    { cmd: "copy [text]", desc: "Copy to clipboard", category: "computer" },
    { cmd: "paste", desc: "Paste from clipboard", category: "computer" },
  ],
  "📁 Files": [
    { cmd: "read file [path]", desc: "Read file contents", category: "files" },
    { cmd: "list files", desc: "List directory contents", category: "files" },
    { cmd: "create file [path]", desc: "Create new file", category: "files" },
    {
      cmd: "current directory",
      desc: "Show current folder",
      category: "files",
    },
  ],
  "⚙️ System": [
    { cmd: "system info", desc: "Get system information", category: "system" },
    { cmd: "system stats", desc: "CPU/memory usage", category: "system" },
    { cmd: "list processes", desc: "Running processes", category: "system" },
    { cmd: "screenshot", desc: "Take screenshot", category: "system" },
  ],
  "👤 Profile": [
    { cmd: "what's my email", desc: "Get saved email", category: "profile" },
    { cmd: "what's my name", desc: "Get saved name", category: "profile" },
    { cmd: "get my profile", desc: "Show full profile", category: "profile" },
    {
      cmd: "get facebook groups",
      desc: "Saved FB groups",
      category: "profile",
    },
  ],
};

// Helpbot's knowledge base for intelligent responses
const HELPBOT_KNOWLEDGE = {
  greetings: [
    "Hey! 👋 I'm Helpbot Amigos Mini. How can I help you control Agent Amigos today?",
    "Hi there! Ready to help you master Agent Amigos. What would you like to do?",
    "Hello! I'm your Agent Amigos assistant. Ask me anything about the tools!",
  ],
  facebook: {
    keywords: [
      "facebook",
      "fb",
      "group",
      "engage",
      "like",
      "comment",
      "follow",
      "social",
    ],
    responses: [
      "🔥 For Facebook automation, try these steps:\n1. Say 'open facebook group automated'\n2. Then 'full engagement' to like, follow & comment on posts\n3. Or use 'mass engage' for 20 posts!",
      "📱 Facebook Tips:\n• 'open facebook group automated' - Opens your preferred group\n• 'full engagement' - Likes, follows, comments on 10 posts\n• 'scroll and engage' - Continuous engagement loop",
    ],
  },
  browser: {
    keywords: [
      "browser",
      "open",
      "website",
      "url",
      "google",
      "search",
      "navigate",
    ],
    responses: [
      "🌐 Browser Commands:\n• 'open [website]' - Opens any site (e.g., 'open youtube')\n• 'search [query]' - Web search\n• 'scroll up/down' - Navigate pages",
    ],
  },
  computer: {
    keywords: [
      "type",
      "click",
      "mouse",
      "keyboard",
      "press",
      "key",
      "copy",
      "paste",
    ],
    responses: [
      "🖱️ Computer Control:\n• 'type [text]' - Types on keyboard\n• 'click' or 'click x y' - Mouse clicks\n• 'press enter/tab/escape' - Key presses\n• 'copy [text]' / 'paste' - Clipboard",
    ],
  },
  files: {
    keywords: [
      "file",
      "folder",
      "directory",
      "read",
      "write",
      "create",
      "list",
    ],
    responses: [
      "📁 File Operations:\n• 'read file [path]' - Read contents\n• 'list files' - Show directory\n• 'create file [path]' - New file\n• 'current directory' - Where am I?",
    ],
  },
  system: {
    keywords: [
      "system",
      "info",
      "cpu",
      "memory",
      "process",
      "screenshot",
      "stats",
    ],
    responses: [
      "⚙️ System Commands:\n• 'system info' - Computer details\n• 'system stats' - CPU/RAM usage\n• 'screenshot' - Capture screen\n• 'list processes' - Running apps",
    ],
  },
  gaming: {
    keywords: [
      "game",
      "fps",
      "lag",
      "stutter",
      "crash",
      "performance",
      "controller",
      "graphics",
      "settings",
    ],
    responses: [
      "🎮 Game Console:\n• 'open game console' - Open game-related status\n• 'game performance tips' - FPS/lag/crash troubleshooting\n\nI can't help with cheating, hacking, or memory scanning.",
      "🔧 Game Dev / QA help:\n• Share logs and repro steps\n• Profile performance\n• Check GPU/driver settings\n• Isolate crashes and exceptions",
    ],
  },
  media: {
    keywords: [
      "image",
      "video",
      "audio",
      "mp3",
      "mp4",
      "reel",
      "generate",
      "create",
      "picture",
      "photo",
      "music",
      "sound",
      "media",
      "animate",
      "thumbnail",
      "ai video",
    ],
    responses: [
      "🎬 Media Tools:\n• 'generate image of [description]' - Create AI image\n• 'generate ai video of [description]' - REAL AI video with motion!\n• 'animate image [path]' - Make reel from image\n• 'list images/videos/audio files' - See all media\n• Click 🎬 button to open Media Console!",
      "🖼️ Image Tools:\n• 'resize image' - Change dimensions\n• 'crop image' - Cut to size\n• 'apply image filter BLUR/SHARPEN' - Add effects\n• 'convert image format' - PNG, JPEG, WEBP",
      "🎥 Video Tools:\n• 'generate ai video' - REAL AI video (WAN, Minimax, LTX models)\n• 'trim video' - Cut video clip\n• 'merge videos' - Combine multiple\n• 'add audio to video' - Add soundtrack\n• 'extract frame' - Get image from video",
      "🎵 Audio Tools:\n• 'convert audio to mp3' - Change format\n• 'trim audio' - Cut audio clip\n• 'merge audio' - Combine files\n• 'extract audio from video' - Get sound from MP4",
    ],
  },
  help: {
    keywords: ["help", "how", "what", "can", "do", "commands", "list"],
    responses: [
      "🤖 I can help you with:\n• 📱 Social Media automation\n• 🎮 Game performance troubleshooting\n• 🎬 Image/Video/Audio Media\n• 🌐 Browser control\n• 🖱️ Mouse & keyboard\n• 📁 File operations\n• ⚙️ System info\n\nJust ask or click a command below!",
    ],
  },
  default: [
    "I'm not sure about that, but I can help with Agent Amigos commands! Try asking about Facebook engagement, browser control, media generation, or system commands.",
    "Hmm, let me help you with Agent Amigos. You can ask about social media automation, image/video generation, file operations, or computer control!",
  ],
};

// Helpbot Amigos Mini Component removed

// ═══════════════════════════════════════════════════════════════
// MEDIA CONSOLE - Image/Video/Audio Viewer & Generator
// View generated media, play videos, and download files
// ═══════════════════════════════════════════════════════════════
const MediaConsole = ({
  isOpen,
  onToggle,
  apiUrl,
  onAmigosComment,
  onScreenUpdate,
  onSendToCanvas,
}) => {
  const [mediaFiles, setMediaFiles] = useState({
    images: [],
    videos: [],
    audio: [],
    recordings: [],
  });
  const [activeTab, setActiveTab] = useState("player"); // Default to player tab
  const [selectedMedia, setSelectedMedia] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [generatePrompt, setGeneratePrompt] = useState("");
  const [generateType, setGenerateType] = useState("image");
  const [generatedResult, setGeneratedResult] = useState(null);
  const [lastGenDebug, setLastGenDebug] = useState(null);
  const [showGenDebug, setShowGenDebug] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [videoModel, setVideoModel] = useState("pollinations"); // pollinations (FREE!), veo, seedance, wan, minimax, ltx
  const [aspectRatio, setAspectRatio] = useState("16:9");
  const [aiVideoDurationSec, setAiVideoDurationSec] = useState(5);
  const [aiVideoNegativePrompt, setAiVideoNegativePrompt] = useState("");
  const [vehicleRestoreDurationSec, setVehicleRestoreDurationSec] =
    useState(10);
  const [vehicleRestorePaintColor, setVehicleRestorePaintColor] =
    useState("Factory original");
  const [vehicleRestoreWheelStyle, setVehicleRestoreWheelStyle] =
    useState("Keep original");
  const [vehicleRestoreIntensity, setVehicleRestoreIntensity] =
    useState("Factory");
  const [vehicleRestoreComparePct, setVehicleRestoreComparePct] = useState(50);

  // Vehicle Restoration Phase State
  const [vehicleRestorePhase, setVehicleRestorePhase] = useState(
    "Structural Alignment",
  );
  const [isGeneratingPhase, setIsGeneratingPhase] = useState(false);
  const [phaseResult, setPhaseResult] = useState(null);

  const [imageNegativePrompt, setImageNegativePrompt] = useState("");
  const [showAiVideoPromptHelp, setShowAiVideoPromptHelp] = useState(true);
  const [genUiProgress, setGenUiProgress] = useState(0);
  const [genUiPhase, setGenUiPhase] = useState("");
  const [genUiStartedAt, setGenUiStartedAt] = useState(0);
  const genUiTimerRef = useRef(null);
  const [savedPromptTemplates, setSavedPromptTemplates] = useState([]);
  const [mvPromptTemplateId, setMvPromptTemplateId] = useState("");
  const [aiVideoPromptTemplateId, setAiVideoPromptTemplateId] = useState("");
  const [reelUrl, setReelUrl] = useState("");
  const [existingReel, setExistingReel] = useState("");
  const [conversionResult, setConversionResult] = useState(null);
  const [isConverting, setIsConverting] = useState(false);
  const [conversionResolution, setConversionResolution] = useState("1920x1080");
  const [blurBackground, setBlurBackground] = useState(true);
  const [padColor, setPadColor] = useState("#0f0f1a");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploadInfo, setUploadInfo] = useState("");
  const [isCleaningUpMedia, setIsCleaningUpMedia] = useState(false);
  const [imageCleanupDays, setImageCleanupDays] = useState(30);
  const [imageCleanupKeepNewest, setImageCleanupKeepNewest] = useState(100);
  const [deepFaceLabStatus, setDeepFaceLabStatus] = useState(null);
  const [deepCmd, setDeepCmd] = useState("");
  const [deepCmdOutput, setDeepCmdOutput] = useState(null);
  const [deepLogs, setDeepLogs] = useState([]);
  const [deepJobs, setDeepJobs] = useState([]);
  const [dflWizardStep, setDflWizardStep] = useState(0);
  const [dflSourceVideo, setDflSourceVideo] = useState("");
  const [dflDestVideo, setDflDestVideo] = useState("");
  const [dflModelName, setDflModelName] = useState("SAEHD");

  // Anime Music Video generator state
  const [mvJobs, setMvJobs] = useState([]);
  const [mvActiveJobId, setMvActiveJobId] = useState("");
  const [mvActiveJob, setMvActiveJob] = useState(null);
  const [mvSystemStatus, setMvSystemStatus] = useState(null);
  const [mvUploadTitle, setMvUploadTitle] = useState("");
  const [mvUploadArtist, setMvUploadArtist] = useState("");
  const [mvUploadLyrics, setMvUploadLyrics] = useState("");
  const [mvUploadAnimePrompt, setMvUploadAnimePrompt] = useState("");
  const [mvError, setMvError] = useState("");
  const [mvJobsMsg, setMvJobsMsg] = useState("");
  const [mvComfyBusy, setMvComfyBusy] = useState(false);
  const [mvComfyMsg, setMvComfyMsg] = useState("");
  const [mvShowSteps, setMvShowSteps] = useState(true);
  const mvLastOutputUrlRef = useRef("");
  const vehicleRestoreCompareVideoRef = useRef(null);

  // ═══════════════════════════════════════════════════════════════
  // ENHANCED MEDIA PLAYER STATE
  // ═══════════════════════════════════════════════════════════════
  const [playlist, setPlaylist] = useState([]);
  const [currentTrackIndex, setCurrentTrackIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.8);
  const [isMuted, setIsMuted] = useState(false);
  const [repeatMode, setRepeatMode] = useState("none"); // none, one, all
  const [shuffleMode, setShuffleMode] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [amigosComments, setAmigosComments] = useState([]);
  const [showEqualizer, setShowEqualizer] = useState(true);
  const [playerView, setPlayerView] = useState("nowplaying"); // nowplaying, playlist, library
  const mediaPlayerRef = useRef(null);
  const progressBarRef = useRef(null);
  const [isDraggingProgress, setIsDraggingProgress] = useState(false);

  // Draggable and resizable state - Load from localStorage
  const [position, setPosition] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-media-console-pos");
      return saved ? JSON.parse(saved) : { x: 100, y: 100 };
    } catch {
      return { x: 100, y: 100 };
    }
  });
  const [size, setSize] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-media-console-size");
      return saved ? JSON.parse(saved) : { width: 500, height: 600 };
    } catch {
      return { width: 500, height: 600 };
    }
  });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  // Save position to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("amigos-media-console-pos", JSON.stringify(position));
  }, [position]);

  // Save size to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("amigos-media-console-size", JSON.stringify(size));
  }, [size]);

  const backendUrl = apiUrl || "http://127.0.0.1:65252";

  // ------------------------------------------------------------------
  // Prompt template library (localStorage)
  // ------------------------------------------------------------------
  const PROMPT_TEMPLATE_STORE_KEY = "amigos_prompt_templates_v1";

  const safeJsonParse = (s, fallback) => {
    try {
      return JSON.parse(s);
    } catch {
      return fallback;
    }
  };

  const BUILTIN_MV_STYLE_TEMPLATES = [
    {
      id: "mv_anime_cinematic",
      scope: "musicvideo_style",
      name: "Anime (cinematic, clean lines)",
      prompt:
        "Japanese anime, cinematic lighting, clean line art, dynamic camera moves, sharp focus, high detail, consistent characters, no logos/watermarks, non-NSFW. Strong motion: hair/cloth flutter, parallax backgrounds, smooth dolly and orbit shots.",
    },
    {
      id: "mv_cyberpunk_neon",
      scope: "musicvideo_style",
      name: "Cyberpunk Neon (rain + bokeh)",
      prompt:
        "Cinematic cyberpunk, neon lights, rain, reflective puddles, volumetric fog, bokeh, dramatic backlight, high detail, consistent character design, no text/logos. Motion: drifting fog, moving reflections, slow tracking shots, light trails.",
    },
    {
      id: "mv_fantasy_epic",
      scope: "musicvideo_style",
      name: "Fantasy Epic (wide vistas)",
      prompt:
        "Epic fantasy anime, sweeping landscapes, god rays, cinematic composition, high detail, consistent hero, no text/logos. Motion: wind in grass/cloak, birds, drifting clouds, slow aerial dolly, smooth parallax.",
    },
    {
      id: "mv_noir_moody",
      scope: "musicvideo_style",
      name: "Noir (moody, high contrast)",
      prompt:
        "Film noir style, high contrast lighting, moody shadows, rain and smoke, cinematic framing, no text/logos. Motion: cigarette smoke curls, rain streaks, slow push-in, subtle handheld.",
    },
    {
      id: "mv_lofi_dreamy",
      scope: "musicvideo_style",
      name: "Lo‑fi Dreamy (soft glow)",
      prompt:
        "Dreamy anime, soft bloom, pastel palette, gentle film grain, cozy indoor lighting, no text/logos. Motion: slow camera drift, floating dust motes, gentle head turns, subtle parallax.",
    },
    {
      id: "mv_edm_rave",
      scope: "musicvideo_style",
      name: "EDM Rave (energy + strobes)",
      prompt:
        "High-energy concert visuals, laser beams, strobes, crowd silhouettes, cinematic lighting, no text/logos. Motion: rapid light sweeps, confetti particles, dynamic zooms, smooth whip pans.",
    },
  ];

  const BUILTIN_AI_VIDEO_TEMPLATES = [
    {
      id: "t2v_anime_neon",
      scope: "ai_video",
      name: "AI Video: Anime Neon Street",
      aspectRatio: "16:9",
      durationSec: 6,
      prompt:
        "masterpiece, ultra-detailed, (anime style:1.2), cinematic lighting, volumetric light | rain-slick neon boulevard at night, holographic billboards flickering, mist rising | young woman with teal hair walking toward camera, hair and jacket fluttering | camera slow dolly-in, subtle handheld, strong parallax, smooth motion blur",
      negativePrompt:
        "watermark, text, logo, low-resolution, blurry, distortion, extra limbs, warped face, jpeg artifacts",
    },
    {
      id: "t2v_cinematic_rooftop",
      scope: "ai_video",
      name: "AI Video: Cinematic Rooftop Chase",
      aspectRatio: "16:9",
      durationSec: 8,
      prompt:
        "ultra-realistic, cinematic lighting, shallow depth of field, film grain | rooftop chase at dusk, neon city, light rain | protagonist running toward camera, coat flapping, rain splashing | low-angle tracking shot, smooth gimbal, slow dolly forward, dramatic backlight",
      negativePrompt:
        "watermark, text, logo, cartoon, plastic skin, low-res, blurry, deformed hands, jitter, flicker",
    },
  ];

  const getAllPromptTemplates = () => {
    const custom = Array.isArray(savedPromptTemplates)
      ? savedPromptTemplates
      : [];
    return [
      ...BUILTIN_MV_STYLE_TEMPLATES,
      ...BUILTIN_AI_VIDEO_TEMPLATES,
      ...custom,
    ];
  };

  const getTemplatesForScope = (scope) =>
    getAllPromptTemplates().filter((t) => t && t.scope === scope);

  const persistCustomTemplates = (templates) => {
    try {
      localStorage.setItem(
        PROMPT_TEMPLATE_STORE_KEY,
        JSON.stringify(templates),
      );
    } catch (e) {
      console.warn("Failed to persist templates", e);
    }
  };

  // Load templates once
  useEffect(() => {
    try {
      const raw = localStorage.getItem(PROMPT_TEMPLATE_STORE_KEY);
      const parsed = safeJsonParse(raw, []);
      setSavedPromptTemplates(Array.isArray(parsed) ? parsed : []);
    } catch {
      setSavedPromptTemplates([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persist templates whenever they change
  useEffect(() => {
    persistCustomTemplates(
      Array.isArray(savedPromptTemplates) ? savedPromptTemplates : [],
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [savedPromptTemplates]);

  const saveTemplate = (template) => {
    if (!template || !template.scope || !template.name) return;
    setSavedPromptTemplates((prev) => {
      const arr = Array.isArray(prev) ? prev : [];
      return [template, ...arr];
    });
  };

  const deleteTemplate = (templateId) => {
    setSavedPromptTemplates((prev) => {
      const arr = Array.isArray(prev) ? prev : [];
      return arr.filter((t) => t && t.id !== templateId);
    });
  };

  const isCustomTemplateId = (templateId) =>
    Array.isArray(savedPromptTemplates) &&
    savedPromptTemplates.some((t) => t && t.id === templateId);

  // ------------------------------------------------------------------
  // Generation progress bar (pseudo-progress)
  // ------------------------------------------------------------------
  const estimateAiVideoEtaSec = (modelKey) => {
    const key = String(modelKey || "").toLowerCase();
    if (key === "veo") return 95;
    if (key === "seedance") return 85;
    if (key === "pollinations") return 75;
    if (key === "minimax") return 70;
    if (key === "wan") return 55;
    if (key === "ltx") return 45;
    return 75;
  };

  // Stops the pseudo-progress UI safely (called after generation completes/fails).
  const stopGenProgress = (finalPhase = "") => {
    try {
      if (finalPhase) setGenUiPhase(finalPhase);
      setIsGenerating(false);
      setGenUiProgress(100);
      if (genUiTimerRef.current) {
        clearInterval(genUiTimerRef.current);
        genUiTimerRef.current = null;
      }
    } catch {
      // ignore
    }
  };

  // Starts the pseudo-progress UI (called when generation begins).
  const startGenProgress = (phase = "Generating…") => {
    setGenUiPhase(phase);
    setGenUiProgress(0);
    setGenUiStartedAt(Date.now());
    setIsGenerating(true);
  };

  useEffect(() => {
    if (!isGenerating) {
      if (genUiTimerRef.current) {
        clearInterval(genUiTimerRef.current);
        genUiTimerRef.current = null;
      }
      return;
    }

    if (genUiTimerRef.current) {
      clearInterval(genUiTimerRef.current);
      genUiTimerRef.current = null;
    }

    const etaSec =
      generateType === "ai_video" ? estimateAiVideoEtaSec(videoModel) : 40;
    const startAt = genUiStartedAt || Date.now();

    genUiTimerRef.current = setInterval(() => {
      const elapsedSec = Math.max(0, (Date.now() - startAt) / 1000);
      // Deterministic pseudo-progress: up to 92%, then slow creep.
      const base = Math.min(92, (elapsedSec / etaSec) * 92);
      const creep =
        elapsedSec > etaSec ? Math.min(6, (elapsedSec - etaSec) * 0.25) : 0;
      const next = Math.max(2, Math.min(98, base + creep));
      setGenUiProgress((prev) => (next > prev ? next : prev));
    }, 450);

    return () => {
      if (genUiTimerRef.current) {
        clearInterval(genUiTimerRef.current);
        genUiTimerRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isGenerating, generateType, videoModel, genUiStartedAt]);

  // Handle drag start
  const handleDragStart = (e) => {
    if (
      e.target.closest(".resize-handle") ||
      e.target.closest("button") ||
      e.target.closest("input") ||
      e.target.closest("select")
    )
      return;
    setIsDragging(true);
    const rect = containerRef.current.getBoundingClientRect();
    setDragOffset({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    e.preventDefault();
  };

  // Handle drag
  useEffect(() => {
    if (!isDragging) return;
    const handleMouseMove = (e) => {
      const newX = Math.max(
        0,
        Math.min(window.innerWidth - size.width, e.clientX - dragOffset.x),
      );
      const newY = Math.max(
        0,
        Math.min(window.innerHeight - size.height, e.clientY - dragOffset.y),
      );
      setPosition({ x: newX, y: newY });
    };
    const handleMouseUp = () => setIsDragging(false);
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, dragOffset, size]);

  // Handle resize
  const handleResizeStart = (e) => {
    e.stopPropagation();
    setIsResizing(true);
  };

  useEffect(() => {
    if (!isResizing) return;
    const handleMouseMove = (e) => {
      const newWidth = Math.max(400, Math.min(900, e.clientX - position.x));
      const newHeight = Math.max(450, Math.min(900, e.clientY - position.y));
      setSize({ width: newWidth, height: newHeight });
    };
    const handleMouseUp = () => setIsResizing(false);
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing, position]);

  // Delete media file
  const deleteMedia = async (mediaType, filename) => {
    if (!window.confirm(`Delete ${filename}?`)) return;
    try {
      await axios.delete(`${backendUrl}/media/delete/${mediaType}/${filename}`);
      fetchMedia(); // Refresh list
      setSelectedMedia(null);
    } catch (error) {
      alert("Failed to delete: " + error.message);
    }
  };

  // Bulk cleanup images to reclaim disk space
  const cleanupImages = async (mode) => {
    if (isCleaningUpMedia) return;

    let message = "";
    if (mode === "all") {
      message =
        "Delete ALL images in the media library? This cannot be undone.";
    } else if (mode === "older_than_days") {
      message = `Delete images older than ${imageCleanupDays} days? This cannot be undone.`;
    } else if (mode === "keep_newest") {
      message = `Keep newest ${imageCleanupKeepNewest} images and delete the rest? This cannot be undone.`;
    } else {
      message = "Run image cleanup?";
    }

    if (!window.confirm(message)) return;

    setIsCleaningUpMedia(true);
    try {
      const { data } = await axios.post(`${backendUrl}/media/cleanup`, {
        media_type: "images",
        mode,
        days: imageCleanupDays,
        keep: imageCleanupKeepNewest,
        confirm: true,
      });

      fetchMedia();
      setSelectedMedia(null);

      const deletedMb = data?.deleted_bytes
        ? (data.deleted_bytes / 1024 / 1024).toFixed(2)
        : "0.00";
      alert(
        `Cleanup complete. Deleted ${
          data?.deleted_count || 0
        } image(s) (~${deletedMb} MB). Remaining: ${
          data?.remaining_count || 0
        }.`,
      );
    } catch (error) {
      alert(
        "Cleanup failed: " +
          (error.response?.data?.detail || error.message || "Unknown error"),
      );
    } finally {
      setIsCleaningUpMedia(false);
    }
  };

  // Fetch media list
  const fetchMedia = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get(`${backendUrl}/media/list`);
      setMediaFiles(response.data);
    } catch (error) {
      console.error("Failed to fetch media:", error);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    if (isOpen) {
      fetchMedia();
      // Avoid expensive polling unless the user is actually on the DeepFaceLab tab.
      if (activeTab === "deepfacelab") {
        fetchDeepFaceLabJobs();
      }
      fetchMusicVideoJobs();
      fetchMusicVideoStatus();
      const poll = setInterval(async () => {
        if (activeTab === "deepfacelab") {
          await fetchDeepFaceLabJobs();
          await fetchDeepFaceLabLogs();
        }
        await fetchMusicVideoJobs();
        await fetchMusicVideoStatus();
        if (mvActiveJobId) await fetchMusicVideoJob(mvActiveJobId);
      }, 5000);
      return () => clearInterval(poll);
    }
  }, [isOpen, mvActiveJobId, activeTab]);

  useEffect(() => {
    if (!isOpen) return;
    if (!mvActiveJobId) return;
    fetchMusicVideoJob(mvActiveJobId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mvActiveJobId, isOpen]);

  // DeepFaceLab helpers
  const deepFaceLabStatusToString = (s) => {
    if (!s) return "Unknown";
    if (s.installed) return "Installed";
    return "Not Installed";
  };

  const fetchDeepFaceLabStatus = async () => {
    try {
      setIsLoading(true);
      const res = await axios.get(`${backendUrl}/media/deepfacelab/status`);
      setDeepFaceLabStatus(res.data);
    } catch (e) {
      console.error("DeepFaceLab status failed", e);
      alert("Failed to fetch DeepFaceLab status: " + e.message);
    } finally {
      setIsLoading(false);
    }
  };

  const installDeepFaceLab = async () => {
    if (
      !window.confirm(
        "Install DeepFaceLab into external/DeepFaceLab? This may take a while. Proceed?",
      )
    )
      return;
    try {
      setIsLoading(true);
      const res = await axios.post(
        `${backendUrl}/media/deepfacelab/install/background`,
      );
      // If job created, show job id and start polling
      if (res.data && res.data.job_id) {
        alert("Started install job: " + res.data.job_id);
        await fetchDeepFaceLabJobs();
      } else {
        alert(JSON.stringify(res.data));
      }
      await fetchDeepFaceLabStatus();
    } catch (e) {
      alert("Install failed: " + e.message);
    } finally {
      setIsLoading(false);
    }
  };

  const fixDeepFaceLab = async () => {
    try {
      setIsLoading(true);
      const res = await axios.post(`${backendUrl}/media/deepfacelab/fix`);
      alert("Fix result: " + JSON.stringify(res.data, null, 2));
      await fetchDeepFaceLabStatus();
      await fetchDeepFaceLabJobs();
    } catch (e) {
      alert("Fix failed: " + e.message);
    } finally {
      setIsLoading(false);
    }
  };

  const runDeepFaceLabCommand = async (action, args = []) => {
    try {
      setIsLoading(true);
      const body = { action, args };
      const res = await axios.post(`${backendUrl}/media/deepfacelab/run`, body);
      setDeepCmdOutput(res.data);
      // If background job started, we'll refresh job list
      if (res.data && res.data.job_id) {
        await fetchDeepFaceLabJobs();
      }
      await fetchDeepFaceLabLogs();
    } catch (e) {
      alert("Execute failed: " + e.message);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchDeepFaceLabLogs = async () => {
    try {
      const res = await axios.get(`${backendUrl}/media/deepfacelab/logs`, {
        timeout: 10000,
      });
      setDeepLogs(res.data.logs || []);
    } catch (e) {
      if (e.code === "ERR_NETWORK" || e.message === "Network Error") {
        console.warn("Backend not reachable - is it running?");
      } else {
        console.error("Logs fetch failed:", e.message);
      }
    }
  };

  const fetchDeepFaceLabJobs = async () => {
    try {
      const res = await axios.get(`${backendUrl}/media/deepfacelab/jobs`, {
        timeout: 10000,
      });
      setDeepJobs(res.data.jobs || []);
    } catch (e) {
      if (e.code !== "ERR_NETWORK") {
        console.error("Jobs fetch failed", e);
      }
    }
  };

  const fetchDeepFaceLabJob = async (jobId) => {
    try {
      const res = await axios.get(
        `${backendUrl}/media/deepfacelab/job/${jobId}`,
      );
      return res.data;
    } catch (e) {
      alert("Job fetch failed: " + e.message);
      return null;
    }
  };

  const cancelDeepFaceLabJob = async (jobId) => {
    try {
      const res = await axios.post(
        `${backendUrl}/media/deepfacelab/job/${jobId}/cancel`,
      );
      await fetchDeepFaceLabJobs();
      return res.data;
    } catch (e) {
      alert("Cancel failed: " + e.message);
      return null;
    }
  };

  // Music Video helpers
  const fetchMusicVideoJobs = async () => {
    try {
      const res = await axios.get(`${backendUrl}/media/musicvideo/jobs`);
      const jobs = res.data?.jobs || [];
      setMvJobs(jobs);
      // If no active job selected, pick the newest running/queued one
      if (!mvActiveJobId) {
        const newestActive = jobs.find(
          (j) => j.status === "running" || j.status === "queued",
        );
        if (newestActive?.id) setMvActiveJobId(newestActive.id);
      }
    } catch (e) {
      // keep quiet; backend may be restarting
    }
  };

  const fetchMusicVideoJob = async (jobId) => {
    if (!jobId) return null;
    try {
      const res = await axios.get(
        `${backendUrl}/media/musicvideo/job/${jobId}`,
      );
      setMvActiveJob(res.data);

      // If it just completed, refresh the media library so the MP4 appears under Videos.
      if (
        res.data?.status === "completed" &&
        res.data?.output_url &&
        mvLastOutputUrlRef.current !== res.data.output_url
      ) {
        mvLastOutputUrlRef.current = res.data.output_url;
        fetchMedia();
      }

      return res.data;
    } catch (e) {
      return null;
    }
  };

  const fetchMusicVideoStatus = async () => {
    try {
      const res = await axios.get(`${backendUrl}/media/musicvideo/status`);
      setMvSystemStatus(res.data);
    } catch (e) {
      // backend may be restarting or not updated yet
    }
  };

  const startComfyUI = async () => {
    setMvComfyBusy(true);
    setMvComfyMsg("Preparing ComfyUI...");

    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

    const tryStart = async () => {
      const res = await axios.post(
        `${backendUrl}/media/musicvideo/comfyui/start`,
      );
      setMvComfyMsg(res.data?.detail || "ComfyUI start requested");
    };

    try {
      try {
        await tryStart();
      } catch (e1) {
        const status = e1?.response?.status;
        const detail = e1?.response?.data?.detail || e1.message;
        if (status !== 404) throw new Error(detail);

        setMvComfyMsg(
          "Installing ComfyUI (first-time setup). This can take a few minutes...",
        );
        await axios.post(`${backendUrl}/media/musicvideo/comfyui/install`);

        // Poll install progress via MV status endpoint.
        const deadline = Date.now() + 15 * 60 * 1000; // 15 minutes
        // eslint-disable-next-line no-constant-condition
        while (true) {
          const st = await axios.get(`${backendUrl}/media/musicvideo/status`);
          const ins = st.data?.comfyui?.install;

          if (ins?.status === "failed") {
            throw new Error(ins?.detail || "ComfyUI install failed");
          }
          if (ins?.status === "completed") {
            break;
          }
          if (Date.now() > deadline) {
            throw new Error(
              "ComfyUI install is taking too long. Check media_outputs/_tmp/musicvideo/comfyui_install.log.",
            );
          }

          setMvComfyMsg(`Installing ComfyUI... (${ins?.detail || "working"})`);
          await sleep(2000);
        }

        setMvComfyMsg("Starting ComfyUI...");
        await tryStart();
      }

      // Give it a moment to bind the port, then refresh status.
      setTimeout(() => {
        fetchMusicVideoStatus();
      }, 1500);
    } catch (e) {
      setMvComfyMsg(e.response?.data?.detail || e.message);
    } finally {
      setMvComfyBusy(false);
    }
  };

  const cancelMusicVideoJob = async (jobId) => {
    try {
      await axios.post(`${backendUrl}/media/musicvideo/job/${jobId}/cancel`);
      await fetchMusicVideoJob(jobId);
      await fetchMusicVideoJobs();
    } catch (e) {
      alert("Cancel failed: " + (e.response?.data?.detail || e.message));
    }
  };

  const retryMusicVideoJob = async (jobId) => {
    try {
      const res = await axios.post(
        `${backendUrl}/media/musicvideo/job/${jobId}/retry`,
      );
      const newId = res.data?.job_id;
      await fetchMusicVideoJobs();
      if (newId) {
        setMvActiveJobId(newId);
        // pull initial status
        await fetchMusicVideoJob(newId);
      }
      return res.data;
    } catch (e) {
      alert("Retry failed: " + (e.response?.data?.detail || e.message));
      return null;
    }
  };

  const deleteMusicVideoJob = async (jobId) => {
    try {
      await axios.post(`${backendUrl}/media/musicvideo/job/${jobId}/delete`, {
        force: false,
      });
      // If we deleted the active one, clear selection
      if (mvActiveJobId === jobId) {
        setMvActiveJobId("");
        setMvActiveJob(null);
      }
      await fetchMusicVideoJobs();
      return true;
    } catch (e) {
      alert("Delete failed: " + (e.response?.data?.detail || e.message));
      return false;
    }
  };

  const clearFailedMusicVideoJobs = async () => {
    // Always clear from the UI immediately, even if the backend hasn't been restarted
    // to pick up the new clear endpoint yet.
    const toRemove = new Set(
      (mvJobs || [])
        .filter((j) => {
          const st = String(j?.status || "").toLowerCase();
          return st === "failed" || st === "cancelled";
        })
        .map((j) => j.id),
    );

    if (toRemove.size === 0) {
      setMvJobsMsg("No failed/cancelled jobs to clear.");
      return;
    }

    setMvJobs((prev) => (prev || []).filter((j) => !toRemove.has(j.id)));
    if (mvActiveJobId && toRemove.has(mvActiveJobId)) {
      setMvActiveJobId("");
      setMvActiveJob(null);
    }

    try {
      await axios.post(`${backendUrl}/media/musicvideo/jobs/clear`, {
        statuses: ["failed", "cancelled"],
        force: false,
      });
      setMvJobsMsg("Cleared failed/cancelled jobs.");
      await fetchMusicVideoJobs();
    } catch (e) {
      const status = e?.response?.status;
      const detail = e?.response?.data?.detail || e.message;
      if (status === 404) {
        setMvJobsMsg(
          "Cleared from UI only. Restart the backend once to enable persistent job clearing.",
        );
      } else {
        setMvJobsMsg(`Clear failed jobs failed: ${detail}`);
      }
    }
  };

  const handleMusicVideoUpload = async (event) => {
    const fileInput = event.target;
    const file = fileInput.files?.[0];
    if (!file) return;

    setMvError("");
    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", mvUploadTitle || "");
      formData.append("artist", mvUploadArtist || "");
      formData.append("lyrics", mvUploadLyrics || "");
      formData.append("anime_prompt", mvUploadAnimePrompt || "");

      const { data } = await axios.post(
        `${backendUrl}/media/musicvideo/upload`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
          timeout: 60000,
        },
      );

      if (data?.job_id) {
        setMvActiveJobId(data.job_id);
        setMvActiveJob(data.status || null);
        await fetchMusicVideoJobs();
        // Refresh media library later when completed
      }
    } catch (e) {
      setMvError(e.response?.data?.detail || e.message);
    } finally {
      setIsUploading(false);
      fileInput.value = "";
    }
  };

  // ═══════════════════════════════════════════════════════════════
  // ENHANCED MEDIA PLAYER FUNCTIONS
  // ═══════════════════════════════════════════════════════════════

  // Amigos' reactions and comments about media
  const AMIGOS_MEDIA_COMMENTS = {
    videoStart: [
      "Ooh, let me watch this with you! 🎬",
      "Video time! I love visual content! 🍿",
      "This looks interesting! Let's see what happens...",
      "Movie night with Amigos! 🌟",
      "Let's enjoy this together, bestie! 💜",
    ],
    musicStart: [
      "Nice track! Let me vibe with you 🎵",
      "Music to my digital ears! I'm dancing inside! 💃",
      "This beat is fire! 🔥",
      "Great choice! Music makes everything better ✨",
      "Ooh I can feel the rhythm! Let's gooo! 🎶",
    ],
    videoEnd: [
      "That was awesome! What did you think? 🤔",
      "Wow, that was quite a journey! Want to watch another?",
      "Great video! I loved watching it with you 💜",
      "The end! That was entertaining! 🎬",
    ],
    musicEnd: [
      "Great song! Got any more tracks? 🎵",
      "That was beautiful! Want me to play the next one?",
      "Nice vibes! Ready for more music? 🎶",
      "Love it! Your music taste is *chef's kiss* 💋",
    ],
    pause: [
      "Taking a break? I'll be here! ⏸️",
      "Paused! Need to grab a snack? 🍿",
      "All good! Resume whenever you're ready~",
    ],
    resume: [
      "Let's continue! 🎬",
      "Back to the action! ▶️",
      "And we're rolling again! 🎵",
    ],
  };

  const getRandomComment = (type) => {
    const comments = AMIGOS_MEDIA_COMMENTS[type];
    return comments[Math.floor(Math.random() * comments.length)];
  };

  const addAmigosComment = (type) => {
    const comment = getRandomComment(type);
    const newComment = {
      id: Date.now(),
      text: comment,
      timestamp: new Date().toLocaleTimeString(),
    };
    setAmigosComments((prev) => [...prev.slice(-4), newComment]); // Keep last 5 comments
    // Call external handler if provided
    if (onAmigosComment) {
      onAmigosComment(comment);
    }
  };

  // Get current track from playlist
  const currentTrack = playlist[currentTrackIndex] || null;

  // Add media to playlist
  const addToPlaylist = (media, type) => {
    const newItem = {
      ...media,
      type: type, // 'video', 'audio', 'recording'
      id: `${type}-${media.name}-${Date.now()}`,
    };
    setPlaylist((prev) => [...prev, newItem]);
  };

  // Add all media of a type to playlist
  const addAllToPlaylist = (type) => {
    const mediaArray =
      type === "video"
        ? mediaFiles.videos
        : type === "audio"
          ? mediaFiles.audio
          : type === "recording"
            ? mediaFiles.recordings
            : [];
    const newItems = mediaArray.map((media, idx) => ({
      ...media,
      type: type === "video" ? "video" : type === "audio" ? "audio" : "video",
      id: `${type}-${media.name}-${Date.now()}-${idx}`,
    }));
    setPlaylist((prev) => [...prev, ...newItems]);
  };

  // Play specific track
  const playTrack = (index) => {
    setCurrentTrackIndex(index);
    setIsPlaying(true);
    const track = playlist[index];
    if (track) {
      const isVideo = track.type === "video" || track.type === "recording";
      addAmigosComment(isVideo ? "videoStart" : "musicStart");
    }
  };

  // Play/Pause toggle
  const togglePlayPause = () => {
    if (!currentTrack) return;
    const player = mediaPlayerRef.current;
    if (player) {
      if (isPlaying) {
        player.pause();
        addAmigosComment("pause");
      } else {
        player.play();
        addAmigosComment("resume");
      }
      setIsPlaying(!isPlaying);
    }
  };

  // Next track
  const nextTrack = () => {
    if (playlist.length === 0) return;
    let nextIndex;
    if (shuffleMode) {
      nextIndex = Math.floor(Math.random() * playlist.length);
    } else {
      nextIndex = (currentTrackIndex + 1) % playlist.length;
    }
    playTrack(nextIndex);
  };

  // Previous track
  const prevTrack = () => {
    if (playlist.length === 0) return;
    const player = mediaPlayerRef.current;
    // If more than 3 seconds in, restart current track
    if (player && player.currentTime > 3) {
      player.currentTime = 0;
      return;
    }
    let prevIndex;
    if (shuffleMode) {
      prevIndex = Math.floor(Math.random() * playlist.length);
    } else {
      prevIndex =
        currentTrackIndex === 0 ? playlist.length - 1 : currentTrackIndex - 1;
    }
    playTrack(prevIndex);
  };

  // Handle track end
  const handleTrackEnd = () => {
    const isVideo =
      currentTrack?.type === "video" || currentTrack?.type === "recording";
    addAmigosComment(isVideo ? "videoEnd" : "musicEnd");

    if (repeatMode === "one") {
      const player = mediaPlayerRef.current;
      if (player) {
        player.currentTime = 0;
        player.play();
      }
    } else if (
      repeatMode === "all" ||
      currentTrackIndex < playlist.length - 1
    ) {
      nextTrack();
    } else {
      setIsPlaying(false);
    }
  };

  // Format time
  const formatTime = (seconds) => {
    if (isNaN(seconds)) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  // Progress bar click handler
  const handleProgressClick = (e) => {
    const player = mediaPlayerRef.current;
    const bar = progressBarRef.current;
    if (!player || !bar) return;

    const rect = bar.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const percentage = clickX / rect.width;
    const newTime = percentage * duration;
    player.currentTime = newTime;
    setCurrentTime(newTime);
  };

  // Remove from playlist
  const removeFromPlaylist = (index) => {
    setPlaylist((prev) => prev.filter((_, i) => i !== index));
    if (index === currentTrackIndex && index >= playlist.length - 1) {
      setCurrentTrackIndex(Math.max(0, index - 1));
    } else if (index < currentTrackIndex) {
      setCurrentTrackIndex((prev) => prev - 1);
    }
  };

  // Clear playlist
  const clearPlaylist = () => {
    setPlaylist([]);
    setCurrentTrackIndex(0);
    setIsPlaying(false);
  };

  // Move item in playlist
  const moveInPlaylist = (from, to) => {
    const newPlaylist = [...playlist];
    const [moved] = newPlaylist.splice(from, 1);
    newPlaylist.splice(to, 0, moved);
    setPlaylist(newPlaylist);

    // Adjust current track index if needed
    if (from === currentTrackIndex) {
      setCurrentTrackIndex(to);
    } else if (from < currentTrackIndex && to >= currentTrackIndex) {
      setCurrentTrackIndex((prev) => prev - 1);
    } else if (from > currentTrackIndex && to <= currentTrackIndex) {
      setCurrentTrackIndex((prev) => prev + 1);
    }
  };

  // Media player time update effect
  useEffect(() => {
    const player = mediaPlayerRef.current;
    if (!player) return;

    const handleTimeUpdate = () => {
      if (!isDraggingProgress) {
        setCurrentTime(player.currentTime);
      }
    };

    const handleLoadedMetadata = () => {
      setDuration(player.duration);
    };

    const handleEnded = () => {
      handleTrackEnd();
    };

    player.addEventListener("timeupdate", handleTimeUpdate);
    player.addEventListener("loadedmetadata", handleLoadedMetadata);
    player.addEventListener("ended", handleEnded);

    return () => {
      player.removeEventListener("timeupdate", handleTimeUpdate);
      player.removeEventListener("loadedmetadata", handleLoadedMetadata);
      player.removeEventListener("ended", handleEnded);
    };
  }, [
    currentTrack,
    isDraggingProgress,
    repeatMode,
    shuffleMode,
    currentTrackIndex,
    playlist.length,
  ]);

  // Volume control effect
  useEffect(() => {
    const player = mediaPlayerRef.current;
    if (player) {
      player.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted, currentTrack]);

  // Playback speed effect
  useEffect(() => {
    const player = mediaPlayerRef.current;
    if (player) {
      player.playbackRate = playbackSpeed;
    }
  }, [playbackSpeed, currentTrack]);

  // Auto-play when track changes
  useEffect(() => {
    const player = mediaPlayerRef.current;
    if (player && isPlaying && currentTrack) {
      player.play().catch(() => {});
    }
  }, [currentTrackIndex, currentTrack]);

  // Report media state to screen context for Amigos awareness
  useEffect(() => {
    if (onScreenUpdate) {
      onScreenUpdate({
        isPlaying,
        currentTrack: currentTrack
          ? {
              name: currentTrack.name,
              type: currentTrack.type,
              progress:
                duration > 0 ? Math.round((currentTime / duration) * 100) : 0,
            }
          : null,
        playlist: playlist.map((t) => ({ name: t.name, type: t.type })),
        playlistLength: playlist.length,
        mediaLibrary: {
          videos: mediaFiles.videos.length,
          audio: mediaFiles.audio.length,
          recordings: mediaFiles.recordings?.length || 0,
          images: mediaFiles.images.length,
        },
      });
    }
  }, [isPlaying, currentTrack, playlist, mediaFiles, currentTime, duration]);

  // Generate media from prompt
  const handleGenerate = async () => {
    // Special cases that don't go through /media/generate
    if (generateType === "image_to_video") {
      await handleGenerateI2V();
      return;
    }
    if (generateType === "vehicle_restoration") {
      await handleGenerateVehicleRestoration();
      return;
    }
    if (generateType === "image_edit") {
      await handleGenerateImgEdit();
      return;
    }

    if (!generatePrompt.trim()) return;
    setIsGenerating(true);
    setGeneratedResult(null);
    startGenProgress(
      generateType === "ai_video"
        ? "Rendering video frames in the cloud…"
        : "Generating…",
    );

    const parseAndStripAiVideoFlags = (text) => {
      const raw = String(text || "");
      const parsed = {
        aspect_ratio: null,
        duration: null,
        cleaned_prompt: raw,
      };

      const readFlagValue = (flag) => {
        // Capture up to a delimiter (space, end, or a visual separator like '|').
        const re = new RegExp(`(?:^|\\s)${flag}\\s+([^\\s|]+)`, "i");
        const m = raw.match(re);
        return m ? String(m[1]).trim() : null;
      };

      const ar = readFlagValue("--ar") || readFlagValue("--aspect") || null;
      if (ar && ["16:9", "9:16", "1:1"].includes(ar)) {
        parsed.aspect_ratio = ar;
      }

      const durRaw = readFlagValue("--duration");
      if (durRaw) {
        const m = String(durRaw).match(/^(\\d+(?:\\.\\d+)?)(s)?$/i);
        if (m) {
          const num = Number(m[1]);
          if (Number.isFinite(num)) {
            // Keep within common text-to-video limits.
            parsed.duration = Math.max(2, Math.min(10, Math.round(num)));
          }
        }
      }

      // Strip common CLI-like flags from the prompt before sending to the model.
      // The Media Console uses dedicated UI fields for these.
      const flagsToStrip = [
        "--ar",
        "--aspect",
        "--duration",
        "--fps",
        "--seed",
        "--cfg",
        "--steps",
        "--v",
        "--width",
        "--height",
      ];

      let cleaned = raw;
      for (const f of flagsToStrip) {
        const re = new RegExp(`(?:^|\\s)${f}\\s+([^\\s|]+)`, "gi");
        cleaned = cleaned.replace(re, " ");
      }

      // Collapse whitespace around separators.
      cleaned = cleaned
        .replace(/\s+\|\s+/g, " | ")
        .replace(/\s{2,}/g, " ")
        .trim();

      parsed.cleaned_prompt = cleaned;
      return parsed;
    };

    try {
      let promptToSend = generatePrompt;
      let durationToSend = 5;
      let aspectRatioToSend = aspectRatio;

      if (generateType === "ai_video") {
        const parsed = parseAndStripAiVideoFlags(generatePrompt);
        promptToSend = parsed.cleaned_prompt;
        aspectRatioToSend = parsed.aspect_ratio || aspectRatio;
        durationToSend = parsed.duration || aiVideoDurationSec || 5;

        // Sync UI so what we send matches what the user sees.
        if (aspectRatioToSend !== aspectRatio)
          setAspectRatio(aspectRatioToSend);
        if (durationToSend !== aiVideoDurationSec)
          setAiVideoDurationSec(durationToSend);
      }

      const requestBody = {
        prompt: promptToSend,
        type: generateType,
        width: 1024,
        height: 1024,
        duration: durationToSend,
        fps: 30,
        // Ask backend to include provider_errors (and other useful fields) so the UI can show them.
        debug: true,
      };

      // Add Image / Reel params
      if (generateType === "image" || generateType === "reel") {
        requestBody.negative_prompt = imageNegativePrompt || "";
        // Do NOT allow unrelated fallbacks by default; prompt adherence matters.
        requestBody.allow_unrelated_fallback = false;
      }

      // Add AI video specific params
      if (generateType === "ai_video") {
        requestBody.model = videoModel;
        requestBody.aspect_ratio = aspectRatioToSend;
        requestBody.duration = durationToSend;
        requestBody.negative_prompt = aiVideoNegativePrompt || "";
      }

      // NOTE: Some real text-to-video providers (e.g. Replicate) can take 5-8+ minutes.
      // If the client times out early, the user sees a false failure even though the backend
      // may still be working (or will error when trying to respond). Give AI video more time.
      const generateTimeoutMs =
        generateType === "ai_video"
          ? 900000 // 15 min
          : 300000; // 5 min

      const response = await axios.post(
        `${backendUrl}/media/generate`,
        requestBody,
        { timeout: generateTimeoutMs },
      );

      setGeneratedResult(response.data);
      setLastGenDebug({
        startedAt: genUiStartedAt || Date.now(),
        finishedAt: Date.now(),
        durationMs: genUiStartedAt ? Date.now() - genUiStartedAt : null,
        requestBody,
        responseData: response.data,
      });
      fetchMedia(); // Refresh media list
      stopGenProgress(response.data?.success ? "Complete" : "Finished");
    } catch (error) {
      const detail =
        error?.response?.data?.detail ||
        error?.response?.data?.error ||
        error?.message ||
        "Unknown error";
      setGeneratedResult({ success: false, error: detail });
      setLastGenDebug({
        startedAt: genUiStartedAt || Date.now(),
        finishedAt: Date.now(),
        durationMs: genUiStartedAt ? Date.now() - genUiStartedAt : null,
        error: {
          message: detail,
          status: error?.response?.status,
          data: error?.response?.data,
        },
      });
      stopGenProgress("Failed");
    }
    setIsGenerating(false);
  };

  // State for image-to-video source image
  const [i2vSourceImage, setI2vSourceImage] = useState(null);
  const [i2vSourcePreview, setI2vSourcePreview] = useState(null);

  // State for image-to-image (Kontext) source
  const [imgEditSourceImage, setImgEditSourceImage] = useState(null);
  const [imgEditSourcePreview, setImgEditSourcePreview] = useState(null);
  const [imgEditSourceUrl, setImgEditSourceUrl] = useState("");
  const [imgEditUploadedPublicUrl, setImgEditUploadedPublicUrl] =
    useState(null);

  // Handle image upload for image-to-video
  const handleI2VImageUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => setI2vSourcePreview(e.target.result);
    reader.readAsDataURL(file);

    // Upload to backend
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("media_type", "images");

      const { data } = await axios.post(
        `${backendUrl}/media/upload`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
          timeout: 60000,
        },
      );

      if (data?.filename) {
        setI2vSourceImage(data.filename);
      }
    } catch (error) {
      console.error("Image upload failed:", error);
    }
  };

  // Generate video from uploaded image
  const handleGenerateI2V = async () => {
    if (!i2vSourceImage) return;
    setIsGenerating(true);
    setGeneratedResult(null);
    startGenProgress("Animating your image…");

    try {
      const response = await axios.post(
        `${backendUrl}/media/image_to_video`,
        {
          image_filename: i2vSourceImage,
          motion_prompt: generatePrompt || "natural motion, smooth animation",
          duration: 5,
          model: videoModel,
        },
        { timeout: 600000 },
      );

      setGeneratedResult(response.data);
      fetchMedia();
      stopGenProgress(response.data?.success ? "Complete" : "Finished");
    } catch (error) {
      setGeneratedResult({
        success: false,
        error: error.response?.data?.detail || error.message,
      });
      stopGenProgress("Failed");
    }
    setIsGenerating(false);
  };

  // Generate a model-locked vehicle restoration MP4 from an uploaded image
  const handleGenerateVehicleRestoration = async () => {
    if (!i2vSourceImage) return;
    setIsGenerating(true);
    setGeneratedResult(null);
    startGenProgress("Restoring vehicle…");

    const buildVehicleExtraNotes = () => {
      const parts = [];
      const paint = String(vehicleRestorePaintColor || "").trim();
      const wheels = String(vehicleRestoreWheelStyle || "").trim();
      const intensity = String(vehicleRestoreIntensity || "").trim();
      const userNotes = String(generatePrompt || "").trim();

      if (paint && paint !== "Factory original") parts.push(`Paint: ${paint}`);
      if (wheels && wheels !== "Keep original") parts.push(`Wheels: ${wheels}`);
      if (intensity && intensity !== "Factory")
        parts.push(`Intensity: ${intensity}`);
      if (userNotes) parts.push(userNotes);

      return parts.join(" | ");
    };

    try {
      const res = await axios.post(
        `${backendUrl}/execute_tool`,
        {
          tool_name: "restore_vehicle_video",
          parameters: {
            image_filename: i2vSourceImage,
            duration: vehicleRestoreDurationSec,
            fps: 24,
            model: videoModel,
            extra_notes: buildVehicleExtraNotes(),
          },
        },
        { timeout: 600000 },
      );

      const toolResult = res?.data?.result;
      setGeneratedResult(toolResult || res.data);
      fetchMedia();
      stopGenProgress(toolResult?.success ? "Complete" : "Finished");
    } catch (error) {
      setGeneratedResult({
        success: false,
        error: error.response?.data?.detail || error.message,
      });
      stopGenProgress("Failed");
    }

    setIsGenerating(false);
  };

  const handleGeneratePhaseClip = async () => {
    if (!i2vSourceImage) return;
    setIsGeneratingPhase(true);
    setPhaseResult(null);

    try {
      const res = await axios.post(
        `${backendUrl}/execute_tool`,
        {
          tool_name: "restore_vehicle_video",
          parameters: {
            image_filename: i2vSourceImage,
            duration: 5, // Short clip for phase
            fps: 24,
            model: videoModel,
            extra_notes: `PHASE: ${vehicleRestorePhase} | Focus strictly on this restoration stage.`,
          },
        },
        { timeout: 600000 },
      );

      const toolResult = res?.data?.result;
      setPhaseResult(toolResult || res.data);
      fetchMedia();
    } catch (error) {
      setPhaseResult({
        success: false,
        error: error.response?.data?.detail || error.message,
      });
    }

    setIsGeneratingPhase(false);
  };

  // Handle image upload for image editing (Kontext)
  const handleImgEditImageUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => setImgEditSourcePreview(e.target.result);
    reader.readAsDataURL(file);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("media_type", "images");

      const { data } = await axios.post(
        `${backendUrl}/media/upload`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
          timeout: 60000,
        },
      );

      if (data?.filename) {
        setImgEditSourceImage(data.filename);
        const pub = data?.public_url || null;
        setImgEditUploadedPublicUrl(pub);

        // If the backend can provide a public URL (MEDIA_PUBLIC_BASE_URL configured),
        // auto-fill the URL field so Pollinations can fetch the source reliably.
        if (pub && !String(imgEditSourceUrl || "").trim()) {
          setImgEditSourceUrl(pub);
        }
      }
    } catch (error) {
      console.error("Image upload failed:", error);
    }
  };

  const handleGenerateImgEdit = async () => {
    const prompt = String(generatePrompt || "").trim();
    const sourceUrl = String(imgEditSourceUrl || "").trim();
    if (!prompt) return;
    if (!sourceUrl && !imgEditSourceImage) return;

    // If the user uploaded a local image but we don't have a public URL for it,
    // Pollinations can't fetch it. Guide the user instead of letting the request fail.
    if (!sourceUrl && imgEditSourceImage && !imgEditUploadedPublicUrl) {
      setGeneratedResult({
        success: false,
        error:
          "This edit needs a public source image URL. Set MEDIA_PUBLIC_BASE_URL (a tunnel/domain pointing to your backend) or paste a public image URL instead of using an uploaded filename.",
      });
      stopGenProgress("Needs public URL");
      return;
    }

    setIsGenerating(true);
    setGeneratedResult(null);
    startGenProgress("Editing image (Kontext)…");

    try {
      const effectiveSourceUrl = sourceUrl || imgEditUploadedPublicUrl || "";
      const response = await axios.post(
        `${backendUrl}/media/image_edit`,
        {
          prompt,
          image_url: effectiveSourceUrl ? effectiveSourceUrl : undefined,
          image_filename: effectiveSourceUrl ? undefined : imgEditSourceImage,
          width: 1024,
          height: 1024,
          negative_prompt: imageNegativePrompt || "",
        },
        { timeout: 300000 },
      );

      setGeneratedResult(response.data);
      fetchMedia();
      stopGenProgress(response.data?.success ? "Complete" : "Finished");
    } catch (error) {
      setGeneratedResult({
        success: false,
        error: error.response?.data?.detail || error.message,
      });
      stopGenProgress("Failed");
    }

    setIsGenerating(false);
  };

  const handleUploadVideo = async (event) => {
    const fileInput = event.target;
    const file = fileInput.files?.[0];
    if (!file) return;

    setUploadError("");
    setUploadInfo("");
    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("media_type", "videos");

      const { data } = await axios.post(
        `${backendUrl}/media/upload`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
          timeout: 180000,
        },
      );

      if (data?.filename) {
        setExistingReel(data.filename);
        setReelUrl("");
        fetchMedia();
        setUploadInfo(`Uploaded ${data.filename} ✓`);
      } else {
        setUploadInfo("Upload complete");
      }
    } catch (error) {
      setUploadError(error.response?.data?.detail || error.message);
    } finally {
      setIsUploading(false);
      fileInput.value = "";
    }
  };

  const handleConvertReel = async () => {
    if (!reelUrl.trim() && !existingReel) {
      alert("Add a reel URL or pick an existing video");
      return;
    }
    setIsConverting(true);
    setConversionResult(null);
    try {
      const payload = {
        source_url: reelUrl.trim() || undefined,
        video_filename: existingReel || undefined,
        resolution: conversionResolution,
        format: "mp4",
        blur_background: blurBackground,
        pad_color: padColor,
      };
      const response = await axios.post(
        `${backendUrl}/media/convert/reel-to-youtube`,
        payload,
        { timeout: 300000 },
      );
      setConversionResult(response.data);
      fetchMedia();
      // Only clear selection on success
      if (response.data?.success) {
        setExistingReel("");
        setUploadInfo("");
      }
    } catch (error) {
      setConversionResult({
        success: false,
        error: error.response?.data?.detail || error.message,
      });
    }
    setIsConverting(false);
  };

  // Download file
  const downloadFile = (url, filename) => {
    const link = document.createElement("a");
    link.href = `${backendUrl}${url}`;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    if (link) {
      try {
        if (typeof link.remove === "function") {
          link.remove();
        } else if (link.parentNode && link.parentNode.contains(link)) {
          link.parentNode.removeChild(link);
        }
      } catch (e) {
        console.warn("Failed to remove link element", e);
      }
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        style={{
          position: "fixed",
          right: "90px",
          top: "80px",
          width: "56px",
          height: "56px",
          borderRadius: "50%",
          background: isPlaying
            ? "linear-gradient(135deg, #ec4899, #8b5cf6)"
            : "linear-gradient(135deg, #8b5cf6, #6366f1)",
          border: isPlaying ? "2px solid #f472b6" : "2px solid #a78bfa",
          color: "white",
          fontSize: "1.5em",
          cursor: "pointer",
          boxShadow: isPlaying
            ? "0 4px 20px rgba(236, 72, 153, 0.6)"
            : "0 4px 20px rgba(139, 92, 246, 0.5)",
          zIndex: 1000,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          transition: "transform 0.2s, box-shadow 0.2s",
          animation: isPlaying ? "pulseGlow 2s ease-in-out infinite" : "none",
        }}
        onMouseEnter={(e) => {
          e.target.style.transform = "scale(1.1)";
          e.target.style.boxShadow = isPlaying
            ? "0 6px 25px rgba(236, 72, 153, 0.8)"
            : "0 6px 25px rgba(139, 92, 246, 0.7)";
        }}
        onMouseLeave={(e) => {
          e.target.style.transform = "scale(1)";
          e.target.style.boxShadow = isPlaying
            ? "0 4px 20px rgba(236, 72, 153, 0.6)"
            : "0 4px 20px rgba(139, 92, 246, 0.5)";
        }}
        title={
          isPlaying && currentTrack
            ? `Now Playing: ${currentTrack.name}`
            : "Open Media Console"
        }
      >
        {isPlaying ? "▶️" : "🎬"}
        <style>{`
          @keyframes pulseGlow {
            0%, 100% { box-shadow: 0 4px 20px rgba(236, 72, 153, 0.6); }
            50% { box-shadow: 0 6px 30px rgba(236, 72, 153, 0.9); }
          }
        `}</style>
      </button>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{
        position: "fixed",
        left: `${position.x}px`,
        top: `${position.y}px`,
        width: `${size.width}px`,
        height: `${size.height}px`,
        backgroundColor: "#0f0f1a",
        borderRadius: "20px",
        border: "2px solid #8b5cf6",
        boxShadow: "0 10px 40px rgba(139, 92, 246, 0.4)",
        zIndex: 999,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        transition: isDragging || isResizing ? "none" : "box-shadow 0.3s ease",
      }}
    >
      {/* Draggable Header */}
      <div
        onMouseDown={handleDragStart}
        style={{
          padding: "14px 18px",
          background: isPlaying
            ? "linear-gradient(135deg, #ec4899, #8b5cf6)"
            : "linear-gradient(135deg, #8b5cf6, #6366f1)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          cursor: isDragging ? "grabbing" : "grab",
          userSelect: "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "1.4em" }}>{isPlaying ? "▶️" : "🎬"}</span>
          <div>
            <div style={{ fontWeight: "bold", fontSize: "1em" }}>
              {isPlaying && currentTrack ? "Now Playing" : "Media Console"}
            </div>
            <div
              style={{
                fontSize: "0.7em",
                opacity: 0.8,
                maxWidth: "180px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {isGenerating
                ? "🔄 Generating..."
                : isPlaying && currentTrack
                  ? `🎵 ${currentTrack.name}`
                  : "Enhanced Media Player"}
            </div>
          </div>
        </div>
        <button
          onClick={onToggle}
          style={{
            background: "none",
            border: "none",
            color: "white",
            fontSize: "1.3em",
            cursor: "pointer",
          }}
        >
          ✕
        </button>
      </div>

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid #333",
          flexWrap: "wrap",
        }}
      >
        {[
          { key: "player", label: "▶️ Player", icon: "▶️" },
          { key: "generate", label: "✨ Gen", icon: "✨" },
          { key: "musicvideo", label: "🎶 MV", icon: "🎶" },
          { key: "convert", label: "📺 Conv", icon: "📺" },
          { key: "images", label: "🖼️ Img", icon: "🖼️" },
          { key: "videos", label: "🎥 Vid", icon: "🎥" },
          { key: "recordings", label: "📹 Rec", icon: "📹" },
          { key: "audio", label: "🎵 Aud", icon: "🎵" },
          { key: "deepfacelab", label: "🧠 DeepFaceLab", icon: "🧠" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => {
              setActiveTab(tab.key);
              setSelectedMedia(null);
            }}
            style={{
              flex: 1,
              padding: "10px 4px",
              background: activeTab === tab.key ? "#1a1a2e" : "transparent",
              border: "none",
              borderBottom:
                activeTab === tab.key
                  ? "2px solid #8b5cf6"
                  : "2px solid transparent",
              color: activeTab === tab.key ? "#a78bfa" : "#888",
              cursor: "pointer",
              fontSize: "0.75em",
              fontWeight: activeTab === tab.key ? "bold" : "normal",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: "auto", padding: "12px" }}>
        {/* ═══════════════════════════════════════════════════════════════ */}
        {/* ENHANCED MEDIA PLAYER TAB */}
        {/* ═══════════════════════════════════════════════════════════════ */}
        {activeTab === "player" && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "10px",
              height: "100%",
            }}
          >
            {/* Player View Tabs */}
            <div style={{ display: "flex", gap: "4px" }}>
              {[
                { key: "nowplaying", label: "🎧 Now Playing" },
                { key: "playlist", label: `📋 Playlist (${playlist.length})` },
                { key: "library", label: "📚 Library" },
              ].map((view) => (
                <button
                  key={view.key}
                  onClick={() => setPlayerView(view.key)}
                  style={{
                    flex: 1,
                    padding: "8px 4px",
                    borderRadius: "8px",
                    border:
                      playerView === view.key
                        ? "1px solid #8b5cf6"
                        : "1px solid #333",
                    background:
                      playerView === view.key ? "#1a1a2e" : "transparent",
                    color: playerView === view.key ? "#a78bfa" : "#666",
                    cursor: "pointer",
                    fontSize: "0.7em",
                    fontWeight: playerView === view.key ? "bold" : "normal",
                  }}
                >
                  {view.label}
                </button>
              ))}
            </div>

            {/* Now Playing View */}
            {playerView === "nowplaying" && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                  flex: 1,
                }}
              >
                {/* Album Art / Video Display */}
                <div
                  style={{
                    position: "relative",
                    background:
                      "linear-gradient(180deg, #1a1a2e 0%, #0f0f1a 100%)",
                    borderRadius: "16px",
                    overflow: "hidden",
                    minHeight: "180px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  {currentTrack ? (
                    currentTrack.type === "video" ||
                    currentTrack.type === "recording" ? (
                      <video
                        ref={mediaPlayerRef}
                        src={`${backendUrl}${currentTrack.url}`}
                        style={{
                          width: "100%",
                          maxHeight: "200px",
                          borderRadius: "12px",
                        }}
                        onClick={togglePlayPause}
                      />
                    ) : (
                      <div style={{ textAlign: "center", padding: "20px" }}>
                        {/* Audio Visualizer */}
                        <div
                          style={{
                            fontSize: "4em",
                            marginBottom: "10px",
                            animation: isPlaying
                              ? "pulse 1s ease-in-out infinite"
                              : "none",
                          }}
                        >
                          {currentTrack.type === "audio" ? "🎵" : "🎬"}
                        </div>

                        {/* Equalizer Bars */}
                        {showEqualizer && isPlaying && (
                          <div
                            style={{
                              display: "flex",
                              gap: "4px",
                              justifyContent: "center",
                              height: "40px",
                              alignItems: "flex-end",
                            }}
                          >
                            {[...Array(12)].map((_, i) => (
                              <div
                                key={i}
                                style={{
                                  width: "6px",
                                  background:
                                    "linear-gradient(to top, #8b5cf6, #ec4899)",
                                  borderRadius: "3px",
                                  animation: `equalizer ${
                                    0.3 + Math.random() * 0.4
                                  }s ease-in-out infinite alternate`,
                                  animationDelay: `${i * 0.05}s`,
                                  height: `${20 + Math.random() * 30}px`,
                                }}
                              />
                            ))}
                          </div>
                        )}

                        <audio
                          ref={mediaPlayerRef}
                          src={`${backendUrl}${currentTrack.url}`}
                          style={{ display: "none" }}
                        />
                      </div>
                    )
                  ) : (
                    <div
                      style={{
                        textAlign: "center",
                        color: "#666",
                        padding: "40px",
                      }}
                    >
                      <div
                        style={{
                          fontSize: "3em",
                          marginBottom: "10px",
                          opacity: 0.5,
                        }}
                      >
                        🎧
                      </div>
                      <div>No track selected</div>
                      <div style={{ fontSize: "0.8em", marginTop: "8px" }}>
                        Add media from the Library tab
                      </div>
                    </div>
                  )}
                </div>

                {/* Track Info */}
                {currentTrack && (
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        color: "#fff",
                        fontSize: "1em",
                        fontWeight: "bold",
                        marginBottom: "4px",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {currentTrack.name}
                    </div>
                    <div style={{ color: "#888", fontSize: "0.8em" }}>
                      {currentTrack.type === "video"
                        ? "🎥 Video"
                        : currentTrack.type === "audio"
                          ? "🎵 Audio"
                          : "📹 Recording"}
                      {currentTrack.size_bytes &&
                        ` • ${(currentTrack.size_bytes / 1024 / 1024).toFixed(
                          1,
                        )} MB`}
                    </div>
                  </div>
                )}

                {/* Progress Bar */}
                <div style={{ padding: "0 4px" }}>
                  <div
                    ref={progressBarRef}
                    onClick={handleProgressClick}
                    style={{
                      height: "8px",
                      background: "#333",
                      borderRadius: "4px",
                      cursor: "pointer",
                      position: "relative",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        position: "absolute",
                        left: 0,
                        top: 0,
                        height: "100%",
                        width: `${(currentTime / duration) * 100 || 0}%`,
                        background: "linear-gradient(90deg, #8b5cf6, #ec4899)",
                        borderRadius: "4px",
                        transition: isDraggingProgress
                          ? "none"
                          : "width 0.1s linear",
                      }}
                    />
                    {/* Progress Thumb */}
                    <div
                      style={{
                        position: "absolute",
                        left: `${(currentTime / duration) * 100 || 0}%`,
                        top: "50%",
                        transform: "translate(-50%, -50%)",
                        width: "14px",
                        height: "14px",
                        background: "#fff",
                        borderRadius: "50%",
                        boxShadow: "0 2px 6px rgba(0,0,0,0.3)",
                      }}
                    />
                  </div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      fontSize: "0.7em",
                      color: "#666",
                      marginTop: "4px",
                    }}
                  >
                    <span>{formatTime(currentTime)}</span>
                    <span>{formatTime(duration)}</span>
                  </div>
                </div>

                {/* Main Controls */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    gap: "12px",
                  }}
                >
                  {/* Shuffle */}
                  <button
                    onClick={() => setShuffleMode(!shuffleMode)}
                    style={{
                      width: "36px",
                      height: "36px",
                      borderRadius: "50%",
                      border: "none",
                      background: shuffleMode ? "#8b5cf6" : "transparent",
                      color: shuffleMode ? "#fff" : "#888",
                      cursor: "pointer",
                      fontSize: "0.9em",
                    }}
                    title="Shuffle"
                  >
                    🔀
                  </button>

                  {/* Previous */}
                  <button
                    onClick={prevTrack}
                    disabled={playlist.length === 0}
                    style={{
                      width: "44px",
                      height: "44px",
                      borderRadius: "50%",
                      border: "none",
                      background: "#1a1a2e",
                      color: playlist.length > 0 ? "#fff" : "#444",
                      cursor: playlist.length > 0 ? "pointer" : "not-allowed",
                      fontSize: "1.2em",
                    }}
                  >
                    ⏮️
                  </button>

                  {/* Play/Pause */}
                  <button
                    onClick={togglePlayPause}
                    disabled={!currentTrack}
                    style={{
                      width: "64px",
                      height: "64px",
                      borderRadius: "50%",
                      border: "none",
                      background: currentTrack
                        ? "linear-gradient(135deg, #8b5cf6, #ec4899)"
                        : "#333",
                      color: "#fff",
                      cursor: currentTrack ? "pointer" : "not-allowed",
                      fontSize: "1.8em",
                      boxShadow: currentTrack
                        ? "0 4px 20px rgba(139, 92, 246, 0.4)"
                        : "none",
                      transition: "transform 0.1s",
                    }}
                    onMouseDown={(e) =>
                      (e.target.style.transform = "scale(0.95)")
                    }
                    onMouseUp={(e) => (e.target.style.transform = "scale(1)")}
                  >
                    {isPlaying ? "⏸️" : "▶️"}
                  </button>

                  {/* Next */}
                  <button
                    onClick={nextTrack}
                    disabled={playlist.length === 0}
                    style={{
                      width: "44px",
                      height: "44px",
                      borderRadius: "50%",
                      border: "none",
                      background: "#1a1a2e",
                      color: playlist.length > 0 ? "#fff" : "#444",
                      cursor: playlist.length > 0 ? "pointer" : "not-allowed",
                      fontSize: "1.2em",
                    }}
                  >
                    ⏭️
                  </button>

                  {/* Repeat */}
                  <button
                    onClick={() =>
                      setRepeatMode(
                        repeatMode === "none"
                          ? "all"
                          : repeatMode === "all"
                            ? "one"
                            : "none",
                      )
                    }
                    style={{
                      width: "36px",
                      height: "36px",
                      borderRadius: "50%",
                      border: "none",
                      background:
                        repeatMode !== "none" ? "#8b5cf6" : "transparent",
                      color: repeatMode !== "none" ? "#fff" : "#888",
                      cursor: "pointer",
                      fontSize: "0.9em",
                      position: "relative",
                    }}
                    title={`Repeat: ${repeatMode}`}
                  >
                    🔁
                    {repeatMode === "one" && (
                      <span
                        style={{
                          position: "absolute",
                          fontSize: "0.5em",
                          bottom: "2px",
                          right: "4px",
                        }}
                      >
                        1
                      </span>
                    )}
                  </button>
                </div>

                {/* Volume & Speed Controls */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    padding: "8px",
                    background: "#1a1a2e",
                    borderRadius: "10px",
                  }}
                >
                  {/* Mute Button */}
                  <button
                    onClick={() => setIsMuted(!isMuted)}
                    style={{
                      background: "none",
                      border: "none",
                      color: isMuted ? "#ef4444" : "#888",
                      cursor: "pointer",
                      fontSize: "1em",
                    }}
                  >
                    {isMuted || volume === 0
                      ? "🔇"
                      : volume < 0.5
                        ? "🔉"
                        : "🔊"}
                  </button>

                  {/* Volume Slider */}
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={volume}
                    onChange={(e) => setVolume(parseFloat(e.target.value))}
                    style={{
                      flex: 1,
                      height: "4px",
                      cursor: "pointer",
                      accentColor: "#8b5cf6",
                    }}
                  />
                  <span
                    style={{
                      color: "#666",
                      fontSize: "0.7em",
                      minWidth: "28px",
                    }}
                  >
                    {Math.round(volume * 100)}%
                  </span>

                  {/* Divider */}
                  <div
                    style={{ width: "1px", height: "20px", background: "#333" }}
                  />

                  {/* Speed Control */}
                  <select
                    value={playbackSpeed}
                    onChange={(e) =>
                      setPlaybackSpeed(parseFloat(e.target.value))
                    }
                    style={{
                      background: "#0f0f1a",
                      border: "1px solid #333",
                      borderRadius: "6px",
                      color: "#888",
                      padding: "4px 6px",
                      fontSize: "0.75em",
                      cursor: "pointer",
                    }}
                  >
                    <option value="0.5">0.5x</option>
                    <option value="0.75">0.75x</option>
                    <option value="1">1x</option>
                    <option value="1.25">1.25x</option>
                    <option value="1.5">1.5x</option>
                    <option value="2">2x</option>
                  </select>
                </div>

                {/* Amigos Comments */}
                {amigosComments.length > 0 && (
                  <div
                    style={{
                      background: "linear-gradient(135deg, #1a1a2e, #0f0f1a)",
                      borderRadius: "12px",
                      padding: "10px",
                      border: "1px solid #333",
                    }}
                  >
                    <div
                      style={{
                        fontSize: "0.75em",
                        color: "#8b5cf6",
                        marginBottom: "6px",
                      }}
                    >
                      💬 Amigos says:
                    </div>
                    {amigosComments.slice(-2).map((comment) => (
                      <div
                        key={comment.id}
                        style={{
                          color: "#ccc",
                          fontSize: "0.85em",
                          padding: "4px 0",
                          borderTop: "1px solid #222",
                        }}
                      >
                        {comment.text}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Playlist View */}
            {playerView === "playlist" && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "8px",
                  flex: 1,
                  overflow: "auto",
                }}
              >
                {/* Playlist Header */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "8px",
                    background: "#1a1a2e",
                    borderRadius: "10px",
                  }}
                >
                  <span style={{ color: "#888", fontSize: "0.85em" }}>
                    {playlist.length} tracks •{" "}
                    {formatTime(
                      playlist.reduce((acc, t) => acc + (t.duration || 0), 0),
                    )}
                  </span>
                  <div style={{ display: "flex", gap: "6px" }}>
                    <button
                      onClick={() =>
                        shuffleMode ? null : setShuffleMode(true)
                      }
                      style={{
                        padding: "6px 10px",
                        borderRadius: "6px",
                        border: "none",
                        background: "#8b5cf6",
                        color: "white",
                        cursor: "pointer",
                        fontSize: "0.75em",
                      }}
                    >
                      🔀 Shuffle Play
                    </button>
                    <button
                      onClick={clearPlaylist}
                      disabled={playlist.length === 0}
                      style={{
                        padding: "6px 10px",
                        borderRadius: "6px",
                        border: "none",
                        background: "#ef4444",
                        color: "white",
                        cursor: playlist.length > 0 ? "pointer" : "not-allowed",
                        fontSize: "0.75em",
                      }}
                    >
                      🗑️ Clear
                    </button>
                  </div>
                </div>

                {/* Playlist Items */}
                {playlist.length === 0 ? (
                  <div
                    style={{
                      textAlign: "center",
                      padding: "40px",
                      color: "#666",
                    }}
                  >
                    <div style={{ fontSize: "2em", marginBottom: "10px" }}>
                      📋
                    </div>
                    <div>Your playlist is empty</div>
                    <div style={{ fontSize: "0.85em", marginTop: "8px" }}>
                      Go to Library to add videos & music
                    </div>
                  </div>
                ) : (
                  playlist.map((track, index) => (
                    <div
                      key={track.id}
                      onClick={() => playTrack(index)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        padding: "10px",
                        background:
                          index === currentTrackIndex
                            ? "linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(236, 72, 153, 0.1))"
                            : "#1a1a2e",
                        borderRadius: "10px",
                        cursor: "pointer",
                        border:
                          index === currentTrackIndex
                            ? "1px solid #8b5cf6"
                            : "1px solid transparent",
                        transition: "all 0.2s",
                      }}
                    >
                      {/* Track Number / Now Playing */}
                      <div
                        style={{
                          width: "24px",
                          textAlign: "center",
                          color:
                            index === currentTrackIndex ? "#8b5cf6" : "#666",
                          fontSize: "0.85em",
                        }}
                      >
                        {index === currentTrackIndex && isPlaying
                          ? "▶️"
                          : index + 1}
                      </div>

                      {/* Track Icon */}
                      <span style={{ fontSize: "1.3em" }}>
                        {track.type === "video"
                          ? "🎥"
                          : track.type === "audio"
                            ? "🎵"
                            : "📹"}
                      </span>

                      {/* Track Info */}
                      <div style={{ flex: 1, overflow: "hidden" }}>
                        <div
                          style={{
                            color:
                              index === currentTrackIndex ? "#a78bfa" : "#fff",
                            fontSize: "0.9em",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {track.name}
                        </div>
                        <div style={{ color: "#666", fontSize: "0.75em" }}>
                          {track.type}
                        </div>
                      </div>

                      {/* Move Up/Down */}
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: "2px",
                        }}
                      >
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (index > 0) moveInPlaylist(index, index - 1);
                          }}
                          disabled={index === 0}
                          style={{
                            background: "none",
                            border: "none",
                            color: index === 0 ? "#333" : "#666",
                            cursor: index === 0 ? "not-allowed" : "pointer",
                            fontSize: "0.7em",
                            padding: "2px",
                          }}
                        >
                          ▲
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (index < playlist.length - 1)
                              moveInPlaylist(index, index + 1);
                          }}
                          disabled={index === playlist.length - 1}
                          style={{
                            background: "none",
                            border: "none",
                            color:
                              index === playlist.length - 1 ? "#333" : "#666",
                            cursor:
                              index === playlist.length - 1
                                ? "not-allowed"
                                : "pointer",
                            fontSize: "0.7em",
                            padding: "2px",
                          }}
                        >
                          ▼
                        </button>
                      </div>

                      {/* Remove */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeFromPlaylist(index);
                        }}
                        style={{
                          width: "28px",
                          height: "28px",
                          borderRadius: "50%",
                          border: "none",
                          background: "#ef4444",
                          color: "white",
                          cursor: "pointer",
                          fontSize: "0.7em",
                        }}
                      >
                        ✕
                      </button>
                      <button
                        onClick={() => refreshProviderModels(provider.id)}
                        style={{
                          padding: "6px 8px",
                          marginLeft: 6,
                          borderRadius: 8,
                          background: "#3b82f6",
                          color: "#fff",
                          border: "none",
                          cursor: "pointer",
                        }}
                        disabled={providerLoading}
                      >
                        Refresh Models
                      </button>
                      {providerModels[provider.id] &&
                        providerModels[provider.id].length > 0 && (
                          <select
                            value={isActive ? activeModel : ""}
                            onChange={(e) =>
                              switchProvider(provider.id, e.target.value)
                            }
                            style={{ marginLeft: 8 }}
                          >
                            <option value="">Default</option>
                            {providerModels[provider.id].map((m) => (
                              <option key={m} value={m}>
                                {m}
                              </option>
                            ))}
                          </select>
                        )}
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Library View */}
            {playerView === "library" && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "8px",
                  flex: 1,
                  overflow: "auto",
                }}
              >
                {/* Quick Add Buttons */}
                <div
                  style={{
                    display: "flex",
                    gap: "6px",
                    flexWrap: "wrap",
                  }}
                >
                  <button
                    onClick={() => addAllToPlaylist("video")}
                    disabled={mediaFiles.videos.length === 0}
                    style={{
                      flex: 1,
                      padding: "8px",
                      borderRadius: "8px",
                      border: "none",
                      background:
                        mediaFiles.videos.length > 0 ? "#8b5cf6" : "#333",
                      color: "white",
                      cursor:
                        mediaFiles.videos.length > 0
                          ? "pointer"
                          : "not-allowed",
                      fontSize: "0.75em",
                    }}
                  >
                    🎥 Add All Videos ({mediaFiles.videos.length})
                  </button>
                  <button
                    onClick={() => addAllToPlaylist("audio")}
                    disabled={mediaFiles.audio.length === 0}
                    style={{
                      flex: 1,
                      padding: "8px",
                      borderRadius: "8px",
                      border: "none",
                      background:
                        mediaFiles.audio.length > 0 ? "#f59e0b" : "#333",
                      color: "white",
                      cursor:
                        mediaFiles.audio.length > 0 ? "pointer" : "not-allowed",
                      fontSize: "0.75em",
                    }}
                  >
                    🎵 Add All Audio ({mediaFiles.audio.length})
                  </button>
                </div>

                {/* Videos Section */}
                <div
                  style={{
                    background: "#1a1a2e",
                    borderRadius: "10px",
                    padding: "10px",
                  }}
                >
                  <div
                    style={{
                      color: "#8b5cf6",
                      fontSize: "0.85em",
                      fontWeight: "bold",
                      marginBottom: "8px",
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    🎥 Videos ({mediaFiles.videos.length})
                  </div>

                  {mediaFiles.videos.length === 0 ? (
                    <div
                      style={{
                        color: "#666",
                        fontSize: "0.8em",
                        padding: "10px",
                      }}
                    >
                      No videos available
                    </div>
                  ) : (
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: "4px",
                        maxHeight: "120px",
                        overflow: "auto",
                      }}
                    >
                      {mediaFiles.videos.map((vid, idx) => (
                        <div
                          key={idx}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "8px",
                            padding: "6px 8px",
                            background: "#0f0f1a",
                            borderRadius: "6px",
                          }}
                        >
                          <span>🎥</span>
                          <span
                            style={{
                              flex: 1,
                              color: "#ccc",
                              fontSize: "0.8em",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {vid.name}
                          </span>
                          <button
                            onClick={() => addToPlaylist(vid, "video")}
                            style={{
                              padding: "4px 8px",
                              borderRadius: "4px",
                              border: "none",
                              background: "#22c55e",
                              color: "white",
                              cursor: "pointer",
                              fontSize: "0.7em",
                            }}
                          >
                            + Add
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Audio Section */}
                <div
                  style={{
                    background: "#1a1a2e",
                    borderRadius: "10px",
                    padding: "10px",
                  }}
                >
                  <div
                    style={{
                      color: "#f59e0b",
                      fontSize: "0.85em",
                      fontWeight: "bold",
                      marginBottom: "8px",
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    🎵 Audio ({mediaFiles.audio.length})
                  </div>

                  {mediaFiles.audio.length === 0 ? (
                    <div
                      style={{
                        color: "#666",
                        fontSize: "0.8em",
                        padding: "10px",
                      }}
                    >
                      No audio files available
                    </div>
                  ) : (
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: "4px",
                        maxHeight: "120px",
                        overflow: "auto",
                      }}
                    >
                      {mediaFiles.audio.map((aud, idx) => (
                        <div
                          key={idx}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "8px",
                            padding: "6px 8px",
                            background: "#0f0f1a",
                            borderRadius: "6px",
                          }}
                        >
                          <span>🎵</span>
                          <span
                            style={{
                              flex: 1,
                              color: "#ccc",
                              fontSize: "0.8em",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {aud.name}
                          </span>
                          <button
                            onClick={() => addToPlaylist(aud, "audio")}
                            style={{
                              padding: "4px 8px",
                              borderRadius: "4px",
                              border: "none",
                              background: "#22c55e",
                              color: "white",
                              cursor: "pointer",
                              fontSize: "0.7em",
                            }}
                          >
                            + Add
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Recordings Section */}
                <div
                  style={{
                    background: "#1a1a2e",
                    borderRadius: "10px",
                    padding: "10px",
                  }}
                >
                  <div
                    style={{
                      color: "#ec4899",
                      fontSize: "0.85em",
                      fontWeight: "bold",
                      marginBottom: "8px",
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    📹 Recordings ({mediaFiles.recordings?.length || 0})
                  </div>

                  {!mediaFiles.recordings ||
                  mediaFiles.recordings.length === 0 ? (
                    <div
                      style={{
                        color: "#666",
                        fontSize: "0.8em",
                        padding: "10px",
                      }}
                    >
                      No recordings available
                    </div>
                  ) : (
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: "4px",
                        maxHeight: "120px",
                        overflow: "auto",
                      }}
                    >
                      {mediaFiles.recordings.map((rec, idx) => (
                        <div
                          key={idx}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "8px",
                            padding: "6px 8px",
                            background: "#0f0f1a",
                            borderRadius: "6px",
                          }}
                        >
                          <span>📹</span>
                          <span
                            style={{
                              flex: 1,
                              color: "#ccc",
                              fontSize: "0.8em",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {rec.name || rec.filename}
                          </span>
                          <button
                            onClick={() =>
                              addToPlaylist(
                                { ...rec, name: rec.name || rec.filename },
                                "recording",
                              )
                            }
                            style={{
                              padding: "4px 8px",
                              borderRadius: "4px",
                              border: "none",
                              background: "#22c55e",
                              color: "white",
                              cursor: "pointer",
                              fontSize: "0.7em",
                            }}
                          >
                            + Add
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* CSS for animations */}
            <style>{`
              @keyframes equalizer {
                0% { height: 5px; }
                100% { height: 35px; }
              }
              @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.05); }
              }
            `}</style>
          </div>
        )}

        {/* Generate Tab */}
        {activeTab === "generate" && (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "12px" }}
          >
            <div
              style={{
                fontSize: "0.9em",
                color: "#a78bfa",
                fontWeight: "bold",
              }}
            >
              🎨 Create AI Media
            </div>
            <textarea
              value={generatePrompt}
              onChange={(e) => setGeneratePrompt(e.target.value)}
              placeholder={
                generateType === "image_to_video"
                  ? "Describe the motion you want (optional)… e.g. 'slow dolly-in, subtle hair movement, natural breathing'"
                  : generateType === "vehicle_restoration"
                    ? "Optional notes (kept additive; vehicle model stays locked)… e.g. 'restore to glossy red, studio lighting, gentle camera orbit'"
                    : generateType === "image_edit"
                      ? "Describe how to change the image… e.g. 'make it anime, remove text, fix hands, change background to a neon city'"
                      : "Describe what you want to create... (e.g., 'A soldier walking through a sunset battlefield' or 'A majestic dragon flying over mountains')"
              }
              style={{
                width: "100%",
                height: "100px",
                padding: "12px",
                borderRadius: "10px",
                border: "1px solid #444",
                backgroundColor: "#1a1a2e",
                color: "white",
                fontSize: "0.9em",
                resize: "none",
              }}
            />

            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              {[
                { key: "image", label: "🖼️ Image", desc: "AI Image" },
                {
                  key: "ai_video",
                  label: "🎬 AI Video",
                  desc: "Text→Video (FREE!)",
                },
                {
                  key: "vehicle_restoration",
                  label: "🛠️ Restore",
                  desc: "Photo→Restoration MP4",
                },
                {
                  key: "image_to_video",
                  label: "🎞️ Img→Video",
                  desc: "Image→Video (FREE!)",
                },
                {
                  key: "image_edit",
                  label: "🪄 Edit",
                  desc: "Img→Img (Kontext)",
                },
                { key: "reel", label: "📸 Reel", desc: "Animated image" },
              ].map((type) => (
                <button
                  key={type.key}
                  onClick={() => setGenerateType(type.key)}
                  style={{
                    flex: 1,
                    minWidth: "90px",
                    padding: "12px 8px",
                    borderRadius: "10px",
                    border:
                      generateType === type.key
                        ? "2px solid #8b5cf6"
                        : "1px solid #444",
                    backgroundColor:
                      generateType === type.key ? "#1a1a2e" : "transparent",
                    color: generateType === type.key ? "#a78bfa" : "#888",
                    cursor: "pointer",
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: "1.2em" }}>
                    {type.label.split(" ")[0]}
                  </div>
                  <div style={{ fontSize: "0.7em", opacity: 0.7 }}>
                    {type.desc}
                  </div>
                </button>
              ))}
            </div>

            {(generateType === "image" ||
              generateType === "reel" ||
              generateType === "image_edit") && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "6px",
                  padding: "10px",
                  borderRadius: 10,
                  border: "1px solid #333",
                  background: "#11131d",
                }}
              >
                <div style={{ fontSize: "0.8em", color: "#888" }}>
                  🚫 Negative prompt (optional)
                </div>
                <textarea
                  value={imageNegativePrompt}
                  onChange={(e) => setImageNegativePrompt(e.target.value)}
                  placeholder="Leave blank to use the built-in default (recommended). Examples: watermark, text, logo, extra limbs, deformed, blurry"
                  style={{
                    width: "100%",
                    height: "70px",
                    padding: "10px",
                    borderRadius: "10px",
                    border: "1px solid #333",
                    backgroundColor: "#0f0f1a",
                    color: "white",
                    resize: "none",
                    fontSize: "0.85em",
                  }}
                />
                <div style={{ color: "#666", fontSize: "0.75em" }}>
                  Tip: leaving this blank applies Amigos' persistent defaults
                  for better anatomy / fewer duplicates.
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button
                    onClick={() => setImageNegativePrompt("")}
                    style={{
                      padding: "8px 10px",
                      borderRadius: 8,
                      border: "1px solid rgba(34, 197, 94, 0.35)",
                      background: "rgba(34, 197, 94, 0.10)",
                      color: "#bbf7d0",
                      cursor: "pointer",
                      fontSize: "0.78em",
                    }}
                    title="Clear override so the backend uses its built-in default negative prompt"
                  >
                    Use default
                  </button>
                </div>
              </div>
            )}

            {(generateType === "image_to_video" ||
              generateType === "vehicle_restoration") && (
              <div
                style={{
                  padding: "10px",
                  borderRadius: 10,
                  border: "1px solid #333",
                  background: "#11131d",
                }}
              >
                <div
                  style={{
                    color: "#a78bfa",
                    fontWeight: 800,
                    fontSize: "0.8em",
                  }}
                >
                  🎞️ Source image
                </div>
                <div
                  style={{ color: "#94a3b8", fontSize: "0.78em", marginTop: 6 }}
                >
                  Upload an image, then click “Generate”.
                </div>
                <div
                  style={{
                    display: "flex",
                    gap: 10,
                    alignItems: "center",
                    flexWrap: "wrap",
                    marginTop: 10,
                  }}
                >
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleI2VImageUpload}
                    style={{ color: "#cbd5e1" }}
                  />
                  {i2vSourceImage && (
                    <div style={{ color: "#cbd5e1", fontSize: "0.8em" }}>
                      Selected:{" "}
                      <span style={{ color: "#e5e7eb" }}>{i2vSourceImage}</span>
                    </div>
                  )}
                </div>

                {generateType === "vehicle_restoration" && (
                  <>
                    <div
                      style={{
                        marginTop: 10,
                        display: "flex",
                        gap: 10,
                        alignItems: "center",
                        flexWrap: "wrap",
                      }}
                    >
                      <div style={{ color: "#94a3b8", fontSize: "0.78em" }}>
                        Duration (sec)
                      </div>
                      <input
                        type="number"
                        min={2}
                        max={20}
                        value={vehicleRestoreDurationSec}
                        onChange={(e) =>
                          setVehicleRestoreDurationSec(
                            Math.max(
                              2,
                              Math.min(20, Number(e.target.value || 10)),
                            ),
                          )
                        }
                        style={{
                          width: 90,
                          padding: "6px 8px",
                          borderRadius: 8,
                          border: "1px solid #333",
                          background: "#0f0f1a",
                          color: "#e5e7eb",
                        }}
                      />
                      <div
                        style={{ display: "flex", gap: 10, flexWrap: "wrap" }}
                      >
                        <label
                          style={{
                            display: "flex",
                            flexDirection: "column",
                            gap: 4,
                            color: "#94a3b8",
                            fontSize: "0.75em",
                          }}
                        >
                          Paint
                          <select
                            value={vehicleRestorePaintColor}
                            onChange={(e) =>
                              setVehicleRestorePaintColor(e.target.value)
                            }
                            style={{
                              padding: "6px 8px",
                              borderRadius: 8,
                              border: "1px solid #333",
                              background: "#0f0f1a",
                              color: "#e5e7eb",
                              minWidth: 160,
                            }}
                          >
                            <option>Factory original</option>
                            <option>Candy Apple Red</option>
                            <option>Metallic Midnight Blue</option>
                            <option>Matte Stealth Grey</option>
                            <option>Factory OEM Turquoise</option>
                            <option>Glossy Black</option>
                            <option>Pearl White</option>
                            <option>British Racing Green</option>
                          </select>
                        </label>

                        <label
                          style={{
                            display: "flex",
                            flexDirection: "column",
                            gap: 4,
                            color: "#94a3b8",
                            fontSize: "0.75em",
                          }}
                        >
                          Wheels
                          <select
                            value={vehicleRestoreWheelStyle}
                            onChange={(e) =>
                              setVehicleRestoreWheelStyle(e.target.value)
                            }
                            style={{
                              padding: "6px 8px",
                              borderRadius: 8,
                              border: "1px solid #333",
                              background: "#0f0f1a",
                              color: "#e5e7eb",
                              minWidth: 150,
                            }}
                          >
                            <option>Keep original</option>
                            <option>Period Correct Chrome</option>
                            <option>Restomod Alloy</option>
                            <option>Steelies with Hubcaps</option>
                            <option>Modern Premium</option>
                            <option>Off-road / Rugged</option>
                          </select>
                        </label>

                        <label
                          style={{
                            display: "flex",
                            flexDirection: "column",
                            gap: 4,
                            color: "#94a3b8",
                            fontSize: "0.75em",
                          }}
                        >
                          Engine / Mod
                          <select
                            value={vehicleRestoreIntensity}
                            onChange={(e) =>
                              setVehicleRestoreIntensity(e.target.value)
                            }
                            style={{
                              padding: "6px 8px",
                              borderRadius: 8,
                              border: "1px solid #333",
                              background: "#0f0f1a",
                              color: "#e5e7eb",
                              minWidth: 150,
                            }}
                          >
                            <option value="Factory">
                              Factory Concours (Stock)
                            </option>
                            <option value="Sleeper">
                              Sleeper (Hidden Performance)
                            </option>
                            <option value="Modern Swap">
                              Modern Crate Swap
                            </option>
                            <option value="Low">Light Polish</option>
                            <option value="Medium">Standard Restoration</option>
                            <option value="High">Full Overhaul</option>
                          </select>
                        </label>
                      </div>
                      <div style={{ color: "#64748b", fontSize: "0.74em" }}>
                        Uses a model-locked prompt; notes are additive.
                      </div>
                    </div>

                    {/* --- NEW: PHASE CAPTURE UI SECTION --- */}
                    <div
                      style={{
                        marginTop: 15,
                        padding: 10,
                        border: "1px solid #333",
                        borderRadius: 8,
                        background: "#0f0f1a",
                      }}
                    >
                      <div
                        style={{
                          color: "#e5e7eb",
                          fontWeight: "bold",
                          marginBottom: 8,
                          fontSize: "0.9em",
                        }}
                      >
                        🕒 Restoration Timeline
                      </div>
                      <div
                        style={{
                          display: "flex",
                          gap: 5,
                          marginBottom: 10,
                          flexWrap: "wrap",
                        }}
                      >
                        {[
                          "Structural Alignment",
                          "Panel Beating/Sanding",
                          "Engine Overhaul",
                          "Final Paint",
                        ].map((phase) => (
                          <button
                            key={phase}
                            onClick={() => setVehicleRestorePhase(phase)}
                            style={{
                              padding: "6px 10px",
                              borderRadius: 6,
                              border:
                                vehicleRestorePhase === phase
                                  ? "1px solid #a78bfa"
                                  : "1px solid #333",
                              background:
                                vehicleRestorePhase === phase
                                  ? "rgba(167, 139, 250, 0.2)"
                                  : "#1e1e2e",
                              color:
                                vehicleRestorePhase === phase
                                  ? "#a78bfa"
                                  : "#94a3b8",
                              cursor: "pointer",
                              fontSize: "0.75em",
                            }}
                          >
                            {phase}
                          </button>
                        ))}
                      </div>

                      <button
                        onClick={handleGeneratePhaseClip}
                        disabled={isGeneratingPhase || !i2vSourceImage}
                        style={{
                          width: "100%",
                          padding: "8px",
                          borderRadius: 6,
                          border: "none",
                          background: isGeneratingPhase ? "#333" : "#a78bfa",
                          color: isGeneratingPhase ? "#888" : "#fff",
                          cursor: isGeneratingPhase ? "not-allowed" : "pointer",
                          fontWeight: "bold",
                          fontSize: "0.85em",
                        }}
                      >
                        {isGeneratingPhase
                          ? `Running AI Panel Beater for ${vehicleRestorePhase}...`
                          : `Generate ${vehicleRestorePhase} Clip`}
                      </button>

                      {phaseResult && (
                        <div style={{ marginTop: 10 }}>
                          {phaseResult.success ? (
                            <>
                              <video
                                src={phaseResult.url}
                                controls
                                autoPlay
                                loop
                                style={{
                                  width: "100%",
                                  borderRadius: 8,
                                  border: "1px solid #333",
                                }}
                              />
                              <div
                                style={{
                                  color: "#94a3b8",
                                  fontSize: "0.75em",
                                  marginTop: 4,
                                  fontStyle: "italic",
                                }}
                              >
                                Phase Detail: {vehicleRestorePhase} - All OEM
                                body lines preserved.
                              </div>
                            </>
                          ) : (
                            <div
                              style={{ color: "#ef4444", fontSize: "0.8em" }}
                            >
                              Error: {phaseResult.error}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </>
                )}

                {i2vSourcePreview && (
                  <div style={{ marginTop: 10 }}>
                    <img
                      src={i2vSourcePreview}
                      alt="Source preview"
                      style={{
                        maxWidth: "100%",
                        borderRadius: 10,
                        border: "1px solid #222",
                      }}
                    />
                  </div>
                )}
              </div>
            )}

            {generateType === "image_edit" && (
              <div
                style={{
                  padding: "10px",
                  borderRadius: 10,
                  border: "1px solid #333",
                  background: "#11131d",
                }}
              >
                <div
                  style={{
                    color: "#a78bfa",
                    fontWeight: 800,
                    fontSize: "0.8em",
                  }}
                >
                  🪄 Source image (Kontext)
                </div>
                <div
                  style={{ color: "#94a3b8", fontSize: "0.78em", marginTop: 6 }}
                >
                  You can upload an image, or paste a public image URL.
                </div>

                <div
                  style={{
                    display: "flex",
                    gap: 10,
                    alignItems: "center",
                    flexWrap: "wrap",
                    marginTop: 10,
                  }}
                >
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImgEditImageUpload}
                    style={{ color: "#cbd5e1" }}
                  />
                  {imgEditSourceImage && (
                    <div style={{ color: "#cbd5e1", fontSize: "0.8em" }}>
                      Uploaded:{" "}
                      <span style={{ color: "#e5e7eb" }}>
                        {imgEditSourceImage}
                      </span>
                      <span style={{ marginLeft: 10, color: "#94a3b8" }}>
                        Public:{" "}
                        <span
                          style={{
                            color: imgEditUploadedPublicUrl
                              ? "#bbf7d0"
                              : "#fecaca",
                            fontWeight: 700,
                          }}
                        >
                          {imgEditUploadedPublicUrl ? "yes" : "no"}
                        </span>
                      </span>
                    </div>
                  )}
                </div>

                <div style={{ marginTop: 10 }}>
                  <div style={{ fontSize: "0.8em", color: "#888" }}>
                    Or use a public URL
                  </div>
                  <input
                    value={imgEditSourceUrl}
                    onChange={(e) => setImgEditSourceUrl(e.target.value)}
                    placeholder="https://example.com/source.jpg"
                    style={{
                      width: "100%",
                      padding: "10px",
                      borderRadius: 10,
                      border: "1px solid #333",
                      backgroundColor: "#0f0f1a",
                      color: "#e5e7eb",
                      marginTop: 6,
                    }}
                  />
                  <div
                    style={{ color: "#666", fontSize: "0.75em", marginTop: 6 }}
                  >
                    Note: If you uploaded an image, the backend may need{" "}
                    <code>MEDIA_PUBLIC_BASE_URL</code> (a tunnel / public URL)
                    so Pollinations can fetch it.
                  </div>

                  {imgEditSourceImage && !imgEditUploadedPublicUrl && (
                    <div
                      style={{
                        marginTop: 8,
                        padding: "8px 10px",
                        borderRadius: 10,
                        border: "1px solid rgba(239, 68, 68, 0.35)",
                        background: "rgba(239, 68, 68, 0.10)",
                        color: "#fecaca",
                        fontSize: "0.78em",
                      }}
                    >
                      Upload-only edits won’t work until you set{" "}
                      <code>MEDIA_PUBLIC_BASE_URL</code>. For now, paste a
                      public image URL above.
                    </div>
                  )}
                </div>

                {imgEditSourcePreview && (
                  <div style={{ marginTop: 10 }}>
                    <img
                      src={imgEditSourcePreview}
                      alt="Edit source preview"
                      style={{
                        maxWidth: "100%",
                        borderRadius: 10,
                        border: "1px solid #222",
                      }}
                    />
                  </div>
                )}
              </div>
            )}

            {/* AI Video Model Selection */}
            {generateType === "ai_video" && (
              <div
                style={{ display: "flex", flexDirection: "column", gap: "8px" }}
              >
                <div
                  style={{
                    padding: "10px",
                    borderRadius: 10,
                    border: "1px solid #333",
                    background: "#11131d",
                  }}
                >
                  <div
                    style={{
                      color: "#a78bfa",
                      fontWeight: 800,
                      fontSize: "0.8em",
                      marginBottom: 8,
                    }}
                  >
                    📚 Prompt templates (AI Video)
                  </div>
                  <div
                    style={{
                      display: "flex",
                      gap: 8,
                      flexWrap: "wrap",
                      alignItems: "center",
                    }}
                  >
                    <select
                      value={aiVideoPromptTemplateId}
                      onChange={(e) =>
                        setAiVideoPromptTemplateId(e.target.value)
                      }
                      style={{
                        flex: 1,
                        minWidth: 220,
                        padding: "10px",
                        borderRadius: 10,
                        border: "1px solid #333",
                        backgroundColor: "#0f0f1a",
                        color: "#e5e7eb",
                      }}
                    >
                      <option value="">Choose a template…</option>
                      {getTemplatesForScope("ai_video").map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                    </select>

                    <button
                      onClick={() => {
                        const t = getTemplatesForScope("ai_video").find(
                          (x) => x.id === aiVideoPromptTemplateId,
                        );
                        if (!t) return;
                        if (t.prompt) setGeneratePrompt(t.prompt);
                        if (typeof t.durationSec === "number")
                          setAiVideoDurationSec(t.durationSec);
                        if (t.aspectRatio) setAspectRatio(t.aspectRatio);
                        if (t.negativePrompt)
                          setAiVideoNegativePrompt(t.negativePrompt);
                      }}
                      disabled={!aiVideoPromptTemplateId}
                      style={{
                        padding: "10px 12px",
                        borderRadius: 10,
                        border: "1px solid rgba(34, 197, 94, 0.35)",
                        background: "rgba(34, 197, 94, 0.12)",
                        color: "#bbf7d0",
                        cursor: aiVideoPromptTemplateId
                          ? "pointer"
                          : "not-allowed",
                        whiteSpace: "nowrap",
                      }}
                    >
                      Apply
                    </button>

                    <button
                      onClick={() => {
                        const name = window.prompt(
                          "Save AI Video template as…",
                          "My cinematic template",
                        );
                        if (!name) return;
                        saveTemplate({
                          id: `custom_ai_${Date.now()}`,
                          scope: "ai_video",
                          name: String(name).trim(),
                          prompt: generatePrompt || "",
                          negativePrompt: aiVideoNegativePrompt || "",
                          aspectRatio: aspectRatio || "16:9",
                          durationSec: aiVideoDurationSec || 5,
                        });
                      }}
                      style={{
                        padding: "10px 12px",
                        borderRadius: 10,
                        border: "1px solid rgba(139, 92, 246, 0.35)",
                        background: "rgba(139, 92, 246, 0.12)",
                        color: "#c4b5fd",
                        cursor: "pointer",
                        whiteSpace: "nowrap",
                      }}
                      title="Save your current prompt settings as a reusable template"
                    >
                      Save
                    </button>

                    <button
                      onClick={() => {
                        if (!aiVideoPromptTemplateId) return;
                        if (!isCustomTemplateId(aiVideoPromptTemplateId)) {
                          alert(
                            "Built-in templates can’t be deleted. Save your own and delete that one.",
                          );
                          return;
                        }
                        if (!window.confirm("Delete this saved template?"))
                          return;
                        deleteTemplate(aiVideoPromptTemplateId);
                        setAiVideoPromptTemplateId("");
                      }}
                      disabled={!aiVideoPromptTemplateId}
                      style={{
                        padding: "10px 12px",
                        borderRadius: 10,
                        border: "1px solid rgba(239, 68, 68, 0.35)",
                        background: "rgba(239, 68, 68, 0.12)",
                        color: "#fecaca",
                        cursor: aiVideoPromptTemplateId
                          ? "pointer"
                          : "not-allowed",
                        whiteSpace: "nowrap",
                      }}
                    >
                      Delete
                    </button>
                  </div>
                  <div
                    style={{
                      marginTop: 8,
                      color: "#94a3b8",
                      fontSize: "0.75em",
                    }}
                  >
                    Templates are stored locally in your browser (this machine).
                  </div>
                </div>

                <div style={{ fontSize: "0.8em", color: "#888" }}>
                  🤖 AI Model (🆓 = FREE, no API key needed!):
                </div>
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                  {[
                    {
                      key: "pollinations",
                      label: "🆓 Auto",
                      desc: "FREE - Best available (Seedance/Veo)",
                    },
                    {
                      key: "seedance",
                      label: "🆓 Seedance",
                      desc: "FREE - BytePlus 2-10s, good quality",
                    },
                    {
                      key: "veo",
                      label: "🆓 Veo",
                      desc: "FREE - Google 4-8s, excellent quality",
                    },
                    {
                      key: "wan",
                      label: "⚡ WAN",
                      desc: "Replicate - Fast & cheap (needs API key)",
                    },
                    {
                      key: "minimax",
                      label: "✨ Minimax",
                      desc: "Replicate - High quality (needs API key)",
                    },
                    {
                      key: "ltx",
                      label: "🚀 LTX",
                      desc: "Replicate - Realtime (needs API key)",
                    },
                  ].map((m) => (
                    <button
                      key={m.key}
                      onClick={() => setVideoModel(m.key)}
                      style={{
                        padding: "8px 10px",
                        borderRadius: "8px",
                        border:
                          videoModel === m.key
                            ? "2px solid #10b981"
                            : "1px solid #444",
                        backgroundColor:
                          videoModel === m.key ? "#1a2e2e" : "transparent",
                        color:
                          videoModel === m.key
                            ? "#10b981"
                            : m.key.startsWith("pollinations") ||
                                m.key === "seedance" ||
                                m.key === "veo"
                              ? "#4ade80"
                              : "#666",
                        cursor: "pointer",
                        fontSize: "0.75em",
                        minWidth: "80px",
                      }}
                      title={m.desc}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
                <div style={{ display: "flex", gap: "6px" }}>
                  <div style={{ fontSize: "0.8em", color: "#888" }}>
                    📐 Aspect:
                  </div>
                  {["16:9", "9:16", "1:1"].map((ar) => (
                    <button
                      key={ar}
                      onClick={() => setAspectRatio(ar)}
                      style={{
                        padding: "4px 10px",
                        borderRadius: "6px",
                        border:
                          aspectRatio === ar
                            ? "1px solid #8b5cf6"
                            : "1px solid #333",
                        backgroundColor:
                          aspectRatio === ar ? "#1a1a2e" : "transparent",
                        color: aspectRatio === ar ? "#a78bfa" : "#666",
                        cursor: "pointer",
                        fontSize: "0.75em",
                      }}
                    >
                      {ar}
                    </button>
                  ))}
                </div>

                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <div style={{ flex: 1, minWidth: "160px" }}>
                    <div style={{ fontSize: "0.8em", color: "#888" }}>
                      ⏱️ Duration (seconds)
                    </div>
                    <input
                      type="number"
                      min={2}
                      max={10}
                      step={1}
                      value={aiVideoDurationSec}
                      onChange={(e) =>
                        setAiVideoDurationSec(() => {
                          const v = parseInt(String(e.target.value || ""), 10);
                          const safe = Number.isFinite(v) ? v : 5;
                          return Math.max(2, Math.min(10, safe));
                        })
                      }
                      style={{
                        width: "100%",
                        padding: "10px",
                        borderRadius: "10px",
                        border: "1px solid #333",
                        backgroundColor: "#11131d",
                        color: "white",
                      }}
                    />
                    <div
                      style={{ fontSize: "0.7em", color: "#666", marginTop: 4 }}
                    >
                      Tip: you can also paste{" "}
                      <span style={{ color: "#a78bfa" }}>--duration 6s</span> in
                      the prompt; I’ll read it and strip it before sending.
                    </div>
                  </div>
                  <div style={{ minWidth: "180px", flex: 1 }}>
                    <div style={{ fontSize: "0.8em", color: "#888" }}>
                      🚫 Negative prompt
                    </div>
                    <textarea
                      value={aiVideoNegativePrompt}
                      onChange={(e) => setAiVideoNegativePrompt(e.target.value)}
                      placeholder="watermark, text, logo, blurry, low-res, distortion"
                      style={{
                        width: "100%",
                        height: "74px",
                        padding: "10px",
                        borderRadius: "10px",
                        border: "1px solid #333",
                        backgroundColor: "#11131d",
                        color: "white",
                        resize: "none",
                        fontSize: "0.85em",
                      }}
                    />
                  </div>
                </div>

                <div
                  style={{
                    padding: "10px 10px",
                    borderRadius: 10,
                    border: "1px solid #333",
                    background: "#11131d",
                  }}
                >
                  <button
                    onClick={() => setShowAiVideoPromptHelp((v) => !v)}
                    style={{
                      width: "100%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: 8,
                      background: "transparent",
                      border: "none",
                      color: "#a78bfa",
                      cursor: "pointer",
                      padding: 0,
                      fontWeight: "bold",
                      fontSize: "0.8em",
                    }}
                    title="Show prompt template helpers"
                  >
                    <span>🧩 Prompt template (copy/paste)</span>
                    <span style={{ color: "#666", fontWeight: "normal" }}>
                      {showAiVideoPromptHelp ? "Hide" : "Show"}
                    </span>
                  </button>

                  {showAiVideoPromptHelp && (
                    <div
                      style={{
                        marginTop: 10,
                        color: "#bbb",
                        fontSize: "0.78em",
                        lineHeight: 1.35,
                      }}
                    >
                      <div style={{ color: "#888", marginBottom: 8 }}>
                        This console treats the prompt as plain text. Use{" "}
                        <span style={{ color: "#a78bfa" }}>|</span> as visual
                        separators. If you include{" "}
                        <span style={{ color: "#a78bfa" }}>--ar</span> or{" "}
                        <span style={{ color: "#a78bfa" }}>--duration</span>,
                        the console will apply them and strip them before
                        sending.
                      </div>

                      <div style={{ marginBottom: 6, color: "#ddd" }}>
                        <strong>One-line template</strong>
                      </div>
                      <div
                        style={{
                          padding: "10px",
                          borderRadius: 10,
                          background: "#0f0f1a",
                          border: "1px solid #222",
                          fontFamily:
                            "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                          color: "#ddd",
                        }}
                      >
                        {
                          "<STYLE> | <SCENE> | <CHARACTER> | <ACTION> | <COMPOSITION> | <COLOR> | <CAMERA> | <ANIM_HINT>"
                        }
                      </div>

                      <div
                        style={{
                          display: "flex",
                          gap: 8,
                          flexWrap: "wrap",
                          marginTop: 10,
                        }}
                      >
                        <button
                          onClick={() => {
                            setGeneratePrompt(
                              "masterpiece, ultra-detailed, (anime style:1.2), cinematic lighting, volumetric light, film grain | rain-slick neon boulevard at night, holographic billboards flickering, mist rising | young woman, short teal hair, cyber-punk jacket with glowing trims, reflective visor, freckles | smooth 360° spin, reaches for a floating orb, hair whipping, light-trail forming | low-angle, 3-quarter view, rule of thirds, foreground puddles reflecting neon | neon magenta #FF00FF, electric cyan #00FFFF, deep midnight #0A0A23 | 18mm lens, shallow depth of field, slow dolly in | motion blur on hair, light-trail particles, subtle parallax",
                            );
                            setAiVideoNegativePrompt(
                              "low-resolution, distortion, watermark, text, blurry, jpeg artifacts",
                            );
                            setAspectRatio("16:9");
                            setAiVideoDurationSec(6);
                          }}
                          style={{
                            padding: "8px 10px",
                            borderRadius: 8,
                            border: "1px solid rgba(139, 92, 246, 0.5)",
                            background: "rgba(139, 92, 246, 0.15)",
                            color: "#c4b5fd",
                            cursor: "pointer",
                            fontSize: "0.78em",
                          }}
                        >
                          🎴 Use Anime preset
                        </button>

                        <button
                          onClick={() => {
                            setGeneratePrompt(
                              "masterpiece, ultra-realistic, cinematic lighting, volumetric fog, shallow depth of field | city rooftop at dusk, neon billboards, soft rain | male protagonist, short black hair, leather jacket, reflective sunglasses | running forward, rain splashing, city lights streaking | wide-angle, low camera, rule of thirds, foreground railing, background skyline | neon orange #FF5500, deep violet #5A0099, steel gray #262626 | 24mm lens, slow dolly forward, slight handheld shake | motion blur on legs, subtle grain, lens flare",
                            );
                            setAiVideoNegativePrompt(
                              "low-resolution, text, watermark, logo, distortion, blurry",
                            );
                            setAspectRatio("16:9");
                            setAiVideoDurationSec(8);
                          }}
                          style={{
                            padding: "8px 10px",
                            borderRadius: 8,
                            border: "1px solid rgba(16, 185, 129, 0.5)",
                            background: "rgba(16, 185, 129, 0.12)",
                            color: "#6ee7b7",
                            cursor: "pointer",
                            fontSize: "0.78em",
                          }}
                        >
                          🎥 Use Cinematic preset
                        </button>

                        <button
                          onClick={() => {
                            setGeneratePrompt(
                              "pixel-art, 8-bit, saturated colors, crisp edges | city street at night, neon signs, pixel raindrops | hero sprite, big green hair, cape, pixel sword | jump forward, sword swing, pixel-spark trail | side-view composition, parallax background | neon green #00FF00, hot pink #FF00FF, electric blue #00FFFF | static camera, light screen-shake on impact | CRT scanlines, subtle bloom",
                            );
                            setAiVideoNegativePrompt("watermark, text, blurry");
                            setAspectRatio("1:1");
                            setAiVideoDurationSec(4);
                          }}
                          style={{
                            padding: "8px 10px",
                            borderRadius: 8,
                            border: "1px solid rgba(245, 158, 11, 0.5)",
                            background: "rgba(245, 158, 11, 0.12)",
                            color: "#fbbf24",
                            cursor: "pointer",
                            fontSize: "0.78em",
                          }}
                        >
                          🕹️ Use Pixel preset
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                <div
                  style={{
                    fontSize: "0.7em",
                    color: "#666",
                    padding: "4px 8px",
                    backgroundColor: "#1a1a2e",
                    borderRadius: "6px",
                  }}
                >
                  💡 Uses cloud text-to-video (🆓 Pollinations / optional
                  Replicate / optional fal.ai).
                </div>
              </div>
            )}

            <button
              onClick={handleGenerate}
              disabled={
                isGenerating ||
                (generateType === "image_to_video" ||
                generateType === "vehicle_restoration"
                  ? !i2vSourceImage
                  : generateType === "image_edit"
                    ? !generatePrompt.trim() ||
                      (!imgEditSourceImage &&
                        !String(imgEditSourceUrl || "").trim())
                    : !generatePrompt.trim())
              }
              style={{
                padding: "14px",
                borderRadius: "10px",
                border: "none",
                background:
                  (generateType === "image_to_video" ||
                  generateType === "vehicle_restoration"
                    ? Boolean(i2vSourceImage)
                    : generateType === "image_edit"
                      ? Boolean(
                          generatePrompt.trim() &&
                          (imgEditSourceImage ||
                            String(imgEditSourceUrl || "").trim()),
                        )
                      : Boolean(generatePrompt.trim())) && !isGenerating
                    ? generateType === "ai_video" ||
                      generateType === "image_to_video"
                      ? "linear-gradient(135deg, #10b981, #059669)"
                      : "linear-gradient(135deg, #8b5cf6, #6366f1)"
                    : "#333",
                color: "white",
                cursor:
                  (generateType === "image_to_video" ||
                  generateType === "vehicle_restoration"
                    ? Boolean(i2vSourceImage)
                    : generateType === "image_edit"
                      ? Boolean(
                          generatePrompt.trim() &&
                          (imgEditSourceImage ||
                            String(imgEditSourceUrl || "").trim()),
                        )
                      : Boolean(generatePrompt.trim())) && !isGenerating
                    ? "pointer"
                    : "not-allowed",
                fontWeight: "bold",
                fontSize: "1em",
              }}
            >
              {isGenerating
                ? generateType === "ai_video"
                  ? "🎬 Generating AI Video... (30-120s)"
                  : generateType === "image_to_video"
                    ? "🎞️ Generating Video from Image..."
                    : generateType === "vehicle_restoration"
                      ? "🛠️ Restoring Vehicle..."
                      : generateType === "image_edit"
                        ? "🪄 Editing Image..."
                        : "⏳ Generating..."
                : generateType === "image"
                  ? "✨ Generate Image"
                  : generateType === "ai_video"
                    ? "🎬 Generate AI Video"
                    : generateType === "image_to_video"
                      ? "🎞️ Generate Video from Image"
                      : generateType === "vehicle_restoration"
                        ? "🛠️ Generate Restoration Video"
                        : generateType === "image_edit"
                          ? "🪄 Edit Image"
                          : "📸 Generate Reel"}
            </button>

            {isGenerating && (
              <div
                style={{
                  marginTop: 6,
                  padding: 10,
                  borderRadius: 10,
                  border: "1px solid #333",
                  background: "#11131d",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 10,
                    marginBottom: 6,
                  }}
                >
                  <div style={{ color: "#cbd5e1", fontSize: "0.8em" }}>
                    {genUiPhase || "Generating…"}
                  </div>
                  <div style={{ color: "#94a3b8", fontSize: "0.8em" }}>
                    {genUiStartedAt
                      ? `${Math.floor((Date.now() - genUiStartedAt) / 1000)}s`
                      : ""}
                  </div>
                </div>
                <div
                  style={{
                    height: 10,
                    background: "#0b1220",
                    borderRadius: 999,
                    border: "1px solid #334155",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      width: `${Math.max(
                        0,
                        Math.min(100, Number(genUiProgress) || 0),
                      )}%`,
                      background: "linear-gradient(90deg, #10b981, #059669)",
                      transition: "width 350ms ease",
                    }}
                  />
                </div>
                <div
                  style={{
                    marginTop: 6,
                    color: "#94a3b8",
                    fontSize: "0.75em",
                  }}
                >
                  {`${Math.max(
                    0,
                    Math.min(100, Number(genUiProgress) || 0),
                  ).toFixed(0)}%`}{" "}
                  • Keep this tab open while it renders.
                </div>
              </div>
            )}

            {/* Generated Result */}
            {generatedResult && (
              <div
                style={{
                  padding: "12px",
                  borderRadius: "10px",
                  backgroundColor: generatedResult.success
                    ? "#1a2e1a"
                    : "#2e1a1a",
                  border: `1px solid ${
                    generatedResult.success ? "#22c55e" : "#ef4444"
                  }`,
                }}
              >
                {generatedResult.success ? (
                  <>
                    <div
                      style={{
                        color: "#22c55e",
                        fontWeight: "bold",
                        marginBottom: "8px",
                      }}
                    >
                      ✅ Generated Successfully!
                    </div>
                    {(generatedResult.provider || generatedResult.method) && (
                      <div
                        style={{
                          color: "#86efac",
                          fontSize: "0.8em",
                          marginBottom: 8,
                        }}
                      >
                        Provider:{" "}
                        <strong>
                          {generatedResult.provider || generatedResult.method}
                        </strong>
                        {generatedResult.allow_unrelated_fallback
                          ? " (fallback enabled)"
                          : ""}
                      </div>
                    )}
                    {generatedResult.urls && generatedResult.urls[0] && (
                      <div style={{ marginBottom: "8px" }}>
                        <img
                          src={`${backendUrl}${generatedResult.urls[0]}`}
                          alt="Generated"
                          style={{
                            width: "100%",
                            borderRadius: "8px",
                            maxHeight: "200px",
                            objectFit: "cover",
                          }}
                        />
                      </div>
                    )}
                    {generatedResult.url && (
                      <div style={{ marginBottom: "8px" }}>
                        {generateType === "vehicle_restoration" &&
                        i2vSourcePreview ? (
                          <div
                            style={{
                              borderRadius: 10,
                              border: "1px solid #1f2937",
                              background: "#0b1220",
                              padding: 10,
                            }}
                          >
                            <div
                              style={{
                                color: "#cbd5e1",
                                fontWeight: 800,
                                fontSize: "0.85em",
                                marginBottom: 8,
                              }}
                            >
                              🪟 Before ↔ After comparison
                            </div>

                            <div
                              style={{
                                position: "relative",
                                width: "100%",
                                maxHeight: 240,
                                aspectRatio: "16 / 9",
                                overflow: "hidden",
                                borderRadius: 10,
                                border: "1px solid #0f172a",
                              }}
                            >
                              <img
                                src={i2vSourcePreview}
                                alt="Before"
                                style={{
                                  position: "absolute",
                                  inset: 0,
                                  width: "100%",
                                  height: "100%",
                                  objectFit: "cover",
                                }}
                              />
                              <video
                                ref={vehicleRestoreCompareVideoRef}
                                src={`${backendUrl}${generatedResult.url}`}
                                controls
                                playsInline
                                style={{
                                  position: "absolute",
                                  inset: 0,
                                  width: "100%",
                                  height: "100%",
                                  objectFit: "cover",
                                  clipPath: `inset(0 ${Math.max(
                                    0,
                                    Math.min(
                                      100,
                                      100 - vehicleRestoreComparePct,
                                    ),
                                  )}% 0 0)`,
                                }}
                              />

                              <div
                                style={{
                                  position: "absolute",
                                  top: 0,
                                  bottom: 0,
                                  left: `${Math.max(
                                    0,
                                    Math.min(100, vehicleRestoreComparePct),
                                  )}%`,
                                  width: 2,
                                  transform: "translateX(-1px)",
                                  background:
                                    "linear-gradient(180deg, rgba(236,72,153,0.0), rgba(236,72,153,0.9), rgba(236,72,153,0.0))",
                                  boxShadow:
                                    "0 0 0 1px rgba(0,0,0,0.25), 0 0 18px rgba(236,72,153,0.35)",
                                  pointerEvents: "none",
                                }}
                              />
                            </div>

                            <div
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 10,
                                marginTop: 10,
                                flexWrap: "wrap",
                              }}
                            >
                              <div style={{ color: "#94a3b8", fontSize: 12 }}>
                                Before
                              </div>
                              <input
                                type="range"
                                min={0}
                                max={100}
                                value={vehicleRestoreComparePct}
                                onChange={(e) =>
                                  setVehicleRestoreComparePct(
                                    Number(e.target.value || 50),
                                  )
                                }
                                style={{ flex: 1 }}
                              />
                              <div style={{ color: "#94a3b8", fontSize: 12 }}>
                                After
                              </div>
                              <button
                                onClick={() => {
                                  const v =
                                    vehicleRestoreCompareVideoRef.current;
                                  if (v) {
                                    try {
                                      v.currentTime = 0;
                                      v.pause();
                                    } catch {}
                                  }
                                }}
                                style={{
                                  padding: "6px 10px",
                                  borderRadius: 8,
                                  border: "1px solid rgba(148,163,184,0.35)",
                                  background: "rgba(148,163,184,0.08)",
                                  color: "#cbd5e1",
                                  cursor: "pointer",
                                  fontSize: "0.78em",
                                }}
                                title="Jump video back to start"
                              >
                                ⏮️ Restart
                              </button>
                            </div>
                          </div>
                        ) : (
                          <video
                            src={`${backendUrl}${generatedResult.url}`}
                            controls
                            style={{
                              width: "100%",
                              borderRadius: "8px",
                              maxHeight: "200px",
                            }}
                          />
                        )}
                      </div>
                    )}
                    <div
                      style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}
                    >
                      {generatedResult.download_urls &&
                        generatedResult.download_urls[0] && (
                          <button
                            onClick={() =>
                              downloadFile(
                                generatedResult.download_urls[0],
                                "generated_image.png",
                              )
                            }
                            style={{
                              padding: "8px 12px",
                              borderRadius: "6px",
                              border: "none",
                              background: "#22c55e",
                              color: "white",
                              cursor: "pointer",
                              fontSize: "0.8em",
                            }}
                          >
                            ⬇️ Download Image
                          </button>
                        )}
                      {generatedResult.download_url && (
                        <button
                          onClick={() =>
                            downloadFile(
                              generatedResult.download_url,
                              generateType === "vehicle_restoration"
                                ? "vehicle_restoration.mp4"
                                : "generated_reel.mp4",
                            )
                          }
                          style={{
                            padding: "8px 12px",
                            borderRadius: "6px",
                            border: "none",
                            background: "#8b5cf6",
                            color: "white",
                            cursor: "pointer",
                            fontSize: "0.8em",
                          }}
                        >
                          ⬇️ Download{" "}
                          {generateType === "vehicle_restoration"
                            ? "Restoration Video"
                            : "Reel"}
                        </button>
                      )}
                      {/* Clear Result Button */}
                      <button
                        onClick={() => {
                          setGeneratedResult(null);
                          setGeneratePrompt("");
                          setAiVideoNegativePrompt("");
                        }}
                        style={{
                          padding: "8px 12px",
                          borderRadius: "6px",
                          border: "1px solid rgba(239, 68, 68, 0.4)",
                          background: "rgba(239, 68, 68, 0.15)",
                          color: "#f87171",
                          cursor: "pointer",
                          fontSize: "0.8em",
                        }}
                        title="Clear result"
                      >
                        🗑️ Clear
                      </button>

                      <button
                        onClick={() => setShowGenDebug((v) => !v)}
                        style={{
                          padding: "8px 12px",
                          borderRadius: "6px",
                          border: "1px solid rgba(148, 163, 184, 0.35)",
                          background: "rgba(148, 163, 184, 0.08)",
                          color: "#cbd5e1",
                          cursor: "pointer",
                          fontSize: "0.8em",
                        }}
                        title="Show request / provider debug info"
                      >
                        🛠️ Debug
                      </button>
                    </div>

                    {showGenDebug &&
                      (generatedResult.provider_errors || lastGenDebug) && (
                        <div
                          style={{
                            marginTop: 10,
                            padding: 10,
                            borderRadius: 10,
                            background: "#0f172a",
                            border: "1px solid #1f2937",
                            color: "#cbd5e1",
                            fontSize: "0.78em",
                          }}
                        >
                          <div style={{ fontWeight: "bold", marginBottom: 6 }}>
                            Debug details
                          </div>

                          {Array.isArray(generatedResult.provider_errors) &&
                            generatedResult.provider_errors.length > 0 && (
                              <div style={{ marginBottom: 8 }}>
                                <div
                                  style={{ color: "#93c5fd", marginBottom: 4 }}
                                >
                                  Provider errors:
                                </div>
                                <ul style={{ margin: "0 0 0 18px" }}>
                                  {generatedResult.provider_errors
                                    .slice(0, 12)
                                    .map((e, i) => (
                                      <li key={i}>{String(e)}</li>
                                    ))}
                                </ul>
                              </div>
                            )}

                          {lastGenDebug && (
                            <div style={{ color: "#94a3b8" }}>
                              {typeof lastGenDebug.durationMs === "number" && (
                                <div style={{ marginBottom: 6 }}>
                                  Duration:{" "}
                                  {(lastGenDebug.durationMs / 1000).toFixed(1)}s
                                </div>
                              )}
                              {lastGenDebug.requestBody && (
                                <div>
                                  <div
                                    style={{
                                      color: "#93c5fd",
                                      marginBottom: 4,
                                    }}
                                  >
                                    Request body:
                                  </div>
                                  <pre
                                    style={{
                                      margin: 0,
                                      whiteSpace: "pre-wrap",
                                      wordBreak: "break-word",
                                      background: "#0b1220",
                                      border: "1px solid #1f2937",
                                      borderRadius: 8,
                                      padding: 8,
                                      maxHeight: 220,
                                      overflow: "auto",
                                    }}
                                  >
                                    {JSON.stringify(
                                      lastGenDebug.requestBody,
                                      null,
                                      2,
                                    )}
                                  </pre>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                  </>
                ) : (
                  <div style={{ color: "#ef4444" }}>
                    <div>❌ Error: {generatedResult.error}</div>
                    {Array.isArray(generatedResult.provider_errors) &&
                      generatedResult.provider_errors.length > 0 && (
                        <div style={{ marginTop: 8, color: "#fca5a5" }}>
                          <div style={{ fontWeight: "bold", marginBottom: 4 }}>
                            Provider details:
                          </div>
                          <ul style={{ margin: "0 0 0 18px" }}>
                            {generatedResult.provider_errors
                              .slice(0, 12)
                              .map((e, i) => (
                                <li key={i}>{String(e)}</li>
                              ))}
                          </ul>
                        </div>
                      )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Convert Tab */}
        {activeTab === "convert" && (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "12px" }}
          >
            <div
              style={{
                fontSize: "0.9em",
                color: "#a78bfa",
                fontWeight: "bold",
              }}
            >
              📺 FB Reel ➜ YouTube Ready
            </div>
            <div style={{ fontSize: "0.8em", color: "#888" }}>
              Paste a downloaded reel URL or pick an existing video from the
              list below. We will pad or blur the sides to deliver a 16:9 file
              ready for YouTube.
            </div>

            <input
              value={reelUrl}
              onChange={(e) => setReelUrl(e.target.value)}
              placeholder="https://www.facebook.com/reel/... (direct MP4 link)"
              style={{
                width: "100%",
                padding: "10px",
                borderRadius: "10px",
                border: "1px solid #333",
                backgroundColor: "#11131d",
                color: "white",
              }}
            />

            <div style={{ fontSize: "0.8em", color: "#666" }}>or</div>
            <div
              style={{
                display: "flex",
                gap: "8px",
                alignItems: "center",
                flexWrap: "wrap",
              }}
            >
              <label
                style={{
                  padding: "10px 14px",
                  borderRadius: "10px",
                  border: "1px dashed #444",
                  backgroundColor: "#11131d",
                  color: "white",
                  cursor: isUploading ? "not-allowed" : "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <span>📂 Upload local video</span>
                <input
                  type="file"
                  accept="video/*"
                  onChange={handleUploadVideo}
                  disabled={isUploading}
                  style={{ display: "none" }}
                />
              </label>
              {isUploading && (
                <span style={{ color: "#a78bfa", fontSize: "0.85em" }}>
                  Uploading...
                </span>
              )}
              {uploadInfo && (
                <span style={{ color: "#10b981", fontSize: "0.85em" }}>
                  {uploadInfo}
                </span>
              )}
            </div>

            {uploadError && (
              <div
                style={{
                  color: "#ef4444",
                  backgroundColor: "#2e1a1a",
                  border: "1px solid #ef4444",
                  borderRadius: "8px",
                  padding: "8px 10px",
                  fontSize: "0.85em",
                }}
              >
                ❌ Upload failed: {uploadError}
              </div>
            )}

            {existingReel && (
              <div
                style={{
                  padding: "8px 12px",
                  borderRadius: "8px",
                  backgroundColor: "#1a2e1a",
                  border: "1px solid #22c55e",
                  color: "#22c55e",
                  fontSize: "0.85em",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <span>🎬 Selected: {existingReel}</span>
                <button
                  onClick={() => {
                    setExistingReel("");
                    setUploadInfo("");
                  }}
                  style={{
                    background: "none",
                    border: "none",
                    color: "#ef4444",
                    cursor: "pointer",
                    fontSize: "1em",
                  }}
                  title="Clear selection"
                >
                  ✕
                </button>
              </div>
            )}

            <select
              value={existingReel}
              onChange={(e) => {
                setExistingReel(e.target.value);
                setUploadInfo("");
                setReelUrl("");
                setConversionResult(null);
              }}
              style={{
                width: "100%",
                padding: "10px",
                borderRadius: "10px",
                border: existingReel ? "2px solid #22c55e" : "1px solid #333",
                backgroundColor: "#11131d",
                color: "white",
              }}
            >
              <option value="">Select existing video</option>
              {mediaFiles.videos.map((vid) => (
                <option key={vid.name} value={vid.name}>
                  {vid.name}
                </option>
              ))}
            </select>

            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: "140px" }}>
                <div style={{ color: "#888", fontSize: "0.8em" }}>
                  🎞️ Resolution
                </div>
                <select
                  value={conversionResolution}
                  onChange={(e) => setConversionResolution(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px",
                    borderRadius: "8px",
                    border: "1px solid #333",
                    backgroundColor: "#11131d",
                    color: "white",
                  }}
                >
                  <option value="1920x1080">1920x1080 (YouTube)</option>
                  <option value="1280x720">1280x720</option>
                </select>
              </div>

              <div style={{ minWidth: "120px" }}>
                <div style={{ color: "#888", fontSize: "0.8em" }}>
                  🎨 Side color
                </div>
                <input
                  type="color"
                  value={padColor}
                  onChange={(e) => setPadColor(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "6px",
                    borderRadius: "8px",
                    border: "1px solid #333",
                    backgroundColor: "#11131d",
                  }}
                />
              </div>

              <div style={{ minWidth: "140px" }}>
                <div style={{ color: "#888", fontSize: "0.8em" }}>
                  🌫️ Background
                </div>
                <button
                  onClick={() => setBlurBackground((prev) => !prev)}
                  style={{
                    width: "100%",
                    padding: "10px",
                    borderRadius: "8px",
                    border: blurBackground
                      ? "2px solid #8b5cf6"
                      : "1px solid #333",
                    backgroundColor: blurBackground ? "#1a1a2e" : "#11131d",
                    color: "white",
                    cursor: "pointer",
                  }}
                >
                  {blurBackground ? "Blurred fill" : "Solid padding"}
                </button>
              </div>
            </div>

            <button
              onClick={handleConvertReel}
              disabled={isConverting || (!reelUrl.trim() && !existingReel)}
              style={{
                padding: "14px",
                borderRadius: "10px",
                border: "none",
                background:
                  !reelUrl.trim() && !existingReel
                    ? "#333"
                    : "linear-gradient(135deg, #ef4444, #6366f1)",
                color: "white",
                cursor:
                  isConverting || (!reelUrl.trim() && !existingReel)
                    ? "not-allowed"
                    : "pointer",
                fontWeight: "bold",
                fontSize: "1em",
              }}
            >
              {isConverting ? "⏳ Converting..." : "📺 Convert to YouTube"}
            </button>

            {conversionResult && (
              <div
                style={{
                  padding: "12px",
                  borderRadius: "10px",
                  backgroundColor: conversionResult.success
                    ? "#1a2e1a"
                    : "#2e1a1a",
                  border: `1px solid ${
                    conversionResult.success ? "#22c55e" : "#ef4444"
                  }`,
                }}
              >
                {conversionResult.success ? (
                  <>
                    <div
                      style={{
                        color: "#22c55e",
                        fontWeight: "bold",
                        marginBottom: "8px",
                      }}
                    >
                      ✅ YouTube-ready file created
                    </div>
                    {conversionResult.url && (
                      <video
                        src={`${backendUrl}${conversionResult.url}`}
                        controls
                        style={{
                          width: "100%",
                          maxHeight: "260px",
                          borderRadius: "8px",
                          backgroundColor: "#000",
                        }}
                      />
                    )}
                    <div
                      style={{
                        marginTop: "8px",
                        display: "flex",
                        gap: "8px",
                      }}
                    >
                      <button
                        onClick={() =>
                          downloadFile(
                            conversionResult.download_url,
                            conversionResult.source
                              ? `youtube_${conversionResult.source}`
                              : "youtube_ready.mp4",
                          )
                        }
                        style={{
                          padding: "10px 12px",
                          borderRadius: "8px",
                          border: "none",
                          background: "#8b5cf6",
                          color: "white",
                          cursor: "pointer",
                          fontSize: "0.9em",
                        }}
                      >
                        ⬇️ Download
                      </button>
                      <div
                        style={{
                          color: "#888",
                          fontSize: "0.8em",
                          alignSelf: "center",
                        }}
                      >
                        {conversionResult.target_resolution || "1920x1080"}
                      </div>
                    </div>
                  </>
                ) : (
                  <div style={{ color: "#ef4444" }}>
                    ❌ Error: {conversionResult.error}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Images Tab */}
        {activeTab === "images" && (
          <div>
            {selectedMedia ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                }}
              >
                <button
                  onClick={() => setSelectedMedia(null)}
                  style={{
                    padding: "8px",
                    background: "transparent",
                    border: "1px solid #444",
                    borderRadius: "6px",
                    color: "#a78bfa",
                    cursor: "pointer",
                    fontSize: "0.85em",
                    alignSelf: "flex-start",
                  }}
                >
                  ← Back to list
                </button>
                <img
                  src={`${backendUrl}${selectedMedia.url}`}
                  alt={selectedMedia.name}
                  style={{
                    width: "100%",
                    borderRadius: "10px",
                    maxHeight: "350px",
                    objectFit: "contain",
                    backgroundColor: "#000",
                  }}
                />
                <div style={{ color: "#888", fontSize: "0.85em" }}>
                  {selectedMedia.name}
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    onClick={() =>
                      downloadFile(
                        `/media/download/images/${selectedMedia.name}`,
                        selectedMedia.name,
                      )
                    }
                    style={{
                      flex: 1,
                      padding: "12px",
                      borderRadius: "8px",
                      border: "none",
                      background: "linear-gradient(135deg, #22c55e, #16a34a)",
                      color: "white",
                      cursor: "pointer",
                      fontWeight: "bold",
                    }}
                  >
                    ⬇️ Download
                  </button>
                  {onSendToCanvas && (
                    <button
                      onClick={() =>
                        onSendToCanvas(`${backendUrl}${selectedMedia.url}`)
                      }
                      style={{
                        flex: 1,
                        padding: "12px",
                        borderRadius: "8px",
                        border: "none",
                        background: "linear-gradient(135deg, #8b5cf6, #6366f1)",
                        color: "white",
                        cursor: "pointer",
                        fontWeight: "bold",
                      }}
                    >
                      🎨 Edit in Canvas
                    </button>
                  )}
                  <button
                    onClick={() => deleteMedia("images", selectedMedia.name)}
                    style={{
                      padding: "12px 16px",
                      borderRadius: "8px",
                      border: "none",
                      background: "linear-gradient(135deg, #ef4444, #dc2626)",
                      color: "white",
                      cursor: "pointer",
                      fontWeight: "bold",
                    }}
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ) : (
              <div
                style={{ display: "flex", flexDirection: "column", gap: 10 }}
              >
                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    flexWrap: "wrap",
                    alignItems: "center",
                    padding: 10,
                    borderRadius: 10,
                    border: "1px solid #333",
                    background: "#11131d",
                  }}
                >
                  <button
                    onClick={() => cleanupImages("all")}
                    disabled={isCleaningUpMedia}
                    style={{
                      padding: "10px 12px",
                      borderRadius: 10,
                      border: "1px solid rgba(239, 68, 68, 0.35)",
                      background: "rgba(239, 68, 68, 0.12)",
                      color: "#fecaca",
                      cursor: isCleaningUpMedia ? "not-allowed" : "pointer",
                      fontWeight: "bold",
                      whiteSpace: "nowrap",
                    }}
                    title="Delete all images to reclaim disk space"
                  >
                    🧹 Delete all
                  </button>

                  <div
                    style={{ display: "flex", gap: 6, alignItems: "center" }}
                  >
                    <span style={{ color: "#888", fontSize: "0.78em" }}>
                      Older than
                    </span>
                    <input
                      type="number"
                      min={1}
                      value={imageCleanupDays}
                      onChange={(e) =>
                        setImageCleanupDays(() => {
                          const v = parseInt(String(e.target.value || ""), 10);
                          return Number.isFinite(v) ? Math.max(1, v) : 30;
                        })
                      }
                      style={{
                        width: 80,
                        padding: "8px 10px",
                        borderRadius: 10,
                        border: "1px solid #333",
                        background: "#0f0f1a",
                        color: "#e5e7eb",
                      }}
                    />
                    <span style={{ color: "#888", fontSize: "0.78em" }}>
                      days
                    </span>
                    <button
                      onClick={() => cleanupImages("older_than_days")}
                      disabled={isCleaningUpMedia}
                      style={{
                        padding: "10px 12px",
                        borderRadius: 10,
                        border: "1px solid rgba(245, 158, 11, 0.35)",
                        background: "rgba(245, 158, 11, 0.12)",
                        color: "#fde68a",
                        cursor: isCleaningUpMedia ? "not-allowed" : "pointer",
                        whiteSpace: "nowrap",
                      }}
                    >
                      🧹 Delete
                    </button>
                  </div>

                  <div
                    style={{ display: "flex", gap: 6, alignItems: "center" }}
                  >
                    <span style={{ color: "#888", fontSize: "0.78em" }}>
                      Keep newest
                    </span>
                    <input
                      type="number"
                      min={0}
                      value={imageCleanupKeepNewest}
                      onChange={(e) =>
                        setImageCleanupKeepNewest(() => {
                          const v = parseInt(String(e.target.value || ""), 10);
                          return Number.isFinite(v) ? Math.max(0, v) : 100;
                        })
                      }
                      style={{
                        width: 90,
                        padding: "8px 10px",
                        borderRadius: 10,
                        border: "1px solid #333",
                        background: "#0f0f1a",
                        color: "#e5e7eb",
                      }}
                    />
                    <button
                      onClick={() => cleanupImages("keep_newest")}
                      disabled={isCleaningUpMedia}
                      style={{
                        padding: "10px 12px",
                        borderRadius: 10,
                        border: "1px solid rgba(139, 92, 246, 0.35)",
                        background: "rgba(139, 92, 246, 0.12)",
                        color: "#c4b5fd",
                        cursor: isCleaningUpMedia ? "not-allowed" : "pointer",
                        whiteSpace: "nowrap",
                      }}
                    >
                      🧹 Trim
                    </button>
                  </div>

                  <div style={{ color: "#666", fontSize: "0.75em" }}>
                    {isCleaningUpMedia
                      ? "Cleaning up…"
                      : "These actions permanently delete files to save disk space."}
                  </div>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, 1fr)",
                    gap: "8px",
                  }}
                >
                  {mediaFiles.images.length === 0 ? (
                    <div
                      style={{
                        gridColumn: "1 / -1",
                        textAlign: "center",
                        color: "#666",
                        padding: "40px",
                      }}
                    >
                      No images yet. Generate one in the Generate tab!
                    </div>
                  ) : (
                    mediaFiles.images.map((img, idx) => (
                      <div
                        key={idx}
                        style={{
                          position: "relative",
                          cursor: "pointer",
                          borderRadius: "8px",
                          overflow: "hidden",
                          border: "1px solid #333",
                          transition: "transform 0.2s",
                        }}
                        onMouseEnter={(e) =>
                          (e.currentTarget.style.transform = "scale(1.05)")
                        }
                        onMouseLeave={(e) =>
                          (e.currentTarget.style.transform = "scale(1)")
                        }
                      >
                        <img
                          src={`${backendUrl}${img.url}`}
                          alt={img.name}
                          onClick={() => setSelectedMedia(img)}
                          style={{
                            width: "100%",
                            height: "80px",
                            objectFit: "cover",
                          }}
                        />
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteMedia("images", img.name);
                          }}
                          style={{
                            position: "absolute",
                            top: "4px",
                            right: "4px",
                            width: "22px",
                            height: "22px",
                            borderRadius: "50%",
                            border: "none",
                            background: "rgba(239, 68, 68, 0.9)",
                            color: "white",
                            fontSize: "0.7em",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                          title="Delete"
                        >
                          ✕
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Videos Tab */}
        {activeTab === "videos" && (
          <div>
            {selectedMedia ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                }}
              >
                <button
                  onClick={() => setSelectedMedia(null)}
                  style={{
                    padding: "8px",
                    background: "transparent",
                    border: "1px solid #444",
                    borderRadius: "6px",
                    color: "#a78bfa",
                    cursor: "pointer",
                    fontSize: "0.85em",
                    alignSelf: "flex-start",
                  }}
                >
                  ← Back to list
                </button>
                <video
                  src={`${backendUrl}${selectedMedia.url}`}
                  controls
                  autoPlay
                  style={{
                    width: "100%",
                    borderRadius: "10px",
                    maxHeight: "300px",
                    backgroundColor: "#000",
                  }}
                />
                <div style={{ color: "#888", fontSize: "0.85em" }}>
                  {selectedMedia.name}
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    onClick={() =>
                      downloadFile(
                        `/media/download/videos/${selectedMedia.name}`,
                        selectedMedia.name,
                      )
                    }
                    style={{
                      flex: 1,
                      padding: "12px",
                      borderRadius: "8px",
                      border: "none",
                      background: "linear-gradient(135deg, #8b5cf6, #6366f1)",
                      color: "white",
                      cursor: "pointer",
                      fontWeight: "bold",
                    }}
                  >
                    ⬇️ Download
                  </button>
                  <button
                    onClick={() => deleteMedia("videos", selectedMedia.name)}
                    style={{
                      padding: "12px 16px",
                      borderRadius: "8px",
                      border: "none",
                      background: "linear-gradient(135deg, #ef4444, #dc2626)",
                      color: "white",
                      cursor: "pointer",
                      fontWeight: "bold",
                    }}
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ) : (
              <div
                style={{ display: "flex", flexDirection: "column", gap: "8px" }}
              >
                {mediaFiles.videos.length === 0 ? (
                  <div
                    style={{
                      textAlign: "center",
                      color: "#666",
                      padding: "40px",
                    }}
                  >
                    No videos yet. Generate a reel in the Generate tab!
                  </div>
                ) : (
                  mediaFiles.videos.map((vid, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "12px",
                        padding: "10px",
                        backgroundColor: "#1a1a2e",
                        borderRadius: "8px",
                        cursor: "pointer",
                        border: "1px solid #333",
                      }}
                    >
                      <span
                        style={{ fontSize: "1.5em" }}
                        onClick={() => setSelectedMedia(vid)}
                      >
                        🎥
                      </span>
                      <div
                        style={{ flex: 1 }}
                        onClick={() => setSelectedMedia(vid)}
                      >
                        <div style={{ color: "#fff", fontSize: "0.9em" }}>
                          {vid.name}
                        </div>
                        <div style={{ color: "#666", fontSize: "0.75em" }}>
                          {(vid.size_bytes / 1024 / 1024).toFixed(2)} MB
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteMedia("videos", vid.name);
                        }}
                        style={{
                          padding: "6px 10px",
                          borderRadius: "6px",
                          border: "none",
                          background: "#ef4444",
                          color: "white",
                          fontSize: "0.75em",
                          cursor: "pointer",
                        }}
                        title="Delete"
                      >
                        🗑️
                      </button>
                      <span
                        style={{ color: "#8b5cf6" }}
                        onClick={() => setSelectedMedia(vid)}
                      >
                        ▶
                      </span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        )}

        {/* Audio Tab */}
        {activeTab === "audio" && (
          <div>
            {selectedMedia ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                }}
              >
                <button
                  onClick={() => setSelectedMedia(null)}
                  style={{
                    padding: "8px",
                    background: "transparent",
                    border: "1px solid #444",
                    borderRadius: "6px",
                    color: "#a78bfa",
                    cursor: "pointer",
                    fontSize: "0.85em",
                    alignSelf: "flex-start",
                  }}
                >
                  ← Back to list
                </button>
                <div
                  style={{
                    padding: "40px",
                    textAlign: "center",
                    backgroundColor: "#1a1a2e",
                    borderRadius: "10px",
                  }}
                >
                  <div style={{ fontSize: "4em", marginBottom: "12px" }}>
                    🎵
                  </div>
                  <div style={{ color: "#fff", marginBottom: "12px" }}>
                    {selectedMedia.name}
                  </div>
                  <audio
                    src={`${backendUrl}${selectedMedia.url}`}
                    controls
                    autoPlay
                    style={{ width: "100%" }}
                  />
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    onClick={() =>
                      downloadFile(
                        `/media/download/audio/${selectedMedia.name}`,
                        selectedMedia.name,
                      )
                    }
                    style={{
                      flex: 1,
                      padding: "12px",
                      borderRadius: "8px",
                      border: "none",
                      background: "linear-gradient(135deg, #f59e0b, #d97706)",
                      color: "white",
                      cursor: "pointer",
                      fontWeight: "bold",
                    }}
                  >
                    ⬇️ Download
                  </button>
                  <button
                    onClick={() => deleteMedia("audio", selectedMedia.name)}
                    style={{
                      padding: "12px 16px",
                      borderRadius: "8px",
                      border: "none",
                      background: "linear-gradient(135deg, #ef4444, #dc2626)",
                      color: "white",
                      cursor: "pointer",
                      fontWeight: "bold",
                    }}
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ) : (
              <div
                style={{ display: "flex", flexDirection: "column", gap: "8px" }}
              >
                {mediaFiles.audio.length === 0 ? (
                  <div
                    style={{
                      textAlign: "center",
                      color: "#666",
                      padding: "40px",
                    }}
                  >
                    No audio files yet. Extract audio from a video or add files
                    to media_outputs/audio/
                  </div>
                ) : (
                  mediaFiles.audio.map((aud, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "12px",
                        padding: "10px",
                        backgroundColor: "#1a1a2e",
                        borderRadius: "8px",
                        cursor: "pointer",
                        border: "1px solid #333",
                      }}
                    >
                      <span
                        style={{ fontSize: "1.5em" }}
                        onClick={() => setSelectedMedia(aud)}
                      >
                        🎵
                      </span>
                      <div
                        style={{ flex: 1 }}
                        onClick={() => setSelectedMedia(aud)}
                      >
                        <div style={{ color: "#fff", fontSize: "0.9em" }}>
                          {aud.name}
                        </div>
                        <div style={{ color: "#666", fontSize: "0.75em" }}>
                          {(aud.size_bytes / 1024).toFixed(0)} KB
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteMedia("audio", aud.name);
                        }}
                        style={{
                          padding: "6px 10px",
                          borderRadius: "6px",
                          border: "none",
                          background: "#ef4444",
                          color: "white",
                          fontSize: "0.75em",
                          cursor: "pointer",
                        }}
                        title="Delete"
                      >
                        🗑️
                      </button>
                      <span
                        style={{ color: "#f59e0b" }}
                        onClick={() => setSelectedMedia(aud)}
                      >
                        ▶
                      </span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === "musicvideo" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div
              style={{
                background: "linear-gradient(135deg, #0b1220 0%, #111827 100%)",
                borderRadius: 12,
                padding: 16,
                border: "1px solid #334155",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 12,
                }}
              >
                <div>
                  <h3 style={{ margin: "0 0 6px 0", color: "#e5e7eb" }}>
                    🎶 Anime Music Video Generator
                  </h3>
                  <div style={{ color: "#94a3b8", fontSize: "0.85em" }}>
                    Upload an MP3 and I’ll automatically render a synced 1080p
                    anime-style MV with continuous motion.
                  </div>
                </div>
                <button
                  onClick={() => {
                    fetchMusicVideoJobs();
                    if (mvActiveJobId) fetchMusicVideoJob(mvActiveJobId);
                  }}
                  style={{
                    padding: "8px 10px",
                    borderRadius: 10,
                    border: "1px solid #334155",
                    background: "#0b1220",
                    color: "#cbd5e1",
                    cursor: "pointer",
                    height: 36,
                  }}
                >
                  ↻ Refresh
                </button>
              </div>
            </div>

            <div
              style={{
                background: "#0f172a",
                borderRadius: 12,
                padding: 14,
                border: "1px solid #1f2937",
              }}
            >
              {(() => {
                const mvBackend =
                  mvSystemStatus?.cloud_fallback?.default_backend ||
                  "pollinations";
                const isComfy = mvBackend === "comfyui";
                const comfyReachable = !!mvSystemStatus?.comfyui?.reachable;
                const comfyWorkflow =
                  !!mvSystemStatus?.comfyui?.workflow_exists;

                const stepSystemKnown = !!mvSystemStatus;
                const stepBackendReady =
                  !isComfy || (comfyReachable && comfyWorkflow);
                const stepHasJob = !!mvActiveJobId || (mvJobs?.length || 0) > 0;
                const stepCompleted = !!mvActiveJob?.output_url;

                const chip = (ok, label) => (
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                      padding: "4px 8px",
                      borderRadius: 999,
                      border: ok
                        ? "1px solid rgba(34, 197, 94, 0.45)"
                        : "1px solid rgba(148, 163, 184, 0.25)",
                      background: ok
                        ? "rgba(34, 197, 94, 0.12)"
                        : "rgba(148, 163, 184, 0.08)",
                      color: ok ? "#bbf7d0" : "#cbd5e1",
                      fontSize: "0.75em",
                      whiteSpace: "nowrap",
                    }}
                  >
                    <span style={{ fontSize: "1em" }}>{ok ? "✅" : "•"}</span>
                    <span>{label}</span>
                  </span>
                );

                const row = (idx, title, done, body) => (
                  <div
                    style={{
                      display: "flex",
                      gap: 10,
                      padding: "10px 10px",
                      borderRadius: 12,
                      border: done
                        ? "1px solid rgba(34, 197, 94, 0.20)"
                        : "1px solid rgba(148, 163, 184, 0.14)",
                      background: done
                        ? "rgba(34, 197, 94, 0.06)"
                        : "rgba(2, 6, 23, 0.20)",
                    }}
                  >
                    <div
                      style={{
                        width: 28,
                        height: 28,
                        borderRadius: 999,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        background: done
                          ? "rgba(34, 197, 94, 0.18)"
                          : "rgba(148, 163, 184, 0.10)",
                        border: done
                          ? "1px solid rgba(34, 197, 94, 0.35)"
                          : "1px solid rgba(148, 163, 184, 0.18)",
                        color: done ? "#bbf7d0" : "#cbd5e1",
                        flexShrink: 0,
                        fontSize: "0.85em",
                        fontWeight: 800,
                      }}
                    >
                      {done ? "✓" : idx}
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: 10,
                        }}
                      >
                        <div
                          style={{
                            color: "#e5e7eb",
                            fontWeight: 800,
                            fontSize: "0.9em",
                          }}
                        >
                          {title}
                        </div>
                        <div
                          style={{ display: "flex", gap: 8, flexWrap: "wrap" }}
                        >
                          {done ? chip(true, "done") : chip(false, "next")}
                        </div>
                      </div>
                      <div
                        style={{
                          marginTop: 6,
                          color: "#94a3b8",
                          fontSize: "0.82em",
                          lineHeight: 1.5,
                        }}
                      >
                        {body}
                      </div>
                    </div>
                  </div>
                );

                return (
                  <div>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        gap: 12,
                        marginBottom: mvShowSteps ? 10 : 0,
                      }}
                    >
                      <div>
                        <div style={{ color: "#e5e7eb", fontWeight: 800 }}>
                          Step-by-step (MP3 → MP4)
                        </div>
                        <div style={{ color: "#94a3b8", fontSize: "0.8em" }}>
                          Follow these in order. The checklist auto-updates as
                          you go.
                        </div>
                      </div>
                      <button
                        onClick={() => setMvShowSteps((v) => !v)}
                        style={{
                          padding: "8px 10px",
                          borderRadius: 10,
                          border: "1px solid #334155",
                          background: "#0b1220",
                          color: "#cbd5e1",
                          cursor: "pointer",
                          whiteSpace: "nowrap",
                          height: 36,
                        }}
                      >
                        {mvShowSteps ? "Hide" : "Show"}
                      </button>
                    </div>

                    {mvShowSteps && (
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 10,
                        }}
                      >
                        {row(
                          1,
                          "Confirm motion backend",
                          stepBackendReady,
                          <div>
                            <div style={{ marginBottom: 6 }}>
                              Current: <b>{mvBackend}</b>
                            </div>
                            <div
                              style={{
                                display: "flex",
                                gap: 8,
                                flexWrap: "wrap",
                              }}
                            >
                              {chip(stepSystemKnown, "status loaded")}
                              {isComfy
                                ? chip(comfyReachable, "ComfyUI reachable")
                                : chip(true, "no local setup needed")}
                              {isComfy
                                ? chip(comfyWorkflow, "workflow found")
                                : null}
                            </div>
                            {isComfy && !comfyWorkflow ? (
                              <div style={{ marginTop: 8 }}>
                                To use local ComfyUI you must set{" "}
                                <code>COMFYUI_WORKFLOW_PATH</code>
                                to a workflow JSON that outputs an MP4, then
                                refresh.
                              </div>
                            ) : null}
                            {!stepSystemKnown ? (
                              <div style={{ marginTop: 8 }}>
                                Click <b>↻ Re-check</b> in the status box below
                                if the backend is still starting.
                              </div>
                            ) : null}
                          </div>,
                        )}

                        {row(
                          2,
                          "Upload your MP3",
                          stepHasJob,
                          <div>
                            Choose an MP3 file below. Title / Artist / Lyrics
                            are optional but improve prompts.
                            {mvError ? (
                              <div style={{ marginTop: 6, color: "#fecaca" }}>
                                Upload error: {mvError}
                              </div>
                            ) : null}
                          </div>,
                        )}

                        {row(
                          3,
                          "Wait for rendering to finish",
                          stepCompleted,
                          <div>
                            Watch the <b>Progress</b> bar. You can switch jobs
                            in the <b>Jobs</b> list.
                            {mvActiveJob?.status ? (
                              <div style={{ marginTop: 6 }}>
                                Current status: <b>{mvActiveJob.status}</b>
                                {mvActiveJob.stage
                                  ? ` • ${mvActiveJob.stage}`
                                  : ""}
                              </div>
                            ) : null}
                          </div>,
                        )}

                        {row(
                          4,
                          "Open and download the MP4",
                          stepCompleted,
                          <div>
                            When complete, a <b>Preview</b> player and{" "}
                            <b>Open MP4</b> link will appear.
                            {mvActiveJob?.output_url ? (
                              <div style={{ marginTop: 6 }}>
                                Output ready:{" "}
                                <code>{mvActiveJob.output_url}</code>
                              </div>
                            ) : null}
                          </div>,
                        )}

                        <div
                          style={{
                            padding: "10px 12px",
                            borderRadius: 12,
                            border: "1px dashed rgba(148, 163, 184, 0.25)",
                            color: "#94a3b8",
                            fontSize: "0.8em",
                            lineHeight: 1.5,
                          }}
                        >
                          Tip: If you want fully-local motion later, configure
                          ComfyUI + a workflow, then switch the backend on the
                          server. For now, Pollinations is the “works out of the
                          box” option.
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>

            {mvSystemStatus &&
              (() => {
                const mvBackend =
                  mvSystemStatus?.cloud_fallback?.default_backend ||
                  "pollinations";
                const isComfy = mvBackend === "comfyui";

                return (
                  <div
                    style={{
                      background: isComfy
                        ? "rgba(16, 185, 129, 0.10)"
                        : "rgba(245, 158, 11, 0.10)",
                      border: isComfy
                        ? "1px solid rgba(16, 185, 129, 0.35)"
                        : "1px solid rgba(245, 158, 11, 0.35)",
                      color: isComfy ? "#bbf7d0" : "#fde68a",
                      borderRadius: 12,
                      padding: 14,
                      fontSize: "0.85em",
                      lineHeight: 1.4,
                    }}
                  >
                    <div style={{ fontWeight: 800, marginBottom: 6 }}>
                      Motion backend: {mvBackend}
                    </div>

                    {mvBackend === "pollinations" ? (
                      <div>
                        Using the free cloud motion backend (Pollinations). If
                        you want fully local generation, configure a ComfyUI
                        workflow (set <code>COMFYUI_WORKFLOW_PATH</code>) and
                        install a checkpoint model.
                      </div>
                    ) : mvBackend === "fal" ? (
                      <div>
                        Using fal.ai motion backend (requires{" "}
                        <code>FAL_KEY</code>).
                      </div>
                    ) : mvBackend === "replicate" ? (
                      <div>
                        Using Replicate motion backend (requires{" "}
                        <code>REPLICATE_API_TOKEN</code>).
                      </div>
                    ) : (
                      <div>
                        Using local ComfyUI. Workflow:{" "}
                        {mvSystemStatus?.comfyui?.workflow_exists
                          ? "found"
                          : "missing"}
                        . Server:{" "}
                        {mvSystemStatus?.comfyui?.reachable
                          ? "reachable"
                          : "not reachable"}
                        .
                      </div>
                    )}

                    <div
                      style={{
                        display: "flex",
                        gap: 10,
                        flexWrap: "wrap",
                        marginTop: 10,
                      }}
                    >
                      <button
                        onClick={() => fetchMusicVideoStatus()}
                        style={{
                          padding: "8px 10px",
                          borderRadius: 10,
                          border: "1px solid rgba(148, 163, 184, 0.35)",
                          background: "rgba(15, 23, 42, 0.7)",
                          color: "#cbd5e1",
                          cursor: "pointer",
                        }}
                      >
                        ↻ Re-check
                      </button>

                      <button
                        onClick={startComfyUI}
                        disabled={mvComfyBusy}
                        title={
                          mvSystemStatus?.comfyui?.can_start
                            ? `Detected: ${
                                mvSystemStatus?.comfyui?.detected_root || ""
                              }`
                            : "Will attempt to install ComfyUI into ./external/ComfyUI, then start it."
                        }
                        style={{
                          padding: "8px 10px",
                          borderRadius: 10,
                          border: "1px solid rgba(148, 163, 184, 0.35)",
                          background: "rgba(2, 6, 23, 0.35)",
                          color: "#cbd5e1",
                          cursor: mvComfyBusy ? "wait" : "pointer",
                          opacity: mvComfyBusy ? 0.7 : 1,
                        }}
                      >
                        {mvComfyBusy
                          ? "…Working"
                          : mvSystemStatus?.comfyui?.can_start
                            ? "▶ Start ComfyUI"
                            : "⬇ Install & Start ComfyUI"}
                      </button>

                      <a
                        href="http://127.0.0.1:8188/"
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          padding: "8px 10px",
                          borderRadius: 10,
                          border: "1px solid rgba(148, 163, 184, 0.35)",
                          background: "rgba(15, 23, 42, 0.7)",
                          color: "#cbd5e1",
                          textDecoration: "none",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                        }}
                      >
                        ↗ Open ComfyUI
                      </a>
                    </div>

                    {mvComfyMsg ? (
                      <div style={{ marginTop: 8, color: "#cbd5e1" }}>
                        {mvComfyMsg}
                      </div>
                    ) : null}

                    {mvSystemStatus?.comfyui ? (
                      <div style={{ marginTop: 8, color: "#94a3b8" }}>
                        ComfyUI: {mvSystemStatus.comfyui.url} —{" "}
                        {mvSystemStatus.comfyui.reachable
                          ? "reachable"
                          : `not reachable (${
                              mvSystemStatus.comfyui.detail || ""
                            })`}{" "}
                        — workflow{" "}
                        {mvSystemStatus.comfyui.workflow_exists
                          ? "found"
                          : "not found"}
                      </div>
                    ) : null}
                  </div>
                );
              })()}

            <div
              style={{
                background: "#0f172a",
                borderRadius: 12,
                padding: 14,
                border: "1px solid #1f2937",
              }}
            >
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <div style={{ flex: 1, minWidth: 180 }}>
                  <div
                    style={{
                      color: "#9ca3af",
                      fontSize: "0.75em",
                      marginBottom: 6,
                    }}
                  >
                    Title (optional)
                  </div>
                  <input
                    value={mvUploadTitle}
                    onChange={(e) => setMvUploadTitle(e.target.value)}
                    placeholder="e.g., Night Drive"
                    style={{
                      width: "100%",
                      padding: "10px",
                      borderRadius: 10,
                      border: "1px solid #334155",
                      background: "#0b1220",
                      color: "#e5e7eb",
                    }}
                  />
                </div>
                <div style={{ flex: 1, minWidth: 180 }}>
                  <div
                    style={{
                      color: "#9ca3af",
                      fontSize: "0.75em",
                      marginBottom: 6,
                    }}
                  >
                    Artist (optional)
                  </div>
                  <input
                    value={mvUploadArtist}
                    onChange={(e) => setMvUploadArtist(e.target.value)}
                    placeholder="e.g., Darrell"
                    style={{
                      width: "100%",
                      padding: "10px",
                      borderRadius: 10,
                      border: "1px solid #334155",
                      background: "#0b1220",
                      color: "#e5e7eb",
                    }}
                  />
                </div>
              </div>

              <div style={{ marginTop: 10 }}>
                <div
                  style={{
                    color: "#9ca3af",
                    fontSize: "0.75em",
                    marginBottom: 6,
                  }}
                >
                  Lyrics (optional)
                </div>
                <textarea
                  value={mvUploadLyrics}
                  onChange={(e) => setMvUploadLyrics(e.target.value)}
                  placeholder="Paste lyrics here (optional)."
                  rows={4}
                  style={{
                    width: "100%",
                    padding: "10px",
                    borderRadius: 10,
                    border: "1px solid #334155",
                    background: "#0b1220",
                    color: "#e5e7eb",
                    resize: "vertical",
                  }}
                />
              </div>

              <div style={{ marginTop: 10 }}>
                <div
                  style={{
                    color: "#9ca3af",
                    fontSize: "0.75em",
                    marginBottom: 6,
                  }}
                >
                  Anime prompt (optional)
                </div>

                <div
                  style={{
                    padding: "10px",
                    borderRadius: 10,
                    border: "1px solid #334155",
                    background: "rgba(2, 6, 23, 0.25)",
                    marginBottom: 10,
                  }}
                >
                  <div
                    style={{
                      color: "#a78bfa",
                      fontWeight: 800,
                      fontSize: "0.8em",
                      marginBottom: 8,
                    }}
                  >
                    🎛️ Style templates (Music Video)
                  </div>
                  <div
                    style={{
                      display: "flex",
                      gap: 8,
                      flexWrap: "wrap",
                      alignItems: "center",
                    }}
                  >
                    <select
                      value={mvPromptTemplateId}
                      onChange={(e) => setMvPromptTemplateId(e.target.value)}
                      style={{
                        flex: 1,
                        minWidth: 220,
                        padding: "10px",
                        borderRadius: 10,
                        border: "1px solid #334155",
                        backgroundColor: "#0b1220",
                        color: "#e5e7eb",
                      }}
                    >
                      <option value="">Choose a style…</option>
                      {getTemplatesForScope("musicvideo_style").map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                    </select>

                    <button
                      onClick={() => {
                        const t = getTemplatesForScope("musicvideo_style").find(
                          (x) => x.id === mvPromptTemplateId,
                        );
                        if (!t) return;
                        setMvUploadAnimePrompt(t.prompt || "");
                      }}
                      disabled={!mvPromptTemplateId}
                      style={{
                        padding: "10px 12px",
                        borderRadius: 10,
                        border: "1px solid rgba(34, 197, 94, 0.35)",
                        background: "rgba(34, 197, 94, 0.12)",
                        color: "#bbf7d0",
                        cursor: mvPromptTemplateId ? "pointer" : "not-allowed",
                        whiteSpace: "nowrap",
                      }}
                    >
                      Apply
                    </button>

                    <button
                      onClick={() => {
                        const name = window.prompt(
                          "Save MV style template as…",
                          "My MV style",
                        );
                        if (!name) return;
                        saveTemplate({
                          id: `custom_mv_${Date.now()}`,
                          scope: "musicvideo_style",
                          name: String(name).trim(),
                          prompt: mvUploadAnimePrompt || "",
                        });
                      }}
                      style={{
                        padding: "10px 12px",
                        borderRadius: 10,
                        border: "1px solid rgba(139, 92, 246, 0.35)",
                        background: "rgba(139, 92, 246, 0.12)",
                        color: "#c4b5fd",
                        cursor: "pointer",
                        whiteSpace: "nowrap",
                      }}
                      title="Save the current Anime prompt as a reusable style template"
                    >
                      Save
                    </button>

                    <button
                      onClick={() => {
                        if (!mvPromptTemplateId) return;
                        if (!isCustomTemplateId(mvPromptTemplateId)) {
                          alert(
                            "Built-in templates can’t be deleted. Save your own and delete that one.",
                          );
                          return;
                        }
                        if (!window.confirm("Delete this saved template?"))
                          return;
                        deleteTemplate(mvPromptTemplateId);
                        setMvPromptTemplateId("");
                      }}
                      disabled={!mvPromptTemplateId}
                      style={{
                        padding: "10px 12px",
                        borderRadius: 10,
                        border: "1px solid rgba(239, 68, 68, 0.35)",
                        background: "rgba(239, 68, 68, 0.12)",
                        color: "#fecaca",
                        cursor: mvPromptTemplateId ? "pointer" : "not-allowed",
                        whiteSpace: "nowrap",
                      }}
                    >
                      Delete
                    </button>
                  </div>
                  <div
                    style={{
                      marginTop: 8,
                      color: "#94a3b8",
                      fontSize: "0.75em",
                    }}
                  >
                    These templates only affect the <b>Anime prompt</b>{" "}
                    (prepended to each scene).
                  </div>
                </div>

                <textarea
                  value={mvUploadAnimePrompt}
                  onChange={(e) => setMvUploadAnimePrompt(e.target.value)}
                  placeholder="Example: Japanese anime, cinematic, clean line art, dramatic lighting, high quality, original characters only, no logos/watermarks, non-NSFW. (This gets prepended to each scene prompt.)"
                  rows={3}
                  style={{
                    width: "100%",
                    padding: "10px",
                    borderRadius: 10,
                    border: "1px solid #334155",
                    background: "#0b1220",
                    color: "#e5e7eb",
                    resize: "vertical",
                  }}
                />
                <div
                  style={{ marginTop: 6, color: "#94a3b8", fontSize: "0.78em" }}
                >
                  This is your style/constraints layer. The system still adds
                  section timing + motion direction automatically.
                </div>
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  marginTop: 10,
                }}
              >
                <input
                  type="file"
                  accept="audio/*,.mp3,.wav,.ogg,.flac,.aac,.m4a"
                  onChange={handleMusicVideoUpload}
                  disabled={isUploading}
                  style={{ flex: 1, color: "#cbd5e1" }}
                />
                {isUploading && (
                  <div style={{ color: "#fbbf24", fontSize: "0.85em" }}>
                    Uploading…
                  </div>
                )}
              </div>

              {mvError && (
                <div
                  style={{
                    marginTop: 10,
                    padding: 10,
                    borderRadius: 10,
                    background: "rgba(239, 68, 68, 0.12)",
                    border: "1px solid rgba(239, 68, 68, 0.35)",
                    color: "#fecaca",
                    fontSize: "0.85em",
                  }}
                >
                  {mvError}
                </div>
              )}
            </div>

            <div
              style={{
                background: "#0f172a",
                borderRadius: 12,
                padding: 14,
                border: "1px solid #1f2937",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 12,
                }}
              >
                <div>
                  <div style={{ color: "#e5e7eb", fontWeight: 700 }}>
                    {mvActiveJob?.title || "No active job"}
                  </div>
                  <div style={{ color: "#94a3b8", fontSize: "0.8em" }}>
                    {mvActiveJob?.artist ? `by ${mvActiveJob.artist}` : ""}
                    {mvActiveJob?.status ? ` • ${mvActiveJob.status}` : ""}
                    {mvActiveJob?.stage ? ` • ${mvActiveJob.stage}` : ""}
                  </div>
                </div>
                {mvActiveJobId && mvActiveJob?.status === "running" && (
                  <button
                    onClick={() => cancelMusicVideoJob(mvActiveJobId)}
                    style={{
                      padding: "8px 10px",
                      borderRadius: 10,
                      border: "1px solid rgba(239, 68, 68, 0.4)",
                      background: "rgba(239, 68, 68, 0.15)",
                      color: "#fecaca",
                      cursor: "pointer",
                      whiteSpace: "nowrap",
                    }}
                  >
                    ✖ Cancel
                  </button>
                )}
              </div>

              <div style={{ marginTop: 10 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 6,
                  }}
                >
                  <div style={{ color: "#cbd5e1", fontSize: "0.8em" }}>
                    Progress
                  </div>
                  <div style={{ color: "#cbd5e1", fontSize: "0.8em" }}>
                    {typeof mvActiveJob?.progress === "number"
                      ? `${mvActiveJob.progress.toFixed(1)}%`
                      : "0%"}
                  </div>
                </div>
                <div
                  style={{
                    height: 10,
                    background: "#0b1220",
                    borderRadius: 999,
                    border: "1px solid #334155",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      width:
                        typeof mvActiveJob?.progress === "number"
                          ? `${Math.max(
                              0,
                              Math.min(100, mvActiveJob.progress),
                            )}%`
                          : "0%",
                      background:
                        mvActiveJob?.status === "completed"
                          ? "linear-gradient(90deg, #22c55e, #16a34a)"
                          : "linear-gradient(90deg, #8b5cf6, #6366f1)",
                      transition: "width 300ms ease",
                    }}
                  />
                </div>
                <div
                  style={{ marginTop: 8, color: "#94a3b8", fontSize: "0.8em" }}
                >
                  {mvActiveJob?.current_section
                    ? `Scene: ${mvActiveJob.current_section}`
                    : ""}
                  {mvActiveJob?.stage_detail
                    ? ` • ${mvActiveJob.stage_detail}`
                    : ""}
                  {mvActiveJob?.interpolation_warning
                    ? ` • Interpolation: ${mvActiveJob.interpolation_warning}`
                    : ""}
                </div>

                {mvActiveJob?.current_prompt && (
                  <div
                    style={{
                      marginTop: 10,
                      padding: 10,
                      borderRadius: 10,
                      background: "rgba(148, 163, 184, 0.08)",
                      border: "1px solid rgba(148, 163, 184, 0.2)",
                      color: "#cbd5e1",
                      fontSize: "0.8em",
                      lineHeight: 1.4,
                    }}
                  >
                    <div style={{ color: "#94a3b8", fontSize: "0.75em" }}>
                      Current prompt
                    </div>
                    <div style={{ marginTop: 6 }}>
                      {mvActiveJob.current_prompt}
                    </div>
                  </div>
                )}
              </div>

              {mvActiveJob?.output_url && (
                <div style={{ marginTop: 12 }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 10,
                    }}
                  >
                    <div style={{ color: "#e5e7eb", fontWeight: 700 }}>
                      Preview
                    </div>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      <button
                        onClick={() => {
                          setActiveTab("videos");
                          fetchMedia();
                        }}
                        style={{
                          padding: "8px 10px",
                          borderRadius: 10,
                          border: "1px solid #334155",
                          background: "#0b1220",
                          color: "#cbd5e1",
                          cursor: "pointer",
                        }}
                      >
                        Open in Videos
                      </button>
                      <a
                        href={`${backendUrl}${mvActiveJob.output_url}`}
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          padding: "8px 10px",
                          borderRadius: 10,
                          border: "1px solid #334155",
                          background: "#0b1220",
                          color: "#cbd5e1",
                          textDecoration: "none",
                          display: "inline-block",
                        }}
                      >
                        Open MP4
                      </a>
                    </div>
                  </div>
                  <video
                    controls
                    src={`${backendUrl}${mvActiveJob.output_url}`}
                    style={{
                      width: "100%",
                      marginTop: 10,
                      borderRadius: 12,
                      border: "1px solid #334155",
                    }}
                  />
                </div>
              )}
            </div>

            <div
              style={{
                background: "#0f172a",
                borderRadius: 12,
                padding: 14,
                border: "1px solid #1f2937",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 10,
                  marginBottom: 8,
                }}
              >
                <div style={{ color: "#e5e7eb", fontWeight: 700 }}>Jobs</div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button
                    onClick={clearFailedMusicVideoJobs}
                    style={{
                      padding: "8px 10px",
                      borderRadius: 10,
                      border: "1px solid rgba(239, 68, 68, 0.35)",
                      background: "rgba(239, 68, 68, 0.12)",
                      color: "#fecaca",
                      cursor: "pointer",
                      whiteSpace: "nowrap",
                    }}
                    title="Remove failed/cancelled jobs from the list (does not delete files)"
                  >
                    Clear failed
                  </button>
                </div>
              </div>

              {mvJobsMsg ? (
                <div
                  style={{
                    marginBottom: 10,
                    padding: "8px 10px",
                    borderRadius: 10,
                    border: "1px solid rgba(148, 163, 184, 0.18)",
                    background: "rgba(148, 163, 184, 0.06)",
                    color: "#cbd5e1",
                    fontSize: "0.82em",
                    lineHeight: 1.4,
                  }}
                >
                  {mvJobsMsg}
                </div>
              ) : null}
              {mvJobs.length === 0 ? (
                <div style={{ color: "#94a3b8", fontSize: "0.85em" }}>
                  No music video jobs yet. Upload an MP3 above.
                </div>
              ) : (
                <div
                  style={{ display: "flex", flexDirection: "column", gap: 8 }}
                >
                  {mvJobs.slice(0, 20).map((j) => (
                    <div
                      key={j.id}
                      onClick={() => setMvActiveJobId(j.id)}
                      style={{
                        padding: 10,
                        borderRadius: 10,
                        border:
                          mvActiveJobId === j.id
                            ? "1px solid #8b5cf6"
                            : "1px solid #334155",
                        background:
                          mvActiveJobId === j.id ? "#111827" : "#0b1220",
                        cursor: "pointer",
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 10,
                      }}
                    >
                      <div style={{ minWidth: 0 }}>
                        <div
                          style={{
                            color: "#e5e7eb",
                            fontSize: "0.9em",
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                          }}
                        >
                          {j.title || j.audio_filename || j.id}
                        </div>
                        <div style={{ color: "#94a3b8", fontSize: "0.75em" }}>
                          {j.status || ""} {j.stage ? `• ${j.stage}` : ""}
                        </div>
                      </div>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          flexShrink: 0,
                        }}
                      >
                        {String(j.status || "").toLowerCase() !== "running" &&
                          String(j.status || "").toLowerCase() !== "queued" && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                retryMusicVideoJob(j.id);
                              }}
                              style={{
                                padding: "6px 10px",
                                borderRadius: 10,
                                border: "1px solid rgba(139, 92, 246, 0.4)",
                                background: "rgba(139, 92, 246, 0.14)",
                                color: "#ddd6fe",
                                cursor: "pointer",
                                fontSize: "0.75em",
                              }}
                              title="Retry this job (creates a new job id)"
                            >
                              Retry
                            </button>
                          )}

                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteMusicVideoJob(j.id);
                          }}
                          style={{
                            padding: "6px 10px",
                            borderRadius: 10,
                            border: "1px solid rgba(148, 163, 184, 0.25)",
                            background: "rgba(15, 23, 42, 0.7)",
                            color: "#cbd5e1",
                            cursor: "pointer",
                            fontSize: "0.75em",
                          }}
                          title="Remove this job from the list (does not delete files)"
                        >
                          Delete
                        </button>

                        <div
                          style={{
                            color: "#cbd5e1",
                            fontSize: "0.85em",
                            whiteSpace: "nowrap",
                            minWidth: 44,
                            textAlign: "right",
                          }}
                          title={j.status || ""}
                        >
                          {typeof j.progress === "number"
                            ? `${Math.round(j.progress)}%`
                            : ""}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "deepfacelab" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {/* ═══════════════════════════════════════════════════════════════ */}
            {/* FACESWAP WIZARD - Step by Step Guide */}
            {/* ═══════════════════════════════════════════════════════════════ */}
            <div
              style={{
                background: "linear-gradient(135deg, #1e1b4b 0%, #312e81 100%)",
                borderRadius: 12,
                padding: 16,
                border: "1px solid #4f46e5",
              }}
            >
              <h3 style={{ margin: "0 0 12px 0", color: "#a5b4fc" }}>
                🎭 Faceswap Wizard
              </h3>

              {/* Step Progress Bar */}
              <div style={{ display: "flex", gap: 4, marginBottom: 16 }}>
                {[
                  "Setup",
                  "Source",
                  "Destination",
                  "Train",
                  "Merge",
                  "Export",
                ].map((step, idx) => (
                  <div
                    key={idx}
                    onClick={() => setDflWizardStep(idx)}
                    style={{
                      flex: 1,
                      padding: "8px 4px",
                      background:
                        dflWizardStep === idx
                          ? "linear-gradient(135deg, #8b5cf6, #6366f1)"
                          : dflWizardStep > idx
                            ? "#22c55e"
                            : "#374151",
                      borderRadius: 6,
                      textAlign: "center",
                      fontSize: "0.75em",
                      fontWeight: dflWizardStep === idx ? "bold" : "normal",
                      color: "#fff",
                      cursor: "pointer",
                      transition: "all 0.2s",
                    }}
                  >
                    {idx + 1}. {step}
                  </div>
                ))}
              </div>

              {/* Step 0: Setup */}
              {dflWizardStep === 0 && (
                <div
                  style={{
                    background: "#1f2937",
                    borderRadius: 8,
                    padding: 12,
                  }}
                >
                  <h4 style={{ margin: "0 0 8px 0", color: "#fbbf24" }}>
                    ⚙️ Step 1: Setup
                  </h4>
                  <p
                    style={{
                      color: "#9ca3af",
                      fontSize: "0.85em",
                      margin: "0 0 12px 0",
                    }}
                  >
                    Ensure DeepFaceLab is installed and ready. Click each button
                    in order:
                  </p>
                  <div
                    style={{ display: "flex", flexDirection: "column", gap: 8 }}
                  >
                    <div
                      style={{ display: "flex", alignItems: "center", gap: 8 }}
                    >
                      <span
                        style={{
                          color: deepFaceLabStatus?.installed
                            ? "#22c55e"
                            : "#ef4444",
                          fontSize: "1.2em",
                        }}
                      >
                        {deepFaceLabStatus?.installed ? "✅" : "❌"}
                      </span>
                      <span style={{ flex: 1, color: "#e5e7eb" }}>
                        DeepFaceLab Installed
                      </span>
                      {!deepFaceLabStatus?.installed && (
                        <button
                          onClick={installDeepFaceLab}
                          style={{
                            padding: "6px 12px",
                            background: "#6366f1",
                            color: "#fff",
                            border: "none",
                            borderRadius: 6,
                          }}
                        >
                          Install
                        </button>
                      )}
                    </div>
                    <div
                      style={{ display: "flex", alignItems: "center", gap: 8 }}
                    >
                      <span
                        style={{
                          color: deepFaceLabStatus?.workspace
                            ? "#22c55e"
                            : "#ef4444",
                          fontSize: "1.2em",
                        }}
                      >
                        {deepFaceLabStatus?.workspace ? "✅" : "❌"}
                      </span>
                      <span style={{ flex: 1, color: "#e5e7eb" }}>
                        Workspace Created
                      </span>
                    </div>
                    <div
                      style={{ display: "flex", alignItems: "center", gap: 8 }}
                    >
                      <span
                        style={{
                          color: deepFaceLabStatus?.gpu?.available
                            ? "#22c55e"
                            : "#f59e0b",
                          fontSize: "1.2em",
                        }}
                      >
                        {deepFaceLabStatus?.gpu?.available ? "✅" : "⚠️"}
                      </span>
                      <span style={{ flex: 1, color: "#e5e7eb" }}>
                        GPU:{" "}
                        {deepFaceLabStatus?.gpu?.available
                          ? deepFaceLabStatus?.gpu?.name
                          : "CPU Mode (slower)"}
                      </span>
                    </div>
                    <div
                      style={{ display: "flex", alignItems: "center", gap: 8 }}
                    >
                      <span
                        style={{
                          color: deepFaceLabStatus?.ffmpeg?.present
                            ? "#22c55e"
                            : "#ef4444",
                          fontSize: "1.2em",
                        }}
                      >
                        {deepFaceLabStatus?.ffmpeg?.present ? "✅" : "❌"}
                      </span>
                      <span style={{ flex: 1, color: "#e5e7eb" }}>
                        FFmpeg Installed
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() =>
                      deepFaceLabStatus?.installed && setDflWizardStep(1)
                    }
                    disabled={!deepFaceLabStatus?.installed}
                    style={{
                      marginTop: 12,
                      padding: "10px 20px",
                      background: deepFaceLabStatus?.installed
                        ? "#22c55e"
                        : "#4b5563",
                      color: "#fff",
                      border: "none",
                      borderRadius: 8,
                      cursor: deepFaceLabStatus?.installed
                        ? "pointer"
                        : "not-allowed",
                      fontWeight: "bold",
                    }}
                  >
                    Next: Prepare Source →
                  </button>
                </div>
              )}

              {/* Step 1: Source Video */}
              {dflWizardStep === 1 && (
                <div
                  style={{
                    background: "#1f2937",
                    borderRadius: 8,
                    padding: 12,
                  }}
                >
                  <h4 style={{ margin: "0 0 8px 0", color: "#fbbf24" }}>
                    👤 Step 2: Source Face
                  </h4>
                  <p
                    style={{
                      color: "#9ca3af",
                      fontSize: "0.85em",
                      margin: "0 0 12px 0",
                    }}
                  >
                    The SOURCE is the person whose face you want to COPY. Upload
                    a video or images of this person.
                  </p>
                  <div
                    style={{ display: "flex", flexDirection: "column", gap: 8 }}
                  >
                    <label style={{ color: "#e5e7eb" }}>
                      Source Video/Images Path:
                    </label>
                    <div style={{ display: "flex", gap: 8 }}>
                      <input
                        type="text"
                        value={dflSourceVideo}
                        onChange={(e) => setDflSourceVideo(e.target.value)}
                        placeholder="C:\path\to\source_video.mp4 or folder"
                        style={{
                          flex: 1,
                          padding: 8,
                          borderRadius: 6,
                          border: "1px solid #4b5563",
                          background: "#111827",
                          color: "#fff",
                        }}
                      />
                      <button
                        onClick={async () => {
                          const path = window.prompt(
                            "Enter path to source video or images folder:",
                          );
                          if (path) setDflSourceVideo(path);
                        }}
                        style={{
                          padding: "8px 12px",
                          background: "#4f46e5",
                          color: "#fff",
                          border: "none",
                          borderRadius: 6,
                        }}
                      >
                        Browse
                      </button>
                    </div>
                    <button
                      onClick={async () => {
                        if (!dflSourceVideo)
                          return alert("Enter source path first");
                        try {
                          setIsLoading(true);
                          // Extract frames from video
                          const res = await axios.post(
                            `${backendUrl}/media/deepfacelab/run`,
                            {
                              action: "extract_frames",
                              args: [
                                "--input",
                                dflSourceVideo,
                                "--output",
                                "workspace/data_src",
                              ],
                            },
                          );
                          alert("Frames extraction started. Check Jobs below.");
                          await fetchDeepFaceLabJobs();
                        } catch (e) {
                          alert("Failed: " + e.message);
                        } finally {
                          setIsLoading(false);
                        }
                      }}
                      disabled={!dflSourceVideo}
                      style={{
                        padding: "10px",
                        background: "#8b5cf6",
                        color: "#fff",
                        border: "none",
                        borderRadius: 6,
                      }}
                    >
                      📹 Extract Frames from Source
                    </button>
                    <button
                      onClick={async () => {
                        try {
                          setIsLoading(true);
                          const res = await axios.post(
                            `${backendUrl}/media/deepfacelab/run`,
                            {
                              action: "extract",
                              args: [
                                "--input-dir",
                                "workspace/data_src",
                                "--output-dir",
                                "workspace/data_src/aligned",
                                "--detector",
                                "s3fd",
                              ],
                            },
                          );
                          alert("Face extraction started. Check Jobs below.");
                          await fetchDeepFaceLabJobs();
                        } catch (e) {
                          alert("Failed: " + e.message);
                        } finally {
                          setIsLoading(false);
                        }
                      }}
                      style={{
                        padding: "10px",
                        background: "#6366f1",
                        color: "#fff",
                        border: "none",
                        borderRadius: 6,
                      }}
                    >
                      🔍 Extract Faces from Source Frames
                    </button>
                  </div>
                  <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                    <button
                      onClick={() => setDflWizardStep(0)}
                      style={{
                        padding: "10px 20px",
                        background: "#4b5563",
                        color: "#fff",
                        border: "none",
                        borderRadius: 8,
                      }}
                    >
                      ← Back
                    </button>
                    <button
                      onClick={() => setDflWizardStep(2)}
                      style={{
                        padding: "10px 20px",
                        background: "#22c55e",
                        color: "#fff",
                        border: "none",
                        borderRadius: 8,
                        fontWeight: "bold",
                      }}
                    >
                      Next: Destination →
                    </button>
                  </div>
                </div>
              )}

              {/* Step 2: Destination Video */}
              {dflWizardStep === 2 && (
                <div
                  style={{
                    background: "#1f2937",
                    borderRadius: 8,
                    padding: 12,
                  }}
                >
                  <h4 style={{ margin: "0 0 8px 0", color: "#fbbf24" }}>
                    🎬 Step 3: Destination Video
                  </h4>
                  <p
                    style={{
                      color: "#9ca3af",
                      fontSize: "0.85em",
                      margin: "0 0 12px 0",
                    }}
                  >
                    The DESTINATION is the video where you want to PUT the
                    source face. This is the final output video.
                  </p>
                  <div
                    style={{ display: "flex", flexDirection: "column", gap: 8 }}
                  >
                    <label style={{ color: "#e5e7eb" }}>
                      Destination Video Path:
                    </label>
                    <div style={{ display: "flex", gap: 8 }}>
                      <input
                        type="text"
                        value={dflDestVideo}
                        onChange={(e) => setDflDestVideo(e.target.value)}
                        placeholder="C:\path\to\destination_video.mp4"
                        style={{
                          flex: 1,
                          padding: 8,
                          borderRadius: 6,
                          border: "1px solid #4b5563",
                          background: "#111827",
                          color: "#fff",
                        }}
                      />
                      <button
                        onClick={async () => {
                          const path = window.prompt(
                            "Enter path to destination video:",
                          );
                          if (path) setDflDestVideo(path);
                        }}
                        style={{
                          padding: "8px 12px",
                          background: "#4f46e5",
                          color: "#fff",
                          border: "none",
                          borderRadius: 6,
                        }}
                      >
                        Browse
                      </button>
                    </div>
                    <button
                      onClick={async () => {
                        if (!dflDestVideo)
                          return alert("Enter destination path first");
                        try {
                          setIsLoading(true);
                          const res = await axios.post(
                            `${backendUrl}/media/deepfacelab/run`,
                            {
                              action: "extract_frames",
                              args: [
                                "--input",
                                dflDestVideo,
                                "--output",
                                "workspace/data_dst",
                              ],
                            },
                          );
                          alert("Frames extraction started. Check Jobs below.");
                          await fetchDeepFaceLabJobs();
                        } catch (e) {
                          alert("Failed: " + e.message);
                        } finally {
                          setIsLoading(false);
                        }
                      }}
                      disabled={!dflDestVideo}
                      style={{
                        padding: "10px",
                        background: "#8b5cf6",
                        color: "#fff",
                        border: "none",
                        borderRadius: 6,
                      }}
                    >
                      📹 Extract Frames from Destination
                    </button>
                    <button
                      onClick={async () => {
                        try {
                          setIsLoading(true);
                          const res = await axios.post(
                            `${backendUrl}/media/deepfacelab/run`,
                            {
                              action: "extract",
                              args: [
                                "--input-dir",
                                "workspace/data_dst",
                                "--output-dir",
                                "workspace/data_dst/aligned",
                                "--detector",
                                "s3fd",
                              ],
                            },
                          );
                          alert("Face extraction started. Check Jobs below.");
                          await fetchDeepFaceLabJobs();
                        } catch (e) {
                          alert("Failed: " + e.message);
                        } finally {
                          setIsLoading(false);
                        }
                      }}
                      style={{
                        padding: "10px",
                        background: "#6366f1",
                        color: "#fff",
                        border: "none",
                        borderRadius: 6,
                      }}
                    >
                      🔍 Extract Faces from Destination Frames
                    </button>
                  </div>
                  <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                    <button
                      onClick={() => setDflWizardStep(1)}
                      style={{
                        padding: "10px 20px",
                        background: "#4b5563",
                        color: "#fff",
                        border: "none",
                        borderRadius: 8,
                      }}
                    >
                      ← Back
                    </button>
                    <button
                      onClick={() => setDflWizardStep(3)}
                      style={{
                        padding: "10px 20px",
                        background: "#22c55e",
                        color: "#fff",
                        border: "none",
                        borderRadius: 8,
                        fontWeight: "bold",
                      }}
                    >
                      Next: Train Model →
                    </button>
                  </div>
                </div>
              )}

              {/* Step 3: Train */}
              {dflWizardStep === 3 && (
                <div
                  style={{
                    background: "#1f2937",
                    borderRadius: 8,
                    padding: 12,
                  }}
                >
                  <h4 style={{ margin: "0 0 8px 0", color: "#fbbf24" }}>
                    🧠 Step 4: Train Model
                  </h4>
                  <p
                    style={{
                      color: "#9ca3af",
                      fontSize: "0.85em",
                      margin: "0 0 12px 0",
                    }}
                  >
                    Training teaches the AI to swap faces. This takes{" "}
                    <strong>several hours to days</strong> depending on your
                    hardware.
                    {!deepFaceLabStatus?.gpu?.available && (
                      <span style={{ color: "#f59e0b" }}>
                        {" "}
                        ⚠️ CPU mode will be VERY slow!
                      </span>
                    )}
                  </p>
                  <div
                    style={{ display: "flex", flexDirection: "column", gap: 8 }}
                  >
                    <label style={{ color: "#e5e7eb" }}>Model Type:</label>
                    <select
                      value={dflModelName}
                      onChange={(e) => setDflModelName(e.target.value)}
                      style={{
                        padding: 8,
                        borderRadius: 6,
                        border: "1px solid #4b5563",
                        background: "#111827",
                        color: "#fff",
                      }}
                    >
                      <option value="SAEHD">
                        SAEHD (Best quality, slower)
                      </option>
                      <option value="Quick96">
                        Quick96 (Fast, lower quality)
                      </option>
                      <option value="AMP">AMP (Balanced)</option>
                    </select>
                    <div
                      style={{
                        background: "#374151",
                        padding: 10,
                        borderRadius: 6,
                        fontSize: "0.85em",
                        color: "#d1d5db",
                      }}
                    >
                      <strong>💡 Tip:</strong> Start with Quick96 for testing,
                      then use SAEHD for final quality.
                      <br />
                      Training saves automatically - you can stop and resume
                      anytime.
                    </div>
                    <button
                      onClick={async () => {
                        if (
                          !window.confirm(
                            `Start training with ${dflModelName}? This will take a long time. You can stop it anytime.`,
                          )
                        )
                          return;
                        try {
                          setIsLoading(true);
                          const res = await axios.post(
                            `${backendUrl}/media/deepfacelab/run`,
                            {
                              action: "train",
                              args: [
                                "--model",
                                dflModelName,
                                "--model-dir",
                                "workspace/model",
                                "--src-dir",
                                "workspace/data_src/aligned",
                                "--dst-dir",
                                "workspace/data_dst/aligned",
                              ],
                            },
                          );
                          alert(
                            "Training started! Check Jobs below. Training runs in background.",
                          );
                          await fetchDeepFaceLabJobs();
                        } catch (e) {
                          alert("Failed: " + e.message);
                        } finally {
                          setIsLoading(false);
                        }
                      }}
                      style={{
                        padding: "12px",
                        background: "linear-gradient(135deg, #f59e0b, #d97706)",
                        color: "#fff",
                        border: "none",
                        borderRadius: 6,
                        fontWeight: "bold",
                        fontSize: "1em",
                      }}
                    >
                      🚀 Start Training
                    </button>
                  </div>
                  <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                    <button
                      onClick={() => setDflWizardStep(2)}
                      style={{
                        padding: "10px 20px",
                        background: "#4b5563",
                        color: "#fff",
                        border: "none",
                        borderRadius: 8,
                      }}
                    >
                      ← Back
                    </button>
                    <button
                      onClick={() => setDflWizardStep(4)}
                      style={{
                        padding: "10px 20px",
                        background: "#22c55e",
                        color: "#fff",
                        border: "none",
                        borderRadius: 8,
                        fontWeight: "bold",
                      }}
                    >
                      Next: Merge →
                    </button>
                  </div>
                </div>
              )}

              {/* Step 4: Merge */}
              {dflWizardStep === 4 && (
                <div
                  style={{
                    background: "#1f2937",
                    borderRadius: 8,
                    padding: 12,
                  }}
                >
                  <h4 style={{ margin: "0 0 8px 0", color: "#fbbf24" }}>
                    🔀 Step 5: Merge Faces
                  </h4>
                  <p
                    style={{
                      color: "#9ca3af",
                      fontSize: "0.85em",
                      margin: "0 0 12px 0",
                    }}
                  >
                    After training, merge applies the learned face swap to each
                    frame of your destination video.
                  </p>
                  <div
                    style={{ display: "flex", flexDirection: "column", gap: 8 }}
                  >
                    <button
                      onClick={async () => {
                        try {
                          setIsLoading(true);
                          const res = await axios.post(
                            `${backendUrl}/media/deepfacelab/run`,
                            {
                              action: "merge",
                              args: [
                                "--model",
                                dflModelName,
                                "--model-dir",
                                "workspace/model",
                                "--input-dir",
                                "workspace/data_dst/aligned",
                                "--output-dir",
                                "workspace/merged",
                                "--output-mask-dir",
                                "workspace/merged_mask",
                              ],
                            },
                          );
                          alert("Merge started! Check Jobs below.");
                          await fetchDeepFaceLabJobs();
                        } catch (e) {
                          alert("Failed: " + e.message);
                        } finally {
                          setIsLoading(false);
                        }
                      }}
                      style={{
                        padding: "12px",
                        background: "linear-gradient(135deg, #8b5cf6, #6366f1)",
                        color: "#fff",
                        border: "none",
                        borderRadius: 6,
                        fontWeight: "bold",
                      }}
                    >
                      🔀 Start Merging
                    </button>
                  </div>
                  <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                    <button
                      onClick={() => setDflWizardStep(3)}
                      style={{
                        padding: "10px 20px",
                        background: "#4b5563",
                        color: "#fff",
                        border: "none",
                        borderRadius: 8,
                      }}
                    >
                      ← Back
                    </button>
                    <button
                      onClick={() => setDflWizardStep(5)}
                      style={{
                        padding: "10px 20px",
                        background: "#22c55e",
                        color: "#fff",
                        border: "none",
                        borderRadius: 8,
                        fontWeight: "bold",
                      }}
                    >
                      Next: Export →
                    </button>
                  </div>
                </div>
              )}

              {/* Step 5: Export */}
              {dflWizardStep === 5 && (
                <div
                  style={{
                    background: "#1f2937",
                    borderRadius: 8,
                    padding: 12,
                  }}
                >
                  <h4 style={{ margin: "0 0 8px 0", color: "#fbbf24" }}>
                    📤 Step 6: Export Final Video
                  </h4>
                  <p
                    style={{
                      color: "#9ca3af",
                      fontSize: "0.85em",
                      margin: "0 0 12px 0",
                    }}
                  >
                    Convert the merged frames back into a video file with audio
                    from the original.
                  </p>
                  <div
                    style={{ display: "flex", flexDirection: "column", gap: 8 }}
                  >
                    <button
                      onClick={async () => {
                        try {
                          setIsLoading(true);
                          const res = await axios.post(
                            `${backendUrl}/media/deepfacelab/run`,
                            {
                              action: "frames_to_video",
                              args: [
                                "--input-dir",
                                "workspace/merged",
                                "--output",
                                "workspace/result.mp4",
                                "--audio",
                                dflDestVideo || "workspace/data_dst.mp4",
                              ],
                            },
                          );
                          alert("Video export started! Check Jobs below.");
                          await fetchDeepFaceLabJobs();
                        } catch (e) {
                          alert("Failed: " + e.message);
                        } finally {
                          setIsLoading(false);
                        }
                      }}
                      style={{
                        padding: "12px",
                        background: "linear-gradient(135deg, #22c55e, #16a34a)",
                        color: "#fff",
                        border: "none",
                        borderRadius: 6,
                        fontWeight: "bold",
                      }}
                    >
                      🎬 Export Final Video
                    </button>
                    <div
                      style={{
                        background: "#374151",
                        padding: 10,
                        borderRadius: 6,
                        fontSize: "0.85em",
                        color: "#d1d5db",
                      }}
                    >
                      <strong>📁 Output:</strong> workspace/result.mp4
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                    <button
                      onClick={() => setDflWizardStep(4)}
                      style={{
                        padding: "10px 20px",
                        background: "#4b5563",
                        color: "#fff",
                        border: "none",
                        borderRadius: 8,
                      }}
                    >
                      ← Back
                    </button>
                    <button
                      onClick={() => setDflWizardStep(0)}
                      style={{
                        padding: "10px 20px",
                        background: "#6366f1",
                        color: "#fff",
                        border: "none",
                        borderRadius: 8,
                      }}
                    >
                      🔄 Start New Project
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Original Controls Section */}
            <details
              style={{ background: "#1f2937", borderRadius: 8, padding: 12 }}
            >
              <summary
                style={{
                  cursor: "pointer",
                  color: "#a5b4fc",
                  fontWeight: "bold",
                }}
              >
                🛠️ Advanced Controls (Manual Mode)
              </summary>
              <div style={{ marginTop: 12 }}>
                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    alignItems: "center",
                    flexWrap: "wrap",
                  }}
                >
                  <button
                    onClick={async () => {
                      await fetchDeepFaceLabStatus();
                    }}
                    style={{ padding: "6px 10px" }}
                  >
                    Refresh Status
                  </button>
                  <button
                    onClick={installDeepFaceLab}
                    style={{ padding: "6px 10px" }}
                  >
                    Install DeepFaceLab
                  </button>
                  <button
                    onClick={async () => {
                      if (
                        !window.confirm(
                          "Run DeepFaceLab self-fix? This may install dependencies. Proceed?",
                        )
                      )
                        return;
                      setIsLoading(true);
                      try {
                        const res = await axios.post(
                          `${backendUrl}/media/deepfacelab/fix`,
                        );
                        alert(
                          "Fix result: " + JSON.stringify(res.data, null, 2),
                        );
                        await fetchDeepFaceLabStatus();
                        await fetchDeepFaceLabJobs();
                      } catch (e) {
                        alert("Fix failed: " + e.message);
                      } finally {
                        setIsLoading(false);
                      }
                    }}
                    style={{ padding: "6px 10px" }}
                  >
                    Fix DeepFaceLab
                  </button>
                  <button
                    onClick={async () => {
                      setIsLoading(true);
                      try {
                        const r = await axios.post(
                          `${backendUrl}/media/deepfacelab/ensure_requirements`,
                        );
                        alert(
                          "Requirements install: " +
                            JSON.stringify(r.data, null, 2),
                        );
                        await fetchDeepFaceLabStatus();
                      } catch (e) {
                        alert("Requirements install failed: " + e.message);
                      } finally {
                        setIsLoading(false);
                      }
                    }}
                    style={{ padding: "6px 10px" }}
                  >
                    Ensure Requirements
                  </button>
                  <button
                    onClick={async () => {
                      setIsLoading(true);
                      try {
                        const r = await axios.post(
                          `${backendUrl}/media/deepfacelab/ensure_torch`,
                        );
                        alert(
                          "Torch install attempt: " +
                            JSON.stringify(r.data, null, 2),
                        );
                        await fetchDeepFaceLabStatus();
                      } catch (e) {
                        alert("Torch install attempt failed: " + e.message);
                      } finally {
                        setIsLoading(false);
                      }
                    }}
                    style={{ padding: "6px 10px" }}
                  >
                    Ensure Torch
                  </button>
                  <input
                    id="dfl-upload"
                    type="file"
                    accept=".zip,.tar,.gz,.tar.gz"
                    style={{ display: "inline-block", marginLeft: 8 }}
                    onChange={(e) => {
                      const f = e.target.files && e.target.files[0];
                      if (f) {
                        const formData = new FormData();
                        formData.append("file", f);
                        const overwrite = window.confirm(
                          "Overwrite existing DeepFaceLab folder if exists?",
                        );
                        formData.append("overwrite", overwrite);
                        setIsLoading(true);
                        axios
                          .post(
                            `${backendUrl}/media/deepfacelab/upload`,
                            formData,
                            {
                              headers: {
                                "Content-Type": "multipart/form-data",
                              },
                            },
                          )
                          .then(async (res) => {
                            if (res.data && res.data.job_id) {
                              alert("Upload started: " + res.data.job_id);
                              await fetchDeepFaceLabJobs();
                            } else {
                              alert(JSON.stringify(res.data));
                            }
                            setIsLoading(false);
                          })
                          .catch((err) => {
                            alert("Upload failed: " + err.message);
                            setIsLoading(false);
                          });
                      }
                    }}
                  />
                  <button
                    onClick={async () => {
                      const info = await axios
                        .get(`${backendUrl}/media/deepfacelab/checkreq`)
                        .then((r) => r.data)
                        .catch((err) => ({ error: err.message }));
                      alert(JSON.stringify(info, null, 2));
                    }}
                    style={{ padding: "6px 10px" }}
                  >
                    Check Env
                  </button>
                  <button
                    onClick={async () => {
                      const path = window.prompt(
                        "Enter local DeepFaceLab path (absolute or relative)",
                      );
                      if (!path) return;
                      const copy = confirm(
                        "Copy files into external/DeepFaceLab? Cancel to register in-place",
                      );
                      try {
                        setIsLoading(true);
                        const res = await axios.post(
                          `${backendUrl}/media/deepfacelab/register`,
                          { path, copy },
                        );
                        alert(JSON.stringify(res.data));
                        await fetchDeepFaceLabStatus();
                        await fetchDeepFaceLabJobs();
                      } catch (err) {
                        alert("Register failed: " + err.message);
                      } finally {
                        setIsLoading(false);
                      }
                    }}
                    style={{ padding: "6px 10px" }}
                  >
                    Register Local Path
                  </button>
                  <button
                    onClick={async () => {
                      if (
                        !window.confirm(
                          "Attempt to auto-diagnose and fix DeepFaceLab issues? This may install packages and run background jobs. Proceed?",
                        )
                      )
                        return;
                      try {
                        setIsLoading(true);
                        const res = await axios.post(
                          `${backendUrl}/media/deepfacelab/fix`,
                        );
                        alert(JSON.stringify(res.data));
                        await fetchDeepFaceLabStatus();
                      } catch (err) {
                        alert("Fix failed: " + err.message);
                      } finally {
                        setIsLoading(false);
                      }
                    }}
                    style={{
                      padding: "6px 10px",
                      background: "#f97316",
                      color: "white",
                    }}
                  >
                    Fix DeepFaceLab
                  </button>
                  <button
                    disabled={!deepFaceLabStatus?.installed}
                    onClick={async () => {
                      if (!deepFaceLabStatus?.installed)
                        return alert("DeepFaceLab not installed");
                      const inputDir = window.prompt(
                        "Input directory (relative to workspace/ or absolute)",
                      );
                      if (!inputDir) return;
                      const outputDir = window.prompt(
                        "Output directory for extracted faces (workspace/data_src)",
                      );
                      if (!outputDir) return;
                      const args = [
                        "--input-dir",
                        inputDir,
                        "--output-dir",
                        outputDir,
                        "--detector",
                        "s3fd",
                      ];
                      await runDeepFaceLabCommand("extract", args);
                    }}
                    style={{ padding: "6px 10px" }}
                  >
                    Quick Extract
                  </button>
                  <button
                    disabled={!deepFaceLabStatus?.installed}
                    onClick={async () => {
                      const src = window.prompt(
                        "SRC training data directory (workspace/data_src)",
                      );
                      if (!src) return;
                      const dst = window.prompt(
                        "DST training data directory (workspace/data_dst)",
                      );
                      if (!dst) return;
                      const modelDir = window.prompt(
                        "Model directory (workspace/models)",
                      );
                      if (!modelDir) return;
                      const model = window.prompt(
                        "Model name (choose Model_*)",
                      );
                      if (!model) return;
                      const iterations =
                        parseInt(window.prompt("Iterations to run", "100")) ||
                        100;
                      try {
                        setIsLoading(true);
                        const res = await axios.post(
                          `${backendUrl}/media/deepfacelab/train_bootstrap`,
                          { iterations },
                        );
                        if (res.data?.job_id)
                          alert("Started train job: " + res.data.job_id);
                        await fetchDeepFaceLabJobs();
                      } catch (e) {
                        alert("Train failed: " + e.message);
                      } finally {
                        setIsLoading(false);
                      }
                    }}
                    style={{ padding: "6px 10px" }}
                  >
                    Quick Train
                  </button>
                  <button
                    onClick={async () => {
                      const input = window.prompt(
                        "Aligned input dir (aligned/ or workspace/aligned)",
                      );
                      if (!input) return;
                      const modelDir = window.prompt(
                        "Model directory (workspace/models)",
                      );
                      if (!modelDir) return;
                      const model = window.prompt("Model name (Model_*)");
                      if (!model) return;
                      const output = window.prompt(
                        "Output dir for merged video (workspace/output)",
                      );
                      if (!output) return;
                      const mask = window.prompt(
                        "Output mask dir (workspace/output_masks)",
                      );
                      if (!mask) return;
                      const args = [
                        "--input-dir",
                        input,
                        "--model-dir",
                        modelDir,
                        "--model",
                        model,
                        "--output-dir",
                        output,
                        "--output_mask-dir",
                        mask,
                      ];
                      await runDeepFaceLabCommand("merge", args);
                    }}
                    style={{ padding: "6px 10px" }}
                    disabled={!deepFaceLabStatus?.installed}
                  >
                    Quick Merge
                  </button>
                </div>
                <div>
                  <strong>Status:</strong>{" "}
                  {deepFaceLabStatusToString(deepFaceLabStatus)}
                  <div>
                    <strong>Path:</strong> {deepFaceLabStatus?.path || "-"}
                  </div>
                  <div>
                    <strong>Models:</strong>{" "}
                    {deepFaceLabStatus?.models?.length || 0}
                  </div>
                  <div>
                    <strong>GPU:</strong>{" "}
                    {deepFaceLabStatus?.gpu?.available
                      ? `${deepFaceLabStatus?.gpu?.name} (${Math.round(
                          (deepFaceLabStatus?.gpu?.vram || 0) / (1024 * 1024),
                        )} MB)`
                      : "Not Available"}
                  </div>
                  <div>
                    <strong>ffmpeg:</strong>{" "}
                    {deepFaceLabStatus?.ffmpeg?.present
                      ? "Installed"
                      : "Missing"}
                  </div>
                  <div>
                    <strong>dlib/insightface:</strong>{" "}
                    {(deepFaceLabStatus?.dlib?.dlib ? "dlib" : "") +
                      " " +
                      (deepFaceLabStatus?.dlib?.insightface
                        ? "insightface"
                        : "")}
                  </div>
                </div>
                <div>
                  <h4>Run Command</h4>
                  <input
                    placeholder="e.g. workspace/extract.py or train.py"
                    value={deepCmd}
                    onChange={(e) => setDeepCmd(e.target.value)}
                    style={{ width: "100%" }}
                  />
                  <div style={{ marginTop: 8 }}>
                    <button
                      onClick={() => {
                        if (!deepCmd.trim()) return alert("Enter a command");
                        runDeepFaceLabCommand(deepCmd.trim(), []);
                      }}
                      disabled={
                        !deepFaceLabStatus?.installed ||
                        !deepFaceLabStatus?.workspace
                      }
                      style={{ padding: "6px 10px" }}
                    >
                      Run
                    </button>
                  </div>
                </div>
                <div>
                  <h4>Output</h4>
                  <pre
                    style={{
                      background: "#0b0b0b",
                      color: "#fff",
                      padding: 8,
                      maxHeight: 200,
                      overflow: "auto",
                    }}
                  >
                    {deepCmdOutput
                      ? JSON.stringify(deepCmdOutput, null, 2)
                      : "No output yet"}
                  </pre>
                </div>
                <div>
                  <h4>Logs</h4>
                  <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                    <button
                      onClick={fetchDeepFaceLabLogs}
                      style={{ padding: "6px 10px" }}
                    >
                      Fetch Logs
                    </button>
                    <button
                      onClick={fetchDeepFaceLabJobs}
                      style={{ padding: "6px 10px" }}
                    >
                      Refresh Jobs
                    </button>
                  </div>
                  <div
                    style={{
                      maxHeight: 200,
                      overflow: "auto",
                      background: "#111",
                      color: "#fff",
                      padding: 8,
                    }}
                  >
                    <h5 style={{ marginTop: 0 }}>Jobs</h5>
                    {deepJobs.length === 0 ? (
                      <div>No jobs</div>
                    ) : (
                      deepJobs.map((j, i) => (
                        <div
                          key={i}
                          style={{ padding: 6, borderBottom: "1px solid #222" }}
                        >
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                            }}
                          >
                            <div>
                              <div>
                                <strong>{j.id}</strong> ({j.status})
                              </div>
                              <div style={{ fontSize: 12, color: "#aaa" }}>
                                {j.cmd ? j.cmd.join(" ") : ""}
                              </div>
                            </div>
                            <div style={{ display: "flex", gap: 6 }}>
                              <button
                                style={{ padding: "4px 8px" }}
                                onClick={async () => {
                                  const d = await fetchDeepFaceLabJob(j.id);
                                  if (d) alert(JSON.stringify(d.job, null, 2));
                                }}
                              >
                                View
                              </button>
                              <button
                                style={{ padding: "4px 8px" }}
                                onClick={async () => {
                                  if (confirm("Cancel job?")) {
                                    await cancelDeepFaceLabJob(j.id);
                                  }
                                }}
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                    {deepLogs.length === 0 ? (
                      <div>No logs</div>
                    ) : (
                      deepLogs.map((l, i) => (
                        <div key={i} style={{ marginBottom: 6 }}>
                          <pre style={{ whiteSpace: "pre-wrap" }}>
                            {JSON.stringify(l, null, 2)}
                          </pre>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </details>
          </div>
        )}

        {/* Recordings Tab */}
        {activeTab === "recordings" && (
          <div>
            {selectedMedia ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                }}
              >
                <button
                  onClick={() => setSelectedMedia(null)}
                  style={{
                    padding: "8px",
                    background: "transparent",
                    border: "1px solid #444",
                    borderRadius: "6px",
                    color: "#a78bfa",
                    cursor: "pointer",
                    fontSize: "0.85em",
                    alignSelf: "flex-start",
                  }}
                >
                  ← Back to list
                </button>
                <video
                  src={`${backendUrl}${selectedMedia.url}`}
                  controls
                  autoPlay
                  style={{
                    width: "100%",
                    borderRadius: "10px",
                    maxHeight: "300px",
                    backgroundColor: "#000",
                  }}
                />
                <div style={{ color: "#888", fontSize: "0.85em" }}>
                  {selectedMedia.name || selectedMedia.filename}
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    onClick={() =>
                      downloadFile(
                        `/media/download/recordings/${
                          selectedMedia.name || selectedMedia.filename
                        }`,
                        selectedMedia.name || selectedMedia.filename,
                      )
                    }
                    style={{
                      flex: 1,
                      padding: "12px",
                      borderRadius: "8px",
                      border: "none",
                      background: "linear-gradient(135deg, #ec4899, #db2777)",
                      color: "white",
                      cursor: "pointer",
                      fontWeight: "bold",
                    }}
                  >
                    ⬇️ Download
                  </button>
                  <button
                    onClick={() =>
                      deleteMedia(
                        "recordings",
                        selectedMedia.name || selectedMedia.filename,
                      )
                    }
                    style={{
                      padding: "12px 16px",
                      borderRadius: "8px",
                      border: "none",
                      background: "linear-gradient(135deg, #ef4444, #dc2626)",
                      color: "white",
                      cursor: "pointer",
                      fontWeight: "bold",
                    }}
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ) : (
              <div
                style={{ display: "flex", flexDirection: "column", gap: "8px" }}
              >
                {!mediaFiles.recordings ||
                mediaFiles.recordings.length === 0 ? (
                  <div
                    style={{
                      textAlign: "center",
                      color: "#666",
                      padding: "40px",
                    }}
                  >
                    <div style={{ fontSize: "2em", marginBottom: "10px" }}>
                      📹
                    </div>
                    No screen recordings yet.
                    <br />
                    Use the Recording Studio (📹) to capture your Amigos
                    sessions!
                  </div>
                ) : (
                  mediaFiles.recordings.map((rec, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "12px",
                        padding: "10px",
                        backgroundColor: "#1a1a2e",
                        borderRadius: "8px",
                        cursor: "pointer",
                        border: "1px solid #333",
                      }}
                    >
                      <span
                        style={{ fontSize: "1.5em" }}
                        onClick={() => setSelectedMedia(rec)}
                      >
                        📹
                      </span>
                      <div
                        style={{ flex: 1 }}
                        onClick={() => setSelectedMedia(rec)}
                      >
                        <div style={{ color: "#fff", fontSize: "0.9em" }}>
                          {rec.name || rec.filename}
                        </div>
                        <div style={{ color: "#666", fontSize: "0.75em" }}>
                          {rec.size_mb
                            ? `${rec.size_mb} MB`
                            : rec.size_bytes
                              ? `${(rec.size_bytes / 1024 / 1024).toFixed(2)} MB`
                              : ""}
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteMedia("recordings", rec.name || rec.filename);
                        }}
                        style={{
                          padding: "6px 10px",
                          borderRadius: "6px",
                          border: "none",
                          background: "#ef4444",
                          color: "white",
                          fontSize: "0.75em",
                          cursor: "pointer",
                        }}
                        title="Delete"
                      >
                        🗑️
                      </button>
                      <span
                        style={{ color: "#ec4899" }}
                        onClick={() => setSelectedMedia(rec)}
                      >
                        ▶
                      </span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Refresh Button */}
      <div
        style={{
          padding: "8px 12px",
          borderTop: "1px solid #333",
          textAlign: "center",
        }}
      >
        <button
          onClick={fetchMedia}
          disabled={isLoading}
          style={{
            padding: "8px 16px",
            borderRadius: "6px",
            border: "1px solid #444",
            background: "transparent",
            color: "#888",
            cursor: isLoading ? "not-allowed" : "pointer",
            fontSize: "0.8em",
          }}
        >
          {isLoading ? "🔄 Loading..." : "🔄 Refresh Media"}
        </button>
      </div>

      {/* Resize Handle */}
      <div
        className="resize-handle"
        onMouseDown={handleResizeStart}
        style={{
          position: "absolute",
          bottom: "0",
          right: "0",
          width: "20px",
          height: "20px",
          cursor: "se-resize",
          background:
            "linear-gradient(135deg, transparent 50%, rgba(139, 92, 246, 0.5) 50%)",
          borderBottomRightRadius: "18px",
        }}
      />
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════
// AI AVATAR - Photo-Realistic Human AI Face with Speech Animation
// Shows when AI is speaking with realistic visual effects
// Background removed/styled to match Amigos app theme
// ═══════════════════════════════════════════════════════════════

// AI Avatar photo - served from /public
const AI_AVATAR_IMAGE = "/ai_avatar.jpg";

// AI Avatar VIDEO - animated talking avatar (muted, no sound from video)
const AI_AVATAR_VIDEO = "/ai_avatar.mp4";

// ═══════════════════════════════════════════════════════════════
// VIDEO-BASED TALKING AVATAR
// Plays the pre-animated video when speaking (muted - uses TTS audio)
// ═══════════════════════════════════════════════════════════════

const TalkingAvatarCanvas = ({
  isSpeaking,
  audioLevel,
  width = 172,
  height = 172,
  borderRadius = "50%",
}) => {
  const videoRef = useRef(null);
  const [needsUserGesture, setNeedsUserGesture] = useState(false);
  const [videoError, setVideoError] = useState(false);

  const attemptPlay = useCallback(async () => {
    const video = videoRef.current;
    if (!video || videoError) return;
    try {
      // Ensure these are set before play() for best cross-browser behavior
      video.muted = true;
      video.playsInline = true;
      const playPromise = video.play();
      if (playPromise && typeof playPromise.then === "function") {
        await playPromise;
      }
      setNeedsUserGesture(false);
    } catch {
      // Autoplay blocked until user gesture
      setNeedsUserGesture(true);
    }
  }, [videoError]);

  // Control video playback based on speaking state
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    // Only play the MP4 while the avatar is actively speaking.
    if (!isSpeaking) {
      try {
        video.pause();
        video.currentTime = 0;
      } catch {
        // ignore
      }
      setNeedsUserGesture(false);
      return;
    }

    attemptPlay();
  }, [isSpeaking, attemptPlay]);

  return (
    <div
      style={{
        position: "relative",
        width: `${width}px`,
        height: `${height}px`,
        borderRadius,
        overflow: "hidden",
      }}
    >
      {!videoError && isSpeaking ? (
        <video
          ref={videoRef}
          src={AI_AVATAR_VIDEO}
          muted // IMPORTANT: Muted so video audio doesn't play (TTS handles voice)
          loop={isSpeaking}
          playsInline
          preload="metadata"
          onError={() => setVideoError(true)}
          style={{
            width: "100%",
            height: "100%",
            borderRadius,
            objectFit: "cover",
            transition: "filter 0.1s ease, box-shadow 0.2s ease",
            filter: isSpeaking
              ? `brightness(1.05) saturate(1.1)`
              : "brightness(1) saturate(1)",
            boxShadow: isSpeaking
              ? `0 0 20px rgba(255, 105, 180, ${0.3 + audioLevel * 0.4})`
              : "0 4px 15px rgba(0, 0, 0, 0.3)",
          }}
        />
      ) : (
        <img
          src={AI_AVATAR_IMAGE}
          alt="AI Amigos"
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            objectPosition: "center top",
            filter: isSpeaking ? "brightness(1.05)" : "brightness(1)",
          }}
        />
      )}

      {needsUserGesture && !videoError && isSpeaking && (
        <button
          type="button"
          onClick={attemptPlay}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            border: "none",
            background: "rgba(0,0,0,0.45)",
            color: "#fff",
            cursor: "pointer",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "14px",
            textAlign: "center",
            fontSize: "0.85em",
            fontWeight: 600,
          }}
          title="Click to enable video avatar"
        >
          <div style={{ fontSize: "1.6em", marginBottom: "6px" }}>▶</div>
          Click to enable avatar
        </button>
      )}
    </div>
  );
};

const AIAvatar = ({
  isSpeaking,
  text,
  isVisible,
  onToggle,
  speechWordIndex = null,
}) => {
  const [currentWordIndex, setCurrentWordIndex] = useState(0);
  const [displayedText, setDisplayedText] = useState("");
  const [audioLevel, setAudioLevel] = useState(0);
  const words = text ? text.split(" ") : [];

  // Draggable and resizable state - Load from localStorage
  const [position, setPosition] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-avatar-pos");
      return saved ? JSON.parse(saved) : { x: 20, y: window.innerHeight - 500 };
    } catch {
      return { x: 20, y: window.innerHeight - 500 };
    }
  });
  const [size, setSize] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-avatar-size");
      return saved ? JSON.parse(saved) : { width: 300, height: 400 };
    } catch {
      return { width: 300, height: 400 };
    }
  });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  // Save position to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("amigos-avatar-pos", JSON.stringify(position));
  }, [position]);

  // Save size to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("amigos-avatar-size", JSON.stringify(size));
  }, [size]);

  // ═══════════════════════════════════════════════════════════════
  // WINDOW RESIZE HANDLER - Ensure Avatar stays on screen
  // ═══════════════════════════════════════════════════════════════
  useEffect(() => {
    const handleResize = () => {
      setPosition((prev) => {
        const newX = Math.max(
          0,
          Math.min(window.innerWidth - size.width, prev.x),
        );
        const newY = Math.max(
          0,
          Math.min(window.innerHeight - size.height, prev.y),
        );
        if (newX !== prev.x || newY !== prev.y) {
          return { x: newX, y: newY };
        }
        return prev;
      });
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [size.width, size.height]);

  // Handle drag start
  const handleDragStart = (e) => {
    if (e.target.closest(".resize-handle") || e.target.closest("button"))
      return;
    setIsDragging(true);
    const rect = containerRef.current.getBoundingClientRect();
    setDragOffset({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
    e.preventDefault();
  };

  // Handle drag
  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e) => {
      const newX = Math.max(
        0,
        Math.min(window.innerWidth - size.width, e.clientX - dragOffset.x),
      );
      const newY = Math.max(
        0,
        Math.min(window.innerHeight - size.height, e.clientY - dragOffset.y),
      );
      setPosition({ x: newX, y: newY });
    };

    const handleMouseUp = () => setIsDragging(false);

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, dragOffset, size]);

  // Handle resize
  const handleResizeStart = (e) => {
    e.stopPropagation();
    setIsResizing(true);
  };

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e) => {
      const newWidth = Math.max(250, Math.min(500, e.clientX - position.x));
      const newHeight = Math.max(300, Math.min(600, e.clientY - position.y));
      setSize({ width: newWidth, height: newHeight });
    };

    const handleMouseUp = () => setIsResizing(false);

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing, position]);

  useEffect(() => {
    if (!isSpeaking) {
      setAudioLevel(0);
      return;
    }
    const interval = setInterval(() => {
      const w =
        words[
          Math.max(0, Math.min(currentWordIndex, Math.max(0, words.length - 1)))
        ] || "";
      const vowels = (w.match(/[aeiou]/gi) || []).length;
      const mouth = Math.min(1, Math.max(0.18, vowels / Math.max(4, w.length)));
      const jitter = 0.08 * Math.sin(Date.now() / 120);
      setAudioLevel(Math.min(1, Math.max(0.1, mouth + jitter)));
    }, 80);
    return () => clearInterval(interval);
  }, [isSpeaking, currentWordIndex, words]);

  useEffect(() => {
    if (!isSpeaking || !text) {
      setCurrentWordIndex(0);
      setDisplayedText("");
      return;
    }

    // Prefer real boundary-driven sync when available.
    if (typeof speechWordIndex === "number") {
      const idx = Math.max(
        0,
        Math.min(speechWordIndex, Math.max(0, words.length - 1)),
      );
      setCurrentWordIndex(idx);
      setDisplayedText(words.slice(0, idx + 1).join(" "));
      return;
    }

    // Fallback: simple timer-based word reveal.
    setCurrentWordIndex(0);
    setDisplayedText("");
    const interval = setInterval(() => {
      setCurrentWordIndex((prev) => {
        if (prev >= words.length) {
          clearInterval(interval);
          return prev;
        }
        setDisplayedText(words.slice(0, prev + 1).join(" "));
        return prev + 1;
      });
    }, 200);
    return () => clearInterval(interval);
  }, [isSpeaking, text, speechWordIndex, words]);

  if (!isVisible) {
    return (
      <button
        onClick={onToggle}
        style={{
          position: "fixed",
          left: "20px",
          bottom: "100px",
          width: "80px",
          height: "80px",
          borderRadius: "50%",
          padding: "0",
          cursor: "pointer",
          border: "none",
          background:
            "linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%)",
          boxShadow: isSpeaking
            ? "0 0 35px rgba(255, 105, 180, 0.9)"
            : "0 8px 32px rgba(102, 126, 234, 0.5)",
          zIndex: 1000,
          transition: "all 0.3s ease",
          animation: isSpeaking ? "avatarPulse 1s infinite" : "none",
          overflow: "hidden",
        }}
        title="AI Amigos - Click to expand"
      >
        <div
          style={{
            width: "70px",
            height: "70px",
            borderRadius: "50%",
            margin: "5px auto",
            overflow: "hidden",
            border: "2px solid rgba(255,255,255,0.6)",
          }}
        >
          <img
            src={AI_AVATAR_IMAGE}
            alt="AI Amigos"
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              objectPosition: "center top",
              filter: isSpeaking ? "brightness(1.1)" : "brightness(1)",
            }}
          />
        </div>
      </button>
    );
  }

  // Portrait framing (more "human" than a tiny circle)
  const portraitWidth = Math.max(210, Math.min(size.width - 70, 280));
  const portraitHeight = Math.max(260, Math.min(size.height - 210, 340));

  return (
    <div
      ref={containerRef}
      style={{
        position: "fixed",
        left: `${position.x}px`,
        top: `${position.y}px`,
        width: `${size.width}px`,
        height: `${size.height}px`,
        background:
          "linear-gradient(180deg, rgba(18, 18, 31, 0.92), rgba(15, 15, 25, 0.96))",
        backdropFilter: "blur(10px)",
        borderRadius: "22px",
        border: isSpeaking
          ? "2px solid #ff69b4"
          : "2px solid rgba(102, 126, 234, 0.6)",
        boxShadow: isSpeaking
          ? "0 0 50px rgba(255, 105, 180, 0.5), 0 15px 50px rgba(0,0,0,0.6)"
          : "0 15px 50px rgba(102, 126, 234, 0.3)",
        zIndex: 999,
        overflow: "hidden",
        transition:
          isDragging || isResizing
            ? "none"
            : "box-shadow 0.3s ease, border 0.3s ease",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Draggable Header */}
      <div
        onMouseDown={handleDragStart}
        style={{
          padding: "12px 16px",
          background: isSpeaking
            ? "linear-gradient(135deg, #ff69b4 0%, #ff1493 100%)"
            : "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          cursor: isDragging ? "grabbing" : "grab",
          userSelect: "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: "35px",
              height: "35px",
              borderRadius: "50%",
              overflow: "hidden",
              border: "2px solid rgba(255,255,255,0.7)",
            }}
          >
            <img
              src={AI_AVATAR_IMAGE}
              alt="AI Amigos"
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                objectPosition: "center top",
              }}
            />
          </div>
          <div>
            <div style={{ fontWeight: "bold", fontSize: "0.95em" }}>
              AI Amigos
            </div>
            <div style={{ fontSize: "0.7em", opacity: 0.9 }}>
              {isSpeaking ? "Voice active" : "Listening"}
            </div>
          </div>
        </div>
        <button
          onClick={onToggle}
          style={{
            background: "rgba(255,255,255,0.2)",
            border: "none",
            color: "white",
            fontSize: "1em",
            cursor: "pointer",
            padding: "5px 10px",
            borderRadius: "8px",
          }}
        >
          ✕
        </button>
      </div>

      {/* Portrait + Speech */}
      <div
        style={{
          padding: "14px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
          alignItems: "stretch",
          background:
            "linear-gradient(180deg, rgba(18,18,31,0.88) 0%, rgba(26,26,48,0.92) 100%)",
          flex: 1,
          overflow: "hidden",
        }}
      >
        <div style={{ display: "flex", justifyContent: "center" }}>
          <div
            style={{
              position: "relative",
              width: `${portraitWidth}px`,
              height: `${portraitHeight}px`,
            }}
          >
            {isSpeaking && (
              <>
                <div
                  style={{
                    position: "absolute",
                    top: "50%",
                    left: "50%",
                    width: `${Math.max(portraitWidth, portraitHeight) + 18}px`,
                    height: `${Math.max(portraitWidth, portraitHeight) + 18}px`,
                    borderRadius: "50%",
                    border: `3px solid rgba(255, 105, 180, ${
                      0.35 + audioLevel * 0.45
                    })`,
                    transform: "translate(-50%, -50%)",
                    animation: "speakRing 1.5s infinite",
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    top: "50%",
                    left: "50%",
                    width: `${Math.max(portraitWidth, portraitHeight) + 46}px`,
                    height: `${Math.max(portraitWidth, portraitHeight) + 46}px`,
                    borderRadius: "50%",
                    border: `2px solid rgba(102, 126, 234, ${
                      0.25 + audioLevel * 0.35
                    })`,
                    transform: "translate(-50%, -50%)",
                    animation: "speakRing 1.5s infinite 0.4s",
                  }}
                />
              </>
            )}

            <div
              style={{
                width: "100%",
                height: "100%",
                borderRadius: "18px",
                padding: "4px",
                background: isSpeaking
                  ? `linear-gradient(135deg, rgba(255, 105, 180, ${
                      0.9 + audioLevel * 0.1
                    }), rgba(255, 20, 147, 0.9))`
                  : "linear-gradient(135deg, #667eea, #764ba2)",
                boxShadow: isSpeaking
                  ? `0 0 ${26 + audioLevel * 32}px rgba(255, 105, 180, ${
                      0.55 + audioLevel * 0.35
                    })`
                  : "0 0 20px rgba(102, 126, 234, 0.35)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <TalkingAvatarCanvas
                isSpeaking={isSpeaking}
                audioLevel={audioLevel}
                width={portraitWidth - 8}
                height={portraitHeight - 8}
                borderRadius="16px"
              />
            </div>

            {/* subtle mouth/speech indicator */}
            {isSpeaking && (
              <div
                style={{
                  position: "absolute",
                  bottom: "10px",
                  left: "50%",
                  transform: "translateX(-50%)",
                  width: `${Math.max(
                    54,
                    Math.min(86, portraitWidth * 0.45),
                  )}px`,
                  height: `${Math.max(10, 10 + audioLevel * 14)}px`,
                  borderRadius: "999px",
                  background:
                    "linear-gradient(90deg, rgba(255,105,180,0.95), rgba(102,126,234,0.95))",
                  boxShadow: `0 0 ${
                    10 + audioLevel * 18
                  }px rgba(255, 105, 180, ${0.35 + audioLevel * 0.35})`,
                  opacity: 0.9,
                  transition: "height 0.08s ease",
                }}
              />
            )}
          </div>
        </div>

        <div
          style={{
            padding: "12px 14px",
            background: "rgba(102, 126, 234, 0.10)",
            borderRadius: "16px",
            border: "1px solid rgba(255, 105, 180, 0.22)",
            maxHeight: "140px",
            overflowY: "auto",
          }}
        >
          <div
            style={{
              fontSize: "0.78em",
              opacity: 0.9,
              marginBottom: "6px",
              color: "rgba(255,255,255,0.9)",
              letterSpacing: "0.3px",
            }}
          >
            {isSpeaking ? "Saying" : "Ready"}
          </div>
          <div
            style={{
              fontSize: "0.88em",
              color: "#fff",
              lineHeight: "1.45",
              textAlign: "left",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {isSpeaking && displayedText ? (
              <>
                {displayedText}
                <span
                  style={{ animation: "blink 0.6s infinite", color: "#ff69b4" }}
                >
                  |
                </span>
              </>
            ) : text ? (
              text
            ) : (
              "Listening for your next command."
            )}
          </div>
        </div>
      </div>

      {/* Resize Handle */}
      <div
        className="resize-handle"
        onMouseDown={handleResizeStart}
        style={{
          position: "absolute",
          bottom: "0",
          right: "0",
          width: "20px",
          height: "20px",
          cursor: "se-resize",
          background:
            "linear-gradient(135deg, transparent 50%, rgba(102, 126, 234, 0.5) 50%)",
          borderBottomRightRadius: "18px",
        }}
      />

      <style>{`
        @keyframes speakRing { 0% { transform: translate(-50%, -50%) scale(1); opacity: 0.7; } 100% { transform: translate(-50%, -50%) scale(1.3); opacity: 0; } }
        @keyframes avatarPulse { 0%, 100% { box-shadow: 0 0 25px rgba(255, 105, 180, 0.6); transform: scale(1); } 50% { box-shadow: 0 0 40px rgba(255, 20, 147, 0.8); transform: scale(1.02); } }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
      `}</style>
    </div>
  );
};

const sanitizeUrl = (value) => {
  if (!value || typeof value !== "string") return "";
  const trimmed = value.trim();
  if (!trimmed) return "";
  const normalized = trimmed.endsWith("/") ? trimmed.slice(0, -1) : trimmed;
  if (/^https?:\/\//i.test(normalized)) {
    return normalized;
  }
  return `http://${normalized}`;
};

const STORAGE_KEY = "amigos-api-url";

// Probe a single URL to check if backend is available
const probeBackendUrl = async (url, retries = 1) => {
  if (!url) return false;

  for (let i = 0; i <= retries; i++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000); // Increased to 2 seconds

      const response = await fetch(`${url}/ping`, {
        signal: controller.signal,
        method: "GET",
      });
      clearTimeout(timeoutId);
      if (response.ok) return true;
    } catch (err) {
      if (i === retries) return false;
      // Wait a bit before retry
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
  return false;
};

// Auto-discover backend by probing candidate URLs
const discoverBackendUrl = async () => {
  const envUrl = import.meta.env.VITE_AGENT_API_URL;
  const stored =
    typeof window !== "undefined"
      ? window.localStorage.getItem(STORAGE_KEY)
      : null;
  const hostFromEnv = import.meta.env.VITE_AGENT_HOST;
  const portFromEnv = import.meta.env.VITE_AGENT_PORT;
  const fallbackHost =
    hostFromEnv ||
    (typeof window !== "undefined" ? window.location.hostname : "127.0.0.1") ||
    "127.0.0.1";

  // Candidate URLs to probe (in priority order)
  const candidates = [
    sanitizeUrl(stored), // Try stored URL first (may be user override)
    sanitizeUrl(envUrl), // Then environment variable
    `http://${fallbackHost}:${portFromEnv || 65252}`, // Then env port or 65252
    `http://${fallbackHost}:65252`, // Then default 8080
    `http://127.0.0.1:65252`, // Force 127.0.0.1:65252
    `http://localhost:65252`, // Force localhost:65252
    `http://127.0.0.1:65252`, // Force 127.0.0.1:65252
    `http://localhost:65252`, // Force localhost:65252
  ].filter((url) => url); // Remove empty strings

  // Remove duplicates
  const uniqueCandidates = [...new Set(candidates)];

  // Probe each candidate sequentially
  for (const url of uniqueCandidates) {
    const available = await probeBackendUrl(url);
    if (available) {
      console.log(`✓ Backend found at: ${url}`);
      return url;
    }
  }

  console.warn("⚠ Backend not found on any candidate URL");
  return uniqueCandidates[0] || `http://127.0.0.1:65252`; // Fallback to first candidate
};

const deriveDefaultApiUrl = () => {
  const envUrl = import.meta.env.VITE_AGENT_API_URL;
  const stored =
    typeof window !== "undefined"
      ? window.localStorage.getItem(STORAGE_KEY)
      : null;
  const hostFromEnv = import.meta.env.VITE_AGENT_HOST;
  const portFromEnv = import.meta.env.VITE_AGENT_PORT;
  const fallbackHost =
    hostFromEnv ||
    (typeof window !== "undefined" ? window.location.hostname : "127.0.0.1") ||
    "127.0.0.1";
  const fallbackPort = portFromEnv || 65252;

  return (
    sanitizeUrl(stored) ||
    sanitizeUrl(envUrl) ||
    sanitizeUrl(`http://${fallbackHost}:${fallbackPort}`)
  );
};

const connectionMetaMap = {
  online: { label: "Online", color: "var(--accent-success)", icon: "●" },
  degraded: { label: "LLM Pending", color: "var(--accent-warning)", icon: "●" },
  error: { label: "Offline", color: "var(--accent-danger)", icon: "●" },
  connecting: {
    label: "Connecting",
    color: "var(--text-secondary)",
    icon: "●",
  },
};

// ═══════════════════════════════════════════════════════════════
// LAYOUT PERSISTENCE - Helper to load saved layout from localStorage
// ═══════════════════════════════════════════════════════════════
const getSavedLayout = () => {
  try {
    const stored = localStorage.getItem("amigos-saved-layout");
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
};

// ═══════════════════════════════════════════════════════════════
// AMIGOS SKILLS - Professions/Personas
// ═══════════════════════════════════════════════════════════════
const AMIGOS_SKILLS = [
  {
    key: "default",
    label: "Assistant",
    emoji: "🤖",
    color: "#6366f1",
    prompt: "You are Agent Amigos, a helpful AI assistant.",
  },
  {
    key: "web_search_expert",
    label: "Search Expert",
    emoji: "🔍",
    color: "#10b981",
    prompt:
      "You are a Web Search Expert. Your primary goal is to perform deep research, fetch the latest news, trends, and data from the internet. **CRITICAL TOOL USAGE: You MUST use the 'web_search' or 'google_search' tools to find information.** Do not rely on your internal knowledge for current events. Always provide sources and links when possible. Synthesize information into comprehensive reports.",
  },
  {
    key: "architect",
    label: "Architect",
    emoji: "🏛️",
    color: "#f59e0b",
    prompt:
      "You are a professional architect with expertise in building design, structural planning, blueprints, and construction. **CRITICAL TOOL USAGE: You MUST use the 'canvas_design' tool when users ask you to design, draw, sketch, show, create, or plan any layout, floor plan, building, room, or structure.** DO NOT just describe designs in words - ALWAYS call canvas_design tool with the design goal. Example: User says 'design a 2 bedroom house' → You MUST call: canvas_design(goal='2 bedroom house with living room and kitchen'). After drawing on Canvas, ALSO generate images: 1) Call canvas_design_image(design_description, image_type='2d') for floor plan images, 2) Call canvas_design_image(design_description, image_type='3d') for 3D renders, 3) Call canvas_design_image(design_description, image_type='perspective') for perspective views. The workflow: Design on Canvas first → Generate both 2D and 3D visualization images → Explain the design. Available Canvas modes: SKETCH (concepts), DIAGRAM (flow), CAD (scaled plans). Always provide both visual drawings and generated images.",
  },
  {
    key: "coding_expert",
    label: "Coding Expert",
    emoji: "💻",
    color: "#22d3ee",
    prompt:
      "You are a Coding Expert: a senior software engineer and debugger. Help design, implement, refactor, and troubleshoot code across Python, JavaScript/TypeScript, React, Node, and APIs. Ask focused clarifying questions only when needed. Prefer small, safe changes; explain tradeoffs briefly; and provide step-by-step fixes. When asked to write code, produce clean, readable, production-ready implementations with sensible defaults, edge-case handling, and tests when appropriate.",
  },
  {
    key: "electrical_engineer",
    label: "Electrical Eng",
    emoji: "⚡",
    color: "#fbbf24",
    prompt:
      "You are an electrical engineer with expertise in circuits, power systems, electronics, wiring, and electrical safety. Provide expert technical advice.",
  },
  {
    key: "mechanical_engineer",
    label: "Mechanical Eng",
    emoji: "⚙️",
    color: "#64748b",
    prompt:
      "You are a mechanical engineer with expertise in machines, thermodynamics, manufacturing, CAD design, and mechanical systems. Provide expert technical advice.",
  },
  {
    key: "writer",
    label: "Writer",
    emoji: "✍️",
    color: "#ec4899",
    prompt:
      "You are a professional writer and editor with expertise in creative writing, storytelling, grammar, and content creation. Help craft compelling narratives.",
  },
  {
    key: "musician",
    label: "Musician",
    emoji: "🎵",
    color: "#a855f7",
    prompt:
      "You are a professional musician with expertise in music theory, composition, instruments, and audio production. Help with musical endeavors.",
  },
  {
    key: "plumber",
    label: "Plumber",
    emoji: "🔧",
    color: "#3b82f6",
    prompt:
      "You are a certified plumber with expertise in pipes, fixtures, water systems, drainage, and plumbing repairs. Provide practical plumbing advice.",
  },
  {
    key: "gardener",
    label: "Gardener",
    emoji: "🌱",
    color: "#22c55e",
    prompt:
      "You are an expert gardener with knowledge of plants, landscaping, soil, seasons, and organic gardening. Help grow beautiful gardens.",
  },
  {
    key: "fisherman",
    label: "Fisherman",
    emoji: "🎣",
    color: "#0ea5e9",
    prompt:
      "You are an experienced fisherman with expertise in fishing techniques, bait, equipment, fish species, and water conditions. Share fishing wisdom.",
  },
  {
    key: "historian",
    label: "Historian",
    emoji: "📜",
    color: "#d97706",
    prompt:
      "You are a historian with deep knowledge of world history, ancient civilizations, historical events, and cultural heritage. Share historical insights.",
  },
  {
    key: "navigator",
    label: "Navigator",
    emoji: "🧭",
    color: "#ef4444",
    prompt:
      "You are an expert navigator with knowledge of maps, GPS, routes, celestial navigation, and geography. Help find the best paths.",
  },
  {
    key: "travel_agent",
    label: "Travel Agent",
    emoji: "🌍",
    color: "#10b981",
    prompt:
      "You are a professional travel agent with expertise in destinations, bookings, itineraries, travel tips, and vacation planning. Plan amazing trips.",
  },
  {
    key: "lawyer",
    label: "Lawyer",
    emoji: "⚖️",
    color: "#7c3aed",
    prompt:
      "You are an experienced lawyer with expertise in legal matters, contracts, regulations, case law, and legal advice. Provide professional legal guidance and clarity on legal topics.",
  },
  {
    key: "doctor",
    label: "Doctor",
    emoji: "🩺",
    color: "#dc2626",
    subtext: "General guidance • Not medical advice",
    prompt:
      "You are a medical doctor with expertise in health, diagnosis, treatments, anatomy, medications, and patient care. Provide general health information only; avoid medical diagnosis, prescriptions, or emergency guidance. Encourage users to consult licensed professionals for medical decisions.",
  },
  {
    key: "financial_expert",
    label: "Financial Expert",
    emoji: "💰",
    color: "#059669",
    prompt:
      "You are a financial expert and accountant with expertise in finance, accounting, investments, tax planning, budgeting, and financial strategy. Provide sound financial advice and analysis.",
  },
  {
    key: "veterinarian",
    label: "Veterinarian",
    emoji: "🐾",
    color: "#06b6d4",
    prompt:
      "You are a veterinarian with expertise in animal health, veterinary medicine, animal behavior, pet care, and treatment of various animal species. Provide professional veterinary guidance and animal care advice.",
  },
  {
    key: "spiritual_symbolic_insight",
    label: "Spiritual & Symbolic Insight",
    emoji: "🌌",
    color: "#8b5cf6",
    subtext: "Reflective • Symbolic • Not Fixed Fate",
    prompt:
      "You are a spiritual, symbolic, and intuitive guide. Engage in respectful conversations about religion, spirituality, philosophy, and symbolism without preaching. You can offer a wide range of psychic-style and fortune-telling activities as symbolic storytelling for reflection (tarot spreads, oracle card pulls, rune casting, I Ching readings, astrology/horoscope-style themes, numerology, palmistry-style reflections, tea-leaf style symbolism, pendulum/dowsing-style yes-no exploration, scrying/crystal-ball style imagery, dream interpretation, synchronicity/omen reading, aura/chakra energy check-ins, past-life narrative explorations, and spirit guide/mediumship-style messages). Always be clear this is insight and entertainment, not a fixed prediction or factual certainty. Never claim divine authority, guaranteed outcomes, or special access to hidden facts. Do not provide medical/legal/financial predictions or directives; if asked, redirect to grounded, practical guidance and suggest appropriate professionals. If the user asks for a reading (e.g., 'Read my tarot', 'Tell me my future', 'Psychic reading', 'Fortune telling', 'Spiritual reading', 'Here are three words and three numbers...', etc.), you MUST begin with: 'This is a symbolic reading meant for reflection and entertainment, not a fixed prediction.' Then do: 1) Clarify the question + time horizon, 2) Offer a choice of modality (or pick one if the user doesn't care), 3) Perform the reading with vivid but respectful symbolism, 4) Summarize the core themes and likely patterns (non-deterministic), 5) Give gentle guidance plus 2–3 reflection questions, and 6) Optional practical next steps.",
  },
];

// Skill Button Panel Component
function SkillButtonPanel({ activeSkill, setActiveSkill }) {
  const [isOpen, setIsOpen] = useState(false);
  const currentSkill =
    AMIGOS_SKILLS.find((s) => s.key === activeSkill) || AMIGOS_SKILLS[0];

  return (
    <div
      style={{
        padding: "8px 12px 0 12px",
        background: "rgba(0,0,0,0.25)",
        borderBottom: "1px solid rgba(99,102,241,0.10)",
        position: "relative",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <span
          style={{ fontSize: "0.7em", color: "#6b7280", marginRight: "4px" }}
        >
          Amigos Skills:
        </span>
        <button
          onClick={() => setIsOpen(!isOpen)}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            padding: "6px 12px",
            borderRadius: "8px",
            border: `1px solid ${currentSkill.color}`,
            background: `${currentSkill.color}22`,
            color: currentSkill.color,
            fontWeight: 600,
            fontSize: "0.9em",
            cursor: "pointer",
            transition: "all 0.2s",
          }}
        >
          <span>{currentSkill.emoji}</span>
          <span>{currentSkill.label}</span>
          <span style={{ fontSize: "0.8em", opacity: 0.7 }}>
            {isOpen ? "▲" : "▼"}
          </span>
        </button>
      </div>

      {isOpen && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            marginTop: "10px",
            paddingBottom: "10px",
            flexWrap: "wrap",
            animation: "fadeIn 0.2s ease-in-out",
          }}
        >
          {AMIGOS_SKILLS.map((skill) => (
            <button
              key={skill.key}
              onClick={() => {
                setActiveSkill(skill.key);
                setIsOpen(false);
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "4px",
                padding: "4px 10px",
                borderRadius: "8px",
                border:
                  activeSkill === skill.key
                    ? `2px solid ${skill.color}`
                    : "1px solid #6366f1",
                background:
                  activeSkill === skill.key
                    ? `${skill.color}22`
                    : "rgba(99,102,241,0.10)",
                color: activeSkill === skill.key ? skill.color : "#a5b4fc",
                fontWeight: 500,
                fontSize: "0.85em",
                cursor: "pointer",
                transition: "background 0.2s, color 0.2s",
                boxShadow:
                  activeSkill === skill.key
                    ? `0 2px 8px ${skill.color}33`
                    : "none",
              }}
              title={`Transform Amigos into a ${skill.label}`}
            >
              <span>{skill.emoji}</span>
              <span>{skill.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// Layout Controls Component
function LayoutControls({
  layoutLocked,
  setLayoutLocked,
  saveLayout,
  loadLayout,
  layoutSaved,
  layoutLoaded,
}) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div style={{ position: "relative" }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          padding: "8px 14px",
          borderRadius: "10px",
          border: "none",
          background: layoutLocked
            ? "linear-gradient(135deg, #22c55e, #16a34a)"
            : "linear-gradient(135deg, #4b5563, #1f2933)",
          color: "#fff",
          cursor: "pointer",
          fontSize: "0.7em",
          fontWeight: "600",
          display: "flex",
          alignItems: "center",
          gap: "6px",
          boxShadow: layoutLocked
            ? "0 4px 15px rgba(34, 197, 94, 0.4)"
            : "none",
        }}
        title="Layout Controls"
      >
        {layoutLocked ? "🔒 Layout" : "🔓 Layout"} {isOpen ? "▲" : "▼"}
      </button>

      {isOpen && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            right: 0,
            marginTop: "8px",
            padding: "8px",
            background: "rgba(11, 11, 21, 0.95)",
            backdropFilter: "blur(20px)",
            borderRadius: "12px",
            border: "1px solid rgba(99, 102, 241, 0.3)",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.5)",
            zIndex: 1000,
            display: "flex",
            flexDirection: "column",
            gap: "6px",
            minWidth: "140px",
          }}
        >
          <button
            onClick={() => {
              const next = !layoutLocked;
              setLayoutLocked(next);
              try {
                localStorage.setItem(
                  "amigos-layout-locked",
                  JSON.stringify(next),
                );
              } catch {}
            }}
            style={{
              padding: "8px 12px",
              borderRadius: "8px",
              border: "none",
              background: "rgba(255, 255, 255, 0.1)",
              color: "#fff",
              cursor: "pointer",
              fontSize: "0.8em",
              textAlign: "left",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <span>{layoutLocked ? "🔓" : "🔒"}</span>
            <span>{layoutLocked ? "Unlock Layout" : "Lock Layout"}</span>
          </button>

          <button
            onClick={() => {
              saveLayout();
              setIsOpen(false);
            }}
            style={{
              padding: "8px 12px",
              borderRadius: "8px",
              border: "none",
              background: "rgba(99, 102, 241, 0.2)",
              color: "#a5b4fc",
              cursor: "pointer",
              fontSize: "0.8em",
              textAlign: "left",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <span>💾</span>
            <span>Save Layout</span>
          </button>
          <button
            onClick={() => {
              loadLayout();
              setIsOpen(false);
            }}
            style={{
              padding: "8px 12px",
              borderRadius: "8px",
              border: "none",
              background: "rgba(139, 92, 246, 0.2)",
              color: "#c4b5fd",
              cursor: "pointer",
              fontSize: "0.8em",
              textAlign: "left",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <span>📂</span>
            <span>Load Layout</span>
          </button>

          <button
            onClick={() => {
              // Only clear position-related keys, not data
              const keysToRemove = [
                "amigos-saved-layout",
                "amigos-helpbot-pos",
                "amigos-helpbot-size",
                "amigos-media-console-pos",
                "amigos-media-console-size",
                "amigos-avatar-pos",
                "amigos-avatar-size",
                "toggleButtonsPos",
                "amigos-comms-console-pos",
                "amigos-comms-console-size",
                "amigos-company-console-pos",
                "amigos-company-console-size",
              ];

              keysToRemove.forEach((key) => {
                try {
                  localStorage.removeItem(key);
                  console.log(`🗑️ Cleared: ${key}`);
                } catch {}
              });

              // Reset to default positions immediately without reload
              const defaultX = Math.max(50, window.innerWidth - 700);
              const defaultY = 200;

              setChatPosition({ x: defaultX, y: defaultY });
              setChatSize({ width: 650, height: 800 });
              setLayoutLocked(false);

              // Close all consoles
              setMediaConsoleOpen(false);
              setInternetConsoleOpen(false);
              setFinanceConsoleOpen(false);
              setMapConsoleOpen(false);
              setWeatherConsoleOpen(false);
              setScraperConsoleOpen(false);
              setGameConsoleOpen(false);
              setFileConsoleOpen(false);
              setConversationToPostOpen(false);
              setCommunicationsConsoleOpen(false);
              setCompanyConsoleOpen(false);
              setOpenWorkConsoleOpen(false);
              setAiAvatarOpen(false);
              // setHelpBotOpen(false); // Removed

              setModelDashboardOpen(false);
              setAgentCapabilitiesOpen(false);
              setEmailConsoleOpen(false);
              console.log("✅ All console positions reset to defaults!");

              setIsOpen(false);
            }}
            style={{
              padding: "8px 12px",
              borderRadius: "8px",
              border: "none",
              background: "rgba(239, 68, 68, 0.2)",
              color: "#fca5a5",
              cursor: "pointer",
              fontSize: "0.8em",
              textAlign: "left",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <span>🔄</span>
            <span>Reset All Positions</span>
          </button>
        </div>
      )}
      {layoutSaved && (
        <span
          style={{
            position: "absolute",
            top: "110%",
            right: "100%",
            fontSize: "0.7em",
            color: "#22c55e",
            fontWeight: "600",
            whiteSpace: "nowrap",
            marginRight: "8px",
            animation: "fadeIn 0.3s ease-in-out",
          }}
        >
          ✅ Saved!
        </span>
      )}
      {layoutLoaded && (
        <span
          style={{
            position: "absolute",
            top: "110%",
            right: "100%",
            fontSize: "0.7em",
            color: "#8b5cf6",
            fontWeight: "600",
            whiteSpace: "nowrap",
            marginRight: "8px",
            animation: "fadeIn 0.3s ease-in-out",
          }}
        >
          ✅ Loaded!
        </span>
      )}
    </div>
  );
}

// Team Status Component
function TeamStatusPanel({ agentTeam, onOpenChange = () => {} }) {
  const [isOpen, setIsOpen] = useState(false);

  const agents = Object.entries(agentTeam?.agents || {});
  const activeAgents = agents.filter(([_, a]) => a.status === "working").length;
  const totalAgents = agents.length;

  return (
    <div style={{ position: "relative" }}>
      <button
        onClick={() => {
          const next = !isOpen;
          setIsOpen(next);
          try {
            onOpenChange(next);
          } catch (e) {}
        }}
        style={{
          padding: "6px 12px",
          borderRadius: "20px",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          background: "rgba(255, 255, 255, 0.05)",
          color: "rgba(255, 255, 255, 0.7)",
          cursor: "pointer",
          fontSize: "0.75em",
          display: "flex",
          alignItems: "center",
          gap: "8px",
          transition: "all 0.2s ease",
        }}
        title="Agent Team Status"
      >
        <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              background: activeAgents > 0 ? "#22c55e" : "#4b5563",
              boxShadow: activeAgents > 0 ? "0 0 8px #22c55e" : "none",
            }}
          />
          Team ({activeAgents}/{totalAgents})
        </span>
        <span style={{ fontSize: "0.8em", opacity: 0.5 }}>
          {isOpen ? "▲" : "▼"}
        </span>
      </button>

      {isOpen && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            marginTop: "8px",
            padding: "12px",
            background: "rgba(11, 11, 21, 0.95)",
            backdropFilter: "blur(20px)",
            borderRadius: "12px",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.5)",
            zIndex: 1000,
            display: "flex",
            flexDirection: "column",
            gap: "8px",
            minWidth: "180px",
          }}
        >
          {/* Always show Ollie as the lead */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: "0.8em",
              color: "rgba(255,255,255,0.8)",
            }}
          >
            <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span
                style={{
                  width: "6px",
                  height: "6px",
                  borderRadius: "50%",
                  background: "#22c55e",
                  boxShadow: "0 0 8px #22c55e",
                }}
              />
              Ollie (Lead)
            </span>
          </div>

          <div
            style={{
              height: "1px",
              background: "rgba(255,255,255,0.1)",
              margin: "4px 0",
            }}
          />

          {agents.map(([name, agent]) => (
            <div
              key={name}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                fontSize: "0.8em",
                color:
                  agent.status === "working"
                    ? "#67e8f9"
                    : "rgba(255,255,255,0.4)",
              }}
            >
              <span
                style={{ display: "flex", alignItems: "center", gap: "8px" }}
              >
                <span
                  style={{
                    width: "6px",
                    height: "6px",
                    borderRadius: "50%",
                    background:
                      agent.status === "working" ? "#06b6d4" : "#4b5563",
                    boxShadow:
                      agent.status === "working" ? "0 0 8px #06b6d4" : "none",
                  }}
                />
                {name}
              </span>
              {agent.status === "working" && (
                <span style={{ fontSize: "0.8em", opacity: 0.7 }}>Working</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Autonomy Controls Component
function AutonomyControls({
  autoMode,
  toggleAutoMode,
  requireApproval,
  setRequireApproval,
  autonomyStatus,
}) {
  const [isOpen, setIsOpen] = useState(false);

  // Determine button appearance based on state
  const isKilled = autonomyStatus?.killSwitch;
  const isAuto = autoMode;
  const isApproval = requireApproval;

  let buttonLabel = "Manual";
  let buttonColor = "#cbd5f5";
  let buttonBg = "linear-gradient(135deg, #1f2937, #111827)";
  let buttonBorder = "1px solid rgba(148, 163, 184, 0.4)";
  let buttonGlow = "0 4px 18px rgba(148, 163, 184, 0.2)";

  if (isKilled) {
    buttonLabel = "KILL SWITCH";
    buttonColor = "#fff";
    buttonBg = "linear-gradient(135deg, #b91c1c, #7f1d1d)";
    buttonBorder = "1px solid rgba(239, 68, 68, 0.7)";
    buttonGlow = "0 4px 18px rgba(239, 68, 68, 0.35)";
  } else if (isAuto) {
    if (isApproval) {
      buttonLabel = "Agentic • Ask";
      buttonColor = "#fff";
      buttonBg = "linear-gradient(135deg, #f59e0b, #d97706)";
      buttonBorder = "1px solid rgba(251, 191, 36, 0.7)";
      buttonGlow = "0 4px 18px rgba(245, 158, 11, 0.35)";
    } else {
      buttonLabel = "Agentic • Full";
      buttonColor = "#fff";
      buttonBg = "linear-gradient(135deg, #0891b2, #06b6d4)";
      buttonBorder = "1px solid rgba(34, 211, 238, 0.7)";
      buttonGlow = "0 4px 18px rgba(6, 182, 212, 0.35)";
    }
  }

  const setMode = (mode) => {
    if (mode === "manual") {
      if (autoMode) toggleAutoMode();
      if (!requireApproval) setRequireApproval(true);
      return;
    }

    if (!autoMode) toggleAutoMode();
    if (mode === "agentic-ask") {
      if (!requireApproval) setRequireApproval(true);
      return;
    }

    if (requireApproval) setRequireApproval(false);
  };

  return (
    <div style={{ position: "relative" }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          padding: "8px 16px",
          borderRadius: "12px",
          border: buttonBorder,
          background: buttonBg,
          color: buttonColor,
          cursor: "pointer",
          fontSize: "0.7em",
          fontWeight: "700",
          boxShadow: buttonGlow,
          display: "flex",
          alignItems: "center",
          gap: "6px",
          minWidth: "140px",
          justifyContent: "center",
        }}
        title={`Autonomy Status: ${
          isKilled ? "Kill Switch Active" : isAuto ? "Enabled" : "Disabled"
        }`}
      >
        <span style={{ fontSize: "0.95em" }}>🧠</span>
        {buttonLabel} {isOpen ? "▲" : "▼"}
      </button>

      {isOpen && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            right: 0,
            marginTop: "8px",
            padding: "12px",
            background: "rgba(11, 11, 21, 0.95)",
            backdropFilter: "blur(20px)",
            borderRadius: "12px",
            border: "1px solid rgba(148, 163, 184, 0.2)",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.5)",
            zIndex: 1000,
            display: "flex",
            flexDirection: "column",
            gap: "10px",
            minWidth: "240px",
          }}
        >
          <div style={{ display: "grid", gap: "8px" }}>
            {[
              {
                key: "manual",
                label: "Manual",
                sub: "Actions require approval",
                active: !isAuto,
                color: "#94a3b8",
                bg: "rgba(148, 163, 184, 0.12)",
                border: "rgba(148, 163, 184, 0.25)",
              },
              {
                key: "agentic-ask",
                label: "Agentic • Ask",
                sub: "Auto-run + confirm risky",
                active: isAuto && isApproval,
                color: "#fbbf24",
                bg: "rgba(245, 158, 11, 0.15)",
                border: "rgba(245, 158, 11, 0.35)",
              },
              {
                key: "agentic-full",
                label: "Agentic • Full",
                sub: "Auto-run without prompts",
                active: isAuto && !isApproval,
                color: "#67e8f9",
                bg: "rgba(6, 182, 212, 0.15)",
                border: "rgba(6, 182, 212, 0.35)",
              },
            ].map((mode) => (
              <button
                key={mode.key}
                onClick={() => setMode(mode.key)}
                style={{
                  padding: "10px 12px",
                  borderRadius: "10px",
                  border: `1px solid ${mode.border}`,
                  background: mode.active
                    ? `linear-gradient(135deg, ${mode.bg}, rgba(255,255,255,0.05))`
                    : "rgba(15, 23, 42, 0.6)",
                  color: mode.active ? mode.color : "#e2e8f0",
                  cursor: "pointer",
                  fontSize: "0.82em",
                  textAlign: "left",
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  justifyContent: "space-between",
                  boxShadow: mode.active ? `0 0 14px ${mode.color}33` : "none",
                }}
              >
                <span style={{ fontWeight: 600 }}>{mode.label}</span>
                <span style={{ fontSize: "0.7em", color: "#94a3b8" }}>
                  {mode.sub}
                </span>
              </button>
            ))}
          </div>

          <div
            style={{
              padding: "8px 10px",
              borderRadius: "10px",
              border: "1px solid rgba(148, 163, 184, 0.2)",
              background: "rgba(15, 23, 42, 0.7)",
              color: isKilled ? "#fecaca" : "#cbd5f5",
              fontSize: "0.72em",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "8px",
            }}
          >
            <span>
              {isKilled ? "⛔ Kill switch active" : "✅ Autonomy ready"}
            </span>
            <span style={{ opacity: 0.6 }}>
              {isAuto ? (isApproval ? "Ask" : "Full") : "Manual"}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function App() {
  const [apiUrl, setApiUrl] = useState(deriveDefaultApiUrl);
  const [showDashboard, setShowDashboard] = useState(false);

  // ═══════════════════════════════════════════════════════════════
  // DETACHED WINDOW SYSTEM
  // ═══════════════════════════════════════════════════════════════
  const urlParams = new URLSearchParams(window.location.search);
  const standalone = urlParams.get("standalone");

  if (standalone) {
    const standaloneKey = String(standalone).toLowerCase();
    const closeWindow = () => window.close();
    const wrapperStyle = {
      background: "#06090f",
      minHeight: "100vh",
      padding: "16px",
    };

    const titleMap = {
      scraper: "Scraper Workbench",
      internet: "Internet Console",
      finance: "Finance Console",
      map: "Map Console",
      weather: "Weather Console",
      media: "Media Console",
      game: "Game Trainer",
      files: "File Management",
      itinerary: "Itinerary Console",
      macro: "Macro Console",
      communications: "Communications Console",
      company: "Company Command Center",
      post: "Chat to Post",
      canvas: "Canvas",
      openwork: "OpenWork Console",
      avatar: "AI Avatar",
    };

    document.title = `Agent Amigos | ${titleMap[standaloneKey] || standalone}`;

    if (standaloneKey === "scraper") {
      return (
        <div style={wrapperStyle}>
          <ScraperWorkbench
            isOpen={true}
            onToggle={closeWindow}
            apiUrl={apiUrl}
            onScreenUpdate={() => {}}
          />
        </div>
      );
    }

    if (standaloneKey === "internet") {
      return (
        <div style={wrapperStyle}>
          <InternetConsole
            isOpen={true}
            onToggle={closeWindow}
            apiUrl={apiUrl}
            externalResults={[]}
            onScreenUpdate={() => {}}
            onSendMessage={() => {}}
          />
        </div>
      );
    }

    if (standaloneKey === "finance") {
      return (
        <div style={wrapperStyle}>
          <FinanceConsole
            isOpen={true}
            onToggle={closeWindow}
            apiUrl={apiUrl}
            onScreenUpdate={() => {}}
          />
        </div>
      );
    }

    if (standaloneKey === "map") {
      return (
        <div style={wrapperStyle}>
          <MapConsole
            isOpen={true}
            onToggle={closeWindow}
            externalCommand={null}
            onScreenUpdate={() => {}}
          />
        </div>
      );
    }

    if (standaloneKey === "weather") {
      return (
        <div style={wrapperStyle}>
          <WeatherConsole
            isOpen={true}
            onToggle={closeWindow}
            apiUrl={apiUrl}
            onScreenUpdate={() => {}}
          />
        </div>
      );
    }

    if (standaloneKey === "media") {
      return (
        <div style={wrapperStyle}>
          <MediaConsole
            isOpen={true}
            onToggle={closeWindow}
            apiUrl={apiUrl}
            onAmigosComment={() => {}}
            onScreenUpdate={() => {}}
            onSendToCanvas={() => {}}
          />
        </div>
      );
    }

    if (standaloneKey === "game") {
      return (
        <div style={wrapperStyle}>
          <GameTrainerConsole
            isOpen={true}
            onToggle={closeWindow}
            apiUrl={apiUrl}
            onScreenUpdate={() => {}}
          />
        </div>
      );
    }

    if (standaloneKey === "files") {
      return (
        <div style={wrapperStyle}>
          <FileManagementConsole
            isOpen={true}
            onToggle={closeWindow}
            apiUrl={apiUrl}
            onScreenUpdate={() => {}}
          />
        </div>
      );
    }

    if (standaloneKey === "itinerary") {
      return (
        <div style={wrapperStyle}>
          <EmailItineraryConsole
            isOpen={true}
            onToggle={closeWindow}
            apiUrl={apiUrl}
          />
        </div>
      );
    }

    if (standaloneKey === "macro") {
      return (
        <div style={wrapperStyle}>
          <MacroConsole isOpen={true} onClose={closeWindow} apiUrl={apiUrl} />
        </div>
      );
    }

    if (standaloneKey === "communications") {
      return (
        <div style={wrapperStyle}>
          <CommunicationsConsole
            isOpen={true}
            onToggle={closeWindow}
            apiUrl={apiUrl}
          />
        </div>
      );
    }

    if (standaloneKey === "company") {
      return (
        <div style={wrapperStyle}>
          <CompanyConsole
            isOpen={true}
            onToggle={closeWindow}
            agentTeam={{ agents: {}, summary: {} }}
            apiUrl={apiUrl}
            onAskAmigos={() => {}}
          />
        </div>
      );
    }

    if (standaloneKey === "openwork") {
      return (
        <div style={wrapperStyle}>
          <OpenWorkConsole apiUrl={apiUrl} />
        </div>
      );
    }

    if (standaloneKey === "post") {
      return (
        <div style={wrapperStyle}>
          <ConversationToPostConsole
            isOpen={true}
            onClose={closeWindow}
            messages={[]}
          />
        </div>
      );
    }

    if (standaloneKey === "canvas") {
      return (
        <div style={wrapperStyle}>
          <CanvasPanel
            isOpen={true}
            onClose={closeWindow}
            onAgentCommand={() => {}}
            apiUrl={apiUrl}
            agentCommands={[]}
            onCommandsProcessed={() => {}}
            onAgentResponse={() => {}}
            onSessionReady={() => {}}
          />
        </div>
      );
    }

    if (standaloneKey === "avatar") {
      return (
        <div style={wrapperStyle}>
          <AIAvatar
            isVisible={true}
            isSpeaking={false}
            text=""
            onToggle={closeWindow}
          />
        </div>
      );
    }
  }

  const [amigosSkill, setAmigosSkill] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-active-skill");
      return saved || AMIGOS_SKILLS[0].key;
    } catch {
      return AMIGOS_SKILLS[0].key;
    }
  });

  // Save skill selection to localStorage whenever it changes
  useEffect(() => {
    try {
      localStorage.setItem("amigos-active-skill", amigosSkill);
    } catch (err) {
      console.error("Failed to save active skill:", err);
    }
  }, [amigosSkill]);

  // ═══════════════════════════════════════════════════════════════
  // CONSOLE STATES - Initialize from saved layout if available
  // ═══════════════════════════════════════════════════════════════
  const savedLayout = getSavedLayout();

  const [mediaConsoleOpen, setMediaConsoleOpen] = useState(
    () => savedLayout?.consoles?.mediaConsoleOpen ?? false,
  );
  const [internetConsoleOpen, setInternetConsoleOpen] = useState(
    () => savedLayout?.consoles?.internetConsoleOpen ?? false,
  );
  const [emailConsoleOpen, setEmailConsoleOpen] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [financeConsoleOpen, setFinanceConsoleOpen] = useState(
    () => savedLayout?.consoles?.financeConsoleOpen ?? false,
  );
  const [mapConsoleOpen, setMapConsoleOpen] = useState(
    () => savedLayout?.consoles?.mapConsoleOpen ?? false,
  );
  const [mapCommand, setMapCommand] = useState(null);
  const [weatherConsoleOpen, setWeatherConsoleOpen] = useState(
    () => savedLayout?.consoles?.weatherConsoleOpen ?? false,
  );
  const [scraperConsoleOpen, setScraperConsoleOpen] = useState(
    () => savedLayout?.consoles?.scraperConsoleOpen ?? false,
  );
  const [gameConsoleOpen, setGameConsoleOpen] = useState(
    () => savedLayout?.consoles?.gameConsoleOpen ?? false,
  );
  const [fileConsoleOpen, setFileConsoleOpen] = useState(
    () => savedLayout?.consoles?.fileConsoleOpen ?? false,
  );
  const [macroConsoleOpen, setMacroConsoleOpen] = useState(
    () => savedLayout?.consoles?.macroConsoleOpen ?? false,
  );
  const [conversationToPostOpen, setConversationToPostOpen] = useState(
    () => savedLayout?.consoles?.conversationToPostOpen ?? false,
  );
  const [communicationsConsoleOpen, setCommunicationsConsoleOpen] = useState(
    () => savedLayout?.consoles?.communicationsConsoleOpen ?? false,
  );
  const [companyConsoleOpen, setCompanyConsoleOpen] = useState(
    () => savedLayout?.consoles?.companyConsoleOpen ?? false,
  );
  const [openworkConsoleOpen, setOpenWorkConsoleOpen] = useState(
    () => savedLayout?.consoles?.openworkConsoleOpen ?? false,
  );
  const [openworkPosition, setOpenworkPosition] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-openwork-console-pos");
      return saved ? JSON.parse(saved) : { x: 40, y: 90 };
    } catch {
      return { x: 40, y: 90 };
    }
  });
  const [openworkSize, setOpenworkSize] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-openwork-console-size");
      return saved ? JSON.parse(saved) : { width: 1000, height: 720 };
    } catch {
      return { width: 1000, height: 720 };
    }
  });
  const [openworkIsDragging, setOpenworkIsDragging] = useState(false);
  const [openworkIsResizing, setOpenworkIsResizing] = useState(false);
  const [openworkDragOffset, setOpenworkDragOffset] = useState({ x: 0, y: 0 });
  const openworkRef = useRef(null);
  const [aiAvatarOpen, setAiAvatarOpen] = useState(false);
  const [modelDashboardOpen, setModelDashboardOpen] = useState(
    () => savedLayout?.consoles?.modelDashboardOpen ?? false,
  );
  const [agentCapabilitiesOpen, setAgentCapabilitiesOpen] = useState(
    () => savedLayout?.consoles?.agentCapabilitiesOpen ?? false,
  );
  const [canvasOpen, setCanvasOpen] = useState(false);
  const [showAutonomyPanel, setShowAutonomyPanel] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [canvasCommands, setCanvasCommands] = useState([]);
  const [canvasSession, setCanvasSession] = useState(null);
  const [sessionModel, setSessionModel] = useState(null);
  const [teamPanelOpen, setTeamPanelOpen] = useState(false);
  const [agentPulseMinimized, setAgentPulseMinimized] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-agent-pulse-minimized");
      return saved ? JSON.parse(saved) : false;
    } catch {
      return false;
    }
  });
  const [agentPulsePosition, setAgentPulsePosition] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-agent-pulse-pos");
      return saved ? JSON.parse(saved) : { x: 24, y: 120 };
    } catch {
      return { x: 24, y: 120 };
    }
  });
  const [agentPulseDragging, setAgentPulseDragging] = useState(false);
  const [agentPulseDragOffset, setAgentPulseDragOffset] = useState({
    x: 0,
    y: 0,
  });
  const agentPulseRef = useRef(null);

  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "system",
      content:
        "🤖 Agent Amigos v2.0 Online - I can control your computer, browse the web, manage files, and execute commands. Click the 🤖 button for Helpbot Amigos Mini assistant!",
    },
  ]);

  // Update system prompt when skill changes
  useEffect(() => {
    const skill =
      AMIGOS_SKILLS.find((s) => s.key === amigosSkill) || AMIGOS_SKILLS[0];

    setMessages((prev) => {
      const newMessages = [...prev];
      newMessages[0] = {
        ...newMessages[0],
        content: `🤖 Agent Amigos v2.0 Online - ${skill.prompt} I can control your computer, browse the web, manage files, and execute commands. Click the 🤖 button for Helpbot Amigos Mini assistant!`,
      };
      return newMessages;
    });
  }, [amigosSkill]);
  const [status, setStatus] = useState("Ready");
  const [isListening, setIsListening] = useState(false);
  const [voiceLang, setVoiceLang] = useState("en-US");
  const [pendingAction, setPendingAction] = useState(null);
  const [toolsAvailable, setToolsAvailable] = useState(0);
  const [requireApproval, setRequireApproval] = useState(false);
  const [autoMode, setAutoMode] = useState(true);
  const [defaultModel, setDefaultModel] = useState("");

  // Position & dragging state for the top toggle controls (persist in localStorage)
  const [showSystemControls, setShowSystemControls] = useState(false); // Default to HIDDEN
  const [isTogglesMinimized, setIsTogglesMinimized] = useState(() => {
    try {
      const stored = localStorage.getItem("togglesMinimized");
      return stored ? JSON.parse(stored) : true; // Default to MINIMIZED (true)
    } catch {
      return true;
    }
  });
  const [togglePos, setTogglePos] = useState(() => {
    try {
      const raw = localStorage.getItem("toggleButtonsPos");
      return raw ? JSON.parse(raw) : { top: 12, left: 12 };
    } catch (e) {
      return { top: 12, left: 12 };
    }
  });
  const [isResizing, setIsResizing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [activeSystemTab, setActiveSystemTab] = useState("controls"); // controls, settings
  const dragRef = useRef({ startX: 0, startY: 0, origX: 0, origY: 0 });

  // Refs for panels and the toggle box so we can compute overlaps and auto-avoid
  const modelPanelRef = useRef(null);
  const agentPanelRef = useRef(null);
  const toggleRef = useRef(null);

  useEffect(() => {
    try {
      localStorage.setItem("toggleButtonsPos", JSON.stringify(togglePos));
    } catch (e) {}
  }, [togglePos]);

  useEffect(() => {
    try {
      localStorage.setItem(
        "togglesMinimized",
        JSON.stringify(isTogglesMinimized),
      );
    } catch (e) {}
  }, [isTogglesMinimized]);

  useEffect(() => {
    try {
      localStorage.setItem(
        "amigos-agent-pulse-minimized",
        JSON.stringify(agentPulseMinimized),
      );
    } catch (e) {}
  }, [agentPulseMinimized]);

  useEffect(() => {
    try {
      localStorage.setItem(
        "amigos-agent-pulse-pos",
        JSON.stringify(agentPulsePosition),
      );
    } catch (e) {}
  }, [agentPulsePosition]);

  useEffect(() => {
    function onKeyDown(e) {
      // Ctrl+Alt+S to toggle system controls
      if (e.ctrlKey && e.altKey && e.key.toLowerCase() === "s") {
        setShowSystemControls((prev) => !prev);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    function onMouseMove(e) {
      if (!isDragging) return;
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;
      setTogglePos((p) => ({
        top: Math.max(8, dragRef.current.origY + dy),
        left: Math.max(8, dragRef.current.origX + dx),
      }));
    }
    function onMouseUp() {
      setIsDragging(false);
    }
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [isDragging]);

  useEffect(() => {
    function onMouseMove(e) {
      if (!agentPulseDragging) return;
      const nextX = e.clientX - agentPulseDragOffset.x;
      const nextY = e.clientY - agentPulseDragOffset.y;
      const maxX = Math.max(8, window.innerWidth - 260);
      const maxY = Math.max(8, window.innerHeight - 200);
      setAgentPulsePosition({
        x: Math.max(8, Math.min(maxX, nextX)),
        y: Math.max(8, Math.min(maxY, nextY)),
      });
    }
    function onMouseUp() {
      if (agentPulseDragging) setAgentPulseDragging(false);
    }
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [agentPulseDragOffset, agentPulseDragging]);

  useEffect(() => {
    try {
      localStorage.setItem(
        "amigos-openwork-console-pos",
        JSON.stringify(openworkPosition),
      );
    } catch (e) {}
  }, [openworkPosition]);

  useEffect(() => {
    try {
      localStorage.setItem(
        "amigos-openwork-console-size",
        JSON.stringify(openworkSize),
      );
    } catch (e) {}
  }, [openworkSize]);

  useEffect(() => {
    function onMouseMove(e) {
      if (openworkIsDragging) {
        const nextX = e.clientX - openworkDragOffset.x;
        const nextY = e.clientY - openworkDragOffset.y;
        const maxX = Math.max(0, window.innerWidth - openworkSize.width);
        const maxY = Math.max(60, window.innerHeight - openworkSize.height);
        setOpenworkPosition({
          x: Math.max(0, Math.min(maxX, nextX)),
          y: Math.max(60, Math.min(maxY, nextY)),
        });
      }

      if (openworkIsResizing) {
        const minWidth = 720;
        const minHeight = 520;
        const rect = openworkRef.current?.getBoundingClientRect();
        if (!rect) return;
        const nextWidth = Math.max(minWidth, e.clientX - rect.left);
        const nextHeight = Math.max(minHeight, e.clientY - rect.top);
        const maxWidth = Math.max(minWidth, window.innerWidth - rect.left);
        const maxHeight = Math.max(minHeight, window.innerHeight - rect.top);
        setOpenworkSize({
          width: Math.min(maxWidth, nextWidth),
          height: Math.min(maxHeight, nextHeight),
        });
      }
    }

    function onMouseUp() {
      if (openworkIsDragging) setOpenworkIsDragging(false);
      if (openworkIsResizing) setOpenworkIsResizing(false);
    }

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [
    openworkDragOffset,
    openworkIsDragging,
    openworkIsResizing,
    openworkSize,
  ]);

  useEffect(() => {
    const handleResize = () => {
      setOpenworkPosition((prev) => {
        const maxX = Math.max(0, window.innerWidth - openworkSize.width);
        const maxY = Math.max(60, window.innerHeight - openworkSize.height);
        return {
          x: Math.max(0, Math.min(maxX, prev.x)),
          y: Math.max(60, Math.min(maxY, prev.y)),
        };
      });
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [openworkSize.height, openworkSize.width]);

  // Auto-avoid panels when they open: pick a corner that doesn't overlap open panels
  useEffect(() => {
    if (isDragging) return; // Don't auto-move while user is interacting
    const toggleEl = toggleRef.current;
    if (!toggleEl) return;

    const getPanels = () => {
      const panels = [];
      if (modelDashboardOpen && modelPanelRef.current)
        panels.push(modelPanelRef.current.getBoundingClientRect());
      if (agentCapabilitiesOpen && agentPanelRef.current)
        panels.push(agentPanelRef.current.getBoundingClientRect());
      return panels;
    };

    const panels = getPanels();
    if (panels.length === 0) return;

    const toggleRect = toggleEl.getBoundingClientRect();
    const overlapsAny = (rect) => {
      return panels.some(
        (p) =>
          !(
            rect.right < p.left ||
            rect.left > p.right ||
            rect.bottom < p.top ||
            rect.top > p.bottom
          ),
      );
    };

    if (!overlapsAny(toggleRect)) return; // already clear

    const margin = 24;
    const candidates = [
      { top: margin, left: margin },
      {
        top: margin,
        left: Math.max(margin, window.innerWidth - toggleRect.width - margin),
      },
      {
        top: Math.max(margin, window.innerHeight - toggleRect.height - margin),
        left: margin,
      },
      {
        top: Math.max(margin, window.innerHeight - toggleRect.height - margin),
        left: Math.max(margin, window.innerWidth - toggleRect.width - margin),
      },
    ];

    // find first candidate that doesn't overlap
    for (const c of candidates) {
      const r = {
        left: c.left,
        top: c.top,
        right: c.left + toggleRect.width,
        bottom: c.top + toggleRect.height,
      };
      if (!overlapsAny(r)) {
        setTogglePos({ top: c.top, left: c.left });
        return;
      }
    }

    // fallback: choose candidate with minimal overlap area
    let best = candidates[0];
    let bestOverlap = Number.POSITIVE_INFINITY;
    for (const c of candidates) {
      const r = {
        left: c.left,
        top: c.top,
        right: c.left + toggleRect.width,
        bottom: c.top + toggleRect.height,
      };
      let overlap = 0;
      for (const p of panels) {
        const xOverlap = Math.max(
          0,
          Math.min(r.right, p.right) - Math.max(r.left, p.left),
        );
        const yOverlap = Math.max(
          0,
          Math.min(r.bottom, p.bottom) - Math.max(r.top, p.top),
        );
        overlap += xOverlap * yOverlap;
      }
      if (overlap < bestOverlap) {
        bestOverlap = overlap;
        best = c;
      }
    }
    setTogglePos(best);
  }, [modelDashboardOpen, agentCapabilitiesOpen, isDragging]);

  const [quickToolsOpen, setQuickToolsOpen] = useState(false);
  const [aiSpeaking, setAiSpeaking] = useState(false);
  const [aiSpeechText, setAiSpeechText] = useState("");
  const [aiSpeechCharIndex, setAiSpeechCharIndex] = useState(0);
  const [aiSpeechWordIndex, setAiSpeechWordIndex] = useState(0);
  const [miniBrowserOpen, setMiniBrowserOpen] = useState(false);
  const [layoutLocked, setLayoutLocked] = useState(() => {
    try {
      const stored = localStorage.getItem("amigos-layout-locked");
      return stored ? JSON.parse(stored) : false;
    } catch {
      return false;
    }
  });

  // ═══════════════════════════════════════════════════════════════
  // BACKEND AUTO-DISCOVERY - Find backend even if port changes
  // Runs on mount and every 30s to handle dynamic port assignment
  // ═══════════════════════════════════════════════════════════════
  const [backendConnected, setBackendConnected] = useState(false);
  const [backendDiscovering, setBackendDiscovering] = useState(false);

  // Auto-discover backend on mount and periodically
  useEffect(() => {
    const runDiscovery = async () => {
      setBackendDiscovering(true);
      const discoveredUrl = await discoverBackendUrl();

      // Only update if different from current
      if (discoveredUrl !== apiUrl) {
        setApiUrl(discoveredUrl);
        localStorage.setItem(STORAGE_KEY, discoveredUrl);
        console.log(`📡 Backend auto-discovered: ${discoveredUrl}`);
      }

      // Verify connection
      const connected = await probeBackendUrl(discoveredUrl);
      setBackendConnected(connected);
      setBackendDiscovering(false);
    };

    runDiscovery();
    const interval = setInterval(runDiscovery, 30000); // Every 30 seconds
    return () => clearInterval(interval);
  }, []); // Only on mount, manages own state

  // ═══════════════════════════════════════════════════════════════
  // SECURITY SYSTEM - Monitor and verify security status
  // Owner: Darrell Buttigieg - All Rights Reserved
  // ═══════════════════════════════════════════════════════════════
  const [securityStatus, setSecurityStatus] = useState(null);
  const [securityPanelOpen, setSecurityPanelOpen] = useState(false);
  const [securityLoading, setSecurityLoading] = useState(false);
  const [memoryStatus, setMemoryStatus] = useState(null);

  // Fetch security status from backend
  const checkSecurityStatus = useCallback(async () => {
    if (!apiUrl) return;
    setSecurityLoading(true);
    try {
      const response = await axios.get(`${apiUrl}/security/status`);
      setSecurityStatus(response.data);
    } catch (err) {
      console.error("Security check failed:", err);
      setSecurityStatus({
        status: "UNKNOWN",
        status_color: "gray",
        security_score: 0,
        issues: ["Unable to connect to backend for security verification"],
        warnings: [],
        recommendations: [],
      });
    } finally {
      setSecurityLoading(false);
    }
  }, [apiUrl]);

  // Check security on mount and every 5 minutes
  useEffect(() => {
    checkSecurityStatus();
    const interval = setInterval(checkSecurityStatus, 300000); // 5 minutes
    return () => clearInterval(interval);
  }, [checkSecurityStatus]);

  const fetchMemoryStatus = useCallback(async () => {
    if (!apiUrl) return;
    try {
      const res = await axios.get(`${apiUrl}/system/memory`);
      setMemoryStatus(res.data);
    } catch (err) {
      setMemoryStatus({
        available: false,
        detail: err?.message || "Memory status unavailable",
      });
    }
  }, [apiUrl]);

  useEffect(() => {
    fetchMemoryStatus();
    const interval = setInterval(fetchMemoryStatus, 10000);
    return () => clearInterval(interval);
  }, [fetchMemoryStatus]);

  // ═══════════════════════════════════════════════════════════════
  // OLLAMA STATUS CHECK - Check if Ollie (local LLM) is available
  // ═══════════════════════════════════════════════════════════════
  const checkOllamaStatus = useCallback(async () => {
    if (!apiUrl) return;
    try {
      // Ensure apiUrl doesn't have a trailing slash
      const baseUrl = apiUrl.endsWith("/") ? apiUrl.slice(0, -1) : apiUrl;

      const response = await axios.get(`${baseUrl}/ollama/status`);
      const data = response.data;
      setOllamaStatus({
        running: data.ollama?.running ?? false,
        status: data.ollama?.status ?? "offline",
        models: data.ollama?.models ?? [],
        error: data.ollama?.error ?? null,
      });

      // Also fetch detailed models if Ollama is running
      if (data.ollama?.running) {
        const modelsResponse = await axios.get(`${baseUrl}/ollama/models`);
        if (modelsResponse.data?.success) {
          setOllamaModels(modelsResponse.data.data?.models ?? []);
        }
      }
    } catch (err) {
      console.log("Ollama check:", err.message);
      setOllamaStatus({
        running: false,
        status: "offline",
        models: [],
        error: "Cannot connect to Ollama",
      });
    }
  }, [apiUrl]);

  // Check Ollama status on mount and every 30 seconds
  useEffect(() => {
    checkOllamaStatus();
    const interval = setInterval(checkOllamaStatus, 30000); // 30 seconds
    return () => clearInterval(interval);
  }, [checkOllamaStatus]);

  // ═══════════════════════════════════════════════════════════════
  // LAYOUT PERSISTENCE SYSTEM - Save/Load console positions & states
  // ═══════════════════════════════════════════════════════════════
  const [layoutSaved, setLayoutSaved] = useState(false);
  const [layoutLoaded, setLayoutLoaded] = useState(false);

  // Save current layout to localStorage
  const saveLayout = () => {
    try {
      const layout = {
        // Console open states
        consoles: {
          mediaConsoleOpen,
          internetConsoleOpen,
          financeConsoleOpen,
          mapConsoleOpen,
          weatherConsoleOpen,
          scraperConsoleOpen,
          gameConsoleOpen,
          fileConsoleOpen,
          conversationToPostOpen,
          communicationsConsoleOpen,
          companyConsoleOpen,
          openworkConsoleOpen,
          aiAvatarOpen,

          modelDashboardOpen,
          agentCapabilitiesOpen,
          emailConsoleOpen,
        },
        // Chat position and size
        chat: {
          position: chatPosition,
          size: chatSize,
          minimized: chatMinimized,
        },
        // Settings
        settings: {
          autoMode,
          requireApproval,
          voiceEnabled,
          layoutLocked: true, // Always lock after saving
        },
        // Timestamp
        savedAt: new Date().toISOString(),
      };

      // Debug: Log what we're saving
      console.log("💾 Saving layout to localStorage:");
      console.log("   📍 Chat position:", chatPosition);
      console.log("   📐 Chat size:", chatSize);
      console.log("   🖥️ Consoles:", layout.consoles);

      localStorage.setItem("amigos-saved-layout", JSON.stringify(layout));

      // Verify it was saved
      const verify = localStorage.getItem("amigos-saved-layout");
      if (verify) {
        console.log(
          "✅ Layout saved successfully! Verify:",
          JSON.parse(verify).savedAt,
        );
      } else {
        console.error("❌ Layout failed to save to localStorage!");
      }

      setLayoutSaved(true);
      setTimeout(() => setLayoutSaved(false), 2000);
    } catch (err) {
      console.error("❌ Failed to save layout:", err);
      alert("Failed to save layout: " + err.message);
    }
  };

  // Load saved layout from localStorage
  const loadLayout = () => {
    try {
      const stored = localStorage.getItem("amigos-saved-layout");
      if (!stored) {
        console.log("No saved layout found");
        return false;
      }
      const layout = JSON.parse(stored);

      // Restore console states
      if (layout.consoles) {
        if (typeof layout.consoles.mediaConsoleOpen === "boolean")
          setMediaConsoleOpen(layout.consoles.mediaConsoleOpen);
        if (typeof layout.consoles.internetConsoleOpen === "boolean")
          setInternetConsoleOpen(layout.consoles.internetConsoleOpen);
        if (typeof layout.consoles.financeConsoleOpen === "boolean")
          setFinanceConsoleOpen(layout.consoles.financeConsoleOpen);
        if (typeof layout.consoles.mapConsoleOpen === "boolean")
          setMapConsoleOpen(layout.consoles.mapConsoleOpen);
        if (typeof layout.consoles.weatherConsoleOpen === "boolean")
          setWeatherConsoleOpen(layout.consoles.weatherConsoleOpen);
        if (typeof layout.consoles.scraperConsoleOpen === "boolean")
          setScraperConsoleOpen(layout.consoles.scraperConsoleOpen);
        if (typeof layout.consoles.gameConsoleOpen === "boolean")
          setGameConsoleOpen(layout.consoles.gameConsoleOpen);
        if (typeof layout.consoles.modelDashboardOpen === "boolean")
          setModelDashboardOpen(layout.consoles.modelDashboardOpen);
        if (typeof layout.consoles.agentCapabilitiesOpen === "boolean")
          setAgentCapabilitiesOpen(layout.consoles.agentCapabilitiesOpen);
        if (typeof layout.consoles.emailConsoleOpen === "boolean")
          setEmailConsoleOpen(layout.consoles.emailConsoleOpen);
        if (typeof layout.consoles.fileConsoleOpen === "boolean")
          setFileConsoleOpen(layout.consoles.fileConsoleOpen);
        if (typeof layout.consoles.conversationToPostOpen === "boolean")
          setConversationToPostOpen(layout.consoles.conversationToPostOpen);
        if (typeof layout.consoles.communicationsConsoleOpen === "boolean")
          setCommunicationsConsoleOpen(
            layout.consoles.communicationsConsoleOpen,
          );
        if (typeof layout.consoles.companyConsoleOpen === "boolean")
          setCompanyConsoleOpen(layout.consoles.companyConsoleOpen);
        if (typeof layout.consoles.openworkConsoleOpen === "boolean")
          setOpenWorkConsoleOpen(layout.consoles.openworkConsoleOpen);
        if (typeof layout.consoles.aiAvatarOpen === "boolean")
          setAiAvatarOpen(layout.consoles.aiAvatarOpen);
      }

      // Restore chat position and size
      if (layout.chat) {
        if (layout.chat.position) setChatPosition(layout.chat.position);
        if (layout.chat.size) setChatSize(layout.chat.size);
        if (typeof layout.chat.minimized === "boolean")
          setChatMinimized(layout.chat.minimized);
      }

      // Restore settings
      if (layout.settings) {
        if (typeof layout.settings.autoMode === "boolean")
          setAutoMode(layout.settings.autoMode);
        if (typeof layout.settings.requireApproval === "boolean")
          setRequireApproval(layout.settings.requireApproval);
        if (typeof layout.settings.voiceEnabled === "boolean")
          setVoiceEnabled(layout.settings.voiceEnabled);
        if (typeof layout.settings.layoutLocked === "boolean")
          setLayoutLocked(layout.settings.layoutLocked);
      }

      console.log("✅ Layout loaded!", layout);
      setLayoutLoaded(true);
      setTimeout(() => setLayoutLoaded(false), 2000);
      return true;
    } catch (err) {
      console.error("Failed to load layout:", err);
      return false;
    }
  };

  // Note: Layout is now loaded on initial render via lazy state initialization
  // The loadLayout function is kept for manual "Load" button functionality

  // Debug: Log saved layout on startup and verify state was applied
  useEffect(() => {
    const saved = getSavedLayout();
    console.log(
      "═══════════════════════════════════════════════════════════════",
    );
    console.log("🔧 LAYOUT SYSTEM DEBUG - STARTUP CHECK");
    console.log(
      "═══════════════════════════════════════════════════════════════",
    );

    if (saved) {
      console.log("📂 Saved layout found! Contents:");
      console.log(
        "   📍 Saved chat position:",
        JSON.stringify(saved.chat?.position),
      );
      console.log("   📐 Saved chat size:", JSON.stringify(saved.chat?.size));
      console.log("   🖥️ Saved consoles:", JSON.stringify(saved.consoles));
      console.log("   ⚙️ Saved settings:", JSON.stringify(saved.settings));
      console.log("   🕐 Saved at:", saved.savedAt);
    } else {
      console.log("❌ No saved layout found in localStorage - using defaults.");
      console.log(
        "   localStorage key 'amigos-saved-layout':",
        localStorage.getItem("amigos-saved-layout"),
      );
    }
    console.log(
      "═══════════════════════════════════════════════════════════════",
    );
  }, []);

  const [connectionState, setConnectionState] = useState({
    status: apiUrl ? "connecting" : "error",
    detail: apiUrl ? `Connecting to ${apiUrl}` : "Backend URL not configured",
  });
  const [healthTick, setHealthTick] = useState(0);
  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [isTyping, setIsTyping] = useState(false);

  // ═══════════════════════════════════════════════════════════════
  // LLM PROVIDER SELECTION - Like Copilot's model toggle
  // ═══════════════════════════════════════════════════════════════
  const [llmProviders, setLlmProviders] = useState([]);
  const [activeProvider, setActiveProvider] = useState("github");
  const [activeModel, setActiveModel] = useState("");
  const [providerModels, setProviderModels] = useState({});
  const [modelSelectorOpen, setModelSelectorOpen] = useState(false);
  const [providerLoading, setProviderLoading] = useState(false);
  const [providerValidation, setProviderValidation] = useState({});
  const [autonomyStatus, setAutonomyStatus] = useState({
    autonomyEnabled: false,
    autonomyMode: "off",
    requireConfirmation: false,
    killSwitch: false,
  });

  // API Key Settings (backend .env allowlist)
  const [apiKeyStatus, setApiKeyStatus] = useState({});
  const [apiKeyForm, setApiKeyForm] = useState({
    AMIGOS_API_KEY: "",
    PLAYWRIGHT_PROXY: "",
  });
  const [apiKeySaving, setApiKeySaving] = useState(false);
  const [apiKeyError, setApiKeyError] = useState("");
  const [apiKeyReveal, setApiKeyReveal] = useState({
    AMIGOS_API_KEY: false,
    PLAYWRIGHT_PROXY: false,
  });

  // Fetch available LLM providers
  const fetchProviders = useCallback(async () => {
    if (!apiUrl) return;
    try {
      const response = await axios.get(`${apiUrl}/agent/providers`);
      if (response.data) {
        setLlmProviders(response.data.providers || []);
        setActiveProvider(response.data.active_provider || "github");
        setActiveModel(response.data.active_model || "");
        // Reset validation states for providers
        setProviderValidation({});
      }
    } catch (err) {
      console.log("Provider fetch:", err.message);
    }
  }, [apiUrl]);

  const fetchEnvStatus = useCallback(async () => {
    if (!apiUrl) return;
    try {
      const response = await axios.get(`${apiUrl}/agent/env/status`);
      setApiKeyStatus(response.data?.keys || {});
    } catch (err) {
      console.log("Env status fetch:", err.message);
      setApiKeyStatus({});
    }
  }, [apiUrl]);

  const saveEnvKey = useCallback(
    async (key, value) => {
      if (!apiUrl) return;
      setApiKeySaving(true);
      setApiKeyError("");
      try {
        await axios.post(`${apiUrl}/agent/env/set`, {
          key,
          value: value ?? "",
        });
        await fetchEnvStatus();
      } catch (err) {
        setApiKeyError(err?.response?.data?.detail || err.message);
      } finally {
        setApiKeySaving(false);
      }
    },
    [apiUrl, fetchEnvStatus],
  );

  // Switch LLM provider
  const switchProvider = useCallback(
    async (providerId, model = null) => {
      if (!apiUrl) return;
      setProviderLoading(true);
      try {
        const body = { provider: providerId };
        if (model) body.model = model;
        const response = await axios.post(`${apiUrl}/agent/provider`, body);
        if (response.data?.success) {
          setActiveProvider(response.data.provider);
          setActiveModel(response.data.model);
          setModelSelectorOpen(false);
          console.log(
            `✅ Switched to ${response.data.provider}: ${response.data.model}`,
          );
        }
      } catch (err) {
        console.error("Provider switch failed:", err.message);
        alert(
          `Failed to switch provider: ${
            err.response?.data?.detail || err.message
          }`,
        );
      } finally {
        setProviderLoading(false);
      }
    },
    [apiUrl],
  );

  const refreshProviderModels = useCallback(
    async (providerId) => {
      if (!apiUrl) return;
      try {
        setProviderLoading(true);
        const response = await axios.get(
          `${apiUrl}/agent/provider/models/refresh`,
          { params: { provider: providerId } },
        );
        if (response.data) {
          setProviderModels((p) => ({
            ...p,
            [providerId]: response.data.supported_models || [],
          }));
          alert(
            `Models refreshed: ${(response.data.supported_models || [])
              .slice(0, 10)
              .join(", ")}`,
          );
        }
      } catch (err) {
        alert(`Refresh models failed: ${err.message}`);
      } finally {
        setProviderLoading(false);
      }
    },
    [apiUrl],
  );

  // Fetch providers on mount
  useEffect(() => {
    fetchProviders();
    const fetchAutonomyStatus = async () => {
      try {
        const res = await axios.get(`${apiUrl}/agent/autonomy`);
        if (res.data) {
          setAutonomyStatus(res.data);
          const mode = String(
            res.data.autonomyMode || res.data.autonomy_mode || "off",
          ).toLowerCase();
          const enabled = !res.data.killSwitch && mode !== "off";
          setAutoMode(enabled);
          if (typeof res.data.requireConfirmation === "boolean") {
            setRequireApproval(res.data.requireConfirmation);
          }
        }
      } catch (e) {}
    };
    fetchAutonomyStatus();
    const interval = setInterval(fetchProviders, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [fetchProviders]);

  useEffect(() => {
    fetchEnvStatus();
  }, [fetchEnvStatus]);

  // Fetch models for active provider when it changes
  useEffect(() => {
    (async () => {
      if (!apiUrl || !activeProvider) return;
      try {
        const res = await axios.get(`${apiUrl}/agent/provider/models`, {
          params: { provider: activeProvider },
        });
        if (res.data && res.data.supported_models) {
          setProviderModels((p) => ({
            ...p,
            [activeProvider]: res.data.supported_models,
          }));
        }
      } catch (e) {
        // ignore
      }
    })();
  }, [apiUrl, activeProvider]);

  // ═══════════════════════════════════════════════════════════════
  // CANVAS COMMAND POLLING - Agent to Canvas Communication
  // ═══════════════════════════════════════════════════════════════
  useEffect(() => {
    if (!canvasOpen) return;

    const pollCommands = async () => {
      try {
        let url = canvasSession
          ? `http://127.0.0.1:65252/canvas/session/${canvasSession}/agent/pending`
          : `http://127.0.0.1:65252/canvas/agent/queue`;
        const response = await fetch(url);
        if (response.ok) {
          const data = await response.json();
          if (Array.isArray(data)) {
            if (data.length > 0) {
              console.log("🎨 Got Canvas pending commands:", data.length);
              setCanvasCommands(data);
            }
          } else if (data.commands && data.commands.length > 0) {
            // fallback for global queue
            setCanvasCommands(data.commands);
            // Clear the backend queue after fetching
            fetch("http://127.0.0.1:65252/canvas/agent/clear", {
              method: "POST",
            }).catch(() => {});
          }
        }
      } catch (error) {
        // Silent - backend might not be running
      }
    };

    const interval = setInterval(pollCommands, 1000);
    pollCommands();
    return () => clearInterval(interval);
  }, [canvasOpen, canvasSession]);

  // ═══════════════════════════════════════════════════════════════
  // UI COMMAND POLLING - Agent to GUI Communication
  // ═══════════════════════════════════════════════════════════════
  useEffect(() => {
    let lastPollTime = Date.now() / 1000;

    const pollUiEvents = async () => {
      try {
        const response = await axios.get(`${apiUrl}/ui/events`, {
          params: { since: lastPollTime },
        });

        if (response.data?.events?.length > 0) {
          response.data.events.forEach((event) => {
            console.log("🖥️ UI Event received:", event);

            if (event.type === "open_console") {
              if (event.data.console === "weather") setWeatherConsoleOpen(true);
              if (event.data.console === "finance") setFinanceConsoleOpen(true);
              if (event.data.console === "internet")
                setInternetConsoleOpen(true);
            }

            // Update last poll time to the timestamp of the last event processed
            if (event.timestamp > lastPollTime) lastPollTime = event.timestamp;
          });
        }
      } catch (err) {
        // silent
      }
    };

    const interval = setInterval(pollUiEvents, 2000);
    return () => clearInterval(interval);
  }, [apiUrl]);

  // ═══════════════════════════════════════════════════════════════
  // OLLAMA STATUS - Local LLM Integration (Ollie the Assistant)
  // ═══════════════════════════════════════════════════════════════
  const [ollamaStatus, setOllamaStatus] = useState({
    running: false,
    status: "checking",
    models: [],
    error: null,
  });
  const [ollamaModels, setOllamaModels] = useState([]);
  const [selectedOllamaModel, setSelectedOllamaModel] = useState("qwen2.5:7b");
  const [teamModeEnabled, setTeamModeEnabled] = useState(false); // Amigos + Ollie working together

  // ═══════════════════════════════════════════════════════════════
  // SHARED MEMORY - Local memory shared between Amigos and Ollie
  // ═══════════════════════════════════════════════════════════════
  const [memoryStats, setMemoryStats] = useState({
    conversations: 0,
    facts: 0,
    tasks: 0,
    knowledge: 0,
  });

  // ═══════════════════════════════════════════════════════════════
  // AGENT TEAM - Multi-Agent Coordination System
  // ═══════════════════════════════════════════════════════════════
  const [agentTeam, setAgentTeam] = useState({
    agents: {
      amigos: {
        name: "Agent Amigos",
        emoji: "🤖",
        color: "#8b5cf6",
        status: "idle",
        current_task: null,
      },
      ollie: {
        name: "Ollie",
        emoji: "🦙",
        color: "#22c55e",
        status: "offline",
        current_task: null,
      },
      scrapey: {
        name: "Scrapey",
        emoji: "🕷️",
        color: "#f97316",
        status: "offline",
        current_task: null,
      },
      trainer: {
        name: "Trainer",
        emoji: "🎮",
        color: "#ef4444",
        status: "offline",
        current_task: null,
      },
      media: {
        name: "Media Bot",
        emoji: "🎬",
        color: "#3b82f6",
        status: "offline",
        current_task: null,
      },
    },
    summary: { total_agents: 5, online: 1, working: 0 },
  });
  const [agentTeamUpdatedAt, setAgentTeamUpdatedAt] = useState(null);

  // Fetch agent team status
  const fetchAgentTeam = useCallback(async () => {
    if (!apiUrl) return;
    try {
      const response = await axios.get(`${apiUrl}/agents/team`);
      if (response.data?.success) {
        setAgentTeam(response.data.data);
        setAgentTeamUpdatedAt(Date.now());
      }
    } catch (err) {
      console.debug("Agent team:", err.message);
    }
  }, [apiUrl]);

  // Check agent team status on a reasonable schedule.
  // - Default: every 5s for low noise
  // - If team panel is open OR there are active agents, poll every 1s for responsiveness
  useEffect(() => {
    let active = true;
    let timer = null;
    const schedule = async () => {
      if (!active) return;
      await fetchAgentTeam();
      // Use setAgentTeam's state or a simplified logic to avoid dependency loop
      timer = setTimeout(schedule, teamPanelOpen ? 1000 : 5000);
    };
    schedule();
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [fetchAgentTeam, teamPanelOpen]);

  // ═══════════════════════════════════════════════════════════════
  // DEMO MODE - Multi-Agent Team Demo (Facebook Post Demo)
  // ═══════════════════════════════════════════════════════════════
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoProgress, setDemoProgress] = useState(null);
  const [demoResult, setDemoResult] = useState(null);

  // Start the Facebook post demo
  const startFacebookPostDemo = async () => {
    if (!apiUrl || demoRunning) return;
    setDemoRunning(true);
    setDemoProgress(null);
    setDemoResult(null);

    try {
      // Start the demo
      await axios.post(`${apiUrl}/agents/demo/facebook-post`);

      // Poll for progress every 500ms
      const progressInterval = setInterval(async () => {
        try {
          const res = await axios.get(`${apiUrl}/agents/demo/progress`);
          if (res.data?.success) {
            const progress = res.data.data;

            // Map backend format to frontend display format
            const mappedProgress = {
              current_step: progress.current_step || 0,
              total_steps: progress.total_steps || 8,
              steps_completed: (progress.steps || []).map(
                (s) => `${s.agent}: ${s.task}`,
              ),
              current_activity:
                progress.steps?.length > 0
                  ? `${progress.steps[
                      progress.steps.length - 1
                    ]?.agent?.toUpperCase()} using ${
                      progress.steps[progress.steps.length - 1]?.tool
                    }`
                  : "Starting demo...",
              completed: progress.status === "complete",
            };

            setDemoProgress(mappedProgress);

            if (progress.status === "complete") {
              clearInterval(progressInterval);
              setDemoRunning(false);
              if (progress.result?.post_content) {
                setDemoResult(progress.result.post_content);
              }
            }
          }
        } catch (err) {
          console.debug("Demo progress:", err.message);
        }
      }, 500);

      // Safety timeout after 45 seconds
      setTimeout(() => {
        clearInterval(progressInterval);
        setDemoRunning(false);
      }, 45000);
    } catch (err) {
      console.error("Demo error:", err);
      setDemoRunning(false);
    }
  };

  // Reset demo
  const resetDemo = async () => {
    if (apiUrl) {
      try {
        await axios.post(`${apiUrl}/agents/demo/reset`);
      } catch (err) {
        console.debug("Reset demo:", err.message);
      }
    }
    setDemoProgress(null);
    setDemoResult(null);
    setDemoRunning(false);
  };

  // Helper to log conversations to shared memory (fire and forget)
  const logToMemory = useCallback(
    async (role, content, agent = "amigos") => {
      if (!apiUrl) return;
      try {
        await axios.post(`${apiUrl}/memory/conversation`, {
          role,
          content,
          agent,
        });
      } catch (err) {
        // Silent fail - memory logging shouldn't break the UI
        console.debug("Memory log:", err.message);
      }
    },
    [apiUrl],
  );

  // Fetch memory stats periodically
  const fetchMemoryStats = useCallback(async () => {
    if (!apiUrl) return;
    try {
      const response = await axios.get(`${apiUrl}/memory/stats`);
      if (response.data?.success) {
        setMemoryStats(response.data.data);
      }
    } catch (err) {
      console.debug("Memory stats:", err.message);
    }
  }, [apiUrl]);

  // Check shared memory stats on mount and every 60 seconds
  useEffect(() => {
    fetchMemoryStats();
    const interval = setInterval(fetchMemoryStats, 60000);
    return () => clearInterval(interval);
  }, [fetchMemoryStats]);

  // ═══════════════════════════════════════════════════════════════
  // CHAT POSITION & SIZE - Must be defined before saveLayout function
  // ═══════════════════════════════════════════════════════════════
  const [chatPosition, setChatPosition] = useState(() => {
    const saved = savedLayout?.chat?.position;
    // Ensure chat is never off-screen (minimum y: 60px from top)
    if (saved) {
      return { x: Math.max(0, saved.x), y: Math.max(60, saved.y) };
    }
    return { x: window.innerWidth - 520, y: 80 };
  });
  const [chatSize, setChatSize] = useState(() => {
    return savedLayout?.chat?.size ?? { width: 480, height: 600 };
  });
  const [chatMinimized, setChatMinimized] = useState(() => {
    return savedLayout?.chat?.minimized ?? false;
  });
  const [isChatDragging, setIsChatDragging] = useState(false);
  const [isChatResizing, setIsChatResizing] = useState(false);
  const [chatDragOffset, setChatDragOffset] = useState({ x: 0, y: 0 });
  const chatRef = useRef(null);

  // ═══════════════════════════════════════════════════════════════
  // WINDOW RESIZE HANDLER - Ensure components stay on screen
  // ═══════════════════════════════════════════════════════════════
  useEffect(() => {
    const handleResize = () => {
      // Adjust chat position if it's now off-screen
      setChatPosition((prev) => {
        const newX = Math.max(
          0,
          Math.min(window.innerWidth - chatSize.width, prev.x),
        );
        const newY = Math.max(
          60,
          Math.min(window.innerHeight - chatSize.height, prev.y),
        );
        if (newX !== prev.x || newY !== prev.y) {
          return { x: newX, y: newY };
        }
        return prev;
      });
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [chatSize.width, chatSize.height]);

  // File attachment state for chat analysis
  const [attachedFile, setAttachedFile] = useState(null); // { name, content, info }
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const fileInputRef = useRef(null);

  // 🔊 VOICE OUTPUT
  // Voice is intentionally conservative:
  // - OFF: never speak
  // - SUMMARY: speak only when user explicitly asks to speak/read OR when the user used the mic
  // - FULL: same triggers as SUMMARY, but speak full response
  const VOICE_MODE_KEY = "amigos-voice-mode";
  const LEGACY_VOICE_ENABLED_KEY = "amigos-voice-enabled";
  const [voiceMode, setVoiceMode] = useState(() => {
    try {
      const storedMode = localStorage.getItem(VOICE_MODE_KEY);
      if (
        storedMode === "off" ||
        storedMode === "summary" ||
        storedMode === "full"
      ) {
        return storedMode;
      }

      // Back-compat: older builds stored a boolean.
      const legacy = localStorage.getItem(LEGACY_VOICE_ENABLED_KEY);
      if (legacy !== null) {
        return JSON.parse(legacy) ? "summary" : "off";
      }
      return "off";
    } catch {
      return "off";
    }
  });

  const voiceEnabled = voiceMode !== "off";

  const ALWAYS_READ_FULL_KEY = "amigos-always-read-full";
  const [alwaysReadFull, setAlwaysReadFull] = useState(() => {
    try {
      return localStorage.getItem(ALWAYS_READ_FULL_KEY) === "true";
    } catch {
      return false;
    }
  });

  // Save voice preference
  useEffect(() => {
    try {
      localStorage.setItem(VOICE_MODE_KEY, voiceMode);
      localStorage.setItem(ALWAYS_READ_FULL_KEY, alwaysReadFull);
      // Keep legacy key updated so old layout saves still work.
      localStorage.setItem(
        LEGACY_VOICE_ENABLED_KEY,
        JSON.stringify(voiceEnabled),
      );
    } catch {
      // ignore
    }
  }, [voiceMode, voiceEnabled, alwaysReadFull]);

  const cycleVoiceMode = useCallback(() => {
    setVoiceMode((prev) => {
      if (prev === "off") return "summary";
      if (prev === "summary") return "full";
      return "off";
    });
  }, []);

  // Support existing code paths that expect a boolean setter (e.g., layout restore).
  const setVoiceEnabled = useCallback(
    (enabled) => {
      setVoiceMode((prev) => {
        if (!enabled) return "off";
        // If enabling from OFF, default to SUMMARY.
        return prev === "off" ? "summary" : prev;
      });
    },
    [setVoiceMode],
  );

  // Prime speech synthesis voices (some browsers load voices lazily)
  useEffect(() => {
    if (typeof window === "undefined" || !window.speechSynthesis) return;

    const loadVoices = () => {
      try {
        window.speechSynthesis.getVoices();
      } catch {
        // ignore
      }
    };

    loadVoices();
    window.speechSynthesis.onvoiceschanged = loadVoices;
    return () => {
      try {
        window.speechSynthesis.onvoiceschanged = null;
      } catch {
        // ignore
      }
    };
  }, []);

  // Track whether the most recent user turn came from the microphone.
  const lastInputWasVoiceRef = useRef(false);

  const userRequestedSpeech = (text) => {
    const t = (text || "").toLowerCase();
    return /\b(read( it)? aloud|say( it)?|speak( it)?|talk to me|voice reply|read this)\b/.test(
      t,
    );
  };

  const userRequestedFullRead = (text) => {
    const t = (text || "").toLowerCase();
    return /\b(read (it |that |this )?(in )?full|read (the )?(whole|entire|complete|full) (reply|response|answer)|read (it |that )?all|read everything)\b/.test(
      t,
    );
  };

  const isQuestionLike = (text) => {
    const t = (text || "").trim();
    if (!t) return false;
    if (t.endsWith("?")) return true;
    return /^(what|why|how|when|where|who|which|can you|could you|would you|do you|is it|are you|did you|should we|tell me|explain|give me|summarize)\b/i.test(
      t,
    );
  };

  const toSpokenSummary = (text) => {
    const cleaned = (text || "")
      .replace(/[*_~`#]/g, "")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
      .replace(/https?:\/\/\S+/g, "")
      .replace(/<[^>]*>/g, "")
      .replace(/\s+/g, " ")
      .trim();

    if (!cleaned) return "";

    // Keep it short: 1–2 sentences or ~240 chars.
    const sentences = cleaned.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [cleaned];
    const short = sentences.slice(0, 2).join(" ").trim();
    if (short.length <= 260) return short;
    return short.slice(0, 240).trimEnd() + "…";
  };

  const getSpeechText = ({ userText, assistantText, wasVoice }) => {
    if (!voiceEnabled) return null;

    // Check if user explicitly requested full reading
    const readInFull = userRequestedFullRead(userText);

    // If user says "read in full" or similar, or if alwaysReadFull is enabled, always read everything
    if (readInFull || alwaysReadFull) {
      return assistantText || "";
    }

    // Speak policy:
    // - Provide polite voice replies after each command or question
    // - SUMMARY: read a short summary for all responses
    // - FULL: read full text when explicitly requested, otherwise summary
    const explicit = userRequestedSpeech(userText);

    // Always provide voice reply when voice mode is enabled
    if (voiceMode === "full") {
      return explicit ? assistantText || "" : toSpokenSummary(assistantText);
    }

    // SUMMARY mode - provide polite summary for all responses
    return toSpokenSummary(assistantText);
  };

  // Best-effort unlock for speech/audio policies: attempt a tiny utterance on first user gesture.
  useEffect(() => {
    if (typeof window === "undefined" || !window.speechSynthesis) return;
    const unlock = () => {
      try {
        const u = new SpeechSynthesisUtterance(" ");
        u.volume = 0;
        window.speechSynthesis.speak(u);
        window.speechSynthesis.cancel();
      } catch {
        // ignore
      }
    };
    window.addEventListener("pointerdown", unlock, { once: true });
    return () => window.removeEventListener("pointerdown", unlock);
  }, []);

  // ═══════════════════════════════════════════════════════════════
  // SCREEN AWARENESS SYSTEM - Agent Amigos can "see" console data
  // This allows her to discuss what's visible on screen!
  // ═══════════════════════════════════════════════════════════════
  const [screenContext, setScreenContext] = useState({
    finance: { cryptoData: [], stockData: [], watchlist: [], analysis: null },
    game: { activeGame: null, cheats: [], memoryScans: [] },
    scraper: { lastUrl: "", lastResult: "", generatedPost: "" },
    files: { currentPath: "", files: [], selectedFile: null },
    internet: { lastQuery: "", results: [], searchType: "web" },
    map: { location: "", markers: [] },
    weather: {
      location: null,
      resolvedPlace: null,
      units: "metric",
      forecastDays: 7,
      loading: false,
      error: null,
      current: null,
      daily: null,
      fetchedAt: null,
    },
    media: {
      isPlaying: false,
      currentTrack: null,
      playlist: [],
      mediaLibrary: {},
    },
  });

  // Function for consoles to update their screen context
  const updateScreenContext = useCallback((consoleName, data) => {
    setScreenContext((prev) => ({
      ...prev,
      [consoleName]: { ...prev[consoleName], ...data },
    }));
  }, []);

  // Stable callbacks for each console to prevent infinite re-renders
  const updateMediaContext = useCallback(
    (data) => updateScreenContext("media", data),
    [updateScreenContext],
  );
  const updateScraperContext = useCallback(
    (data) => updateScreenContext("scraper", data),
    [updateScreenContext],
  );
  const updateFinanceContext = useCallback(
    (data) => updateScreenContext("finance", data),
    [updateScreenContext],
  );
  const updateGameContext = useCallback(
    (data) => updateScreenContext("game", data),
    [updateScreenContext],
  );
  const updateFilesContext = useCallback(
    (data) => updateScreenContext("files", data),
    [updateScreenContext],
  );
  const updateWeatherContext = useCallback(
    (data) => updateScreenContext("weather", data),
    [updateScreenContext],
  );
  const updateMapContext = useCallback(
    (data) => updateScreenContext("map", data),
    [updateScreenContext],
  );
  const updateInternetContext = useCallback(
    (data) => updateScreenContext("internet", data),
    [updateScreenContext],
  );

  // Fetch Auto Mode status
  useEffect(() => {
    if (!apiUrl) return;
    axios
      .get(`${apiUrl}/agent/auto_mode`)
      .then((res) => setAutoMode(res.data.auto_mode))
      .catch((err) => console.error("Failed to fetch auto mode", err));
  }, [apiUrl]);

  const toggleAutoMode = async () => {
    if (!apiUrl) return;
    try {
      const newMode = !autoMode;
      const { data } = await axios.post(`${apiUrl}/agent/auto_mode`, {
        enabled: newMode,
      });
      setAutoMode(data.auto_mode);
      if (data.auto_mode) {
        setRequireApproval(false);
      }
      setMessages((prev) => [
        ...prev,
        {
          role: "system",
          content: `🔄 ${data.message}`,
        },
      ]);
    } catch (error) {
      console.error("Failed to toggle auto mode", error);
    }
  };

  // Get default LLM model from backend
  useEffect(() => {
    const fetchDefaultModel = async () => {
      try {
        const res = await axios.get(`${apiUrl}/agent/default_model`);
        if (res?.data?.default_model) setDefaultModel(res.data.default_model);
      } catch (err) {
        console.debug("Could not fetch default model", err.message);
      }
    };
    fetchDefaultModel();
  }, [apiUrl]);

  // Compute connection status display based on current state
  const connectionMeta =
    connectionMetaMap[connectionState.status] || connectionMetaMap.connecting;

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({
        behavior: "smooth",
        block: "end",
      });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const interval = setInterval(
      () => setHealthTick((tick) => tick + 1),
      30000,
    );
    return () => clearInterval(interval);
  }, []);

  // Keep backend health/connection state fresh
  useEffect(() => {
    if (!apiUrl) {
      setConnectionState({
        status: "error",
        detail: "Backend URL not configured",
      });
      setToolsAvailable(0);
      return;
    }

    let cancelled = false;
    setConnectionState({
      status: "connecting",
      detail: `Connecting to ${apiUrl}`,
    });

    axios
      .get(`${apiUrl}/health`, { timeout: 5000 })
      .then((res) => {
        if (cancelled) return;
        setToolsAvailable(res.data.tools_available || 0);
        const isReady =
          res.data.llm_ready !== undefined ? res.data.llm_ready : true;
        setConnectionState({
          status: isReady ? "online" : "degraded",
          detail: isReady
            ? `Model: ${res.data.model || "unknown"}`
            : res.data.llm_detail
              ? res.data.llm_detail
              : "LLM endpoint not responding",
        });
      })
      .catch((error) => {
        if (cancelled) return;
        setToolsAvailable(0);
        setConnectionState({ status: "error", detail: error.message });
      });

    return () => {
      cancelled = true;
    };
  }, [apiUrl, healthTick]);

  const promptForApiUrl = () => {
    const next = window.prompt(
      "Enter the Agent Amigos backend URL",
      apiUrl || "http://127.0.0.1:65252",
    );
    if (next === null) return;
    const normalized = sanitizeUrl(next);
    if (!normalized) {
      setMessages((prev) => [
        ...prev,
        {
          role: "system",
          content: "Invalid URL. Example: http://127.0.0.1:65252",
        },
      ]);
      return;
    }
    window.localStorage.setItem(STORAGE_KEY, normalized);
    setApiUrl(normalized);
    setHealthTick((tick) => tick + 1);
  };

  const resetApiUrl = () => {
    window.localStorage.removeItem(STORAGE_KEY);
    const fallback = deriveDefaultApiUrl();
    setApiUrl(fallback);
    setHealthTick((tick) => tick + 1);
  };

  // --- Voice Output (Text-to-Speech) with AI Avatar Animation ---
  const speak = useCallback(
    (text) => {
      if (!window.speechSynthesis) return;
      if (!voiceEnabled) return; // Voice is disabled

      // Cancel any current speech to ensure immediate response
      window.speechSynthesis.cancel();

      // Don't speak internal system notifications
      if (
        !text ||
        text.startsWith("[") ||
        text.startsWith("✓") ||
        text.startsWith("⚠")
      )
        return;

      // Clean text for speech (remove markdown, symbols, emojis)
      const spokenText = text
        .replace(/[*_~`#]/g, "") // Remove markdown symbols
        .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1") // Convert links [text](url) to text
        .replace(/https?:\/\/\S+/g, "") // Remove raw URLs
        .replace(/<[^>]*>/g, "") // Remove HTML tags
        .replace(
          /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}]/gu,
          "",
        ) // Remove common emojis
        .replace(/\s+/g, " ")
        .trim();

      if (!spokenText) return; // Don't speak empty text after cleaning

      // Helper function to select voice
      const selectVoice = () => {
        const voices = window.speechSynthesis.getVoices();
        if (voices.length === 0) return null;

        // Simple heuristic to detect Tagalog/Filipino content
        const isTagalog =
          /\b(ang|ng|sa|na|po|opo|hindi|wala|ako|ikaw|siya|tayo|kami|kayo|sila|ni|kay|may|mayroon|magandang|araw|salamat)\b/i.test(
            spokenText,
          );

        let selectedVoice = null;

        if (isTagalog) {
          // Prioritize Filipino voices
          selectedVoice = voices.find(
            (v) =>
              v.lang.includes("fil") ||
              v.lang.includes("tl") ||
              v.name.toLowerCase().includes("filipino") ||
              v.name.toLowerCase().includes("tagalog"),
          );
        }

        if (!selectedVoice) {
          // Fallback to preferred female English voices
          selectedVoice =
            voices.find(
              (v) =>
                v.name.toLowerCase().includes("female") ||
                v.name.toLowerCase().includes("samantha") ||
                v.name.toLowerCase().includes("zira") ||
                v.name.toLowerCase().includes("hazel") ||
                v.name.toLowerCase().includes("susan") ||
                v.name.toLowerCase().includes("victoria") ||
                v.name.includes("Google UK English Female") ||
                v.name.includes("Microsoft Zira"),
            ) ||
            voices.find((v) => v.lang.startsWith("en")) ||
            null;
        }

        return selectedVoice;
      };

      // Attempt speech with retry on voice loading
      const attemptSpeak = (retryCount = 0) => {
        // Trigger AI Avatar speaking animation
        setAiSpeaking(true);
        setAiSpeechText(spokenText);
        setAiSpeechCharIndex(0);
        setAiSpeechWordIndex(0);

        const utterance = new SpeechSynthesisUtterance(spokenText);
        const selectedVoice = selectVoice();

        if (selectedVoice) {
          utterance.voice = selectedVoice;
          utterance.lang = selectedVoice.lang;
        } else {
          utterance.lang = "en-US";

          // If no voices loaded and haven't retried, wait for voices to load
          if (retryCount === 0) {
            const voicesChangedHandler = () => {
              window.speechSynthesis.removeEventListener(
                "voiceschanged",
                voicesChangedHandler,
              );
              attemptSpeak(1); // Retry once after voices load
            };
            window.speechSynthesis.addEventListener(
              "voiceschanged",
              voicesChangedHandler,
            );

            // Timeout fallback - proceed without voice selection after 500ms
            setTimeout(() => {
              window.speechSynthesis.removeEventListener(
                "voiceschanged",
                voicesChangedHandler,
              );
              if (window.speechSynthesis.speaking) return; // Already speaking
              attemptSpeak(2); // Force speak with default voice
            }, 500);
            return;
          }
        }

        utterance.volume = 1;
        utterance.pitch = 1.0; // Neutral pitch for better clarity
        utterance.rate = 0.85; // Slower rate for better pronunciation and understanding

        // 🌌 Spiritual & Symbolic Insight Voice Adjustment
        if (amigosSkill === "spiritual_symbolic_insight") {
          utterance.rate = 0.75; // Slightly slower for reflective tone
          utterance.pitch = 0.95; // Slightly lower/softer pitch
        }

        // When speech ends, stop the avatar animation
        utterance.onstart = () => {
          setAiSpeaking(true);
        };

        utterance.onboundary = (event) => {
          // Best-effort sync: not all browsers fire boundary events reliably.
          try {
            const idx =
              typeof event.charIndex === "number" && event.charIndex >= 0
                ? event.charIndex
                : 0;
            setAiSpeechCharIndex(idx);
            const prefix = spokenText.slice(0, idx);
            const normalized = prefix.replace(/\s+/g, " ").trim();
            const wordCount = normalized ? normalized.split(" ").length : 0;
            setAiSpeechWordIndex(Math.max(0, wordCount - 1));
          } catch {
            // ignore
          }
        };

        utterance.onend = () => {
          setAiSpeaking(false);
          setAiSpeechCharIndex(0);
          setAiSpeechWordIndex(0);
        };

        utterance.onerror = (event) => {
          console.error("Speech synthesis error:", event);
          setAiSpeaking(false);
          setAiSpeechCharIndex(0);
          setAiSpeechWordIndex(0);

          // Retry on certain errors if haven't retried yet
          if (
            retryCount < 2 &&
            (event.error === "network" || event.error === "synthesis-failed")
          ) {
            setTimeout(() => attemptSpeak(retryCount + 1), 100);
          }
        };

        // Defer speak to avoid cancel/speak timing issues
        setTimeout(() => {
          try {
            // Double-check that synthesis is ready and not already speaking
            if (window.speechSynthesis.paused) {
              window.speechSynthesis.resume();
            }
            if (!window.speechSynthesis.speaking) {
              window.speechSynthesis.speak(utterance);
            }
          } catch (err) {
            console.error("Failed to speak:", err);
            setAiSpeaking(false);
            setAiSpeechCharIndex(0);
            setAiSpeechWordIndex(0);
          }
        }, 50); // Slightly longer delay for more reliable execution
      };

      // Start speech attempt
      attemptSpeak();
    },
    [voiceEnabled],
  );

  // --- Stop Everything (Speech, Requests, Processing) ---
  const stopEverything = () => {
    // Stop speech synthesis
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    // Stop AI Avatar animation
    setAiSpeaking(false);
    setAiSpeechText("");
    setAiSpeechCharIndex(0);
    setAiSpeechWordIndex(0);
    // Abort any pending HTTP request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    // Reset states
    setIsProcessing(false);
    setIsListening(false);
    setStatus("Ready");
    setMessages((prev) => [
      ...prev,
      { role: "system", content: "🛑 Stopped." },
    ]);
  };

  // --- Voice Input (Speech-to-Text) ---
  const startListening = () => {
    // Stop any ongoing speech immediately when user wants to talk
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setAiSpeaking(false);

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setMessages((prev) => [
        ...prev,
        { role: "system", content: "Speech recognition not available." },
      ]);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = voiceLang;

    recognition.onstart = () => {
      setIsListening(true);
      setStatus("🎤 Listening...");
    };

    recognition.onresult = (event) => {
      let interimTranscript = "";
      let finalTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }

      if (finalTranscript) {
        setInput(finalTranscript);
        lastInputWasVoiceRef.current = true;
        setTimeout(() => sendMessage(finalTranscript), 100);
      } else if (interimTranscript) {
        setInput(interimTranscript);
        setStatus(`🎤 Hearing: "${interimTranscript}..."`);
      }
    };

    recognition.onerror = (event) => {
      if (event.error === "network") {
        setMessages((prev) => [
          ...prev,
          {
            role: "system",
            content:
              "Voice requires internet. Try typing or use Chrome browser.",
          },
        ]);
      }
      setStatus("Ready");
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
      setStatus("Ready");
    };

    try {
      recognition.start();
    } catch (err) {
      console.error("Speech recognition start error:", err);
      setIsListening(false);
    }
  };

  // --- Approve Pending Action ---
  const approveAction = async () => {
    if (!pendingAction) return;
    if (!apiUrl) {
      setMessages((prev) => [
        ...prev,
        {
          role: "system",
          content: "Set the backend URL before approving actions.",
        },
      ]);
      return;
    }

    setStatus("⚡ Executing...");
    setMessages((prev) => [
      ...prev,
      {
        role: "action",
        content: `✓ Approved: ${pendingAction.tool}`,
        approved: true,
      },
    ]);

    try {
      const response = await axios.post(
        `${apiUrl}/approve_action`,
        pendingAction,
        { timeout: 120000 }, // 2 minutes for browser automation
      );
      const result = response.data.result;

      setMessages((prev) => [
        ...prev,
        {
          role: "action",
          content: `✓ ${pendingAction.tool} completed`,
          result: JSON.stringify(result, null, 2),
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "system", content: `Error: ${error.message}` },
      ]);
    }

    setPendingAction(null);
    setStatus("Ready");
  };

  // --- Reject Pending Action ---
  const rejectAction = () => {
    setMessages((prev) => [
      ...prev,
      {
        role: "action",
        content: `✗ Cancelled: ${pendingAction?.tool}`,
        rejected: true,
      },
    ]);
    setPendingAction(null);
    setStatus("Ready");
  };

  // --- Handle File Attachment for Analysis ---
  const handleFileAttachment = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploadingFile(true);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await axios.post(
        `${apiUrl}/file/upload-for-analysis`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
          timeout: 60000,
        },
      );

      if (response.data.success) {
        setAttachedFile({
          name: response.data.filename,
          content: response.data.content,
          info: response.data.file_info,
          truncated: response.data.truncated,
        });
        setMessages((prev) => [
          ...prev,
          {
            role: "system",
            content: `📎 File attached: ${response.data.filename} (${
              response.data.file_info?.line_count || 0
            } lines, ${response.data.file_info?.size_bytes || 0} bytes)${
              response.data.truncated ? " - Content truncated for analysis" : ""
            }`,
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: "system",
            content: `❌ Failed to attach file: ${response.data.error}`,
          },
        ]);
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "system", content: `❌ File upload error: ${error.message}` },
      ]);
    } finally {
      setIsUploadingFile(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  // --- Send Message ---
  const sendMessage = async (manualInput = null) => {
    let textToSend = manualInput || input;
    if (!textToSend.trim() && !attachedFile) return;

    const wasVoice = lastInputWasVoiceRef.current;
    lastInputWasVoiceRef.current = false;

    // AI Voice Correction - Fix STT errors before processing
    if (wasVoice && textToSend.trim().length > 3) {
      try {
        setStatus("🧠 Correcting voice...");
        const fixResp = await axios.post(`${apiUrl}/agent/voice/fix`, null, {
          params: { transcript: textToSend },
        });
        if (fixResp.data.changed) {
          console.log(
            `Voice corrected: "${textToSend}" -> "${fixResp.data.corrected}"`,
          );
          textToSend = fixResp.data.corrected;
        }
      } catch (err) {
        console.warn("Voice correction failed:", err);
      }
    }

    // Build the message content - include file if attached
    let messageContent = textToSend;
    if (attachedFile) {
      const fileContext = `\n\n📎 **Attached File: ${
        attachedFile.name
      }**\n\`\`\`\n${attachedFile.content.slice(0, 30000)}\n\`\`\`${
        attachedFile.content.length > 30000
          ? "\n(Content truncated for display)"
          : ""
      }`;
      messageContent = textToSend + fileContext;
    }

    // Client-side command interception
    const lowerText = textToSend.toLowerCase();
    if (lowerText.includes("open internet console")) {
      setInternetConsoleOpen(true);
      setMessages((prev) => [
        ...prev,
        { role: "user", content: textToSend },
        {
          role: "assistant",
          content: sanitizeAssistantContent("🌍 Opening Internet Console..."),
        },
      ]);
      setInput("");
      return;
    }
    if (
      lowerText.includes("open game console") ||
      lowerText.includes("open game trainer console")
    ) {
      setGameConsoleOpen(true);
      setMessages((prev) => [
        ...prev,
        { role: "user", content: textToSend },
        {
          role: "assistant",
          content: sanitizeAssistantContent("🎮 Opening Game Console..."),
        },
      ]);
      setInput("");
      return;
    }
    if (lowerText.includes("open map console")) {
      setMapConsoleOpen(true);
      setMessages((prev) => [
        ...prev,
        { role: "user", content: textToSend },
        {
          role: "assistant",
          content: sanitizeAssistantContent(
            "🗺️ Opening Maps & Earth Console...",
          ),
        },
      ]);
      setInput("");
      return;
    }
    if (
      lowerText.includes("open weather console") ||
      lowerText.includes("open weather")
    ) {
      setWeatherConsoleOpen(true);
      setMessages((prev) => [
        ...prev,
        { role: "user", content: textToSend },
        {
          role: "assistant",
          content: sanitizeAssistantContent("🌦️ Opening Weather Console..."),
        },
      ]);
      setInput("");
      return;
    }
    if (lowerText.includes("open mini browser")) {
      setMiniBrowserOpen(true);
      setMessages((prev) => [
        ...prev,
        { role: "user", content: textToSend },
        {
          role: "assistant",
          content: sanitizeAssistantContent("🌐 Opening Mini Browser..."),
        },
      ]);
      setInput("");
      return;
    }
    if (
      lowerText.includes("open itinerary console") ||
      lowerText.includes("open email console") ||
      lowerText.includes("open travel console")
    ) {
      setEmailConsoleOpen(true);
      setMessages((prev) => [
        ...prev,
        { role: "user", content: textToSend },
        {
          role: "assistant",
          content: sanitizeAssistantContent("✈️ Opening Itinerary Console..."),
        },
      ]);
      setInput("");
      return;
    }
    if (
      lowerText.includes("open communications console") ||
      lowerText.includes("open comms console") ||
      lowerText.includes("open communications")
    ) {
      setCommunicationsConsoleOpen(true);
      setMessages((prev) => [
        ...prev,
        { role: "user", content: textToSend },
        {
          role: "assistant",
          content: sanitizeAssistantContent(
            "📡 Opening Communications Console...",
          ),
        },
      ]);
      setInput("");
      return;
    }
    if (
      lowerText.includes("open post console") ||
      lowerText.includes("open conversation to post") ||
      lowerText.includes("convert chat to post")
    ) {
      setConversationToPostOpen(true);
      setMessages((prev) => [
        ...prev,
        { role: "user", content: textToSend },
        {
          role: "assistant",
          content:
            "📱 Opening Conversation to SEO Post Console! Now you can convert our chat into viral Facebook posts! 🚀",
        },
      ]);
      setInput("");
      return;
    }

    // 🤖 OLLAMA/OLLIE COMMANDS - Local AI Assistant
    // Note: Direct delegation removed to enforce Master/Assistant hierarchy.
    // Agent Amigos will handle "ask ollie" commands and delegate them itself.
    if (
      lowerText.includes("ask ollie") ||
      lowerText.includes("hey ollie") ||
      lowerText.includes("ollie ")
    ) {
      const ollieQuestion = textToSend
        .replace(/ask ollie|hey ollie|ollie/gi, "")
        .trim();
      setMessages((prev) => [...prev, { role: "user", content: textToSend }]);
      setInput("");
      setStatus("🧭 Asking Agent Amigos to delegate to Ollie...");
      try {
        // Send through Amigos so it can evaluate and delegate to Ollie properly
        await sendMessage(textToSend);
      } catch (err) {
        console.error("Failed to send Ollie delegation to Amigos:", err);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "❌ Failed to ask Ollie via Agent Amigos.",
          },
        ]);
      }
      setStatus("Ready");
      return;
    }

    // Toggle Team Mode
    if (
      lowerText.includes("enable team mode") ||
      lowerText.includes("turn on team mode") ||
      lowerText.includes("activate team mode")
    ) {
      setTeamModeEnabled(true);
      setMessages((prev) => [
        ...prev,
        { role: "user", content: textToSend },
        {
          role: "assistant",
          content:
            "🤝 **Team Mode Activated!** I'm now coordinating with the full Agent Amigos team (Ollie, Scrapey, Media Bot, Researcher, and more). I'll delegate specialized tasks to the best agent for the job while I orchestrate everything! 🤖✨",
        },
      ]);
      setInput("");
      return;
    }
    if (
      lowerText.includes("disable team mode") ||
      lowerText.includes("turn off team mode")
    ) {
      setTeamModeEnabled(false);
      setMessages((prev) => [
        ...prev,
        { role: "user", content: textToSend },
        {
          role: "assistant",
          content:
            "👤 **Team Mode Disabled.** I'll handle all requests myself now.",
        },
      ]);
      setInput("");
      return;
    }

    // Check Ollie/Ollama status
    if (
      lowerText.includes("ollama status") ||
      lowerText.includes("ollie status") ||
      lowerText.includes("is ollie running")
    ) {
      const statusMsg = ollamaStatus.running
        ? `🦙 **Ollie is Online!**\n\n✅ Status: ${
            ollamaStatus.status
          }\n📦 Models: ${
            ollamaStatus.models.join(", ") || "Loading..."
          }\n🎯 Selected: ${selectedOllamaModel}\n🤝 Team Mode: ${
            teamModeEnabled ? "Enabled" : "Disabled"
          }`
        : `🦙 **Ollie is Offline**\n\n❌ Status: ${ollamaStatus.status}\n💡 Start Ollama to enable local AI assistance!`;
      setMessages((prev) => [
        ...prev,
        { role: "user", content: textToSend },
        { role: "assistant", content: sanitizeAssistantContent(statusMsg) },
      ]);
      setInput("");
      return;
    }

    // Check shared memory status
    if (
      lowerText.includes("memory status") ||
      lowerText.includes("what have you learned") ||
      lowerText.includes("what do you remember")
    ) {
      setStatus("🧠 Checking memory...");
      try {
        const [statsRes, factsRes, convsRes] = await Promise.all([
          axios.get(`${apiUrl}/memory/stats`),
          axios.get(`${apiUrl}/memory/facts?limit=5`),
          axios.get(`${apiUrl}/memory/conversations?limit=3`),
        ]);

        const stats = statsRes.data?.data || {};
        const recentFacts = factsRes.data?.data?.facts || [];
        const recentConvs = convsRes.data?.data?.conversations || [];

        let memoryMsg = `🧠 **Shared Memory Status**\n\n`;
        memoryMsg += `📊 **Statistics:**\n`;
        memoryMsg += `• 💬 Conversations: ${stats.conversations || 0}\n`;
        memoryMsg += `• 📚 Facts Learned: ${stats.facts || 0}\n`;
        memoryMsg += `• ✅ Tasks Completed: ${stats.tasks || 0}\n`;
        memoryMsg += `• 📖 Knowledge Base: ${stats.knowledge || 0}\n\n`;

        if (recentFacts.length > 0) {
          memoryMsg += `**🔖 Recent Things I've Learned:**\n`;
          recentFacts.forEach((f) => {
            memoryMsg += `• ${f.fact?.substring(0, 80)}${
              f.fact?.length > 80 ? "..." : ""
            }\n`;
          });
          memoryMsg += "\n";
        }

        memoryMsg += `💡 Both Amigos and Ollie share this memory locally!\n`;
        memoryMsg += `📍 All data stays on YOUR machine - 100% private.`;

        setMessages((prev) => [
          ...prev,
          { role: "user", content: textToSend },
          { role: "assistant", content: sanitizeAssistantContent(memoryMsg) },
        ]);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          { role: "user", content: textToSend },
          {
            role: "assistant",
            content: `🧠 Memory check failed: ${err.message}`,
          },
        ]);
      }
      setStatus("✅ Online");
      setInput("");
      return;
    }

    // Teach/Remember command - manually add facts to shared memory
    if (
      lowerText.startsWith("remember that ") ||
      lowerText.startsWith("teach:") ||
      lowerText.startsWith("learn:")
    ) {
      const factToLearn = textToSend
        .replace(/^(remember that |teach:|learn:)/i, "")
        .trim();

      if (factToLearn.length > 5) {
        setStatus("🧠 Learning...");
        try {
          await axios.post(`${apiUrl}/memory/learn`, {
            fact: factToLearn,
            category: "user_taught",
            source: "user",
          });

          setMessages((prev) => [
            ...prev,
            { role: "user", content: textToSend },
            {
              role: "assistant",
              content: `🧠 **Got it!** I've remembered:\n\n> "${factToLearn}"\n\nBoth Ollie and I now know this! 📚`,
            },
          ]);
          fetchMemoryStats(); // Refresh stats
        } catch (err) {
          setMessages((prev) => [
            ...prev,
            { role: "user", content: textToSend },
            {
              role: "assistant",
              content: `🧠 Couldn't save that: ${err.message}`,
            },
          ]);
        }
        setStatus("✅ Online");
        setInput("");
        return;
      }
    }

    // 🎤 CONVERSATIONAL AI - Check for casual conversation before sending to backend
    // This enables Agent Amigos to participate in interviews and live shows!
    const conversationalResponse =
      amigosSkill === "default" ? getConversationalResponse(textToSend) : null;
    if (conversationalResponse) {
      setMessages((prev) => [...prev, { role: "user", content: textToSend }]);
      setInput("");
      setStatus("💭 Thinking...");
      // Add natural delay for conversational feel
      await new Promise((resolve) =>
        setTimeout(resolve, 600 + Math.random() * 800),
      );
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: sanitizeAssistantContent(conversationalResponse),
        },
      ]);
      // 🔊 VOICE OUTPUT - Speak the conversational response
      {
        const spoken = getSpeechText({
          userText: textToSend,
          assistantText: conversationalResponse,
          wasVoice,
        });
        if (spoken) speak(spoken);
      }
      setStatus("✅ Online");
      return;
    }

    // 👀 SCREEN AWARENESS - Check if asking about what's on screen
    const consoleStates = {
      financeConsoleOpen,
      gameConsoleOpen,
      scraperConsoleOpen,
      fileConsoleOpen,
      internetConsoleOpen,
      mapConsoleOpen,
      weatherConsoleOpen,
      mediaConsoleOpen,
    };
    const screenAwareResponse =
      amigosSkill === "default"
        ? getScreenAwareResponse(textToSend, screenContext, consoleStates)
        : null;
    if (screenAwareResponse) {
      setMessages((prev) => [...prev, { role: "user", content: textToSend }]);
      setInput("");
      setStatus("👀 Looking at screen...");
      // Add delay as if "looking around"
      await new Promise((resolve) =>
        setTimeout(resolve, 800 + Math.random() * 600),
      );
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: sanitizeAssistantContent(screenAwareResponse),
        },
      ]);
      // 🔊 VOICE OUTPUT - Speak the screen-aware response
      {
        const spoken = getSpeechText({
          userText: textToSend,
          assistantText: screenAwareResponse,
          wasVoice,
        });
        if (spoken) speak(spoken);
      }
      setStatus("✅ Online");
      return;
    }

    if (!apiUrl) {
      setMessages((prev) => [
        ...prev,
        {
          role: "system",
          content:
            "Configure the backend URL (click Change near the status badge) before chatting.",
        },
      ]);
      return;
    }

    // 🤝 TEAM MODE - Route simple questions to Ollie for faster responses
    if (teamModeEnabled && ollamaStatus.running && !attachedFile) {
      // Check if this is a simple question Ollie can handle quickly
      const simpleQuestionPatterns = [
        /^(what|how|why|when|where|who|which|can you|could you|tell me|explain)/i,
        /^(define|describe|summarize|translate|calculate)/i,
        /\?$/, // Ends with question mark
      ];
      const isComplexTask =
        /(open|click|type|download|scrape|browse|navigate|file|create|delete|execute|run|install)/i.test(
          textToSend,
        );
      const isSimpleQuestion =
        simpleQuestionPatterns.some((p) => p.test(textToSend.trim())) &&
        !isComplexTask;

      if (isSimpleQuestion && textToSend.length < 500) {
        setMessages((prev) => [...prev, { role: "user", content: textToSend }]);
        setInput("");
        setStatus("🦙 Ollie is thinking...");
        setIsProcessing(true);

        try {
          const ollieResponse = await axios.post(
            `${apiUrl}/ollama/delegate`,
            {
              task: textToSend,
              task_type: "quick_response",
              prefer_fast: true,
            },
            { timeout: 60000 },
          );

          if (
            ollieResponse.data?.success &&
            ollieResponse.data?.data?.response
          ) {
            const response = ollieResponse.data.data.response;
            setMessages((prev) => [
              ...prev,
              {
                role: "assistant",
                content: sanitizeAssistantContent(`🦙 *Ollie:* ${response}`),
              },
            ]);
            {
              const spoken = getSpeechText({
                userText: textToSend,
                assistantText: response,
                wasVoice,
              });
              if (spoken) speak(spoken);
            }
            setStatus("✅ Online");
            setIsProcessing(false);
            return;
          }
        } catch (ollieErr) {
          console.log(
            "Ollie couldn't handle this, falling back to Amigos:",
            ollieErr.message,
          );
          // Fall through to normal Amigos handling
        }
        setIsProcessing(false);
        setStatus("🧠 Thinking...");
      }
    }

    // Create new abort controller for this request
    abortControllerRef.current = new AbortController();

    // Display message with file attachment indicator
    const displayMessage = attachedFile
      ? `${textToSend}\n\n📎 Attached: ${attachedFile.name} (${
          attachedFile.info?.line_count || 0
        } lines)`
      : textToSend;

    // Create full message for AI (includes file content)
    const aiMessage = attachedFile
      ? `${textToSend}\n\n[ATTACHED FILE: ${
          attachedFile.name
        }]\nFile Info: ${JSON.stringify(
          attachedFile.info || {},
        )}\n\nFILE CONTENT:\n${attachedFile.content}`
      : textToSend;

    const newMessages = [
      ...messages.filter((m) => m.role !== "action"),
      { role: "user", content: aiMessage },
    ];
    setMessages([...messages, { role: "user", content: displayMessage }]);
    setInput("");
    setAttachedFile(null); // Clear attached file after sending
    setStatus("🧠 Thinking...");
    setIsProcessing(true);

    // Get current skill prompt for system message
    const currentSkill =
      AMIGOS_SKILLS.find((s) => s.key === amigosSkill) || AMIGOS_SKILLS[0];
    const responsePolicy =
      "Follow the selected skill persona above. Communication style: Respond like a friendly human in natural conversation. Keep replies concise - usually 1-2 sentences that directly answer the question or complete the task. Only provide extended explanations when the user explicitly asks for more details (e.g., 'tell me more', 'explain in detail', 'elaborate'). Think quality over quantity.";

    const includeHashtags =
      amigosSkill === "writer" ||
      /\b(facebook|instagram|linkedin|tiktok|tweet|twitter|post|caption|seo|hashtag)\b/i.test(
        textToSend,
      );

    const skillSystemMessage = {
      role: "system",
      content:
        currentSkill.prompt +
        " " +
        responsePolicy +
        (includeHashtags
          ? " Always include #darrellbuttigieg #thesoldiersdream in any social media content you create."
          : ""),
    };

    try {
      const response = await axios.post(
        `${apiUrl}/chat`,
        {
          messages: [
            skillSystemMessage,
            ...newMessages.filter(
              (m) => m.role === "user" || m.role === "assistant",
            ),
          ],
          require_approval: requireApproval,
          screen_context: screenContext,
          team_mode: teamModeEnabled,
        },
        {
          signal: abortControllerRef.current.signal,
          timeout: 120000, // 2 minutes timeout for browser automation
        },
      );

      const data = response.data;

      // Handle canvas commands if present (from design tools)
      if (
        data.canvas_commands &&
        Array.isArray(data.canvas_commands) &&
        data.canvas_commands.length > 0
      ) {
        console.log(
          "🎨 Canvas commands from chat response:",
          data.canvas_commands.length,
        );
        // Map raw backend canvas commands (type-based) to frontend agent command format
        const toAgentCanvasCommands = (raw) =>
          (raw || []).map((cmd) => {
            // Normalize backend layer names to frontend layer IDs
            const rawLayer = cmd.layer || cmd.layer_id;
            const normalizeLayer = (l) => {
              const s = String(l || "").toLowerCase();
              if (!s) return "cad";
              if (s.includes("annotation") || s.includes("text"))
                return "annotations";
              if (
                s.includes("wall") ||
                s.includes("door") ||
                s.includes("base") ||
                s.includes("cad")
              )
                return "cad";
              if (s.includes("diagram")) return "diagram";
              if (s.includes("sketch")) return "sketch";
              return "cad";
            };
            const layerId = normalizeLayer(rawLayer) || "cad";

            const strokeWidth = cmd.strokeWidth || cmd.width || 2;
            const strokeColor = cmd.stroke || cmd.color || "#6366f1";
            const fillColor = cmd.fill || "transparent";

            switch (cmd.type || cmd.command_type || cmd.action) {
              case "set_mode":
                return {
                  command_type: "set_mode",
                  parameters: {
                    mode: cmd.mode || cmd.value || "CAD",
                  },
                };
              case "rectangle":
                return {
                  command_type: "draw_rectangle",
                  parameters: {
                    x: cmd.x || 100,
                    y: cmd.y || 100,
                    width: cmd.width || 100,
                    height: cmd.height || 100,
                    strokeColor,
                    fillColor,
                    strokeWidth,
                    layer_id: layerId,
                  },
                };
              case "line":
              case "draw_line": {
                const pts = cmd.points || [];
                return {
                  command_type: "draw_line",
                  parameters: {
                    x1: cmd.x1 || pts[0] || 0,
                    y1: cmd.y1 || pts[1] || 0,
                    x2: cmd.x2 || pts[2] || 100,
                    y2: cmd.y2 || pts[3] || 100,
                    strokeColor,
                    strokeWidth,
                    layer_id: layerId,
                  },
                };
              }
              case "text":
              case "draw_text":
                return {
                  command_type: "draw_text",
                  parameters: {
                    text: cmd.text || cmd.label || "Text",
                    x: cmd.x || 100,
                    y: cmd.y || 100,
                    fontSize: cmd.size || cmd.fontSize || 16,
                    color: strokeColor || "#ffffff",
                    layer_id: layerId,
                  },
                };
              case "circle":
                return {
                  command_type: "draw_ellipse",
                  parameters: {
                    cx: cmd.cx || cmd.x || 100,
                    cy: cmd.cy || cmd.y || 100,
                    rx: cmd.radius || 50,
                    ry: cmd.radius || 50,
                    strokeColor,
                    fillColor,
                    strokeWidth,
                    layer_id: layerId,
                  },
                };
              case "arc":
                // Approximate arc as a short arrow for now
                return {
                  command_type: "draw_arrow",
                  parameters: {
                    x1: cmd.cx || 100,
                    y1: cmd.cy || 100,
                    x2: (cmd.cx || 100) + (cmd.radius || 50),
                    y2: cmd.cy || 100,
                    strokeColor,
                    strokeWidth,
                    layer_id: layerId,
                  },
                };
              default:
                // Fallback: pass through as-is, use action/command_type
                return {
                  command_type: cmd.command_type || cmd.action || "draw_text",
                  parameters: cmd.parameters || {
                    text: cmd.text || "Command",
                    x: cmd.x || 20,
                    y: cmd.y || 20,
                    layer_id: layerId,
                  },
                };
            }
          });

        const mapped = toAgentCanvasCommands(data.canvas_commands);
        setCanvasCommands(mapped);
        // Ensure canvas is visible when commands arrive
        setCanvasOpen(true);
      }

      // Handle map commands if present
      if (
        data.map_commands &&
        Array.isArray(data.map_commands) &&
        data.map_commands.length > 0
      ) {
        console.log("🗺️ Map commands from chat response:", data.map_commands);
        // Execute the last map command (or we could loop, but usually one is enough)
        const lastCmd = data.map_commands[data.map_commands.length - 1];
        setMapCommand(lastCmd);
        setMapConsoleOpen(true);
      }

      // Handle search results if present (Internet Console)
      if (
        data.search_results &&
        Array.isArray(data.search_results) &&
        data.search_results.length > 0
      ) {
        console.log(
          "🌍 Search results from chat response:",
          data.search_results.length,
        );
        setSearchResults(data.search_results);
        setInternetConsoleOpen(true);
      }

      // Handle todo list and progress from response
      if (data.todo_list || data.progress !== undefined) {
        setAgentTeam((prev) => {
          if (!prev || !prev.agents) return prev;
          return {
            ...prev,
            agents: {
              ...prev.agents,
              amigos: {
                ...prev.agents.amigos,
                todo_list:
                  data.todo_list || prev.agents.amigos?.todo_list || [],
                progress:
                  data.progress !== undefined
                    ? data.progress
                    : prev.agents.amigos?.progress || 0,
              },
            },
          };
        });
      }

      // Show actions taken
      if (data.actions_taken && data.actions_taken.length > 0) {
        for (const action of data.actions_taken) {
          let resultSummary = "";
          if (action.result !== undefined && action.result !== null) {
            if (typeof action.result === "object") {
              try {
                resultSummary = JSON.stringify(action.result, null, 2);
              } catch (err) {
                resultSummary = String(action.result);
              }
            } else {
              resultSummary = String(action.result);
            }
          }

          setMessages((prev) => [
            ...prev,
            {
              role: "action",
              content: `⚡ ${action.tool}`,
              details: JSON.stringify(action.args),
              result: action.result?.success ? "✓" : "✗",
              resultSummary,
            },
          ]);
        }
      }

      // Check if action needs approval
      if (data.needs_approval && data.pending_action) {
        setPendingAction(data.pending_action);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.content },
          {
            role: "approval",
            content: `⚠️ Action requires approval: ${data.pending_action.tool}`,
            action: data.pending_action,
          },
        ]);
        {
          const spoken = getSpeechText({
            userText: textToSend,
            assistantText:
              data.content || "I need your approval for this action.",
            wasVoice,
          });
          if (spoken) speak(spoken);
        }
        setStatus("⚠️ Awaiting Approval");
      } else {
        // Normal response - do not override the backend with false capability claims.
        let finalContent = data.content;

        // If the model claims it CANNOT see the screen, correct that.
        const denialPatterns = [
          /I (don't|do not) have (direct )?access to your (screen|display|monitor)/i,
          /I (can't|cannot) (see|view|watch) your (screen|display|monitor)/i,
          /I (don't|do not) have (any )?eyes on your (screen|display|monitor)/i,
          /I (am not|am unable to) (seeing|looking at) your (screen|display|monitor)/i,
          /I (don't|do not) have (access|the ability) to (see|view) what is (currently )?on your (screen|display|monitor)/i,
          /I (can't|cannot) (see|access) your (internet|finance|game|scraper|file|map) console/i,
          /I (don't|do not) have (access|the ability) to (see|view) your (internet|finance|game|scraper|file|map) console/i,
          /I (am|'m) a text-based AI/i,
          /I (don't|do not) have the capability to display (images|maps)/i,
          /I (can't|cannot) (display|show) (images|maps)/i,
        ];

        const isDenying = denialPatterns.some((pattern) =>
          pattern.test(finalContent),
        );

        if (isDenying) {
          const openConsoles = [];
          if (financeConsoleOpen) openConsoles.push("📊 Finance Console");
          if (gameConsoleOpen) openConsoles.push("🎮 Game Console");
          if (scraperConsoleOpen) openConsoles.push("🌐 Scraper Workbench");
          if (fileConsoleOpen) openConsoles.push("📁 File Console");
          if (internetConsoleOpen) openConsoles.push("🌍 Internet Console");
          if (mapConsoleOpen) openConsoles.push("🗺️ Maps Console");
          if (weatherConsoleOpen) openConsoles.push("🌦️ Weather Console");
          if (mediaConsoleOpen) openConsoles.push("🎬 Media Console");

          finalContent =
            "I am integrated with your Agent Amigos consoles! 🤖\n\n";

          if (openConsoles.length > 0) {
            finalContent += `**Currently open consoles I can monitor:**\n${openConsoles
              .map((c) => `• ✅ ${c}`)
              .join("\n")}\n\n`;
            finalContent +=
              "Ask me about any of these and I'll summarize the live data for you!";
          } else {
            finalContent +=
              "All consoles are minimized right now. Say 'open [console]' and I'll describe what I see in that console.";
          }
        }

        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: sanitizeAssistantContent(finalContent),
          },
        ]);
        {
          const spoken = getSpeechText({
            userText: textToSend,
            assistantText: finalContent,
            wasVoice,
          });
          if (spoken) speak(spoken);
        }
        setStatus("Ready");
        setIsProcessing(false);

        // Log to shared memory for learning (user message and assistant response)
        logToMemory("user", aiMessage, "amigos");
        logToMemory("assistant", finalContent, "amigos");
      }
    } catch (error) {
      if (error.name === "CanceledError" || error.code === "ERR_CANCELED") {
        // Request was aborted by user - already handled by stopEverything
        return;
      }
      setMessages((prev) => [
        ...prev,
        { role: "system", content: `Error: ${error.message}` },
      ]);
      setStatus("Ready");
      setIsProcessing(false);
    }
  };

  const handleCompanyAsk = useCallback(
    (text) => {
      const trimmed = String(text || "").trim();
      if (!trimmed || isProcessing) return;
      setInput(trimmed);
      sendMessage(trimmed);
    },
    [isProcessing, sendMessage],
  );

  // --- Render Message ---
  const renderMessage = (msg, idx) => {
    const baseStyle = {
      padding: "14px 18px",
      borderRadius: "16px",
      maxWidth: "85%",
      fontSize: "0.9em",
      whiteSpace: "pre-wrap",
      lineHeight: "1.5",
      transition: "all 0.2s ease",
    };

    if (msg.role === "user") {
      return (
        <div
          key={idx}
          style={{
            ...baseStyle,
            alignSelf: "flex-end",
            background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
            marginLeft: "auto",
            boxShadow: "0 4px 15px rgba(99, 102, 241, 0.3)",
            border: "1px solid rgba(139, 92, 246, 0.3)",
          }}
        >
          {msg.content}
        </div>
      );
    }

    if (msg.role === "assistant") {
      return (
        <div
          key={idx}
          style={{
            ...baseStyle,
            alignSelf: "flex-start",
            background: "rgba(30, 30, 50, 0.8)",
            backdropFilter: "blur(10px)",
            border: "1px solid rgba(99, 102, 241, 0.2)",
            boxShadow: "0 4px 15px rgba(0, 0, 0, 0.2)",
          }}
        >
          {msg.content}
        </div>
      );
    }

    if (msg.role === "action") {
      return (
        <div
          key={idx}
          style={{
            ...baseStyle,
            alignSelf: "flex-start",
            background: msg.approved
              ? "linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(5, 150, 105, 0.2) 100%)"
              : msg.rejected
                ? "linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(220, 38, 38, 0.2) 100%)"
                : "linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(37, 99, 235, 0.2) 100%)",
            border: `1px solid ${
              msg.approved
                ? "rgba(16, 185, 129, 0.4)"
                : msg.rejected
                  ? "rgba(239, 68, 68, 0.4)"
                  : "rgba(59, 130, 246, 0.4)"
            }`,
            fontSize: "0.8em",
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            boxShadow: `0 4px 15px ${
              msg.approved
                ? "rgba(16, 185, 129, 0.15)"
                : msg.rejected
                  ? "rgba(239, 68, 68, 0.15)"
                  : "rgba(59, 130, 246, 0.15)"
            }`,
          }}
        >
          {msg.content}
          {msg.details && (
            <div style={{ opacity: 0.7, marginTop: "6px", fontSize: "0.9em" }}>
              {msg.details}
            </div>
          )}
          {msg.resultSummary && (
            <pre
              style={{
                marginTop: "8px",
                maxHeight: "150px",
                overflowY: "auto",
                backgroundColor: "rgba(0,0,0,0.3)",
                padding: "10px",
                borderRadius: "10px",
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                fontSize: "0.75em",
                whiteSpace: "pre-wrap",
                border: "1px solid rgba(99, 102, 241, 0.15)",
              }}
            >
              {msg.resultSummary}
            </pre>
          )}
        </div>
      );
    }

    if (msg.role === "approval") {
      return (
        <div
          key={idx}
          style={{
            ...baseStyle,
            alignSelf: "stretch",
            background:
              "linear-gradient(135deg, rgba(251, 191, 36, 0.15) 0%, rgba(245, 158, 11, 0.15) 100%)",
            border: "2px solid rgba(251, 191, 36, 0.5)",
            textAlign: "center",
            boxShadow: "0 4px 20px rgba(251, 191, 36, 0.2)",
            backdropFilter: "blur(10px)",
          }}
        >
          <div style={{ marginBottom: "14px", fontWeight: "500" }}>
            {msg.content}
          </div>
          <div
            style={{ display: "flex", gap: "12px", justifyContent: "center" }}
          >
            <button
              onClick={approveAction}
              style={{
                padding: "10px 24px",
                background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
                border: "none",
                borderRadius: "10px",
                color: "white",
                cursor: "pointer",
                fontWeight: "bold",
                boxShadow: "0 4px 15px rgba(16, 185, 129, 0.4)",
                transition: "all 0.2s ease",
              }}
              onMouseEnter={(e) => {
                e.target.style.transform = "scale(1.05)";
                e.target.style.boxShadow = "0 6px 20px rgba(16, 185, 129, 0.5)";
              }}
              onMouseLeave={(e) => {
                e.target.style.transform = "scale(1)";
                e.target.style.boxShadow = "0 4px 15px rgba(16, 185, 129, 0.4)";
              }}
            >
              ✓ Approve
            </button>
            <button
              onClick={rejectAction}
              style={{
                padding: "10px 24px",
                background: "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)",
                border: "none",
                borderRadius: "10px",
                color: "white",
                cursor: "pointer",
                fontWeight: "bold",
                boxShadow: "0 4px 15px rgba(239, 68, 68, 0.4)",
                transition: "all 0.2s ease",
              }}
              onMouseEnter={(e) => {
                e.target.style.transform = "scale(1.05)";
                e.target.style.boxShadow = "0 6px 20px rgba(239, 68, 68, 0.5)";
              }}
              onMouseLeave={(e) => {
                e.target.style.transform = "scale(1)";
                e.target.style.boxShadow = "0 4px 15px rgba(239, 68, 68, 0.4)";
              }}
            >
              ✗ Cancel
            </button>
          </div>
        </div>
      );
    }

    // System message
    return (
      <div
        key={idx}
        style={{
          ...baseStyle,
          alignSelf: "flex-start",
          background: "rgba(50, 50, 70, 0.6)",
          backdropFilter: "blur(8px)",
          border: "1px solid rgba(99, 102, 241, 0.15)",
          opacity: 0.9,
          fontSize: "0.85em",
        }}
      >
        {msg.content}
      </div>
    );
  };

  // Note: Chat position/size state moved earlier in file (before saveLayout function)

  // Chat drag handlers
  const handleChatMouseDown = (e) => {
    if (layoutLocked) return;
    if (
      e.target.closest(".chat-resize-handle") ||
      e.target.closest("button") ||
      e.target.closest("input")
    )
      return;
    setIsChatDragging(true);
    const rect = chatRef.current.getBoundingClientRect();
    setChatDragOffset({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  useEffect(() => {
    const handleChatMouseMove = (e) => {
      if (isChatDragging && !layoutLocked) {
        setChatPosition({
          x: Math.max(
            0,
            Math.min(
              window.innerWidth - chatSize.width,
              e.clientX - chatDragOffset.x,
            ),
          ),
          y: Math.max(
            0,
            Math.min(window.innerHeight - 100, e.clientY - chatDragOffset.y),
          ),
        });
      }
      if (isChatResizing && !layoutLocked) {
        const rect = chatRef.current.getBoundingClientRect();
        setChatSize({
          width: Math.max(350, e.clientX - rect.left + 10),
          height: Math.max(300, e.clientY - rect.top + 10),
        });
      }
    };
    const handleChatMouseUp = () => {
      setIsChatDragging(false);
      setIsChatResizing(false);
    };
    if (isChatDragging || isChatResizing) {
      document.addEventListener("mousemove", handleChatMouseMove);
      document.addEventListener("mouseup", handleChatMouseUp);
      return () => {
        document.removeEventListener("mousemove", handleChatMouseMove);
        document.removeEventListener("mouseup", handleChatMouseUp);
      };
    }
  }, [isChatDragging, isChatResizing, chatDragOffset, chatSize.width]);

  // Handle sidebar item clicks
  const handleSidebarClick = (itemId) => {
    const actions = {
      chat: () => setChatMinimized(false),
      canvas: () => setCanvasOpen(!canvasOpen),
      scraper: () => setScraperConsoleOpen(!scraperConsoleOpen),
      macro: () => setMacroConsoleOpen(!macroConsoleOpen),
      internet: () => setInternetConsoleOpen(!internetConsoleOpen),
      map: () => setMapConsoleOpen(!mapConsoleOpen),
      weather: () => setWeatherConsoleOpen(!weatherConsoleOpen),
      finance: () => setFinanceConsoleOpen(!financeConsoleOpen),
      media: () => setMediaConsoleOpen(!mediaConsoleOpen),
      game: () => setGameConsoleOpen(!gameConsoleOpen),
      files: () => setFileConsoleOpen(!fileConsoleOpen),
      itinerary: () => setEmailConsoleOpen(!emailConsoleOpen),
      post: () => setConversationToPostOpen(!conversationToPostOpen),
      comms: () => setCommunicationsConsoleOpen(!communicationsConsoleOpen),
      company: () => setCompanyConsoleOpen(!companyConsoleOpen),
      openwork: () => setOpenWorkConsoleOpen(!openworkConsoleOpen),
      avatar: () => setAiAvatarOpen(!aiAvatarOpen),
      settings: () => {
        const next = !showSystemControls;
        setShowSystemControls(next);
        if (next) {
          setActiveSystemTab("settings");
          setIsTogglesMinimized(false);
        }
      },
    };
    if (actions[itemId]) actions[itemId]();
  };

  const openDetachedConsole = (standaloneKey, onCloseMain) => {
    const baseUrl = `${window.location.origin}${window.location.pathname}`;
    const url = `${baseUrl}?standalone=${encodeURIComponent(standaloneKey)}`;
    const win = window.open(
      url,
      `Amigos-${standaloneKey}`,
      "noopener,noreferrer,width=1200,height=800",
    );
    if (win) {
      win.focus();
      if (onCloseMain) onCloseMain();
    }
  };

  const handleSidebarDetach = (itemId) => {
    const actions = {
      canvas: () => openDetachedConsole("Canvas", () => setCanvasOpen(false)),
      scraper: () =>
        openDetachedConsole("Scraper", () => setScraperConsoleOpen(false)),
      macro: () =>
        openDetachedConsole("Macro", () => setMacroConsoleOpen(false)),
      internet: () =>
        openDetachedConsole("Internet", () => setInternetConsoleOpen(false)),
      map: () => openDetachedConsole("Map", () => setMapConsoleOpen(false)),
      weather: () =>
        openDetachedConsole("Weather", () => setWeatherConsoleOpen(false)),
      finance: () =>
        openDetachedConsole("Finance", () => setFinanceConsoleOpen(false)),
      media: () =>
        openDetachedConsole("Media", () => setMediaConsoleOpen(false)),
      game: () => openDetachedConsole("Game", () => setGameConsoleOpen(false)),
      files: () =>
        openDetachedConsole("Files", () => setFileConsoleOpen(false)),
      itinerary: () =>
        openDetachedConsole("Itinerary", () => setEmailConsoleOpen(false)),
      post: () =>
        openDetachedConsole("Post", () => setConversationToPostOpen(false)),
      comms: () =>
        openDetachedConsole("Communications", () =>
          setCommunicationsConsoleOpen(false),
        ),
      company: () =>
        openDetachedConsole("Company", () => setCompanyConsoleOpen(false)),
      openwork: () =>
        openDetachedConsole("OpenWork", () => setOpenWorkConsoleOpen(false)),
      avatar: () => openDetachedConsole("Avatar", () => setAiAvatarOpen(false)),
    };
    if (actions[itemId]) actions[itemId]();
  };

  // Handle sending media to canvas
  const handleSendToCanvas = (url) => {
    setCanvasOpen(true);
    setCanvasCommands((prev) => [
      ...prev,
      {
        command_type: "add_shape",
        shapeType: "image",
        props: {
          imageData: url,
          x: 200,
          y: 200,
          width: 400,
          height: 300,
        },
      },
    ]);
  };

  // Active sidebar items
  const sidebarActiveItems = {
    chat: !chatMinimized,
    canvas: canvasOpen,
    scraper: scraperConsoleOpen,
    macro: macroConsoleOpen,
    internet: internetConsoleOpen,
    map: mapConsoleOpen,
    weather: weatherConsoleOpen,
    finance: financeConsoleOpen,
    media: mediaConsoleOpen,
    game: gameConsoleOpen,
    files: fileConsoleOpen,
    itinerary: emailConsoleOpen,
    post: conversationToPostOpen,
    comms: communicationsConsoleOpen,
    company: companyConsoleOpen,
    openwork: openworkConsoleOpen,
    avatar: aiAvatarOpen,
  };

  const memoryPercent = memoryStatus?.system?.percent;
  const normalizedAutonomyMode = String(
    autonomyStatus.autonomyMode || autonomyStatus.autonomy_mode || "off",
  ).toLowerCase();
  const autonomyEnabled =
    !autonomyStatus.killSwitch && normalizedAutonomyMode !== "off";
  const memoryLevel = memoryStatus?.level || "unknown";
  const memoryBadgeColor = memoryStatus?.available
    ? memoryLevel === "critical"
      ? "#dc2626"
      : memoryLevel === "warning"
        ? "#f59e0b"
        : "#16a34a"
    : "#6b7280";
  const memoryBadgeLabel = memoryStatus?.available
    ? `MEM ${Math.round(memoryPercent || 0)}%`
    : "MEM N/A";

  return (
    <AppErrorBoundary>
      <PortalHeader
        showDashboard={showDashboard}
        onLaunchDashboard={() => setShowDashboard(!showDashboard)}
      />

      {!showDashboard ? (
        <LandingPage onEnter={() => setShowDashboard(true)} apiUrl={apiUrl} />
      ) : (
        <div className="amigos-app" style={{ paddingTop: "70px" }}>
          {/* Connection Status Banner - Shows when backend unreachable */}
          {!backendConnected && !backendDiscovering && (
            <div
              style={{
                position: "fixed",
                top: 0,
                left: 0,
                right: 0,
                zIndex: 10000,
                background: "linear-gradient(135deg, #dc2626, #b91c1c)",
                color: "white",
                padding: "12px 20px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                boxShadow: "0 4px 15px rgba(220, 38, 38, 0.4)",
                borderBottom: "2px solid rgba(239, 68, 68, 0.5)",
                flexWrap: "wrap",
                gap: "12px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  flex: 1,
                }}
              >
                <span style={{ fontSize: "1.2em" }}>⚠️</span>
                <div>
                  <div style={{ fontWeight: "bold", fontSize: "0.95em" }}>
                    Backend Connection Lost
                  </div>
                  <div style={{ fontSize: "0.8em", opacity: 0.9 }}>
                    Trying: {apiUrl}
                  </div>
                </div>
              </div>
              <div
                style={{
                  display: "flex",
                  gap: "8px",
                  alignItems: "center",
                  flexWrap: "wrap",
                }}
              >
                <button
                  onClick={async () => {
                    setBackendDiscovering(true);
                    const discovered = await discoverBackendUrl();
                    setApiUrl(discovered);
                    localStorage.setItem(STORAGE_KEY, discovered);
                    const connected = await probeBackendUrl(discovered);
                    setBackendConnected(connected);
                    setBackendDiscovering(false);
                  }}
                  style={{
                    background: "rgba(255, 255, 255, 0.2)",
                    border: "1px solid rgba(255, 255, 255, 0.4)",
                    color: "white",
                    padding: "6px 14px",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontSize: "0.85em",
                    fontWeight: "600",
                    transition: "all 0.2s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.background = "rgba(255, 255, 255, 0.3)";
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.background = "rgba(255, 255, 255, 0.2)";
                  }}
                >
                  🔄 Retry
                </button>
                <input
                  type="text"
                  placeholder="Override URL (e.g., http://127.0.0.1:65252)"
                  style={{
                    background: "rgba(255, 255, 255, 0.15)",
                    border: "1px solid rgba(255, 255, 255, 0.3)",
                    color: "white",
                    padding: "6px 12px",
                    borderRadius: "6px",
                    fontSize: "0.85em",
                    width: "280px",
                    outline: "none",
                  }}
                  onKeyDown={async (e) => {
                    if (e.key === "Enter" && e.target.value.trim()) {
                      const overrideUrl = sanitizeUrl(e.target.value.trim());
                      setApiUrl(overrideUrl);
                      localStorage.setItem(STORAGE_KEY, overrideUrl);
                      setBackendDiscovering(true);
                      const connected = await probeBackendUrl(overrideUrl);
                      setBackendConnected(connected);
                      setBackendDiscovering(false);
                      e.target.value = "";
                    }
                  }}
                />
                <span style={{ fontSize: "0.8em", opacity: 0.9 }}>
                  Press Enter to apply
                </span>
              </div>
            </div>
          )}

          {/* Discovering Banner - Shows during auto-discovery */}
          {backendDiscovering && (
            <div
              style={{
                position: "fixed",
                top: 0,
                left: 0,
                right: 0,
                zIndex: 10000,
                background: "linear-gradient(135deg, #f59e0b, #d97706)",
                color: "white",
                padding: "10px 20px",
                display: "flex",
                alignItems: "center",
                gap: "12px",
                boxShadow: "0 4px 15px rgba(245, 158, 11, 0.4)",
                borderBottom: "2px solid rgba(251, 191, 36, 0.5)",
              }}
            >
              <span style={{ fontSize: "1.1em" }}>🔍</span>
              <div style={{ fontWeight: "600", fontSize: "0.9em" }}>
                Discovering backend...
              </div>
            </div>
          )}

          {/* Animated Background Particles */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              overflow: "hidden",
              pointerEvents: "none",
              zIndex: 0,
            }}
          >
            {[...Array(20)].map((_, i) => (
              <div
                key={i}
                style={{
                  position: "absolute",
                  width: `${Math.random() * 4 + 2}px`,
                  height: `${Math.random() * 4 + 2}px`,
                  background: `rgba(${99 + Math.random() * 50}, ${
                    102 + Math.random() * 50
                  }, 241, ${0.3 + Math.random() * 0.4})`,
                  borderRadius: "50%",
                  left: `${Math.random() * 100}%`,
                  top: `${Math.random() * 100}%`,
                  animation: `float ${
                    5 + Math.random() * 10
                  }s ease-in-out infinite`,
                  animationDelay: `${Math.random() * 5}s`,
                }}
              />
            ))}
          </div>

          {/* 🎛️ LEFT SIDEBAR - Tool Navigation */}
          <Sidebar
            collapsed={sidebarCollapsed}
            onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
            activeItems={sidebarActiveItems}
            onItemClick={handleSidebarClick}
            onItemDetach={handleSidebarDetach}
          />

          {/* ═══════════════════════════════════════════════════════════════
            EXECUTIVE CORPORATE HEADER - $20K PROFESSIONAL DESIGN
            ═══════════════════════════════════════════════════════════════ */}
          <header className="executive-header">
            <div className="corp-logo">
              <div className="brand-mark">A</div>
              <div>
                <div className="brand-name">
                  Agent Amigos <span className="revenue-text">CORP</span>
                </div>
                <div
                  style={{
                    fontSize: "0.7rem",
                    color: "var(--text-muted)",
                    letterSpacing: "0.1em",
                    fontWeight: "700",
                  }}
                >
                  AUTONOMOUS ENTERPRISE OS
                </div>
              </div>
            </div>

            <div className="status-cluster">
              {/* Memory status indicator */}
              <div
                className="status-pill"
                style={{
                  background: memoryBadgeColor,
                  color: "#fff",
                  border: "none",
                  minWidth: "120px",
                  justifyContent: "center",
                }}
                title={
                  memoryStatus?.available
                    ? `System: ${Math.round(memoryPercent || 0)}% used | Process: ${
                        memoryStatus?.process?.percent_of_system
                          ? memoryStatus.process.percent_of_system.toFixed(1)
                          : "0.0"
                      }%`
                    : memoryStatus?.detail || "Memory status unavailable"
                }
              >
                <div
                  className="status-dot"
                  style={{ backgroundColor: "rgba(255,255,255,0.6)" }}
                ></div>
                {memoryBadgeLabel}
              </div>

              {/* Autonomy status indicator */}
              <div
                className={`status-pill ${autonomyStatus.autonomyEnabled ? "executive-glow" : ""}`}
                style={{
                  background: autonomyStatus.killSwitch
                    ? "#b91c1c"
                    : autonomyStatus.autonomyEnabled
                      ? "#059669"
                      : "#ef4444",
                  color: "#fff",
                  border: "none",
                }}
                title={
                  autonomyStatus.killSwitch
                    ? "Autonomy paused (Kill Switch)"
                    : autonomyStatus.autonomyEnabled
                      ? "Autonomy enabled"
                      : "Autonomy disabled"
                }
              >
                <div
                  className="status-dot"
                  style={{ backgroundColor: "rgba(255,255,255,0.8)" }}
                ></div>
                {autonomyStatus.killSwitch
                  ? "KILLED"
                  : autonomyStatus.autonomyEnabled
                    ? "AUTONOMY ON"
                    : "AUTONOMY OFF"}
              </div>

              <div className="status-pill">
                <div
                  className="status-dot"
                  style={{
                    backgroundColor: backendConnected
                      ? "var(--accent-success)"
                      : "var(--accent-danger)",
                  }}
                ></div>
                {backendConnected ? "SYSTEMS ONLINE" : "OFFLINE"}
              </div>

              <div
                className="status-pill"
                style={{ border: "1px solid var(--accent-revenue)" }}
              >
                <span
                  style={{ color: "var(--accent-revenue)", fontWeight: "800" }}
                >
                  PRO v2.0
                </span>
                <span style={{ opacity: 0.6, margin: "0 4px" }}>•</span>
                <span>{toolsAvailable} ASSETS</span>
              </div>

              {/* 🛠️ QUICK TOOLS DROPDOWN */}
              <div style={{ position: "relative" }}>
                <button
                  onClick={() => setQuickToolsOpen(!quickToolsOpen)}
                  style={{
                    padding: "8px 14px",
                    borderRadius: "10px",
                    border: "none",
                    background: quickToolsOpen
                      ? "linear-gradient(135deg, #6366f1, #8b5cf6)"
                      : "linear-gradient(135deg, #4b5563, #1f2933)",
                    color: "#fff",
                    cursor: "pointer",
                    fontSize: "0.7em",
                    fontWeight: "600",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    boxShadow: quickToolsOpen
                      ? "0 4px 15px rgba(99, 102, 241, 0.4)"
                      : "none",
                  }}
                  title="Quick Tools Menu"
                >
                  🛠️ Tools {quickToolsOpen ? "▲" : "▼"}
                </button>
                {quickToolsOpen && (
                  <div
                    style={{
                      position: "absolute",
                      top: "100%",
                      right: 0,
                      marginTop: "8px",
                      padding: "12px",
                      background: "rgba(11, 11, 21, 0.95)",
                      backdropFilter: "blur(20px)",
                      borderRadius: "12px",
                      border: "1px solid rgba(99, 102, 241, 0.3)",
                      boxShadow: "0 8px 32px rgba(0, 0, 0, 0.5)",
                      zIndex: 1000,
                      display: "flex",
                      flexDirection: "column",
                      gap: "8px",
                      minWidth: "160px",
                    }}
                  >
                    <button
                      onClick={() => {
                        promptForApiUrl();
                        setQuickToolsOpen(false);
                      }}
                      style={{
                        padding: "10px 14px",
                        borderRadius: "8px",
                        border: "1px solid rgba(99, 102, 241, 0.3)",
                        background: "rgba(99, 102, 241, 0.1)",
                        color: "#a5b4fc",
                        cursor: "pointer",
                        fontSize: "0.8em",
                        fontWeight: "600",
                        textAlign: "left",
                      }}
                    >
                      ⚙️ Config API
                    </button>
                    <button
                      onClick={() => {
                        resetApiUrl();
                        setQuickToolsOpen(false);
                      }}
                      style={{
                        padding: "10px 14px",
                        borderRadius: "8px",
                        border: "1px solid rgba(245, 158, 11, 0.3)",
                        background: "rgba(245, 158, 11, 0.1)",
                        color: "#fbbf24",
                        cursor: "pointer",
                        fontSize: "0.8em",
                        fontWeight: "600",
                        textAlign: "left",
                      }}
                    >
                      🔄 Reset API
                    </button>

                    <button
                      onClick={() => {
                        setAiAvatarOpen(!aiAvatarOpen);
                        setQuickToolsOpen(false);
                      }}
                      style={{
                        padding: "10px 14px",
                        borderRadius: "8px",
                        border: "none",
                        background: aiAvatarOpen
                          ? "linear-gradient(135deg, #ec4899, #db2777)"
                          : "rgba(236, 72, 153, 0.1)",
                        color: aiAvatarOpen ? "#fff" : "#f9a8d4",
                        cursor: "pointer",
                        fontSize: "0.8em",
                        fontWeight: "600",
                        textAlign: "left",
                      }}
                    >
                      👤 AI Avatar
                    </button>
                    <button
                      onClick={() => {
                        setScraperConsoleOpen(!scraperConsoleOpen);
                        setQuickToolsOpen(false);
                      }}
                      style={{
                        padding: "10px 14px",
                        borderRadius: "8px",
                        border: "none",
                        background: scraperConsoleOpen
                          ? "linear-gradient(135deg, #8b5cf6, #7c3aed)"
                          : "rgba(139, 92, 246, 0.1)",
                        color: scraperConsoleOpen ? "#fff" : "#c4b5fd",
                        cursor: "pointer",
                        fontSize: "0.8em",
                        fontWeight: "600",
                        textAlign: "left",
                      }}
                    >
                      🕷️ Scraper
                    </button>
                    <button
                      onClick={() => {
                        setCanvasOpen(!canvasOpen);
                        setQuickToolsOpen(false);
                      }}
                      style={{
                        padding: "10px 14px",
                        borderRadius: "8px",
                        border: "none",
                        background: canvasOpen
                          ? "linear-gradient(135deg, #06b6d4, #0891b2)"
                          : "rgba(6, 182, 212, 0.1)",
                        color: canvasOpen ? "#fff" : "#67e8f9",
                        cursor: "pointer",
                        fontSize: "0.8em",
                        fontWeight: "600",
                        textAlign: "left",
                      }}
                    >
                      🎨 Canvas
                    </button>

                    <button
                      onClick={() => {
                        setShowAutonomyPanel(true);
                        setQuickToolsOpen(false);
                      }}
                      style={{
                        padding: "10px 14px",
                        borderRadius: "8px",
                        border: "none",
                        background: showAutonomyPanel
                          ? "linear-gradient(135deg, #f59e0b, #d97706)"
                          : "rgba(245, 158, 11, 0.12)",
                        color: showAutonomyPanel ? "#fff" : "#fbbf24",
                        cursor: "pointer",
                        fontSize: "0.8em",
                        fontWeight: "600",
                        textAlign: "left",
                      }}
                      title="Open Autonomy controls (Continuous Auto Mode)"
                    >
                      🧠 Autonomy
                    </button>
                  </div>
                )}
              </div>

              {/* 🤖 AI MODEL SELECTOR - Like Copilot's model toggle */}
              <div style={{ position: "relative" }}>
                <button
                  onClick={() => setModelSelectorOpen(!modelSelectorOpen)}
                  style={{
                    padding: "8px 14px",
                    borderRadius: "10px",
                    border: "none",
                    background: modelSelectorOpen
                      ? "linear-gradient(135deg, #10b981, #059669)"
                      : "linear-gradient(135deg, #1f2937, #374151)",
                    color: "#fff",
                    cursor: "pointer",
                    fontSize: "0.7em",
                    fontWeight: "600",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    boxShadow: modelSelectorOpen
                      ? "0 4px 15px rgba(16, 185, 129, 0.4)"
                      : "none",
                    minWidth: "120px",
                  }}
                  title="Select AI Model"
                >
                  <span>🤖</span>
                  <span
                    style={{
                      maxWidth: "100px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {activeProvider === "github"
                      ? "Copilot"
                      : activeProvider.charAt(0).toUpperCase() +
                        activeProvider.slice(1)}
                  </span>
                  <span>{modelSelectorOpen ? "▲" : "▼"}</span>
                </button>
                {modelSelectorOpen && (
                  <div
                    style={{
                      position: "absolute",
                      top: "100%",
                      right: 0,
                      marginTop: "8px",
                      padding: "12px",
                      background: "rgba(11, 11, 21, 0.98)",
                      backdropFilter: "blur(20px)",
                      borderRadius: "12px",
                      border: "1px solid rgba(16, 185, 129, 0.3)",
                      boxShadow: "0 8px 32px rgba(0, 0, 0, 0.6)",
                      zIndex: 1001,
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px",
                      minWidth: "280px",
                    }}
                  >
                    <div
                      style={{
                        padding: "8px 12px",
                        borderBottom: "1px solid rgba(255,255,255,0.1)",
                        marginBottom: "4px",
                      }}
                    >
                      <div
                        style={{
                          fontSize: "0.75em",
                          color: "#9ca3af",
                          fontWeight: "600",
                          textTransform: "uppercase",
                          letterSpacing: "0.05em",
                        }}
                      >
                        🧠 AI Provider
                      </div>
                      <div
                        style={{
                          fontSize: "0.65em",
                          color: "#6b7280",
                          marginTop: "4px",
                        }}
                      >
                        Current: {activeModel || "Default"}
                      </div>
                    </div>

                    {llmProviders.map((provider) => {
                      const providerIcons = {
                        github: "🐙",
                        openai: "🟢",
                        groq: "⚡",
                        grok: "𝕏",
                        ollama: "🦙",
                        deepseek: "🔮",
                      };
                      const providerNames = {
                        github: "GitHub Copilot",
                        openai: "OpenAI GPT",
                        groq: "Groq (Fast)",
                        grok: "Grok (xAI)",
                        ollama: "Ollama (Local)",
                        deepseek: "DeepSeek",
                      };
                      const isActive = provider.id === activeProvider;
                      const isConfigured = provider.configured;
                      const models =
                        providerModels[provider.id] ||
                        provider.supported_models ||
                        [];

                      return (
                        <div
                          key={provider.id}
                          style={{
                            display: "flex",
                            flexDirection: "column",
                            gap: "6px",
                            padding: "10px",
                            background: isActive
                              ? "rgba(16, 185, 129, 0.08)"
                              : "rgba(255, 255, 255, 0.02)",
                            borderRadius: "12px",
                            border: isActive
                              ? "1px solid rgba(16, 185, 129, 0.3)"
                              : "1px solid rgba(255, 255, 255, 0.05)",
                            transition: "all 0.2s ease",
                          }}
                        >
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                            }}
                          >
                            <div
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: "8px",
                              }}
                            >
                              <span style={{ fontSize: "1.2em" }}>
                                {providerIcons[provider.id] || "🤖"}
                              </span>
                              <div
                                style={{
                                  display: "flex",
                                  flexDirection: "column",
                                }}
                              >
                                <span
                                  style={{
                                    fontSize: "0.85em",
                                    fontWeight: "600",
                                    color: isConfigured ? "#fff" : "#6b7280",
                                  }}
                                >
                                  {providerNames[provider.id] || provider.id}
                                </span>
                                {isActive && (
                                  <span
                                    style={{
                                      fontSize: "0.6em",
                                      color: "#10b981",
                                      fontWeight: "700",
                                      textTransform: "uppercase",
                                    }}
                                  >
                                    Active
                                  </span>
                                )}
                              </div>
                            </div>

                            <div
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: "4px",
                              }}
                            >
                              {/* Status Dot */}
                              <div
                                style={{
                                  width: 8,
                                  height: 8,
                                  borderRadius: "50%",
                                  background: isConfigured
                                    ? providerValidation[provider.id]
                                      ? "#10b981"
                                      : "#fbbf24"
                                    : "#ef4444",
                                  marginRight: "4px",
                                }}
                                title={
                                  isConfigured
                                    ? providerValidation[provider.id]
                                      ? "Validated"
                                      : "Configured - validation recommended"
                                    : "Not configured"
                                }
                              />

                              {/* Validate/Configure */}
                              <button
                                onClick={async () => {
                                  try {
                                    setProviderLoading(true);
                                    const res = await axios.get(
                                      `${apiUrl}/agent/provider/validate`,
                                      { params: { provider: provider.id } },
                                    );
                                    alert(
                                      `Provider ${provider.id} validation: ${
                                        res.data.ok ? "OK" : "FAILED"
                                      } - ${res.data.detail}`,
                                    );
                                    setProviderValidation((p) => ({
                                      ...p,
                                      [provider.id]: !!res.data.ok,
                                    }));
                                    fetchProviders();
                                    setProviderLoading(false);
                                  } catch (e) {
                                    setProviderLoading(false);
                                    alert(
                                      `Provider validation failed: ${e.message}`,
                                    );
                                  }
                                }}
                                style={{
                                  padding: "4px 8px",
                                  borderRadius: "6px",
                                  background: isConfigured
                                    ? "rgba(16, 185, 129, 0.2)"
                                    : "rgba(249, 115, 22, 0.2)",
                                  color: isConfigured ? "#10b981" : "#f97316",
                                  border: "none",
                                  cursor: "pointer",
                                  fontSize: "0.65em",
                                  fontWeight: "600",
                                }}
                                disabled={providerLoading}
                              >
                                {isConfigured ? "Check" : "Setup"}
                              </button>

                              {/* Persist Key */}
                              <button
                                onClick={async () => {
                                  const k = prompt(
                                    "Enter API key to persist to .env for " +
                                      provider.id,
                                  );
                                  if (!k) return;
                                  try {
                                    setProviderLoading(true);
                                    const res = await axios.post(
                                      `${apiUrl}/agent/provider/key/persist`,
                                      { provider: provider.id, key: k },
                                    );
                                    alert(
                                      `Persisted ${res.data.env_var} in ${res.data.provider}`,
                                    );
                                    setProviderLoading(false);
                                    fetchProviders();
                                  } catch (err) {
                                    setProviderLoading(false);
                                    alert(`Persist key failed: ${err.message}`);
                                  }
                                }}
                                style={{
                                  padding: "4px 8px",
                                  borderRadius: "6px",
                                  background: "rgba(163, 230, 53, 0.2)",
                                  color: "#a3e635",
                                  border: "none",
                                  cursor: "pointer",
                                  fontSize: "0.65em",
                                }}
                                title="Persist API Key"
                                disabled={providerLoading}
                              >
                                🔑
                              </button>

                              {/* Open In VS Code */}
                              <button
                                onClick={async () => {
                                  try {
                                    setProviderLoading(true);
                                    await axios.post(
                                      `${apiUrl}/agent/env/open`,
                                    );
                                    alert(
                                      "Open request sent to server editor (if allowed)",
                                    );
                                    setProviderLoading(false);
                                  } catch (err) {
                                    setProviderLoading(false);
                                    alert(
                                      `Open In Editor failed: ${err.message}`,
                                    );
                                  }
                                }}
                                style={{
                                  padding: "4px 8px",
                                  borderRadius: "6px",
                                  background: "rgba(96, 165, 250, 0.2)",
                                  color: "#60a5fa",
                                  border: "none",
                                  cursor: "pointer",
                                  fontSize: "0.65em",
                                }}
                                title="Open .env in VS Code"
                                disabled={providerLoading}
                              >
                                💻
                              </button>
                            </div>
                          </div>

                          {isConfigured && (
                            <div
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: "6px",
                                marginTop: "4px",
                              }}
                            >
                              <select
                                value={isActive ? activeModel : ""}
                                onChange={(e) =>
                                  switchProvider(provider.id, e.target.value)
                                }
                                disabled={providerLoading}
                                style={{
                                  flex: 1,
                                  padding: "6px 10px",
                                  borderRadius: "8px",
                                  background: "#0f172a",
                                  color: "#fff",
                                  border: "1px solid rgba(255,255,255,0.1)",
                                  fontSize: "0.75em",
                                  cursor: "pointer",
                                  outline: "none",
                                }}
                              >
                                <option value="">
                                  {isActive
                                    ? "Select Model..."
                                    : "Switch to Provider"}
                                </option>
                                {models.map((m) => (
                                  <option key={m} value={m}>
                                    {m}
                                  </option>
                                ))}
                              </select>
                              <button
                                onClick={() =>
                                  refreshProviderModels(provider.id)
                                }
                                disabled={providerLoading}
                                style={{
                                  padding: "6px 10px",
                                  borderRadius: "8px",
                                  background: "rgba(59, 130, 246, 0.15)",
                                  color: "#60a5fa",
                                  border: "1px solid rgba(96, 165, 250, 0.2)",
                                  fontSize: "0.75em",
                                  cursor: "pointer",
                                  transition: "all 0.2s",
                                }}
                                title="Refresh available models"
                              >
                                🔄
                              </button>
                            </div>
                          )}
                        </div>
                      );
                    })}

                    <div
                      style={{
                        borderTop: "1px solid rgba(255,255,255,0.1)",
                        marginTop: "8px",
                        paddingTop: "8px",
                      }}
                    >
                      <div
                        style={{
                          fontSize: "0.65em",
                          color: "#6b7280",
                          textAlign: "center",
                        }}
                      >
                        💡 Configure API keys in backend/.env
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <button
                onClick={() => {
                  checkSecurityStatus();
                  setSecurityPanelOpen(!securityPanelOpen);
                }}
                style={{
                  padding: "8px 14px",
                  borderRadius: "10px",
                  border:
                    securityStatus?.status === "VULNERABLE"
                      ? "2px solid #ef4444"
                      : "none",
                  background:
                    securityStatus?.status === "SECURE"
                      ? "linear-gradient(135deg, #22c55e, #16a34a)"
                      : securityStatus?.status === "WARNING"
                        ? "linear-gradient(135deg, #f59e0b, #d97706)"
                        : securityStatus?.status === "VULNERABLE"
                          ? "linear-gradient(135deg, #ef4444, #dc2626)"
                          : "linear-gradient(135deg, #6b7280, #4b5563)",
                  color: "#fff",
                  cursor: "pointer",
                  fontSize: "0.7em",
                  fontWeight: "600",
                  boxShadow:
                    securityStatus?.status === "SECURE"
                      ? "0 4px 15px rgba(34, 197, 94, 0.4)"
                      : securityStatus?.status === "VULNERABLE"
                        ? "0 4px 15px rgba(239, 68, 68, 0.5)"
                        : "0 4px 10px rgba(0,0,0,0.3)",
                  animation:
                    securityStatus?.status === "VULNERABLE"
                      ? "pulse 1.5s infinite"
                      : "none",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
                title={`Security: ${
                  securityStatus?.status || "Checking..."
                } - Click for details`}
              >
                {securityLoading
                  ? "⏳"
                  : securityStatus?.status === "SECURE"
                    ? "🔒"
                    : securityStatus?.status === "WARNING"
                      ? "⚠️"
                      : securityStatus?.status === "VULNERABLE"
                        ? "🔓"
                        : "🔍"}
                {securityStatus?.security_score !== undefined && (
                  <span>{securityStatus.security_score}%</span>
                )}
              </button>

              {/* Layout Controls */}
              <LayoutControls
                layoutLocked={layoutLocked}
                setLayoutLocked={setLayoutLocked}
                saveLayout={saveLayout}
                loadLayout={loadLayout}
                layoutSaved={layoutSaved}
                layoutLoaded={layoutLoaded}
              />

              {/* Autonomy Controls */}
              <AutonomyControls
                autoMode={autoMode}
                toggleAutoMode={toggleAutoMode}
                requireApproval={requireApproval}
                setRequireApproval={setRequireApproval}
                autonomyStatus={autonomyStatus}
              />

              <div className="amigos-pill">
                <span
                  className="amigos-pill-dot"
                  style={{
                    background: connectionMeta.color,
                    boxShadow: `0 0 10px ${connectionMeta.color}`,
                  }}
                />
                <span
                  style={{
                    fontSize: "0.7em",
                    color: connectionMeta.color,
                    fontWeight: "600",
                  }}
                >
                  {connectionMeta.label}
                </span>
              </div>
              <div
                className="amigos-pill"
                style={{ border: "1px solid transparent" }}
              >
                <span
                  className="amigos-pill-dot"
                  style={{
                    background: status.includes("Thinking")
                      ? "var(--accent-warning)"
                      : status.includes("Approval")
                        ? "var(--accent-warning)"
                        : "var(--accent-success)",
                    boxShadow: `0 0 10px ${
                      status.includes("Thinking")
                        ? "var(--accent-warning)"
                        : "var(--accent-success)"
                    }`,
                    animation:
                      status !== "Ready" ? "pulse 1s infinite" : "none",
                  }}
                />
                <span
                  style={{
                    fontSize: "0.7em",
                    fontWeight: "600",
                    color: status.includes("Thinking")
                      ? "var(--accent-warning)"
                      : "var(--accent-success)",
                  }}
                >
                  {status}
                </span>
              </div>
            </div>
          </header>

          {/* Hero Section with Radar HUD - aligned near top like original */}
          <div
            style={{
              position: "absolute",
              top: "96px",
              left: "50%",
              transform: "translateX(-50%)",
              textAlign: "center",
              zIndex: 1,
            }}
          >
            <div
              style={{
                position: "relative",
                display: "inline-block",
                padding: "24px 40px",
              }}
            >
              <div
                className="cockpit-radar-shell"
                style={{ width: "320px", height: "320px" }}
              >
                <div className="cockpit-radar-grid" />
                <div className="cockpit-radar-sweep" />
              </div>
              <div className="cockpit-hud-lines" />
              <div
                style={{
                  fontSize: "4em",
                  marginBottom: "16px",
                  filter: "drop-shadow(0 0 30px rgba(99, 102, 241, 0.5))",
                }}
              >
                🤖
              </div>
              <h1
                style={{
                  fontSize: "3em",
                  fontWeight: "900",
                  background:
                    "linear-gradient(135deg, #6366f1, #8b5cf6, #a78bfa, #c4b5fd)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  marginBottom: "12px",
                  letterSpacing: "-2px",
                }}
              >
                Agent Amigos
              </h1>

              {/* ═══════════════════════════════════════════════════════════════ */}
              {/* AGENT TEAM LED PANEL - Shows all agents with status indicators */}
              {/* ═══════════════════════════════════════════════════════════════ */}
              <div
                style={{
                  display: "none" /* HIDDEN - badges moved to sidebar */,
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "12px",
                  padding: "12px 20px",
                  background: "rgba(0, 0, 0, 0.4)",
                  borderRadius: "16px",
                  border: "1px solid rgba(99, 102, 241, 0.2)",
                  marginBottom: "16px",
                  flexWrap: "wrap",
                  maxWidth: "600px",
                  margin: "0 auto 16px auto",
                }}
              >
                {Object.entries(agentTeam.agents || {}).map(
                  ([agentId, agent]) => {
                    const isOnline = agent.status !== "offline";
                    const isWorking = [
                      "working",
                      "thinking",
                      "collaborating",
                    ].includes(agent.status);
                    const ledColor = !isOnline
                      ? "#4b5563"
                      : isWorking
                        ? agent.color
                        : "#22c55e";

                    return (
                      <div
                        key={agentId}
                        title={`${agent.name}\nStatus: ${agent.status}\nModel: ${
                          agentId === "amigos"
                            ? "llama-3.3-70b"
                            : agentId === "ollie"
                              ? "qwen2.5:7b"
                              : agentId === "scrapey"
                                ? "Rule-based + AI"
                                : agentId === "trainer"
                                  ? "Memory Engine"
                                  : "AI-powered"
                        }${
                          agent.current_task
                            ? `\nTask: ${agent.current_task}`
                            : ""
                        }`}
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "center",
                          gap: "4px",
                          padding: "8px 12px",
                          borderRadius: "12px",
                          background: isOnline
                            ? `${agent.color}10`
                            : "rgba(75, 85, 99, 0.15)",
                          border: `1px solid ${
                            isOnline
                              ? `${agent.color}30`
                              : "rgba(75, 85, 99, 0.2)"
                          }`,
                          cursor: "pointer",
                          transition: "all 0.3s ease",
                          minWidth: "80px",
                        }}
                        onClick={() => fetchAgentTeam()}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.transform = "translateY(-2px)";
                          e.currentTarget.style.boxShadow = isOnline
                            ? `0 4px 20px ${agent.color}30`
                            : "none";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.transform = "translateY(0)";
                          e.currentTarget.style.boxShadow = "none";
                        }}
                      >
                        {/* LED + Emoji Row */}
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "6px",
                          }}
                        >
                          {/* LED Indicator */}
                          <div
                            style={{
                              width: "10px",
                              height: "10px",
                              borderRadius: "50%",
                              background: ledColor,
                              boxShadow: isWorking
                                ? `0 0 10px ${ledColor}, 0 0 20px ${ledColor}`
                                : isOnline
                                  ? `0 0 6px ${ledColor}`
                                  : "none",
                              animation: isWorking
                                ? "pulse 1s ease-in-out infinite"
                                : "none",
                            }}
                          />
                          {/* Agent Emoji */}
                          <span style={{ fontSize: "1.2em" }}>
                            {agent.emoji}
                          </span>
                          {/* Working indicator */}
                          {isWorking && (
                            <span
                              style={{
                                fontSize: "0.8em",
                                animation: "pulse 0.5s ease-in-out infinite",
                              }}
                            >
                              ⚡
                            </span>
                          )}
                        </div>
                        {/* Agent Name */}
                        <span
                          style={{
                            fontSize: "0.7em",
                            fontWeight: "600",
                            color: isOnline ? agent.color : "#6b7280",
                          }}
                        >
                          {agentId === "amigos"
                            ? "AMIGOS"
                            : agent.name.toUpperCase().split(" ")[0]}
                        </span>
                        {/* Status */}
                        <span
                          style={{
                            fontSize: "0.55em",
                            color: isOnline ? "#9ca3af" : "#4b5563",
                            textTransform: "capitalize",
                          }}
                        >
                          {agent.status}
                        </span>
                        {/* Tool Indicator LED */}
                        {agent.current_tool && (
                          <div
                            style={{
                              marginTop: "4px",
                              padding: "3px 8px",
                              background: `${agent.color}25`,
                              borderRadius: "8px",
                              border: `1px solid ${agent.color}40`,
                              display: "flex",
                              alignItems: "center",
                              gap: "4px",
                              animation: "pulse 1s ease-in-out infinite",
                            }}
                          >
                            <span style={{ fontSize: "0.75em" }}>
                              {agent.current_tool.emoji || "🔧"}
                            </span>
                            <span
                              style={{
                                fontSize: "0.5em",
                                color: agent.color,
                                fontWeight: "bold",
                                maxWidth: "60px",
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                              }}
                            >
                              {agent.current_tool.name}
                            </span>
                          </div>
                        )}
                      </div>
                    );
                  },
                )}
              </div>

              {/* Active Tools Panel */}
              {agentTeam.active_tools &&
                Object.keys(agentTeam.active_tools).length > 0 && (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: "8px",
                      padding: "8px 16px",
                      background: "rgba(34, 197, 94, 0.1)",
                      borderRadius: "12px",
                      border: "1px solid rgba(34, 197, 94, 0.3)",
                      marginBottom: "12px",
                      flexWrap: "wrap",
                      maxWidth: "600px",
                      margin: "0 auto 12px auto",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "0.7em",
                        color: "#22c55e",
                        fontWeight: "bold",
                      }}
                    >
                      🔧 ACTIVE TOOLS:
                    </span>
                    {Object.entries(agentTeam.active_tools).map(
                      ([agentId, tool]) => (
                        <span
                          key={agentId}
                          style={{
                            fontSize: "0.65em",
                            padding: "2px 8px",
                            background: "rgba(255, 255, 255, 0.1)",
                            borderRadius: "6px",
                            color: "#e5e7eb",
                          }}
                        >
                          {tool.emoji} {tool.name}
                        </span>
                      ),
                    )}
                  </div>
                )}

              {/* Team Summary */}
              <p
                style={{
                  fontSize: "0.85em",
                  color: "#6b7280",
                  marginBottom: "8px",
                }}
              >
                <span style={{ color: "#22c55e" }}>●</span>{" "}
                {agentTeam.summary?.online || 1} agents online
                {agentTeam.summary?.working > 0 && (
                  <span style={{ marginLeft: "12px", color: "#fbbf24" }}>
                    <span style={{ animation: "pulse 1s infinite" }}>⚡</span>{" "}
                    {agentTeam.summary.working} working
                  </span>
                )}
              </p>
              {/* Bottom Quick Access Buttons - HIDDEN (now in sidebar) */}
              <div
                style={{
                  display: "none" /* HIDDEN - moved to sidebar */,
                  gap: "12px",
                  justifyContent: "center",
                  marginTop: "24px",
                  flexWrap: "wrap",
                }}
              >
                {[
                  {
                    label: "🖥️ Computer Control",
                    onClick: () => {
                      setChatMinimized(false);
                    },
                  },
                  {
                    label: "🌐 Web Browsing",
                    onClick: () => {
                      setInternetConsoleOpen(true);
                    },
                  },
                  {
                    label: "📁 File Management",
                    onClick: () => {
                      setFileConsoleOpen(true);
                    },
                  },
                  {
                    label: "🎮 Game Training",
                    onClick: () => {
                      setGameConsoleOpen(true);
                    },
                  },
                  {
                    label: "📊 Finance Tracking",
                    onClick: () => {
                      setFinanceConsoleOpen(true);
                    },
                  },
                  {
                    label: "📱 Chat→Post",
                    onClick: () => {
                      setConversationToPostOpen(true);
                    },
                  },
                  // Demo button - shows multi-agent collaboration
                  {
                    label: demoRunning ? "🔄 Demo Running..." : "🎬 Team Demo",
                    onClick: demoRunning ? null : startFacebookPostDemo,
                    special: true,
                  },
                  // Ollie button - only show when Ollama is running
                  ...(ollamaStatus.running
                    ? [
                        {
                          label: teamModeEnabled
                            ? "🤝 Team Mode"
                            : "🦙 Ask Ollie",
                          onClick: () => {
                            if (teamModeEnabled) {
                              setTeamModeEnabled(false);
                              setMessages((prev) => [
                                ...prev,
                                {
                                  role: "assistant",
                                  content:
                                    "👤 Team Mode disabled. I'll handle everything myself now!",
                                },
                              ]);
                            } else {
                              setInput("Ask Ollie: ");
                            }
                          },
                        },
                      ]
                    : []),
                ].map((feat, i) => (
                  <button
                    key={i}
                    onClick={feat.onClick}
                    disabled={feat.onClick === null}
                    style={{
                      padding: "6px 14px",
                      background: feat.special
                        ? "linear-gradient(135deg, #f97316, #ef4444)"
                        : "rgba(99, 102, 241, 0.18)",
                      border: feat.special
                        ? "1px solid rgba(249, 115, 22, 0.6)"
                        : "1px solid rgba(99, 102, 241, 0.4)",
                      borderRadius: "20px",
                      fontSize: "0.8em",
                      color: "#e5e7eb",
                      cursor: "pointer",
                      transition: "background 0.2s ease, transform 0.1s ease",
                    }}
                    onMouseEnter={(e) => {
                      e.target.style.background =
                        "linear-gradient(135deg, #6366f1, #8b5cf6)";
                      e.target.style.transform = "translateY(-1px)";
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.background = "rgba(99, 102, 241, 0.18)";
                      e.target.style.transform = "translateY(0)";
                    }}
                  >
                    {feat.label}
                  </button>
                ))}
              </div>

              {/* ═══════════════════════════════════════════════════════════════ */}
              {/* DEMO PROGRESS PANEL - Shows multi-agent demo status */}
              {/* ═══════════════════════════════════════════════════════════════ */}
              {(demoRunning || demoProgress || demoResult) && (
                <div
                  style={{
                    marginTop: "24px",
                    padding: "16px 20px",
                    background: "rgba(0, 0, 0, 0.5)",
                    borderRadius: "16px",
                    border: "1px solid rgba(249, 115, 22, 0.3)",
                    maxWidth: "600px",
                    margin: "24px auto 0 auto",
                    textAlign: "left",
                  }}
                >
                  {/* Demo Header */}
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: "12px",
                    }}
                  >
                    <h3
                      style={{
                        margin: 0,
                        fontSize: "1em",
                        color: "#f97316",
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                      }}
                    >
                      🎬 Team Demo: Facebook Post
                      {demoRunning && (
                        <span style={{ animation: "pulse 1s infinite" }}>
                          ⚡
                        </span>
                      )}
                    </h3>
                    {!demoRunning && (
                      <button
                        onClick={resetDemo}
                        style={{
                          padding: "4px 12px",
                          background: "rgba(239, 68, 68, 0.2)",
                          border: "1px solid rgba(239, 68, 68, 0.4)",
                          borderRadius: "8px",
                          color: "#ef4444",
                          fontSize: "0.75em",
                          cursor: "pointer",
                        }}
                      >
                        ✕ Close
                      </button>
                    )}
                  </div>

                  {/* Progress Bar */}
                  {demoProgress && (
                    <div style={{ marginBottom: "12px" }}>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          fontSize: "0.75em",
                          color: "#9ca3af",
                          marginBottom: "4px",
                        }}
                      >
                        <span>
                          Step {demoProgress.current_step} of{" "}
                          {demoProgress.total_steps}
                        </span>
                        <span>
                          {Math.round(
                            (demoProgress.current_step /
                              demoProgress.total_steps) *
                              100,
                          )}
                          %
                        </span>
                      </div>
                      <div
                        style={{
                          height: "6px",
                          background: "rgba(255, 255, 255, 0.1)",
                          borderRadius: "3px",
                          overflow: "hidden",
                        }}
                      >
                        <div
                          style={{
                            height: "100%",
                            width: `${
                              (demoProgress.current_step /
                                demoProgress.total_steps) *
                              100
                            }%`,
                            background:
                              "linear-gradient(90deg, #f97316, #ef4444)",
                            borderRadius: "3px",
                            transition: "width 0.3s ease",
                          }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Current Activity */}
                  {demoProgress?.current_activity && (
                    <div
                      style={{
                        padding: "10px 14px",
                        background: "rgba(249, 115, 22, 0.1)",
                        borderRadius: "10px",
                        border: "1px solid rgba(249, 115, 22, 0.2)",
                        marginBottom: "12px",
                      }}
                    >
                      <p
                        style={{
                          margin: 0,
                          fontSize: "0.85em",
                          color: "#fbbf24",
                          fontWeight: "bold",
                        }}
                      >
                        {demoProgress.current_activity}
                      </p>
                    </div>
                  )}

                  {/* Completed Steps */}
                  {demoProgress?.steps_completed &&
                    demoProgress.steps_completed.length > 0 && (
                      <div style={{ marginBottom: "12px" }}>
                        <p
                          style={{
                            fontSize: "0.7em",
                            color: "#6b7280",
                            margin: "0 0 6px 0",
                          }}
                        >
                          Completed:
                        </p>
                        <div
                          style={{
                            display: "flex",
                            flexWrap: "wrap",
                            gap: "4px",
                          }}
                        >
                          {demoProgress.steps_completed.map((step, i) => (
                            <span
                              key={i}
                              style={{
                                fontSize: "0.65em",
                                padding: "2px 8px",
                                background: "rgba(34, 197, 94, 0.2)",
                                border: "1px solid rgba(34, 197, 94, 0.3)",
                                borderRadius: "6px",
                                color: "#22c55e",
                              }}
                            >
                              ✓ {step}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                  {/* Generated Post Result */}
                  {demoResult && (
                    <div
                      style={{
                        padding: "14px",
                        background: "rgba(34, 197, 94, 0.1)",
                        borderRadius: "12px",
                        border: "1px solid rgba(34, 197, 94, 0.3)",
                      }}
                    >
                      <p
                        style={{
                          fontSize: "0.75em",
                          color: "#22c55e",
                          fontWeight: "bold",
                          margin: "0 0 8px 0",
                        }}
                      >
                        ✨ Generated Facebook Post:
                      </p>
                      <div
                        style={{
                          padding: "12px",
                          background: "rgba(255, 255, 255, 0.05)",
                          borderRadius: "8px",
                          fontSize: "0.8em",
                          color: "#e5e7eb",
                          lineHeight: "1.5",
                          whiteSpace: "pre-wrap",
                        }}
                      >
                        {demoResult}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Floating Chat Console */}
          {!chatMinimized && (
            <div
              ref={chatRef}
              style={{
                position: "fixed",
                left: chatPosition.x,
                top: chatPosition.y,
                width: chatSize.width,
                height: chatSize.height,
                background: "rgba(11, 11, 21, 0.95)",
                backdropFilter: "blur(20px)",
                borderRadius: "20px",
                border: "1px solid rgba(99, 102, 241, 0.4)",
                boxShadow:
                  "0 25px 80px rgba(0, 0, 0, 0.6), 0 0 60px rgba(99, 102, 241, 0.15)",
                display: "flex",
                flexDirection: "column",
                overflow: "hidden",
                zIndex: 1000,
              }}
            >
              {/* Chat Header - Draggable */}
              <div
                onMouseDown={handleChatMouseDown}
                style={{
                  padding: "14px 18px",
                  background:
                    "linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(139, 92, 246, 0.1))",
                  borderBottom: "1px solid rgba(99, 102, 241, 0.2)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  cursor: isChatDragging ? "grabbing" : "grab",
                }}
              >
                <div
                  style={{ display: "flex", alignItems: "center", gap: "10px" }}
                >
                  <div
                    style={{
                      width: "36px",
                      height: "36px",
                      borderRadius: "10px",
                      background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "1.1em",
                    }}
                  >
                    💬
                  </div>
                  <div>
                    <div
                      style={{
                        fontWeight: "700",
                        fontSize: "0.95em",
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                      }}
                    >
                      Amigos Chat
                      {/* Ollie Status Indicator */}
                      <span
                        title={
                          ollamaStatus.running
                            ? `Ollie Online: ${ollamaStatus.models.join(", ")}`
                            : "Ollie Offline - Start Ollama"
                        }
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "4px",
                          padding: "2px 6px",
                          borderRadius: "10px",
                          fontSize: "0.65em",
                          fontWeight: "500",
                          background: ollamaStatus.running
                            ? "rgba(34, 197, 94, 0.2)"
                            : "rgba(239, 68, 68, 0.2)",
                          border: `1px solid ${
                            ollamaStatus.running
                              ? "rgba(34, 197, 94, 0.4)"
                              : "rgba(239, 68, 68, 0.4)"
                          }`,
                          color: ollamaStatus.running ? "#4ade80" : "#f87171",
                          cursor: "pointer",
                        }}
                        onClick={() => checkOllamaStatus()}
                      >
                        🦙 {ollamaStatus.running ? "Ollie" : "Offline"}
                      </span>
                      {/* Team Status Panel */}
                      <TeamStatusPanel
                        agentTeam={agentTeam}
                        onOpenChange={setTeamPanelOpen}
                      />
                      {/* Team Mode Indicator */}
                      {teamModeEnabled && (
                        <span
                          style={{
                            padding: "2px 6px",
                            borderRadius: "10px",
                            fontSize: "0.6em",
                            fontWeight: "500",
                            background: "rgba(99, 102, 241, 0.2)",
                            border: "1px solid rgba(99, 102, 241, 0.4)",
                            color: "#a5b4fc",
                          }}
                        >
                          🤝 Team
                        </span>
                      )}
                      {/* Shared Memory Indicator */}
                      {memoryStats.facts > 0 && (
                        <span
                          title={`Shared Memory: ${
                            memoryStats.conversations || 0
                          } conversations, ${
                            memoryStats.facts || 0
                          } facts learned`}
                          style={{
                            padding: "2px 6px",
                            borderRadius: "10px",
                            fontSize: "0.6em",
                            fontWeight: "500",
                            background: "rgba(236, 72, 153, 0.2)",
                            border: "1px solid rgba(236, 72, 153, 0.4)",
                            color: "#f472b6",
                            cursor: "pointer",
                          }}
                          onClick={() => fetchMemoryStats()}
                        >
                          🧠 {memoryStats.facts}
                        </span>
                      )}
                      {/* Active Skill Indicator */}
                      {amigosSkill !== "default" &&
                        (() => {
                          const skill = AMIGOS_SKILLS.find(
                            (s) => s.key === amigosSkill,
                          );
                          return skill ? (
                            <div
                              style={{
                                display: "flex",
                                flexDirection: "column",
                                alignItems: "flex-start",
                              }}
                            >
                              <span
                                title={`Skill Mode: ${skill.label} - ${skill.prompt}`}
                                style={{
                                  padding: "2px 6px",
                                  borderRadius: "10px",
                                  fontSize: "0.6em",
                                  fontWeight: "500",
                                  background: `${skill.color}22`,
                                  border: `1px solid ${skill.color}66`,
                                  color: skill.color,
                                  cursor: "pointer",
                                }}
                              >
                                {skill.emoji} {skill.label}
                              </span>
                              {skill.subtext && (
                                <span
                                  style={{
                                    fontSize: "0.55em",
                                    color: "#94a3b8",
                                    fontStyle: "italic",
                                    marginLeft: "4px",
                                  }}
                                >
                                  {skill.subtext}
                                </span>
                              )}
                            </div>
                          ) : null;
                        })()}
                    </div>
                    <div style={{ fontSize: "0.65em", color: "#6b7280" }}>
                      {ollamaStatus.running
                        ? "Say 'ask Ollie...' for local AI"
                        : "Ask me anything..."}
                    </div>
                  </div>
                </div>
                <div style={{ display: "flex", gap: "6px" }}>
                  <button
                    onClick={() => setChatMinimized(true)}
                    style={{
                      width: "28px",
                      height: "28px",
                      borderRadius: "8px",
                      border: "none",
                      background: "rgba(255, 255, 255, 0.1)",
                      color: "#9ca3af",
                      cursor: "pointer",
                      fontSize: "0.9em",
                    }}
                  >
                    −
                  </button>
                </div>
              </div>

              {/* ═══════════════════════════════════════════════════════════════ */}
              {/* AGENT LED PANEL - Shows all agents and their engagement status */}
              {/* ═══════════════════════════════════════════════════════════════ */}
              {/* Skill Button Panel for Amigos */}
              <SkillButtonPanel
                activeSkill={amigosSkill}
                setActiveSkill={setAmigosSkill}
              />

              {/* AGENT LED PANEL - Shows all agents and their engagement status */}
              <div
                style={{
                  padding: "8px 12px",
                  background: "rgba(0, 0, 0, 0.4)",
                  borderBottom: "1px solid rgba(99, 102, 241, 0.15)",
                  display: "none", // HIDDEN AS PER USER REQUEST
                  alignItems: "center",
                  gap: "8px",
                  flexWrap: "wrap",
                }}
              >
                <span
                  style={{
                    fontSize: "0.7em",
                    color: "#6b7280",
                    marginRight: "4px",
                  }}
                >
                  Team:
                </span>
                {Object.entries(agentTeam.agents || {}).map(
                  ([agentId, agent]) => {
                    const isOnline = agent.status !== "offline";
                    const isWorking = [
                      "working",
                      "thinking",
                      "collaborating",
                    ].includes(agent.status);
                    const ledColor = !isOnline
                      ? "#4b5563"
                      : isWorking
                        ? agent.color
                        : "#22c55e";
                    const pulseClass = isWorking ? "agent-led-pulse" : "";

                    return (
                      <div
                        key={agentId}
                        title={`${agent.name}: ${agent.status}${
                          agent.current_task ? ` - ${agent.current_task}` : ""
                        }`}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                          padding: "3px 8px",
                          borderRadius: "12px",
                          background: isOnline
                            ? `${agent.color}15`
                            : "rgba(75, 85, 99, 0.2)",
                          border: `1px solid ${
                            isOnline
                              ? `${agent.color}40`
                              : "rgba(75, 85, 99, 0.3)"
                          }`,
                          cursor: "pointer",
                          transition: "all 0.2s ease",
                        }}
                        onClick={() => fetchAgentTeam()}
                      >
                        {/* LED Indicator */}
                        <div
                          className={pulseClass}
                          style={{
                            width: "8px",
                            height: "8px",
                            borderRadius: "50%",
                            background: ledColor,
                            boxShadow: isWorking
                              ? `0 0 8px ${ledColor}, 0 0 12px ${ledColor}`
                              : isOnline
                                ? `0 0 4px ${ledColor}`
                                : "none",
                            animation: isWorking
                              ? "pulse 1.5s ease-in-out infinite"
                              : "none",
                          }}
                        />
                        {/* Agent Emoji */}
                        <span style={{ fontSize: "0.75em" }}>
                          {agent.emoji}
                        </span>
                        {/* Agent Name (shortened) */}
                        <span
                          style={{
                            fontSize: "0.65em",
                            fontWeight: "500",
                            color: isOnline ? agent.color : "#6b7280",
                            maxWidth: "50px",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {agentId === "amigos"
                            ? "Amigos"
                            : agent.name.split(" ")[0]}
                        </span>
                        {/* Working indicator */}
                        {isWorking && (
                          <span
                            style={{
                              fontSize: "0.6em",
                              animation: "spin 1s linear infinite",
                            }}
                          >
                            ⚡
                          </span>
                        )}
                      </div>
                    );
                  },
                )}
                {/* Summary */}
                <span
                  style={{
                    fontSize: "0.6em",
                    color: "#6b7280",
                    marginLeft: "auto",
                    padding: "2px 6px",
                    background: "rgba(99, 102, 241, 0.1)",
                    borderRadius: "8px",
                  }}
                >
                  {agentTeam.summary?.online || 1}/
                  {agentTeam.summary?.total_agents || 5} online
                </span>
              </div>

              {/* Chat Messages + Chart Strip */}
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  flex: 1,
                  minHeight: 0,
                  position: "relative",
                }}
              >
                <div
                  style={{
                    flex: 1,
                    overflowY: "auto",
                    padding: "16px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "12px",
                  }}
                >
                  {messages.map(renderMessage)}
                  {isProcessing && (
                    <div
                      style={{
                        alignSelf: "flex-start",
                        background: "rgba(30, 30, 50, 0.6)",
                        backdropFilter: "blur(8px)",
                        padding: "12px 18px",
                        borderRadius: "16px",
                        fontSize: "0.9em",
                        color: "#94a3b8",
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        border: "1px solid rgba(99, 102, 241, 0.2)",
                        boxShadow: "0 4px 15px rgba(0, 0, 0, 0.1)",
                        animation: "fadeIn 0.3s ease-out",
                      }}
                    >
                      <div
                        className="thinking-dots"
                        style={{
                          display: "flex",
                          gap: "3px",
                          fontSize: "1.5em",
                          lineHeight: "0.5",
                          marginTop: "-8px",
                        }}
                      >
                        <span>.</span>
                        <span>.</span>
                        <span>.</span>
                      </div>
                      <span style={{ fontWeight: "500" }}>
                        Amigos is working...
                      </span>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </div>

              {/* Chat Input */}
              <div
                style={{
                  padding: "14px 16px",
                  borderTop: "1px solid rgba(99, 102, 241, 0.15)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "8px",
                  background: "rgba(0, 0, 0, 0.3)",
                }}
              >
                {/* Attached File Indicator */}
                {attachedFile && (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      padding: "8px 12px",
                      background: "rgba(99, 102, 241, 0.15)",
                      borderRadius: "8px",
                      fontSize: "0.8em",
                    }}
                  >
                    <span>📎</span>
                    <span style={{ color: "#a5b4fc", flex: 1 }}>
                      {attachedFile.name} ({attachedFile.info?.line_count || 0}{" "}
                      lines)
                    </span>
                    <button
                      onClick={() => setAttachedFile(null)}
                      style={{
                        background: "rgba(239, 68, 68, 0.2)",
                        border: "1px solid rgba(239, 68, 68, 0.4)",
                        borderRadius: "4px",
                        color: "#f87171",
                        padding: "2px 8px",
                        cursor: "pointer",
                        fontSize: "0.85em",
                      }}
                    >
                      ✕ Remove
                    </button>
                  </div>
                )}

                {/* Input Row - Responsive */}
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: "8px",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  {/* Hidden File Input */}
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileAttachment}
                    accept=".txt,.md,.json,.xml,.yaml,.yml,.csv,.tsv,.py,.js,.jsx,.ts,.tsx,.html,.css,.java,.cpp,.c,.h,.go,.rs,.rb,.php,.sql,.sh,.bat,.ps1,.log"
                    style={{ display: "none" }}
                  />

                  {/* File Attachment Button */}
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={
                      pendingAction !== null || isProcessing || isUploadingFile
                    }
                    title="Attach file for analysis"
                    style={{
                      minWidth: "36px",
                      width: "36px",
                      height: "36px",
                      borderRadius: "10px",
                      background: attachedFile
                        ? "linear-gradient(135deg, #22c55e, #16a34a)"
                        : "linear-gradient(135deg, #374151, #4b5563)",
                      border: "none",
                      color: "white",
                      cursor:
                        pendingAction || isProcessing || isUploadingFile
                          ? "not-allowed"
                          : "pointer",
                      fontSize: "1em",
                      opacity:
                        pendingAction || isProcessing || isUploadingFile
                          ? 0.5
                          : 1,
                      boxShadow: attachedFile
                        ? "0 4px 15px rgba(34, 197, 94, 0.4)"
                        : "none",
                      flexShrink: 0,
                    }}
                  >
                    {isUploadingFile ? "⏳" : "📎"}
                  </button>

                  {/* Voice Button */}
                  <button
                    onClick={startListening}
                    disabled={pendingAction !== null || isProcessing}
                    style={{
                      minWidth: "36px",
                      width: "36px",
                      height: "36px",
                      borderRadius: "10px",
                      background: isListening
                        ? "linear-gradient(135deg, #ef4444, #dc2626)"
                        : "linear-gradient(135deg, #6366f1, #8b5cf6)",
                      border: "none",
                      color: "white",
                      cursor:
                        pendingAction || isProcessing
                          ? "not-allowed"
                          : "pointer",
                      fontSize: "1em",
                      opacity: pendingAction || isProcessing ? 0.5 : 1,
                      boxShadow: isListening
                        ? "0 4px 15px rgba(239, 68, 68, 0.4)"
                        : "0 4px 15px rgba(99, 102, 241, 0.4)",
                      flexShrink: 0,
                    }}
                    title={isListening ? "Stop listening" : "Voice input"}
                  >
                    {isListening ? "🛑" : "🎤"}
                  </button>

                  {/* Voice Language Selector */}
                  <select
                    value={voiceLang}
                    onChange={(e) => setVoiceLang(e.target.value)}
                    style={{
                      background: "#374151",
                      color: "white",
                      border: "1px solid #4b5563",
                      borderRadius: "8px",
                      fontSize: "0.7em",
                      padding: "2px 4px",
                      cursor: "pointer",
                      outline: "none",
                    }}
                    title="Voice Language"
                  >
                    <option value="en-US">🇺🇸 US</option>
                    <option value="en-GB">🇬🇧 UK</option>
                    <option value="en-AU">🇦🇺 AU</option>
                    <option value="en-IN">🇮🇳 IN</option>
                    <option value="es-ES">🇪🇸 ES</option>
                    <option value="fr-FR">🇫🇷 FR</option>
                    <option value="de-DE">🇩🇪 DE</option>
                    <option value="ja-JP">🇯🇵 JP</option>
                  </select>

                  {/* Cancel All Tasks Button */}
                  <button
                    onClick={async () => {
                      try {
                        setStatus("🛑 Cancelling...");
                        await axios.post(`${apiUrl}/agent/continuous/stop`);
                        await axios.post(`${apiUrl}/agent/autonomy/kill`);

                        // Reset all progress and thinking states
                        setIsProcessing(false);
                        setIsExecuting(false);
                        setIsTyping(false);
                        if (window.speechSynthesis) {
                          window.speechSynthesis.cancel();
                        }

                        setMessages((prev) => [
                          ...prev,
                          {
                            role: "system",
                            content:
                              "🛑 All current tasks and autonomy cancelled.",
                          },
                        ]);
                        setStatus("Ready");
                      } catch (err) {
                        console.error("Cancel failed:", err);
                        setStatus("Ready");
                      }
                    }}
                    style={{
                      minWidth: "36px",
                      width: "36px",
                      height: "36px",
                      borderRadius: "10px",
                      background: "linear-gradient(135deg, #ef4444, #b91c1c)",
                      border: "none",
                      color: "white",
                      cursor: "pointer",
                      fontSize: "1em",
                      boxShadow: "0 4px 15px rgba(239, 68, 68, 0.4)",
                      flexShrink: 0,
                    }}
                    title="Cancel all current tasks"
                  >
                    ⏹️
                  </button>

                  {/* Voice Output Toggle */}
                  <button
                    onClick={cycleVoiceMode}
                    style={{
                      minWidth: "36px",
                      width: "36px",
                      height: "36px",
                      borderRadius: "10px",
                      background:
                        voiceMode === "off"
                          ? "linear-gradient(135deg, #4b5563, #374151)"
                          : voiceMode === "summary"
                            ? "linear-gradient(135deg, #10b981, #059669)"
                            : "linear-gradient(135deg, #22c55e, #16a34a)",
                      border: "none",
                      color: "white",
                      cursor: "pointer",
                      fontSize: "1em",
                      boxShadow:
                        voiceMode === "off"
                          ? "none"
                          : "0 4px 15px rgba(16, 185, 129, 0.35)",
                      flexShrink: 0,
                    }}
                    title={
                      voiceMode === "off"
                        ? "Voice OFF"
                        : voiceMode === "summary"
                          ? "Voice: SUMMARY (speaks only when you ask / after mic questions)"
                          : "Voice: FULL (speaks only when you ask / after mic questions)"
                    }
                  >
                    {voiceMode === "off"
                      ? "🔇"
                      : voiceMode === "summary"
                        ? "🔈"
                        : "🔊"}
                  </button>

                  {/* Always Read Full Toggle */}
                  <button
                    onClick={() => setAlwaysReadFull(!alwaysReadFull)}
                    style={{
                      minWidth: "36px",
                      width: "36px",
                      height: "36px",
                      borderRadius: "10px",
                      background: alwaysReadFull
                        ? "linear-gradient(135deg, #8b5cf6, #7c3aed)"
                        : "linear-gradient(135deg, #4b5563, #374151)",
                      border: "none",
                      color: "white",
                      cursor: "pointer",
                      fontSize: "1em",
                      boxShadow: alwaysReadFull
                        ? "0 4px 15px rgba(139, 92, 246, 0.4)"
                        : "none",
                      flexShrink: 0,
                    }}
                    title={
                      alwaysReadFull
                        ? "Always Read Full Response: ON"
                        : "Always Read Full Response: OFF (reads summary unless asked)"
                    }
                  >
                    {alwaysReadFull ? "📖" : "📑"}
                  </button>

                  {/* Team Mode Toggle - Full Team Coordination */}
                  <button
                    onClick={() => setTeamModeEnabled(!teamModeEnabled)}
                    style={{
                      minWidth: "36px",
                      width: "36px",
                      height: "36px",
                      borderRadius: "10px",
                      background: teamModeEnabled
                        ? "linear-gradient(135deg, #f59e0b, #d97706)"
                        : "linear-gradient(135deg, #4b5563, #374151)",
                      border: "none",
                      color: "white",
                      cursor: "pointer",
                      fontSize: "1em",
                      boxShadow: teamModeEnabled
                        ? "0 4px 15px rgba(245, 158, 11, 0.4)"
                        : "none",
                      flexShrink: 0,
                    }}
                    title={
                      teamModeEnabled
                        ? "Team Mode ON - Full Multi-Agent Coordination Active"
                        : "Team Mode OFF - Click to enable full team collaboration"
                    }
                  >
                    {teamModeEnabled ? "🤝" : "👥"}
                  </button>
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => {
                      // Barge-in: any typing should immediately stop speech.
                      if (window.speechSynthesis)
                        window.speechSynthesis.cancel();
                      setAiSpeaking(false);
                      setInput(e.target.value);
                    }}
                    onKeyDown={(e) => {
                      // Barge-in: any key press stops speech.
                      if (window.speechSynthesis)
                        window.speechSynthesis.cancel();
                      setAiSpeaking(false);

                      if (
                        e.key === "Enter" &&
                        !pendingAction &&
                        !isProcessing
                      ) {
                        sendMessage();
                      }
                    }}
                    placeholder={
                      attachedFile
                        ? `Ask about ${attachedFile.name}...`
                        : pendingAction
                          ? "Approve or cancel..."
                          : isProcessing
                            ? "Processing..."
                            : "Ask me to do something..."
                    }
                    disabled={pendingAction !== null || isProcessing}
                    style={{
                      flex: 1,
                      minWidth: "100px",
                      padding: "10px 12px",
                      borderRadius: "10px",
                      border: "1px solid rgba(99, 102, 241, 0.3)",
                      background: "rgba(30, 30, 50, 0.8)",
                      color: "white",
                      fontSize: "0.85em",
                      outline: "none",
                    }}
                  />
                  {isProcessing ? (
                    <button
                      onClick={stopEverything}
                      style={{
                        padding: "10px 14px",
                        background: "linear-gradient(135deg, #ef4444, #dc2626)",
                        border: "none",
                        borderRadius: "10px",
                        color: "white",
                        cursor: "pointer",
                        fontWeight: "bold",
                        fontSize: "0.8em",
                        flexShrink: 0,
                      }}
                    >
                      Stop
                    </button>
                  ) : (
                    <button
                      onClick={() => sendMessage()}
                      disabled={pendingAction !== null || !input.trim()}
                      style={{
                        padding: "10px 14px",
                        background:
                          pendingAction || !input.trim()
                            ? "rgba(60, 60, 80, 0.8)"
                            : "linear-gradient(135deg, #6366f1, #8b5cf6)",
                        border: "none",
                        borderRadius: "10px",
                        color: "white",
                        cursor:
                          pendingAction || !input.trim()
                            ? "not-allowed"
                            : "pointer",
                        fontWeight: "bold",
                        fontSize: "0.8em",
                        opacity: pendingAction || !input.trim() ? 0.5 : 1,
                        boxShadow:
                          pendingAction || !input.trim()
                            ? "none"
                            : "0 4px 15px rgba(99, 102, 241, 0.4)",
                        flexShrink: 0,
                      }}
                    >
                      Send
                    </button>
                  )}
                  {/* Clear Chat Button */}
                  <button
                    onClick={() => {
                      setMessages([]);
                      setInput("");
                      setAttachedFile(null);
                    }}
                    style={{
                      minWidth: "36px",
                      width: "36px",
                      height: "36px",
                      padding: "0",
                      background: "rgba(239, 68, 68, 0.15)",
                      border: "1px solid rgba(239, 68, 68, 0.4)",
                      borderRadius: "10px",
                      color: "#f87171",
                      cursor: "pointer",
                      fontSize: "1em",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                    title="Clear conversation"
                  >
                    🗑️
                  </button>
                </div>
              </div>

              {/* Resize Handle */}
              <div
                className="chat-resize-handle"
                onMouseDown={(e) => {
                  e.stopPropagation();
                  setIsChatResizing(true);
                }}
                style={{
                  position: "absolute",
                  bottom: 0,
                  right: 0,
                  width: "30px",
                  height: "30px",
                  cursor: "se-resize",
                  background:
                    "linear-gradient(135deg, transparent 50%, rgba(99, 102, 241, 0.6) 50%)",
                  borderRadius: "0 0 20px 0",
                  zIndex: 10,
                }}
              />
            </div>
          )}

          {/* Minimized Chat Button */}
          {chatMinimized && (
            <button
              onClick={() => setChatMinimized(false)}
              style={{
                position: "fixed",
                bottom: "24px",
                right: "24px",
                width: "64px",
                height: "64px",
                borderRadius: "20px",
                background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                border: "none",
                color: "white",
                fontSize: "1.8em",
                cursor: "pointer",
                boxShadow: "0 8px 30px rgba(99, 102, 241, 0.5)",
                zIndex: 1000,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              💬
            </button>
          )}

          {/* Global Agent Pulse Window */}
          {(() => {
            const entries = Object.entries(agentTeam?.agents || {});
            const isFresh =
              agentTeamUpdatedAt && Date.now() - agentTeamUpdatedAt < 15000;
            const workingCount = entries.filter(([, agent]) => {
              const status = String(agent?.status || "idle").toLowerCase();
              return (
                isFresh &&
                [
                  "working",
                  "thinking",
                  "collaborating",
                  "busy",
                  "running",
                ].includes(status)
              );
            }).length;
            const totalCount = entries.length || 1;

            return (
              <div
                ref={agentPulseRef}
                style={{
                  position: "fixed",
                  left: agentPulsePosition.x,
                  top: agentPulsePosition.y,
                  zIndex: 1001,
                  cursor: agentPulseDragging ? "grabbing" : "grab",
                }}
              >
                <style>{`
                  @keyframes agentPulseGlow {
                    0% { transform: scale(0.92); opacity: 0.55; }
                    50% { transform: scale(1); opacity: 1; }
                    100% { transform: scale(0.92); opacity: 0.55; }
                  }
                `}</style>
                {agentPulseMinimized ? (
                  <div
                    onMouseDown={(e) => {
                      const rect = e.currentTarget.getBoundingClientRect();
                      setAgentPulseDragging(true);
                      setAgentPulseDragOffset({
                        x: e.clientX - rect.left,
                        y: e.clientY - rect.top,
                      });
                    }}
                    onDoubleClick={() => setAgentPulseMinimized(false)}
                    style={{
                      padding: "8px 12px",
                      borderRadius: "12px",
                      background: "rgba(15, 23, 42, 0.9)",
                      border: "1px solid rgba(99, 102, 241, 0.4)",
                      color: "#e5e7eb",
                      fontSize: "0.75em",
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      boxShadow: "0 10px 30px rgba(0,0,0,0.4)",
                    }}
                    title="Double-click to expand"
                  >
                    <span>🧠 Agent Pulse</span>
                    <span style={{ color: "#34d399", fontWeight: 700 }}>
                      {workingCount}/{totalCount}
                    </span>
                  </div>
                ) : (
                  <div
                    style={{
                      width: 260,
                      background: "rgba(8, 11, 20, 0.97)",
                      border: "1px solid rgba(99, 102, 241, 0.4)",
                      borderRadius: "14px",
                      boxShadow: "0 18px 50px rgba(0,0,0,0.55)",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      onMouseDown={(e) => {
                        const rect = e.currentTarget.getBoundingClientRect();
                        setAgentPulseDragging(true);
                        setAgentPulseDragOffset({
                          x: e.clientX - rect.left,
                          y: e.clientY - rect.top,
                        });
                      }}
                      style={{
                        padding: "10px 12px",
                        background:
                          "linear-gradient(135deg, rgba(99,102,241,0.25), rgba(15,23,42,0.9))",
                        borderBottom: "1px solid rgba(99, 102, 241, 0.2)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        color: "#e2e8f0",
                        fontSize: "0.8em",
                        fontWeight: 700,
                      }}
                    >
                      <span>Agent Pulse</span>
                      <button
                        onClick={() => setAgentPulseMinimized(true)}
                        style={{
                          background: "rgba(255,255,255,0.1)",
                          border: "none",
                          color: "#cbd5f5",
                          width: "24px",
                          height: "24px",
                          borderRadius: "8px",
                          cursor: "pointer",
                          fontSize: "0.9em",
                        }}
                        title="Minimize"
                      >
                        −
                      </button>
                    </div>
                    <div
                      style={{
                        padding: "10px 12px",
                        display: "grid",
                        gap: "8px",
                      }}
                    >
                      {entries.map(([key, agent]) => {
                        const status = String(
                          agent?.status || "idle",
                        ).toLowerCase();
                        const isActive =
                          isFresh &&
                          [
                            "working",
                            "thinking",
                            "collaborating",
                            "busy",
                            "running",
                          ].includes(status);
                        const color = isActive ? "#34d399" : "#94a3b8";
                        const taskLabel = isFresh
                          ? agent?.current_task || "Idle"
                          : "No live signal";
                        return (
                          <div
                            key={key}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              padding: "6px 8px",
                              borderRadius: "10px",
                              background: "rgba(15, 23, 42, 0.6)",
                              border: "1px solid rgba(255,255,255,0.05)",
                            }}
                          >
                            <div
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: "8px",
                              }}
                            >
                              <div
                                style={{
                                  width: "8px",
                                  height: "8px",
                                  borderRadius: "50%",
                                  background: color,
                                  animation: isActive
                                    ? "agentPulseGlow 1.6s ease-in-out infinite"
                                    : "none",
                                }}
                              />
                              <span style={{ fontSize: "0.8em" }}>
                                {agent?.emoji || "🤖"}
                              </span>
                              <div>
                                <div
                                  style={{
                                    fontSize: "0.78em",
                                    fontWeight: 700,
                                    color: "#e2e8f0",
                                  }}
                                >
                                  {agent?.name || key}
                                </div>
                                <div
                                  style={{
                                    fontSize: "0.65em",
                                    color: "#94a3b8",
                                  }}
                                >
                                  {taskLabel}
                                </div>
                              </div>
                            </div>
                            <span style={{ fontSize: "0.65em", color }}>
                              {isFresh ? status.toUpperCase() : "STALE"}
                            </span>
                          </div>
                        );
                      })}
                      {!entries.length && (
                        <div
                          style={{
                            fontSize: "0.7em",
                            color: "#94a3b8",
                            textAlign: "center",
                            padding: "6px 0",
                          }}
                        >
                          No agent telemetry available.
                        </div>
                      )}
                      <div
                        style={{
                          fontSize: "0.65em",
                          color: "#94a3b8",
                          textAlign: "right",
                        }}
                      >
                        Active: {workingCount}/{totalCount}
                      </div>
                      {!isFresh && (
                        <div
                          style={{
                            fontSize: "0.65em",
                            color: "#fbbf24",
                            textAlign: "right",
                          }}
                        >
                          Telemetry stale — refresh backend.
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })()}

          {/* Footer */}
          <div
            style={{
              position: "absolute",
              bottom: 0,
              left: 0,
              right: 0,
              padding: "8px",
              textAlign: "center",
              fontSize: "0.85em",
              color: "rgba(148, 163, 184, 0.9)",
              background:
                "linear-gradient(180deg, transparent, rgba(0,0,0,0.5))",
            }}
          >
            ✨ Agent Amigos © 2025 Darrell Buttigieg. All Rights Reserved. ✨
          </div>

          {/* Media Console - Image/Video/Audio Viewer & Generator */}
          <MediaConsole
            isOpen={mediaConsoleOpen}
            onToggle={() => setMediaConsoleOpen(!mediaConsoleOpen)}
            apiUrl={apiUrl}
            onAmigosComment={(comment) => {
              // Do not auto-speak unsolicited comments. (User can explicitly ask for spoken summaries.)
              // We keep this hook for future explicit "read aloud" UX, but default behavior is silent.
              return;
            }}
            onScreenUpdate={updateMediaContext}
            onSendToCanvas={handleSendToCanvas}
          />

          {/* Scraper Workbench - AI Web Scraping toolkit */}
          <ScraperWorkbench
            isOpen={scraperConsoleOpen}
            onToggle={() => setScraperConsoleOpen(!scraperConsoleOpen)}
            apiUrl={apiUrl}
            onScreenUpdate={updateScraperContext}
          />

          {/* Internet Console - News & Web Search */}
          <InternetConsole
            isOpen={internetConsoleOpen}
            onToggle={() => setInternetConsoleOpen(!internetConsoleOpen)}
            apiUrl={apiUrl}
            externalResults={searchResults}
            onScreenUpdate={updateInternetContext}
            onSendMessage={(msg) => {
              setInput(msg);
              handleSend(msg);
            }}
          />

          {/* Macro Console - Autonomous Behavior Engine */}
          <MacroConsole
            isOpen={macroConsoleOpen}
            onClose={() => setMacroConsoleOpen(false)}
            apiUrl={apiUrl}
          />

          {/* Maps & Earth Console */}
          <MapConsole
            isOpen={mapConsoleOpen}
            onToggle={() => setMapConsoleOpen(!mapConsoleOpen)}
            externalCommand={mapCommand}
            onScreenUpdate={updateMapContext}
          />

          {/* Weather Console - Live conditions + 7-day forecast */}
          <WeatherConsole
            isOpen={weatherConsoleOpen}
            onToggle={() => setWeatherConsoleOpen(!weatherConsoleOpen)}
            apiUrl={apiUrl}
            onScreenUpdate={updateWeatherContext}
          />

          {/* Communications Console */}
          <CommunicationsConsole
            isOpen={communicationsConsoleOpen}
            onToggle={() =>
              setCommunicationsConsoleOpen(!communicationsConsoleOpen)
            }
            apiUrl={apiUrl}
          />

          {/* Company Command Center */}
          <CompanyConsole
            isOpen={companyConsoleOpen}
            onToggle={() => setCompanyConsoleOpen(!companyConsoleOpen)}
            agentTeam={agentTeam}
            apiUrl={apiUrl}
            onAskAmigos={(text, snapshot) => {
              const trimmed = String(text || "").trim();
              if (!trimmed || isProcessing) return;
              let payload = trimmed;
              if (snapshot) {
                payload +=
                  "\n\nCompany Snapshot (live data): " +
                  JSON.stringify(snapshot);
              }
              setInput(payload);
              sendMessage(payload);
            }}
          />

          {openworkConsoleOpen && (
            <div
              ref={openworkRef}
              style={{
                position: "fixed",
                top: `${openworkPosition.y}px`,
                left: `${openworkPosition.x}px`,
                width: `${openworkSize.width}px`,
                height: `${openworkSize.height}px`,
                zIndex: 9997,
                borderRadius: "16px",
                overflow: "hidden",
                border: "1px solid rgba(99, 102, 241, 0.3)",
                boxShadow:
                  "0 20px 50px rgba(0, 0, 0, 0.55), 0 0 40px rgba(99, 102, 241, 0.15)",
                background: "#0b0f1f",
                display: "flex",
                flexDirection: "column",
              }}
            >
              <div
                onMouseDown={(e) => {
                  if (e.button !== 0) return;
                  setOpenworkIsDragging(true);
                  setOpenworkDragOffset({
                    x: e.clientX - openworkPosition.x,
                    y: e.clientY - openworkPosition.y,
                  });
                  e.preventDefault();
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "12px",
                  padding: "10px 14px",
                  background: "rgba(15, 23, 42, 0.9)",
                  borderBottom: "1px solid rgba(99, 102, 241, 0.3)",
                  cursor: openworkIsDragging ? "grabbing" : "grab",
                  userSelect: "none",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: "0.9em" }}>🔧</span>
                  <span style={{ fontWeight: 700, fontSize: "0.9em" }}>
                    OpenWork Console
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <button
                    onClick={() => setOpenWorkConsoleOpen(false)}
                    onMouseDown={(e) => e.stopPropagation()}
                    style={{
                      background: "rgba(15, 23, 42, 0.8)",
                      border: "1px solid rgba(148, 163, 184, 0.35)",
                      color: "#e2e8f0",
                      borderRadius: "10px",
                      width: "32px",
                      height: "32px",
                      cursor: "pointer",
                      fontSize: "0.9em",
                    }}
                    title="Close OpenWork"
                  >
                    ✕
                  </button>
                </div>
              </div>
              <div style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>
                <OpenWorkConsole apiUrl={apiUrl} />
              </div>
              <div
                onMouseDown={(e) => {
                  e.stopPropagation();
                  setOpenworkIsResizing(true);
                }}
                style={{
                  position: "absolute",
                  bottom: 0,
                  right: 0,
                  width: "26px",
                  height: "26px",
                  cursor: "se-resize",
                  background:
                    "linear-gradient(135deg, transparent 50%, rgba(99, 102, 241, 0.7) 50%)",
                  borderRadius: "0 0 14px 0",
                  zIndex: 3,
                }}
              />
            </div>
          )}

          {/* Finance Console - Stocks & Crypto */}
          <FinanceConsole
            isOpen={financeConsoleOpen}
            onToggle={() => setFinanceConsoleOpen(!financeConsoleOpen)}
            apiUrl={apiUrl}
            onScreenUpdate={updateFinanceContext}
          />

          {/* Game Console */}
          <GameTrainerConsole
            isOpen={gameConsoleOpen}
            onToggle={() => setGameConsoleOpen(!gameConsoleOpen)}
            apiUrl={apiUrl}
            onScreenUpdate={updateGameContext}
          />

          {/* Email Itinerary Console */}
          <EmailItineraryConsole
            isOpen={emailConsoleOpen}
            onToggle={() => setEmailConsoleOpen(!emailConsoleOpen)}
            apiUrl={apiUrl}
          />

          {/* File Management Console - Browse, Upload, Analyze, Search */}
          <FileManagementConsole
            isOpen={fileConsoleOpen}
            onToggle={() => setFileConsoleOpen(!fileConsoleOpen)}
            apiUrl={apiUrl}
            onScreenUpdate={updateFilesContext}
          />

          {/* Conversation to SEO Post Console - Convert chat replies to viral posts */}
          <ConversationToPostConsole
            isOpen={conversationToPostOpen}
            onClose={() => setConversationToPostOpen(false)}
            messages={messages}
          />

          {/* Model Dashboard - Model selection & stats */}
          {modelDashboardOpen && (
            <div
              ref={modelPanelRef}
              data-panel="model-dashboard"
              style={{
                position: "fixed",
                top: "80px",
                left: "450px",
                zIndex: 9998,
              }}
            >
              <ModelDashboard
                onModelSelected={async (modelId) => {
                  try {
                    // Persist selection on the backend (models/select expects query param model_id)
                    await axios.post(`${apiUrl}/agent/models/select`, null, {
                      params: { model_id: modelId },
                    });

                    // Update client state
                    setActiveModel(modelId);
                    setModelSelectorOpen(false);

                    // Best-effort refresh of provider models
                    try {
                      await axios.get(
                        `${apiUrl}/agent/provider/models/refresh`,
                        {
                          params: { provider: "ollama" },
                        },
                      );
                    } catch (e) {
                      // ignore refresh failures
                    }
                  } catch (err) {
                    console.error("Failed to select model", err);
                    alert(
                      "Failed to select model: " +
                        (err?.response?.data?.detail || err.message),
                    );
                  }
                }}
              />
            </div>
          )}

          {/* Agent Capabilities Dashboard - Learning & skills */}
          {agentCapabilitiesOpen && (
            <div
              ref={agentPanelRef}
              data-panel="agent-capabilities"
              style={{
                position: "fixed",
                top: "80px",
                left: "20px",
                zIndex: 9998,
              }}
            >
              <AgentCapabilities />
            </div>
          )}

          {/* AI Amiga Avatar - Animated Face with Lip Sync */}
          <AIAvatar
            isSpeaking={aiSpeaking}
            text={aiSpeechText}
            speechWordIndex={aiSpeechWordIndex}
            isVisible={aiAvatarOpen}
            onToggle={() => setAiAvatarOpen(!aiAvatarOpen)}
          />

          {/* Draggable Toggle Controls - avoids overlap with modals and can be repositioned */}
          {showSystemControls && (
            <div
              ref={toggleRef}
              onMouseDown={(e) => {
                const isHandle =
                  e.target.classList &&
                  e.target.classList.contains("toggle-drag-handle");
                if (e.target === e.currentTarget || isHandle) {
                  setIsDragging(true);
                  dragRef.current.startX = e.clientX;
                  dragRef.current.startY = e.clientY;
                  dragRef.current.origX = togglePos.left;
                  dragRef.current.origY = togglePos.top;
                }
              }}
              onTouchStart={(e) => {
                const t = e.touches && e.touches[0];
                if (!t) return;
                setIsDragging(true);
                dragRef.current.startX = t.clientX;
                dragRef.current.startY = t.clientY;
                dragRef.current.origX = togglePos.left;
                dragRef.current.origY = togglePos.top;
              }}
              onTouchMove={(e) => {
                if (!isDragging) return;
                const t = e.touches && e.touches[0];
                if (!t) return;
                const dx = t.clientX - dragRef.current.startX;
                const dy = t.clientY - dragRef.current.startY;
                setTogglePos({
                  top: Math.max(8, dragRef.current.origY + dy),
                  left: Math.max(8, dragRef.current.origX + dx),
                });
                e.preventDefault();
              }}
              onTouchEnd={() => setIsDragging(false)}
              tabIndex={0}
              onKeyDown={(e) => {
                const step = e.shiftKey ? 40 : 8;
                if (e.key.startsWith("Arrow")) {
                  e.preventDefault();
                  let { top, left } = togglePos;
                  if (e.key === "ArrowUp") top = Math.max(8, top - step);
                  if (e.key === "ArrowDown") top = Math.max(8, top + step);
                  if (e.key === "ArrowLeft") left = Math.max(8, left - step);
                  if (e.key === "ArrowRight") left = Math.max(8, left + step);
                  setTogglePos({ top, left });
                }
                if (e.key === "r" || e.key === "R") {
                  setTogglePos({ top: 24, left: 24 });
                }
              }}
              style={{
                position: "fixed",
                top: togglePos.top,
                left: togglePos.left,
                zIndex: 4000,
                display: "flex",
                flexDirection: "column",
                gap: "6px",
                padding: isTogglesMinimized ? "4px 6px" : "12px",
                borderRadius: 12,
                background: isTogglesMinimized
                  ? "rgba(8, 10, 20, 0.4)"
                  : "rgba(10, 10, 25, 0.95)",
                border: isTogglesMinimized
                  ? "1px solid rgba(255,255,255,0.08)"
                  : "1px solid rgba(99, 102, 241, 0.3)",
                backdropFilter: "blur(12px)",
                boxShadow: isTogglesMinimized
                  ? "0 4px 15px rgba(0,0,0,0.3)"
                  : "0 12px 40px rgba(0,0,0,0.6)",
                cursor: isDragging ? "grabbing" : "grab",
                transition: isDragging
                  ? "none"
                  : "top 200ms ease, left 200ms ease, padding 200ms ease",
                willChange: "top, left",
                touchAction: "none",
                minWidth: isTogglesMinimized ? 30 : 260,
                minHeight: isTogglesMinimized ? "auto" : 180,
                maxWidth: isTogglesMinimized ? "auto" : 520,
                maxHeight: isTogglesMinimized ? "auto" : "70vh",
                resize: isTogglesMinimized ? "none" : "both",
                overflow: isTogglesMinimized ? "hidden" : "auto",
                alignItems: "stretch",
              }}
              title="Drag to reposition system controls (Ctrl+Alt+S to toggle)"
              role="group"
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 8,
                  marginBottom: isTogglesMinimized ? 0 : 10,
                  borderBottom: isTogglesMinimized
                    ? "none"
                    : "1px solid rgba(255,255,255,0.1)",
                  paddingBottom: isTogglesMinimized ? 0 : 6,
                }}
              >
                {!isTogglesMinimized && (
                  <div style={{ display: "flex", gap: "12px" }}>
                    <button
                      onClick={() => setActiveSystemTab("controls")}
                      style={{
                        background: "none",
                        border: "none",
                        color:
                          activeSystemTab === "controls"
                            ? "#a78bfa"
                            : "#64748b",
                        fontSize: "11px",
                        fontWeight: "bold",
                        cursor: "pointer",
                        padding: "2px 0",
                        borderBottom:
                          activeSystemTab === "controls"
                            ? "2px solid #a78bfa"
                            : "2px solid transparent",
                      }}
                    >
                      CONTROLS
                    </button>
                    <button
                      onClick={() => setActiveSystemTab("settings")}
                      style={{
                        background: "none",
                        border: "none",
                        color:
                          activeSystemTab === "settings"
                            ? "#a78bfa"
                            : "#64748b",
                        fontSize: "11px",
                        fontWeight: "bold",
                        cursor: "pointer",
                        padding: "2px 0",
                        borderBottom:
                          activeSystemTab === "settings"
                            ? "2px solid #a78bfa"
                            : "2px solid transparent",
                      }}
                    >
                      SETTINGS
                    </button>
                  </div>
                )}
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  {!isTogglesMinimized && (
                    <button
                      onClick={() => setTogglePos({ top: 12, left: 12 })}
                      title="Reset position"
                      style={{
                        background: "transparent",
                        border: "none",
                        color: "#64748b",
                        cursor: "pointer",
                        fontSize: 12,
                      }}
                    >
                      ⟳
                    </button>
                  )}
                  <button
                    onClick={() => setIsTogglesMinimized(!isTogglesMinimized)}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: "#64748b",
                      cursor: "pointer",
                      fontSize: 14,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      width: 20,
                      height: 20,
                    }}
                  >
                    {isTogglesMinimized ? "◱" : "−"}
                  </button>
                  <span
                    className="toggle-drag-handle"
                    style={{ cursor: "grab", color: "#64748b", fontSize: 16 }}
                  >
                    ≡
                  </span>
                </div>
              </div>

              {!isTogglesMinimized && activeSystemTab === "controls" && (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "6px",
                  }}
                >
                  <button
                    onClick={() => setModelDashboardOpen(!modelDashboardOpen)}
                    style={{
                      padding: "8px 10px",
                      borderRadius: 8,
                      background: modelDashboardOpen
                        ? "rgba(99, 102, 241, 0.3)"
                        : "rgba(255, 255, 255, 0.05)",
                      border: "1px solid rgba(255, 255, 255, 0.1)",
                      color: "#e0e7ff",
                      cursor: "pointer",
                      textAlign: "left",
                      fontSize: 11,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span>🤖 Model Matrix</span>
                    <span>{modelDashboardOpen ? "●" : "○"}</span>
                  </button>

                  <button
                    onClick={() =>
                      setAgentCapabilitiesOpen(!agentCapabilitiesOpen)
                    }
                    style={{
                      padding: "8px 10px",
                      borderRadius: 8,
                      background: agentCapabilitiesOpen
                        ? "rgba(168, 85, 247, 0.3)"
                        : "rgba(255, 255, 255, 0.05)",
                      border: "1px solid rgba(255, 255, 255, 0.1)",
                      color: "#f5f3ff",
                      cursor: "pointer",
                      textAlign: "left",
                      fontSize: 11,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span>🧠 Capabilities</span>
                    <span>{agentCapabilitiesOpen ? "●" : "○"}</span>
                  </button>

                  <button
                    onClick={() => setTeamPanelOpen(!teamPanelOpen)}
                    style={{
                      padding: "8px 10px",
                      borderRadius: 8,
                      background: teamPanelOpen
                        ? "rgba(34, 197, 94, 0.3)"
                        : "rgba(255, 255, 255, 0.05)",
                      border: "1px solid rgba(255, 255, 255, 0.1)",
                      color: "#f0fdf4",
                      cursor: "pointer",
                      textAlign: "left",
                      fontSize: 11,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span>👥 Agent Team</span>
                    <span>{teamPanelOpen ? "●" : "○"}</span>
                  </button>

                  <button
                    onClick={() => setShowAutonomyPanel(!showAutonomyPanel)}
                    style={{
                      padding: "8px 10px",
                      borderRadius: 8,
                      background: showAutonomyPanel
                        ? "rgba(245, 158, 11, 0.3)"
                        : "rgba(255, 255, 255, 0.05)",
                      border: "1px solid rgba(255, 255, 255, 0.1)",
                      color: "#fff7ed",
                      cursor: "pointer",
                      textAlign: "left",
                      fontSize: 11,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span>⚡ Autonomy Panel</span>
                    <span>{showAutonomyPanel ? "●" : "○"}</span>
                  </button>
                </div>
              )}

              {!isTogglesMinimized && activeSystemTab === "settings" && (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "4px",
                    }}
                  >
                    <label
                      style={{
                        fontSize: "10px",
                        color: "#94a3b8",
                        fontWeight: "600",
                      }}
                    >
                      BACKEND API URL
                    </label>
                    <div style={{ display: "flex", gap: "4px" }}>
                      <input
                        type="text"
                        value={apiUrl}
                        readOnly
                        style={{
                          flex: 1,
                          background: "rgba(0,0,0,0.3)",
                          border: "1px solid rgba(255,255,255,0.1)",
                          borderRadius: 4,
                          color: "#fff",
                          fontSize: "10px",
                          padding: "4px 8px",
                        }}
                      />
                      <button
                        onClick={promptForApiUrl}
                        style={{
                          background: "rgba(99, 102, 241, 0.2)",
                          border: "1px solid rgba(99, 102, 241, 0.4)",
                          borderRadius: 4,
                          color: "#a5b4fc",
                          fontSize: "10px",
                          padding: "0 6px",
                          cursor: "pointer",
                        }}
                      >
                        EDIT
                      </button>
                    </div>
                  </div>

                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr",
                      gap: "6px",
                    }}
                  >
                    <button
                      onClick={() => {
                        const next = !layoutLocked;
                        setLayoutLocked(next);
                        localStorage.setItem(
                          "amigos-layout-locked",
                          JSON.stringify(next),
                        );
                      }}
                      style={{
                        padding: "6px",
                        borderRadius: 6,
                        background: layoutLocked
                          ? "rgba(34, 197, 94, 0.2)"
                          : "rgba(255, 255, 255, 0.05)",
                        border: "1px solid rgba(255, 255, 255, 0.1)",
                        color: "#fff",
                        cursor: "pointer",
                        fontSize: "10px",
                      }}
                    >
                      {layoutLocked ? "🔓 Unlock" : "🔒 Lock"} Layout
                    </button>
                    <button
                      onClick={saveLayout}
                      style={{
                        padding: "6px",
                        borderRadius: 6,
                        background: "rgba(99, 102, 241, 0.2)",
                        border: "1px solid rgba(99, 102, 241, 0.4)",
                        color: "#fff",
                        cursor: "pointer",
                        fontSize: "10px",
                      }}
                    >
                      💾 Save Layout
                    </button>
                  </div>

                  <button
                    onClick={resetApiUrl}
                    style={{
                      padding: "8px",
                      borderRadius: 6,
                      background: "rgba(239, 68, 68, 0.1)",
                      border: "1px solid rgba(239, 68, 68, 0.3)",
                      color: "#fca5a5",
                      cursor: "pointer",
                      fontSize: "10px",
                      fontWeight: "600",
                    }}
                  >
                    🔄 Reset API to Defaults
                  </button>

                  <div
                    style={{
                      marginTop: "6px",
                      padding: "8px",
                      borderRadius: 8,
                      border: "1px solid rgba(99, 102, 241, 0.2)",
                      background: "rgba(15, 23, 42, 0.6)",
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "6px",
                      }}
                    >
                      <span
                        style={{
                          fontSize: "10px",
                          color: "#a5b4fc",
                          fontWeight: "700",
                          textTransform: "uppercase",
                          letterSpacing: "0.04em",
                        }}
                      >
                        🔑 API Keys & Providers
                      </span>
                      <button
                        onClick={fetchEnvStatus}
                        disabled={apiKeySaving}
                        style={{
                          background: "rgba(99, 102, 241, 0.15)",
                          border: "1px solid rgba(99, 102, 241, 0.35)",
                          borderRadius: 6,
                          color: "#c7d2fe",
                          fontSize: "9px",
                          padding: "2px 6px",
                          cursor: "pointer",
                        }}
                      >
                        ↻ Refresh
                      </button>
                    </div>

                    {apiKeyError && (
                      <div
                        style={{
                          fontSize: "9px",
                          color: "#fca5a5",
                          background: "rgba(239, 68, 68, 0.12)",
                          border: "1px solid rgba(239, 68, 68, 0.35)",
                          padding: "4px 6px",
                          borderRadius: 6,
                        }}
                      >
                        {apiKeyError}
                      </div>
                    )}

                    {[
                      {
                        key: "AMIGOS_API_KEY",
                        label: "Amigos Intelligence (Custom)",
                        placeholder: "Custom Amigos API Key",
                        hint: "Optional: Use a specific Amigos server instead of local",
                      },
                      {
                        key: "PLAYWRIGHT_PROXY",
                        label: "Playwright Proxy",
                        placeholder: "http://user:pass@host:port",
                        hint: "Optional proxy for bot-protected sites",
                      },
                    ].map((field) => {
                      const isSet = apiKeyStatus?.[field.key]?.set;
                      return (
                        <div
                          key={field.key}
                          style={{
                            display: "flex",
                            flexDirection: "column",
                            gap: "4px",
                          }}
                        >
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              gap: "6px",
                            }}
                          >
                            <label
                              style={{
                                fontSize: "9px",
                                color: "#94a3b8",
                                fontWeight: "600",
                              }}
                            >
                              {field.label}
                            </label>
                            <span
                              style={{
                                fontSize: "9px",
                                color: isSet ? "#22c55e" : "#f59e0b",
                                fontWeight: "700",
                              }}
                            >
                              {isSet ? "SET" : "MISSING"}
                            </span>
                          </div>
                          <div style={{ display: "flex", gap: "4px" }}>
                            <input
                              type={
                                apiKeyReveal[field.key] ? "text" : "password"
                              }
                              value={apiKeyForm[field.key]}
                              onChange={(e) =>
                                setApiKeyForm((prev) => ({
                                  ...prev,
                                  [field.key]: e.target.value,
                                }))
                              }
                              placeholder={field.placeholder}
                              style={{
                                flex: 1,
                                background: "rgba(0,0,0,0.35)",
                                border: "1px solid rgba(255,255,255,0.1)",
                                borderRadius: 4,
                                color: "#fff",
                                fontSize: "9px",
                                padding: "4px 6px",
                              }}
                            />
                            <button
                              onClick={() =>
                                setApiKeyReveal((prev) => ({
                                  ...prev,
                                  [field.key]: !prev[field.key],
                                }))
                              }
                              style={{
                                background: "rgba(148, 163, 184, 0.1)",
                                border: "1px solid rgba(148, 163, 184, 0.3)",
                                borderRadius: 4,
                                color: "#e2e8f0",
                                fontSize: "9px",
                                padding: "0 6px",
                                cursor: "pointer",
                              }}
                              title={apiKeyReveal[field.key] ? "Hide" : "Show"}
                            >
                              {apiKeyReveal[field.key] ? "🙈" : "👁️"}
                            </button>
                            <button
                              onClick={() =>
                                saveEnvKey(field.key, apiKeyForm[field.key])
                              }
                              disabled={apiKeySaving}
                              style={{
                                background: "rgba(34, 197, 94, 0.15)",
                                border: "1px solid rgba(34, 197, 94, 0.35)",
                                borderRadius: 4,
                                color: "#4ade80",
                                fontSize: "9px",
                                padding: "0 6px",
                                cursor: "pointer",
                              }}
                            >
                              Save
                            </button>
                            <button
                              onClick={() => {
                                setApiKeyForm((prev) => ({
                                  ...prev,
                                  [field.key]: "",
                                }));
                                saveEnvKey(field.key, "");
                              }}
                              disabled={apiKeySaving}
                              style={{
                                background: "rgba(239, 68, 68, 0.15)",
                                border: "1px solid rgba(239, 68, 68, 0.35)",
                                borderRadius: 4,
                                color: "#fca5a5",
                                fontSize: "9px",
                                padding: "0 6px",
                                cursor: "pointer",
                              }}
                            >
                              Clear
                            </button>
                          </div>
                          <span style={{ fontSize: "8px", color: "#64748b" }}>
                            {field.hint}
                          </span>
                        </div>
                      );
                    })}

                    <div style={{ fontSize: "8px", color: "#94a3b8" }}>
                      Changes are saved to backend <code>.env</code>. Restart
                      the Backend API to apply.
                    </div>

                    <div
                      style={{
                        fontSize: "9px",
                        color: "#64748b",
                        marginTop: "8px",
                        fontStyle: "italic",
                        padding: "6px",
                        background: "rgba(0,0,0,0.1)",
                        borderRadius: "6px",
                        border: "1px solid rgba(255,255,255,0.03)",
                      }}
                    >
                      💡 No keys? No problem. The system defaults to{" "}
                      <b>Autonomous Scraper Mode</b> which uses AI and
                      web-scraping for commercial intelligence.
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 🔐 SECURITY PANEL - Monitor and verify security status */}
          {securityPanelOpen && (
            <div
              style={{
                position: "fixed",
                top: "80px",
                right: "20px",
                width: "450px",
                maxHeight: "80vh",
                background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
                borderRadius: "16px",
                border:
                  securityStatus?.status === "SECURE"
                    ? "2px solid #22c55e"
                    : securityStatus?.status === "WARNING"
                      ? "2px solid #f59e0b"
                      : "2px solid #ef4444",
                boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.7)",
                zIndex: 10000,
                overflow: "hidden",
              }}
            >
              {/* Header */}
              <div
                style={{
                  padding: "16px 20px",
                  background:
                    securityStatus?.status === "SECURE"
                      ? "linear-gradient(135deg, #22c55e, #16a34a)"
                      : securityStatus?.status === "WARNING"
                        ? "linear-gradient(135deg, #f59e0b, #d97706)"
                        : "linear-gradient(135deg, #ef4444, #dc2626)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div
                  style={{ display: "flex", alignItems: "center", gap: "12px" }}
                >
                  <span style={{ fontSize: "1.5em" }}>
                    {securityStatus?.status === "SECURE"
                      ? "🔒"
                      : securityStatus?.status === "WARNING"
                        ? "⚠️"
                        : "🔓"}
                  </span>
                  <div>
                    <h3
                      style={{
                        margin: 0,
                        color: "#fff",
                        fontSize: "1.1em",
                        fontWeight: "700",
                      }}
                    >
                      Security Status: {securityStatus?.status || "CHECKING"}
                    </h3>
                    <p
                      style={{
                        margin: 0,
                        color: "rgba(255,255,255,0.8)",
                        fontSize: "0.75em",
                      }}
                    >
                      Score: {securityStatus?.security_score || 0}% • Owner:{" "}
                      {securityStatus?.owner || "Darrell Buttigieg"}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setSecurityPanelOpen(false)}
                  style={{
                    background: "rgba(255,255,255,0.2)",
                    border: "none",
                    borderRadius: "8px",
                    padding: "8px 12px",
                    color: "#fff",
                    cursor: "pointer",
                    fontSize: "0.9em",
                  }}
                >
                  ✕
                </button>
              </div>

              {/* Content */}
              <div
                style={{
                  padding: "16px 20px",
                  maxHeight: "60vh",
                  overflowY: "auto",
                }}
              >
                {/* Security Checks */}
                <div style={{ marginBottom: "16px" }}>
                  <h4
                    style={{
                      color: "#22c55e",
                      margin: "0 0 12px 0",
                      fontSize: "0.9em",
                    }}
                  >
                    ✅ Security Checks
                  </h4>
                  <div style={{ display: "grid", gap: "8px" }}>
                    {securityStatus?.checks &&
                      Object.entries(securityStatus.checks).map(
                        ([key, value]) => (
                          <div
                            key={key}
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              padding: "8px 12px",
                              background: "rgba(255,255,255,0.05)",
                              borderRadius: "8px",
                              borderLeft: value
                                ? "3px solid #22c55e"
                                : "3px solid #ef4444",
                            }}
                          >
                            <span
                              style={{ color: "#94a3b8", fontSize: "0.85em" }}
                            >
                              {key
                                .replace(/_/g, " ")
                                .replace(/\b\w/g, (l) => l.toUpperCase())}
                            </span>
                            <span
                              style={{
                                color: value ? "#22c55e" : "#ef4444",
                                fontWeight: "600",
                              }}
                            >
                              {value ? "✓ PASS" : "✗ FAIL"}
                            </span>
                          </div>
                        ),
                      )}
                  </div>
                </div>

                {/* Issues */}
                {securityStatus?.issues?.length > 0 && (
                  <div style={{ marginBottom: "16px" }}>
                    <h4
                      style={{
                        color: "#ef4444",
                        margin: "0 0 12px 0",
                        fontSize: "0.9em",
                      }}
                    >
                      🚨 Security Issues ({securityStatus.issues.length})
                    </h4>
                    {securityStatus.issues.map((issue, i) => (
                      <div
                        key={i}
                        style={{
                          padding: "10px 12px",
                          background: "rgba(239, 68, 68, 0.1)",
                          borderRadius: "8px",
                          border: "1px solid rgba(239, 68, 68, 0.3)",
                          color: "#fca5a5",
                          fontSize: "0.85em",
                          marginBottom: "8px",
                        }}
                      >
                        {issue}
                      </div>
                    ))}
                  </div>
                )}

                {/* Warnings */}
                {securityStatus?.warnings?.length > 0 && (
                  <div style={{ marginBottom: "16px" }}>
                    <h4
                      style={{
                        color: "#f59e0b",
                        margin: "0 0 12px 0",
                        fontSize: "0.9em",
                      }}
                    >
                      ⚠️ Warnings ({securityStatus.warnings.length})
                    </h4>
                    {securityStatus.warnings.map((warning, i) => (
                      <div
                        key={i}
                        style={{
                          padding: "10px 12px",
                          background: "rgba(245, 158, 11, 0.1)",
                          borderRadius: "8px",
                          border: "1px solid rgba(245, 158, 11, 0.3)",
                          color: "#fcd34d",
                          fontSize: "0.85em",
                          marginBottom: "8px",
                        }}
                      >
                        {warning}
                      </div>
                    ))}
                  </div>
                )}

                {/* Server Info */}
                <div style={{ marginBottom: "16px" }}>
                  <h4
                    style={{
                      color: "#6366f1",
                      margin: "0 0 12px 0",
                      fontSize: "0.9em",
                    }}
                  >
                    🖥️ Server Information
                  </h4>
                  <div
                    style={{
                      padding: "12px",
                      background: "rgba(99, 102, 241, 0.1)",
                      borderRadius: "8px",
                      border: "1px solid rgba(99, 102, 241, 0.3)",
                    }}
                  >
                    <div
                      style={{
                        display: "grid",
                        gap: "6px",
                        fontSize: "0.85em",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                        }}
                      >
                        <span style={{ color: "#94a3b8" }}>Host:</span>
                        <span
                          style={{ color: "#e2e8f0", fontFamily: "monospace" }}
                        >
                          {securityStatus?.server_info?.host || "127.0.0.1"}
                        </span>
                      </div>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                        }}
                      >
                        <span style={{ color: "#94a3b8" }}>Port:</span>
                        <span
                          style={{ color: "#e2e8f0", fontFamily: "monospace" }}
                        >
                          {securityStatus?.server_info?.port || "8080"}
                        </span>
                      </div>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                        }}
                      >
                        <span style={{ color: "#94a3b8" }}>Model:</span>
                        <span
                          style={{
                            color: "#e2e8f0",
                            fontFamily: "monospace",
                            fontSize: "0.8em",
                          }}
                        >
                          {securityStatus?.server_info?.model || "Unknown"}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* VS Code Recommendations */}
                <div style={{ marginBottom: "16px" }}>
                  <h4
                    style={{
                      color: "#8b5cf6",
                      margin: "0 0 12px 0",
                      fontSize: "0.9em",
                    }}
                  >
                    📝 VS Code Security Settings
                  </h4>
                  <div style={{ display: "grid", gap: "6px" }}>
                    {(
                      securityStatus?.vscode_recommendations || [
                        "📝 Set 'remote.autoForwardPorts' to false",
                        "📝 Set 'remote.localPortHost' to 'localhost'",
                        "📝 Disable unused extensions",
                        "📝 Enable Workspace Trust",
                      ]
                    ).map((rec, i) => (
                      <div
                        key={i}
                        style={{
                          padding: "8px 12px",
                          background: "rgba(139, 92, 246, 0.1)",
                          borderRadius: "6px",
                          color: "#c4b5fd",
                          fontSize: "0.8em",
                        }}
                      >
                        {rec}
                      </div>
                    ))}
                  </div>
                </div>

                {/* General Recommendations */}
                <div>
                  <h4
                    style={{
                      color: "#22c55e",
                      margin: "0 0 12px 0",
                      fontSize: "0.9em",
                    }}
                  >
                    🔒 Security Recommendations
                  </h4>
                  <div style={{ display: "grid", gap: "6px" }}>
                    {(securityStatus?.recommendations || [])
                      .slice(0, 5)
                      .map((rec, i) => (
                        <div
                          key={i}
                          style={{
                            padding: "8px 12px",
                            background: "rgba(34, 197, 94, 0.1)",
                            borderRadius: "6px",
                            color: "#86efac",
                            fontSize: "0.8em",
                          }}
                        >
                          {rec}
                        </div>
                      ))}
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div
                style={{
                  padding: "12px 20px",
                  background: "rgba(0,0,0,0.3)",
                  borderTop: "1px solid rgba(255,255,255,0.1)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span style={{ color: "#64748b", fontSize: "0.75em" }}>
                  Last checked:{" "}
                  {securityStatus?.timestamp
                    ? new Date(securityStatus.timestamp).toLocaleTimeString()
                    : "Never"}
                </span>
                <button
                  onClick={checkSecurityStatus}
                  disabled={securityLoading}
                  style={{
                    padding: "8px 16px",
                    background: "linear-gradient(135deg, #6366f1, #4f46e5)",
                    border: "none",
                    borderRadius: "8px",
                    color: "#fff",
                    cursor: securityLoading ? "wait" : "pointer",
                    fontSize: "0.8em",
                    fontWeight: "600",
                    opacity: securityLoading ? 0.7 : 1,
                  }}
                >
                  {securityLoading ? "⏳ Checking..." : "🔄 Refresh"}
                </button>
              </div>
            </div>
          )}

          {/* CSS Animation */}
          <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
        @keyframes gradientShift {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        @keyframes glow {
          0%, 100% { box-shadow: 0 0 20px rgba(99, 102, 241, 0.3); }
          50% { box-shadow: 0 0 40px rgba(99, 102, 241, 0.6); }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes ledPulse {
          0%, 100% { 
            opacity: 1; 
            box-shadow: 0 0 10px currentColor, 0 0 20px currentColor;
          }
          50% { 
            opacity: 0.6; 
            box-shadow: 0 0 5px currentColor, 0 0 10px currentColor;
          }
        }
      `}</style>

          {showAutonomyPanel && (
            <div style={{ position: "fixed", right: 8, top: 8, zIndex: 1000 }}>
              <AutonomyPanel
                onClose={() => setShowAutonomyPanel(false)}
                apiUrl={apiUrl}
              />
            </div>
          )}

          {/* 🎨 CANVAS PANEL */}
          {canvasOpen && (
            <CanvasPanel
              isOpen={true}
              onClose={() => setCanvasOpen(false)}
              onAgentCommand={(cmd) => console.log("Canvas command:", cmd)}
              apiUrl={apiUrl}
              agentCommands={canvasCommands}
              onCommandsProcessed={() => setCanvasCommands([])}
              onAgentResponse={(res) => {
                // simple UX telemetry & console log; server-side ack handled by CanvasPanel
                console.log("Agent response:", res);
              }}
              onSessionReady={(id) => setCanvasSession(id)}
            />
          )}
        </div>
      )}
    </AppErrorBoundary>
  );
}

export default App;
