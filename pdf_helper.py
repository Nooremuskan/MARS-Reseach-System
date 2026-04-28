import time
try:
    from fpdf import FPDF
    PDF_OK = True
except ImportError:
    PDF_OK = False

def make_pdf(results):
    if not PDF_OK:
        return None
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    W = 180
    topic = str(results.get("topic", "Research Report"))
    r = results.get("results", {})

    def sf(txt):
        return str(txt).encode("latin-1", errors="replace").decode("latin-1")

    def sec(title):
        pdf.set_left_margin(15)
        pdf.set_right_margin(15)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(11, 47, 138)
        pdf.set_fill_color(188, 212, 255)
        pdf.cell(W, 8, sf(title), ln=True, fill=True)
        pdf.ln(2)

    def body(t, sz=10):
        pdf.set_left_margin(15)
        pdf.set_right_margin(15)
        pdf.set_font("Helvetica", "", sz)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(W, 6, sf(str(t)))
        pdf.ln(1)

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(11, 47, 138)
    pdf.cell(W, 12, "Multi-Agent Research Report", ln=True, align="C")
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(W, 8, sf("Topic: " + topic), ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    date_str = time.strftime("%Y-%m-%d %H:%M")
    elapsed_str = str(results.get("elapsed_sec", "?"))
    info = "Date: " + date_str + "  Time: " + elapsed_str + "s"
    pdf.cell(W, 6, sf(info), ln=True, align="C")
    pdf.ln(6)

    coord = r.get("coordinator_synthesis", "")
    if coord:
        sec("Executive Summary")
        body(str(coord)[:1500])

    wiki = r.get("researcher", {}).get("data", {}).get("wikipedia", {})
    if wiki.get("success"):
        sec("Wikipedia: " + str(wiki.get("title", "")))
        body(str(wiki.get("summary", ""))[:1000])

    papers = r.get("researcher", {}).get("data", {}).get("arxiv", {}).get("papers", [])
    if papers:
        sec("Academic Papers (arXiv)")
        for idx, p in enumerate(papers[:4], 1):
            pdf.set_left_margin(15)
            pdf.set_right_margin(15)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(11, 47, 138)
            pdf.multi_cell(W, 6, sf(str(idx) + ". " + str(p.get("title", ""))))
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(80, 80, 80)
            au = ", ".join(str(a) for a in p.get("authors", []))
            pb = str(p.get("published", ""))
            pdf.multi_cell(W, 5, sf("Authors: " + au + "  Published: " + pb))
            body(str(p.get("summary", ""))[:250])

    articles = r.get("news", {}).get("data", {}).get("news", {}).get("articles", [])
    if articles:
        sec("Latest News")
        for a in articles[:5]:
            pdf.set_left_margin(15)
            pdf.set_right_margin(15)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(11, 47, 138)
            pdf.multi_cell(W, 6, sf("- " + str(a.get("title", ""))))
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(W, 5, sf("Published: " + str(a.get("published", ""))), ln=True)
            sn = str(a.get("snippet", ""))
            if sn:
                body(sn[:180])

    verifs = r.get("fact_checker", {}).get("verifications", [])
    if verifs:
        sec("Fact Check Results")
        sm = r.get("fact_checker", {}).get("summary", {})
        summary_line = (
            "Total: " + str(sm.get("total_claims", 0)) +
            "  Verified: " + str(sm.get("verified", 0)) +
            "  Unverified: " + str(sm.get("unverified", 0))
        )
        body(summary_line)
        for v in verifs:
            pdf.set_left_margin(15)
            pdf.set_right_margin(15)
            has_ev = v.get("evidence_count", 0) > 0
            icon2 = "[VERIFIED]" if has_ev else "[UNVERIFIED]"
            pdf.set_font("Helvetica", "B", 10)
            if has_ev:
                pdf.set_text_color(22, 163, 74)
            else:
                pdf.set_text_color(220, 38, 38)
            pdf.multi_cell(W, 6, sf(icon2 + " " + str(v.get("claim", ""))))
            pdf.set_text_color(60, 60, 60)
            pdf.set_font("Helvetica", "", 9)
            detail = (
                "Verdict: " + str(v.get("verdict", "")) +
                "  Evidence: " + str(v.get("evidence_count", 0))
            )
            pdf.multi_cell(W, 5, sf(detail))

    final = str(r.get("summarizer", {}).get("final_report", ""))
    if final:
        sec("Final Report (AI Synthesized)")
        chunk = final[:4000]
        start = 0
        while start < len(chunk):
            body(chunk[start:start + 800])
            start += 800

    pdf.set_y(-15)
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(W, 6, sf("Generated by Multi-Agent Research System"), align="C")

    return bytes(pdf.output())