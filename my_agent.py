import os, time
from tools import run_tool, TOOL_DESCRIPTIONS

# ── GROQ CLIENT ─────────────────────────────────────────────
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # ✅ FIXED: placeholder key
MODEL = "llama-3.3-70b-versatile"   # ✅ FIXED: was "llama-3.1-8b-instant" (deprecated)


def get_groq_client():
    if not GROQ_AVAILABLE or not GROQ_API_KEY:
        return None
    return Groq(api_key=GROQ_API_KEY)


def llm_call(system_prompt, user_prompt):
    client = get_groq_client()
    if client:
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt}
                ],
                temperature=0.3
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"[LLM Error: {e}]"
    return "[No LLM available]"


# ═════════════════════════════════════════════════════════════
# BASE AGENT
# ═════════════════════════════════════════════════════════════
class BaseAgent:
    def __init__(self, name, role, tools, description):
        self.name        = name
        self.role        = role
        self.tools       = tools
        self.description = description
        self.memory      = []
        self.log         = []

    def think(self, task):
        tool_desc = "\n".join(
            f"{t}: {TOOL_DESCRIPTIONS.get(t, '')}" for t in self.tools
        )
        system = (
            f"You are {self.name}, {self.role}. {self.description}\n"
            f"Available tools:\n{tool_desc}"
        )
        return llm_call(system, f"Task: {task}")

    def act(self, tool_name, **kwargs):
        self.log.append({"tool": tool_name, "args": kwargs, "time": time.time()})
        result = run_tool(tool_name, **kwargs)
        self.memory.append(result)
        return result

    def get_status(self):
        return {
            "agent":        self.name,
            "role":         self.role,
            "tools":        self.tools,
            "memory_items": len(self.memory),
            "log_entries":  len(self.log),
        }


# ═════════════════════════════════════════════════════════════
# RESEARCHER
# ═════════════════════════════════════════════════════════════
class ResearcherAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "ResearcherAgent",
            "Research Specialist",
            ["search_wikipedia", "search_web", "search_arxiv"],
            "Collect detailed research data from multiple sources."
        )

    def run(self, topic):
        wiki   = self.act("search_wikipedia", query=topic)
        web    = self.act("search_web",       query=topic)
        arxiv  = self.act("search_arxiv",     query=topic)

        return {
            "data": {"wiki": wiki, "web": web, "arxiv": arxiv},
            "synthesis": self.think(f"Summarize key research findings on: {topic}"),
        }


# ═════════════════════════════════════════════════════════════
# NEWS
# ═════════════════════════════════════════════════════════════
class NewsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "NewsAgent",
            "News Analyst",
            ["fetch_news", "search_web"],
            "Find and analyse the latest news articles."
        )

    def run(self, topic):
        news = self.act("fetch_news", topic=topic)
        return {
            "data":      {"news": news},
            "synthesis": self.think(f"Summarise and analyse the latest news about: {topic}"),
        }


# ═════════════════════════════════════════════════════════════
# FACT CHECKER
# ═════════════════════════════════════════════════════════════
class FactChecker(BaseAgent):
    def __init__(self):
        super().__init__(
            "FactChecker",
            "Fact Checker",
            ["fact_check"],
            "Verify claims and assess their credibility."
        )

    def run(self, claims):
        results = [self.act("fact_check", claim=c) for c in claims]
        return {
            "verifications": results,
            "summary": {"total": len(results)},
        }


# ═════════════════════════════════════════════════════════════
# SUMMARIZER  ← THE FIX IS HERE
# ═════════════════════════════════════════════════════════════
class SummarizerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "SummarizerAgent",
            "Research Summarizer",
            ["summarize_text"],
            "Synthesise all collected research into a final structured report."
        )

    def run(self, data):
        # ✅ FIX: extract everything collected by the other agents
        topic = data.get("topic", "the research topic")

        # --- researcher output ---
        researcher         = data.get("researcher", {})
        wiki_data          = researcher.get("data", {}).get("wiki",  "N/A")
        web_data           = researcher.get("data", {}).get("web",   "N/A")
        arxiv_data         = researcher.get("data", {}).get("arxiv", "N/A")
        research_synthesis = researcher.get("synthesis", "")

        # --- news output ---
        news_agent     = data.get("news", {})
        news_data      = news_agent.get("data", {}).get("news", "N/A")
        news_synthesis = news_agent.get("synthesis", "")

        # --- fact-checker output ---
        fact_data     = data.get("fact_checker", {})
        verifications = fact_data.get("verifications", [])
        fact_summary  = fact_data.get("summary", {})

        # ✅ Build a rich prompt that includes ALL the data
        user_prompt = f"""
You are writing a comprehensive final research report on: **{topic}**

Use ALL of the following collected data to write the report.

--- WIKIPEDIA ---
{wiki_data}

--- WEB SEARCH RESULTS ---
{web_data}

--- ARXIV / ACADEMIC PAPERS ---
{arxiv_data}

--- RESEARCH SYNTHESIS ---
{research_synthesis}

--- LATEST NEWS ---
{news_data}

--- NEWS ANALYSIS ---
{news_synthesis}

--- FACT-CHECKING RESULTS ---
Verifications: {verifications}
Summary: {fact_summary}

---
Write a well-structured final report with these sections:
1. Executive Summary
2. Key Findings
3. Recent Developments (News)
4. Academic / Research Perspective
5. Fact-Check Summary
6. Conclusion

Be detailed, factual, and cite the sources above where possible.
"""

        system_prompt = (
            "You are an expert research report writer. "
            "You receive structured research data and produce a clear, "
            "professional, and comprehensive final report."
        )

        final_report = llm_call(system_prompt, user_prompt)
        return {"final_report": final_report}


# ═════════════════════════════════════════════════════════════
# COORDINATOR
# ═════════════════════════════════════════════════════════════
class CoordinatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "CoordinatorAgent",
            "Orchestrator",
            [],
            "Manage and coordinate all specialist agents."
        )
        self.sub_agents = {
            "researcher":   ResearcherAgent(),
            "news":         NewsAgent(),
            "fact_checker": FactChecker(),
            "summarizer":   SummarizerAgent(),
        }

    def run(self, topic, options=None):
        options = options or {}
        result  = {"topic": topic}   # ✅ pass topic so summarizer can use it

        if options.get("researcher", True):
            result["researcher"] = self.sub_agents["researcher"].run(topic)

        if options.get("news", True):
            result["news"] = self.sub_agents["news"].run(topic)

        if options.get("fact_checker", True):
            claims = [topic, f"{topic} benefits", f"{topic} risks"]
            result["fact_checker"] = self.sub_agents["fact_checker"].run(claims)

        if options.get("summarizer", True):
            # ✅ pass the full result dict (includes topic + all agent outputs)
            result["summarizer"] = self.sub_agents["summarizer"].run(result)

        return result

    def get_all_statuses(self):
        statuses = [self.get_status()]
        for agent in self.sub_agents.values():
            statuses.append(agent.get_status())
        return statuses