"""
pipeline.py - Research pipeline orchestrating all agents
"""
import time
from my_agent import CoordinatorAgent, ResearcherAgent, NewsAgent, FactChecker, SummarizerAgent


class ResearchPipeline:
    def __init__(self):
        self.coordinator = CoordinatorAgent()
        self.history = []
        self.current_run = None

    # ── FULL PIPELINE ─────────────────────────────────────────
    def run_full_pipeline(self, topic: str, options: dict = None) -> dict:
        start_time = time.time()

        options = options or {
            "researcher": True,
            "news": True,
            "fact_checker": True,
            "summarizer": True
        }

        run_record = {
            "topic": topic,
            "start_time": start_time,
            "options": options,
            "status": "running",
            "results": {}
        }

        self.current_run = run_record

        try:
            results = self.coordinator.run(topic, options)

            run_record.update({
                "status": "complete",
                "results": results,
                "elapsed_sec": round(time.time() - start_time, 2),
                "agents_used": [k for k, v in options.items() if v]
            })

        except Exception as e:
            run_record.update({
                "status": "error",
                "error": str(e)
            })

        self.history.append(run_record)
        return run_record

    # ── INDIVIDUAL AGENTS ─────────────────────────────────────
    def run_researcher_only(self, topic: str) -> dict:
        agent = ResearcherAgent()
        return {
            "agent": "ResearcherAgent",
            "topic": topic,
            "result": agent.run(topic)
        }

    def run_news_only(self, topic: str) -> dict:
        agent = NewsAgent()
        return {
            "agent": "NewsAgent",
            "topic": topic,
            "result": agent.run(topic)
        }

    def run_fact_checker_only(self, claims: list) -> dict:
        agent = FactChecker()   # ✅ FIXED
        return {
            "agent": "FactChecker",   # ✅ FIXED
            "claims": claims,
            "result": agent.run(claims)
        }

    def run_summarizer_only(self, text: str) -> dict:
        from tools import run_tool
        result = run_tool("summarize_text", text=text, max_sentences=6)
        return {
            "agent": "SummarizerAgent",
            "result": result
        }

    # ── UTILITIES ─────────────────────────────────────────────
    def get_agent_statuses(self) -> list:
        return self.coordinator.get_all_statuses()

    def get_history(self) -> list:
        return self.history

    def clear_history(self):
        self.history = []
        self.current_run = None

    # ── EXPORT REPORT ─────────────────────────────────────────
    def export_report(self, run_record: dict) -> str:
        topic = run_record.get("topic", "Unknown")
        elapsed = run_record.get("elapsed_sec", "N/A")
        results = run_record.get("results", {})

        lines = [
            f"# Multi-Agent Research Report: {topic}",
            f"*Generated in {elapsed}s*\n",
            "---",
            "## Executive Summary",
            results.get("coordinator_synthesis", "N/A"),
            "\n---",
            "## Background Research"
        ]

        # Researcher
        r = results.get("researcher", {})
        wiki = r.get("data", {}).get("wiki", {})
        if wiki:
            lines.append(str(wiki)[:500])

        # News
        lines += ["\n---", "## News"]
        news = results.get("news", {}).get("data", {}).get("news", {})
        for a in news.get("articles", [])[:5]:
            lines.append(f"- {a.get('title','')}")

        # Fact Check
        lines += ["\n---", "## Fact Check"]
        fc = results.get("fact_checker", {})
        summary = fc.get("summary", {})
        lines.append(f"Total Checked: {summary.get('total',0)}")

        # Final Summary
        lines += ["\n---", "## Final Summary"]
        lines.append(results.get("summarizer", {}).get("final_report", "N/A"))

        return "\n".join(lines)