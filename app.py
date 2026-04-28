import streamlit as st
import time, json, os, logging

# ── VERBOSE LOGGING SETUP ─────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s » %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("MARS.App")
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger.info("=" * 60)
logger.info("  MARS - Multi-Agent Research System STARTING")
logger.info("=" * 60)

from pipeline import ResearchPipeline
logger.info("✅ Pipeline imported successfully")

# ── PAGE CONFIG ────────────────────────────────────────────────
st.set_page_config(
    page_title="🔬 Multi-Agent Research System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)
logger.info("✅ Streamlit page config set")

# ── CUSTOM CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #a7c7ff 0%, #8fb5ff 50%, #78a6ff 100%);
        padding: 2rem; border-radius: 12px; text-align: center; margin-bottom: 1.5rem;
    }
    .main-header h1 { color: #0b2f8a; font-size: 2.2rem; margin: 0; }
    .main-header p  { color: #0f172a; margin: 0.5rem 0 0 0; font-size: 1rem; }

    .agent-card {
        background: #bcd4ff; border: 1px solid #6ea8fe; border-radius: 10px;
        padding: 1rem; margin: 0.5rem 0;
    }
    .agent-name { color: #0b2f8a; font-weight: bold; font-size: 1.1rem; }

    .status-badge {
        display: inline-block; padding: 2px 10px; border-radius: 20px;
        font-size: 0.75rem; font-weight: bold;
    }
    .badge-complete { background: #86efac; color: #064e3b; }
    .badge-running  { background: #93c5fd; color: #1e3a8a; }
    .badge-error    { background: #fca5a5; color: #7f1d1d; }

    /* ✅ FIXED: was #000000 (pure black) — now white background */
    .metric-box {
        background: #ffffff;
        border-radius: 8px; padding: 1rem;
        text-align: center; border: 1px solid #6ea8fe;
    }
    .metric-num   { font-size: 2rem; font-weight: bold; color: #0b2f8a; }
    .metric-label { font-size: 0.8rem; color: #0f172a; }
    /* agent icon */
    .metric-box .agent-icon { font-size: 1.8rem; }
    /* agent name inside metric box */
    .metric-box .agent-title { font-weight: bold; color: #1d4ed8; }
    /* agent desc inside metric box */
    .metric-box .agent-desc  { font-size: 0.75rem; color: #374151; }

    .result-section {
        background: #bcd4ff; border-radius: 8px; padding: 1.2rem;
        margin: 0.5rem 0; border-left: 3px solid #1e3a8a;
    }

    .paper-card {
        background: #93c5fd; border-radius: 6px; padding: 0.8rem; margin: 0.4rem 0;
    }

    .news-item {
        background: #93c5fd; border-radius: 6px; padding: 0.6rem; margin: 0.3rem 0;
        border-left: 2px solid #1e3a8a;
    }

    .fact-item  {
        background: #93c5fd; border-radius: 6px; padding: 0.8rem; margin: 0.4rem 0;
    }

    .verified   { border-left: 3px solid #16a34a; }
    .unverified { border-left: 3px solid #dc2626; }

    .stButton > button {
        background: linear-gradient(135deg, #1d4ed8, #0b2f8a);
        color: white; border: none; border-radius: 8px;
        font-weight: bold; padding: 0.6rem 1.5rem; font-size: 1rem;
    }
    .stButton > button:hover { opacity: 0.9; }

    /* Verbose log box */
    .vlog-box {
        background: #0f172a; color: #86efac;
        font-family: monospace; font-size: 0.75rem;
        padding: 1rem; border-radius: 8px;
        max-height: 300px; overflow-y: auto;
        border: 1px solid #1e3a8a;
    }
</style>
""", unsafe_allow_html=True)


# ── SESSION STATE ──────────────────────────────────────────────
if "pipeline" not in st.session_state:
    logger.info("🔧 Creating new ResearchPipeline instance")
    st.session_state.pipeline = ResearchPipeline()
if "results"  not in st.session_state:
    st.session_state.results  = None
if "running"  not in st.session_state:
    st.session_state.running  = False
if "verbose_logs" not in st.session_state:
    st.session_state.verbose_logs = []

pipeline = st.session_state.pipeline
logger.info("✅ Session state initialised")


def add_vlog(msg):
    """Add a line to the on-screen verbose log."""
    ts = time.strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    st.session_state.verbose_logs.append(entry)
    logger.info(msg)


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚙️ Configuration")

    groq_key = st.text_input("🔑 Groq API Key (Free)", type="password",
        placeholder="gsk_...",
        help="Get free key at groq.com")
    if groq_key:
        os.environ["GROQ_API_KEY"] = groq_key
        logger.info("🔑 Groq API key set from sidebar")
        st.success("✅ Groq API key set")
    else:
        st.info("ℹ️ Works without key (rule-based). Add free Groq key for AI synthesis.")

    st.markdown("---")
    st.markdown("### 🤖 Select Agents")
    use_researcher   = st.checkbox("🔍 Researcher Agent",   value=True)
    use_news         = st.checkbox("📰 News Agent",          value=True)
    use_fact_checker = st.checkbox("✅ Fact Checker Agent",  value=True)
    use_summarizer   = st.checkbox("📝 Summarizer Agent",    value=True)

    st.markdown("---")

    # ── Verbose log toggle ──
    st.markdown("### 🖥️ Verbose Logging")
    show_verbose = st.checkbox("Show live agent logs", value=True)
    if st.button("🗑️ Clear Logs"):
        st.session_state.verbose_logs = []
        st.rerun()

    st.markdown("---")
    st.markdown("### 📊 Pipeline History")
    hist = pipeline.get_history()
    if hist:
        for h in reversed(hist[-5:]):
            icon = "🟢" if h["status"] == "complete" else "🔴"
            st.markdown(f"{icon} **{h['topic'][:25]}...** ({h.get('elapsed_sec','?')}s)")
        if st.button("🗑️ Clear History"):
            pipeline.clear_history()
            st.rerun()
    else:
        st.caption("No runs yet.")

    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.markdown("""
**Multi-Agent Research System**
- 5 specialized AI agents
- 6 free research tools
- No paid APIs needed
- Groq (free) for AI synthesis

**Tools Used:**
- Wikipedia REST API
- arXiv API
- DuckDuckGo API
- Google News RSS
- Local summarizer
""")


# ══════════════════════════════════════════════════════════════
# MAIN HEADER
# ══════════════════════════════════════════════════════════════
st.markdown("""
<div class="main-header">
    <h1>🔬 Multi-Agent Research System</h1>
    <p>Agentic AI • 5 Specialized Agents • Wikipedia • arXiv • News • Fact Checking</p>
</div>
""", unsafe_allow_html=True)


# ── AGENT STATUS ROW ───────────────────────────────────────────
agents_info = [
    ("🎯", "Coordinator",  "Orchestrates all agents"),
    ("🔍", "Researcher",   "Wikipedia + arXiv + Web"),
    ("📰", "News",         "Google News RSS"),
    ("✅", "Fact Checker", "Cross-references claims"),
    ("📝", "Summarizer",   "Condensed reports"),
]
cols = st.columns(5)
for col, (icon, name, desc) in zip(cols, agents_info):
    with col:
        st.markdown(f"""
<div class="metric-box">
    <div class="agent-icon">{icon}</div>
    <div class="agent-title">{name}</div>
    <div class="agent-desc">{desc}</div>
</div>""", unsafe_allow_html=True)

st.markdown("")

# ── VERBOSE LOG PANEL (shown below agent row) ──────────────────
if show_verbose and st.session_state.verbose_logs:
    with st.expander("🖥️ Live Agent Verbose Log", expanded=True):
        log_html = "<br>".join(st.session_state.verbose_logs[-50:])
        st.markdown(f'<div class="vlog-box">{log_html}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🚀 Full Research", "🔍 Single Agent", "✅ Fact Checker",
    "📊 Results", "📄 Export Report"
])


# ──────────────────────────────────────────────
# TAB 1 – FULL PIPELINE
# ──────────────────────────────────────────────
with tab1:
    st.markdown("### 🚀 Full Multi-Agent Research Pipeline")
    st.markdown("Enter any topic and all selected agents will research it in parallel.")

    col1, col2 = st.columns([3, 1])
    with col1:
        topic = st.text_input("🔎 Research Topic",
            placeholder="e.g. Artificial Intelligence, Climate Change...",
            label_visibility="collapsed")
    with col2:
        run_btn = st.button("🚀 Start Research", use_container_width=True)

    st.markdown("**Quick Topics:**")
    ecols = st.columns(5)
    examples = ["Artificial Intelligence", "Climate Change",
                "Quantum Computing", "CRISPR Gene Editing", "Space Exploration"]
    for ec, ex in zip(ecols, examples):
        if ec.button(ex, key=f"ex_{ex}"):
            topic   = ex
            run_btn = True

    if run_btn and topic:
        logger.info(f"\n{'#'*60}")
        logger.info(f"🚀 FULL PIPELINE START » topic='{topic}'")
        logger.info(f"{'#'*60}")
        add_vlog(f"🚀 PIPELINE START » topic='{topic}'")

        options = {
            "researcher":   use_researcher,
            "news":         use_news,
            "fact_checker": use_fact_checker,
            "summarizer":   use_summarizer,
        }
        active_agents = [k for k, v in options.items() if v]
        add_vlog(f"📋 Active agents: {active_agents}")

        progress_bar = st.progress(0)
        status_text  = st.empty()

        with st.spinner(f"🤖 Running {len(active_agents)} agents on '{topic}'..."):
            for i, step in enumerate(active_agents):
                msg = f"⚡ {step.title()} Agent working..."
                status_text.markdown(f"**{msg}**")
                add_vlog(f">>> RUNNING: {step}")
                progress_bar.progress((i + 1) / (len(active_agents) + 1))
                time.sleep(0.3)

            t0      = time.time()
            results = pipeline.run_full_pipeline(topic, options)
            elapsed = round(time.time() - t0, 2)

            progress_bar.progress(1.0)
            status_text.markdown(f"✅ **Complete! ({results.get('elapsed_sec', elapsed)}s)**")

        add_vlog(f"✅ PIPELINE DONE » {elapsed}s | status={results.get('status')}")
        logger.info(f"✅ PIPELINE DONE » {elapsed}s")

        st.session_state.results = results

        if results["status"] == "complete":
            st.success(f"✅ Research complete in {results.get('elapsed_sec', elapsed)} seconds!")

            r   = results["results"]
            m1, m2, m3, m4, m5 = st.columns(5)

            wiki_ok  = r.get("researcher", {}).get("data", {}).get("wikipedia", {}).get("success", False)
            papers   = r.get("researcher", {}).get("data", {}).get("arxiv", {}).get("count", 0)
            news_ct  = len(r.get("news", {}).get("data", {}).get("news", {}).get("articles", []))
            claims   = r.get("fact_checker", {}).get("summary", {}).get("total_claims", 0)
            verified = r.get("fact_checker", {}).get("summary", {}).get("verified", 0)

            add_vlog(f"📊 METRICS » wiki={'✅' if wiki_ok else '❌'} | papers={papers} | news={news_ct} | verified={verified}/{claims}")

            m1.metric("📚 Wikipedia", "✅" if wiki_ok else "❌")
            m2.metric("🎓 Papers",    papers)
            m3.metric("📰 Articles",  news_ct)
            m4.metric("✅ Verified",  f"{verified}/{claims}")
            m5.metric("⏱️ Time",     f"{results.get('elapsed_sec', elapsed)}s")

            # Executive Summary
            if r.get("coordinator_synthesis"):
                add_vlog("📝 Coordinator synthesis available → displaying")
                st.markdown("### 🎯 Executive Summary")
                st.markdown(f'<div class="result-section">{r["coordinator_synthesis"]}</div>',
                            unsafe_allow_html=True)

            # Research Results
            if use_researcher and r.get("researcher"):
                add_vlog("🔍 Researcher results → rendering")
                with st.expander("🔍 Research Agent Results", expanded=True):
                    wiki = r["researcher"].get("data", {}).get("wikipedia", {})
                    if wiki.get("success"):
                        st.markdown(f"**📖 Wikipedia — {wiki.get('title', '')}**")
                        st.markdown(wiki.get("summary", "")[:600])
                        if wiki.get("url"):
                            st.markdown(f"[🔗 Read more]({wiki['url']})")

                    arxiv_res = r["researcher"].get("data", {}).get("arxiv", {})
                    if arxiv_res.get("papers"):
                        st.markdown("**🎓 Academic Papers (arXiv)**")
                        for p in arxiv_res["papers"][:4]:
                            st.markdown(f"""<div class="paper-card">
                                <b>{p['title']}</b><br>
                                <small>👥 {', '.join(p['authors'])} | 📅 {p['published']}</small><br>
                                <small>{p['summary'][:200]}...</small><br>
                                <a href="{p['url']}" target="_blank">🔗 View Paper</a>
                            </div>""", unsafe_allow_html=True)

            # News Results
            if use_news and r.get("news"):
                add_vlog("📰 News results → rendering")
                with st.expander("📰 News Agent Results", expanded=True):
                    articles = r["news"].get("data", {}).get("news", {}).get("articles", [])
                    add_vlog(f"  → {len(articles)} articles found")
                    for a in articles[:6]:
                        st.markdown(f"""<div class="news-item">
                            <b>{a['title']}</b><br>
                            <small>📅 {a['published']}</small>
                            {"<br><small>" + a['snippet'][:200] + "</small>" if a.get('snippet') else ""}
                        </div>""", unsafe_allow_html=True)

            # Fact Check
            if use_fact_checker and r.get("fact_checker"):
                add_vlog("✅ Fact checker results → rendering")
                with st.expander("✅ Fact Checker Results", expanded=False):
                    fc   = r["fact_checker"]
                    summ = fc.get("summary", {})
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Claims Checked", summ.get("total_claims", 0))
                    c2.metric("✅ Verified",     summ.get("verified", 0))
                    c3.metric("❌ Unverified",   summ.get("unverified", 0))
                    for v in fc.get("verifications", []):
                        has_ev = v.get("evidence_count", 0) > 0
                        css    = "verified" if has_ev else "unverified"
                        icon   = "✅" if has_ev else "❓"
                        verdict = v.get("verdict", "")
                        add_vlog(f"  Claim: '{v.get('claim','')[:60]}' → {verdict}")
                        st.markdown(f"""<div class="fact-item {css}">
                            {icon} <b>{v.get('claim', '')}</b><br>
                            <small>Evidence: {v.get('evidence_count', 0)} | Verdict: {verdict}</small>
                        </div>""", unsafe_allow_html=True)

            # Summarizer
            if use_summarizer and r.get("summarizer"):
                add_vlog("📝 Final report from SummarizerAgent → rendering")
                with st.expander("📝 Final Report (SummarizerAgent)", expanded=True):
                    report = r["summarizer"].get("final_report", "N/A")
                    add_vlog(f"  Report length: {len(report)} chars")
                    st.markdown(report)

        else:
            logger.error(f"❌ Pipeline error: {results.get('error')}")
            add_vlog(f"❌ PIPELINE ERROR » {results.get('error', 'Unknown')}")
            st.error(f"❌ Error: {results.get('error', 'Unknown')}")

    elif run_btn:
        st.warning("⚠️ Please enter a research topic.")


# ──────────────────────────────────────────────
# TAB 2 – SINGLE AGENT
# ──────────────────────────────────────────────
with tab2:
    st.markdown("### 🔍 Run Individual Agents")
    agent_choice = st.selectbox("Select Agent", [
        "🔍 Researcher Agent (Wikipedia + arXiv + Web)",
        "📰 News Agent (Google News)",
        "📝 Summarizer Agent (Text Summarizer)"
    ])
    single_topic = st.text_input("Topic / Text",
        placeholder="Enter topic or paste text to summarize...")

    if st.button("▶️ Run Agent", key="single_run"):
        if single_topic:
            logger.info(f"▶ Single agent run » agent={agent_choice} | topic='{single_topic}'")
            add_vlog(f"▶ Single agent: {agent_choice} | topic='{single_topic}'")
            with st.spinner("Running agent..."):
                if "Researcher" in agent_choice:
                    result = pipeline.run_researcher_only(single_topic)
                    add_vlog(f"  Researcher done → {len(str(result))} chars")
                    st.json(result)
                elif "News" in agent_choice:
                    result   = pipeline.run_news_only(single_topic)
                    articles = result.get("result", {}).get("data", {}).get("news", {}).get("articles", [])
                    add_vlog(f"  News done → {len(articles)} articles")
                    for a in articles:
                        st.markdown(f"**{a['title']}** — {a['published']}")
                        if a.get("snippet"):
                            st.caption(a["snippet"][:200])
                elif "Summarizer" in agent_choice:
                    result  = pipeline.run_summarizer_only(single_topic)
                    summary = result.get("result", {}).get("summary", "")
                    add_vlog(f"  Summarizer done → {len(summary)} chars")
                    st.markdown("**Summary:**")
                    st.markdown(summary if summary else "No summary generated.")
        else:
            st.warning("Please enter a topic or text.")


# ──────────────────────────────────────────────
# TAB 3 – FACT CHECKER
# ──────────────────────────────────────────────
with tab3:
    st.markdown("### ✅ Fact Checker")
    st.markdown("Enter claims (one per line) to verify against Wikipedia and web sources.")
    claims_text = st.text_area("Claims to Verify", height=150,
        placeholder="The Earth orbits the Sun.\nWater is H2O.\nAI was invented in 1950.")

    if st.button("🔎 Verify Claims", key="fc_run"):
        if claims_text.strip():
            claims_list = [c.strip() for c in claims_text.strip().split("\n") if c.strip()]
            logger.info(f"✅ Fact check » {len(claims_list)} claims")
            add_vlog(f"✅ Fact checker START » {len(claims_list)} claims")
            with st.spinner(f"Checking {len(claims_list)} claims..."):
                result = pipeline.run_fact_checker_only(claims_list)

            verifications = result.get("result", {}).get("verifications", [])
            for v in verifications:
                has_ev  = v.get("evidence_count", 0) > 0
                verdict = v.get("verdict", "N/A")
                add_vlog(f"  Claim: '{v.get('claim','')[:60]}' → {verdict}")
                with st.expander(f"{'✅' if has_ev else '❓'} {v.get('claim', '')[:80]}"):
                    st.markdown(f"**Verdict:** {verdict}")
                    st.markdown(f"**Evidence sources:** {v.get('evidence_count', 0)}")
                    for ev in v.get("evidence", []):
                        st.markdown(f"*{ev['source']}:* {ev['content'][:300]}")
        else:
            st.warning("Please enter at least one claim.")


# ──────────────────────────────────────────────
# TAB 4 – RAW RESULTS
# ──────────────────────────────────────────────
with tab4:
    st.markdown("### 📊 Raw Pipeline Results")
    if st.session_state.results:
        results = st.session_state.results
        m1, m2, m3 = st.columns(3)
        m1.metric("Status",   results.get("status",  "N/A"))
        m2.metric("Topic",    results.get("topic",   "N/A"))
        m3.metric("Time (s)", results.get("elapsed_sec", "N/A"))

        with st.expander("📋 Full JSON Results"):
            st.json(results.get("results", {}))

        statuses = pipeline.get_agent_statuses()
        st.markdown("### 🤖 Agent Status")
        for s in statuses:
            add_vlog(f"📊 {s['agent']} | memory={s['memory_items']} | logs={s['log_entries']}")
            st.markdown(f"""<div class="agent-card">
                <span class="agent-name">🤖 {s['agent']}</span> — {s['role']}<br>
                <small>Tools: {', '.join(s['tools']) or 'None'} |
                Memory: {s['memory_items']} | Logs: {s['log_entries']}</small>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("No results yet. Run a pipeline from the '🚀 Full Research' tab.")


# ──────────────────────────────────────────────
# TAB 5 – EXPORT
# ──────────────────────────────────────────────
from pdf_helper import make_pdf, PDF_OK

with tab5:
    st.markdown("### 📄 Export Report")
    if st.session_state.results:
        md_report  = pipeline.export_report(st.session_state.results)
        topic_slug = st.session_state.results.get("topic", "report").replace(" ", "_")
        add_vlog("Export ready")
        st.markdown(md_report)
        st.markdown("---")
        st.markdown("### Download Options")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                "Download Markdown Report",
                data=md_report,
                file_name="research_" + topic_slug + ".md",
                mime="text/markdown",
                use_container_width=True
            )
        with col2:
            json_data = json.dumps(st.session_state.results, indent=2, default=str)
            st.download_button(
                "Download JSON Data",
                data=json_data,
                file_name="research_" + topic_slug + ".json",
                mime="application/json",
                use_container_width=True
            )
        with col3:
            if PDF_OK:
                try:
                    pdf_bytes = make_pdf(st.session_state.results)
                    st.download_button(
                        "Download PDF Report",
                        data=pdf_bytes,
                        file_name="research_" + topic_slug + ".pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as pdf_err:
                    st.error("PDF error: " + str(pdf_err))
            else:
                st.warning("Run: pip install fpdf2")
    else:
        st.info("Run a research pipeline first to generate an exportable report.")


# ── FOOTER ─────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<center><small>🤖 Multi-Agent Research System | "
    "Free APIs: Wikipedia • arXiv • DuckDuckGo • Google News RSS | "
    "AI Synthesis: Groq (free tier)</small></center>",
    unsafe_allow_html=True
)

logger.info("✅ Streamlit app rendered successfully")
