"""
tools.py - All tool functions for research agents.
100% free APIs. No paid keys needed.
"""
import requests, re, urllib.parse, xml.etree.ElementTree as ET

# ── WIKIPEDIA ──────────────────────────────────────────────────────────
def search_wikipedia(query: str, sentences: int = 5) -> dict:
    try:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(query.replace(" ","_"))
        r = requests.get(url, timeout=10, headers={"User-Agent":"ResearchBot/1.0"})
        if r.status_code == 200:
            d = r.json()
            return {"success":True,"title":d.get("title",""),"summary":d.get("extract","")[:2000],
                    "url":d.get("content_urls",{}).get("desktop",{}).get("page",""),"source":"Wikipedia"}
        # fallback search
        r2 = requests.get("https://en.wikipedia.org/w/api.php",
            params={"action":"query","list":"search","srsearch":query,"format":"json","srlimit":3},
            timeout=10, headers={"User-Agent":"ResearchBot/1.0"})
        results = r2.json().get("query",{}).get("search",[])
        if results:
            return {"success":True,"title":results[0]["title"],
                    "summary":re.sub('<.*?>','',results[0].get("snippet","")),"url":"","source":"Wikipedia"}
        return {"success":False,"error":"Not found","source":"Wikipedia"}
    except Exception as e:
        return {"success":False,"error":str(e),"source":"Wikipedia"}


# ── ARXIV ──────────────────────────────────────────────────────────────
def search_arxiv(query: str, max_results: int = 5) -> dict:
    try:
        r = requests.get("http://export.arxiv.org/api/query",
            params={"search_query":f"all:{query}","start":0,"max_results":max_results,"sortBy":"relevance"},
            timeout=15)
        root = ET.fromstring(r.content)
        ns = {"a":"http://www.w3.org/2005/Atom"}
        papers = []
        for e in root.findall("a:entry",ns):
            t = e.find("a:title",ns); s = e.find("a:summary",ns)
            l = e.find("a:id",ns);   p = e.find("a:published",ns)
            auths = [a.find("a:name",ns).text for a in e.findall("a:author",ns)[:3]
                     if a.find("a:name",ns) is not None]
            papers.append({"title":t.text.strip() if t is not None else "N/A",
                           "summary":s.text.strip()[:500] if s is not None else "N/A",
                           "url":l.text.strip() if l is not None else "",
                           "published":p.text[:10] if p is not None else "N/A","authors":auths})
        return {"success":True,"papers":papers,"count":len(papers),"source":"arXiv"}
    except Exception as e:
        return {"success":False,"error":str(e),"source":"arXiv"}


# ── DUCKDUCKGO ─────────────────────────────────────────────────────────
def search_web(query: str, max_results: int = 5) -> dict:
    try:
        r = requests.get("https://api.duckduckgo.com/",
            params={"q":query,"format":"json","no_html":1,"skip_disambig":1}, timeout=10)
        d = r.json(); results = []
        if d.get("AbstractText"):
            results.append({"title":d.get("Heading",query),"snippet":d["AbstractText"][:500],
                            "url":d.get("AbstractURL",""),"source":d.get("AbstractSource","Web")})
        for item in d.get("RelatedTopics",[])[:max_results]:
            if isinstance(item,dict) and item.get("Text"):
                results.append({"title":item["Text"][:100],"snippet":item["Text"][:500],
                                 "url":item.get("FirstURL",""),"source":"DuckDuckGo"})
        return {"success":True,"results":results[:max_results],"source":"DuckDuckGo"}
    except Exception as e:
        return {"success":False,"error":str(e),"source":"DuckDuckGo"}


# ── GOOGLE NEWS RSS ────────────────────────────────────────────────────
def fetch_news(topic: str, max_results: int = 5) -> dict:
    try:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(topic)}&hl=en-US&gl=US&ceid=US:en"
        r = requests.get(url, timeout=10, headers={"User-Agent":"ResearchBot/1.0"})
        root = ET.fromstring(r.content)
        news = []
        for item in root.findall(".//item")[:max_results]:
            t=item.find("title"); l=item.find("link"); p=item.find("pubDate"); d=item.find("description")
            news.append({"title":t.text if t is not None else "N/A",
                         "url":l.text if l is not None else "",
                         "published":p.text[:16] if p is not None else "N/A",
                         "snippet":re.sub('<.*?>','',d.text)[:300] if d is not None else ""})
        return {"success":True,"articles":news,"source":"Google News RSS"}
    except Exception as e:
        return {"success":False,"error":str(e),"source":"News"}


# ── FACT CHECKER ───────────────────────────────────────────────────────
def fact_check(claim: str) -> dict:
    wiki = search_wikipedia(claim, sentences=3)
    web  = search_web(claim, max_results=3)
    evidence = []
    if wiki.get("success"):
        evidence.append({"source":"Wikipedia","content":wiki.get("summary","")[:400]})
    for r in web.get("results",[])[:2]:
        evidence.append({"source":r.get("source","Web"),"content":r.get("snippet","")[:300]})
    return {"success":True,"claim":claim,"evidence":evidence,
            "evidence_count":len(evidence),
            "verdict":"Evidence Found" if evidence else "No Evidence Found","source":"Fact Checker"}


# ── TEXT SUMMARIZER (local, no API) ───────────────────────────────────
def summarize_text(text: str, max_sentences: int = 5) -> dict:
    try:
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if len(s.strip())>40]
        if len(sentences) <= max_sentences:
            return {"success":True,"summary":" ".join(sentences),"original_length":len(text)}
        stopwords = {'the','a','an','is','it','in','on','at','to','for','of','and','or','but','with','this','that','was','are'}
        freq = {}
        for w in re.findall(r'\b\w+\b', text.lower()):
            if w not in stopwords and len(w)>3: freq[w]=freq.get(w,0)+1
        scored = sorted([(sum(freq.get(w.lower(),0) for w in re.findall(r'\b\w+\b',s))+(len(sentences)-i)*0.3,i,s)
                          for i,s in enumerate(sentences)], reverse=True)
        top = sorted(scored[:max_sentences], key=lambda x:x[1])
        return {"success":True,"summary":" ".join(s for _,_,s in top),"original_length":len(text)}
    except Exception as e:
        return {"success":False,"error":str(e)}


# ── REGISTRY ───────────────────────────────────────────────────────────
TOOL_REGISTRY = {
    "search_wikipedia": search_wikipedia,
    "search_arxiv":     search_arxiv,
    "search_web":       search_web,
    "fetch_news":       fetch_news,
    "fact_check":       fact_check,
    "summarize_text":   summarize_text,
}

TOOL_DESCRIPTIONS = {
    "search_wikipedia": "Search Wikipedia for encyclopedic knowledge on any topic.",
    "search_arxiv":     "Search arXiv for academic papers and publications.",
    "search_web":       "Search the web via DuckDuckGo (free, no key).",
    "fetch_news":       "Fetch latest news via Google News RSS (free, no key).",
    "fact_check":       "Verify a claim using multiple free sources.",
    "summarize_text":   "Local extractive text summarizer — no API needed.",
}

def run_tool(name: str, **kwargs) -> dict:
    if name not in TOOL_REGISTRY:
        return {"success":False,"error":f"Tool '{name}' not found. Available: {list(TOOL_REGISTRY)}"}
    try:
        return TOOL_REGISTRY[name](**kwargs)
    except Exception as e:
        return {"success":False,"error":str(e)}