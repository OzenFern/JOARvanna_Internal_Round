"""
generate_integration_pdf.py
───────────────────────────
Generates a comprehensive developer guide PDF:
"BlackBox_External_Agent_Integration_Guide.pdf"
"""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

PDF_PATH = Path("BlackBox_External_Agent_Integration_Guide.pdf")


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_header_footer(self, total_pages):
        self.saveState()
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#475569"))
            self.drawString(54, 750, "BLACK BOX · DEVELOPER INTEGRATION & SDK GUIDE")
            self.setFont("Helvetica", 8)
            self.drawRightString(612 - 54, 750, "EXTERNAL AGENT IMPLEMENTATION")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.75)
            self.line(54, 742, 612 - 54, 742)

        # Footer
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.75)
        self.line(54, 45, 612 - 54, 45)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(54, 32, "Black Box SDK Documentation · Step-by-Step External Agent Integration")
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(612 - 54, 32, page_str)
        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=60,
        bottomMargin=55
    )

    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#334155"),
        spaceAfter=14
    )
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=12,
        spaceAfter=5,
        keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#0284c7"),
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
        spaceAfter=5
    )
    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        textColor=colors.HexColor("#334155"),
        leftIndent=12,
        spaceAfter=2
    )
    code_style = ParagraphStyle(
        'Code_Block',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=0
    )

    story = []

    # ── Cover / Header Banner ────────────────────────────────────────────────
    story.append(Paragraph("⬛ EXTERNAL AGENT INTEGRATION GUIDE", title_style))
    story.append(Paragraph("Step-by-Step Implementation Guide for Instrumenting Custom Agents, Capturing Checkpointed Traces, and Debugging with Black Box", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0284c7"), spaceAfter=10))

    # Introduction
    story.append(Paragraph(
        "This guide walks developers through connecting external AI agents (LangChain, LlamaIndex, CrewAI, AutoGen, "
        "or native Python ReAct loops) to the Black Box diagnostic ecosystem. By instrumenting your agent with lightweight "
        "observability hooks, Black Box enables automatic root-cause localization, 1-click remediation, and time-travel replay.",
        body_style
    ))
    story.append(Spacer(1, 6))

    # ── Step 1: SDK Installation & Setup ─────────────────────────────────────
    story.append(Paragraph("Step 1: Installation & Directory Configuration", h1_style))
    story.append(Paragraph(
        "Include the `blackbox` package in your project or install your environment:",
        body_style
    ))
    
    s1_code = Paragraph(
        "# Set up Black Box trace repository\n"
        "from pathlib import Path\n"
        "from blackbox.capture.store import TraceStore\n\n"
        "store = TraceStore(Path('data/traces'))",
        code_style
    )
    s1_box = Table([[s1_code]], colWidths=[504])
    s1_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(s1_box)
    story.append(Spacer(1, 8))

    # ── Step 2: Instrumenting Agent Steps with TraceContext ──────────────────
    story.append(Paragraph("Step 2: Instrumenting Agent Execution Loops", h1_style))
    story.append(Paragraph(
        "Wrap your agent's execution cycle with <b>TraceContext</b>. Each LLM call, tool invocation, or context retrieval "
        "is recorded within a `with ctx.step(...)` block:",
        body_style
    ))

    s2_code = Paragraph(
        "from blackbox.capture.instrument import TraceContext\n"
        "from blackbox.capture.schema import TaskType, StepType\n\n"
        "def run_custom_agent(user_query: str) -> str:\n"
        "    with TraceContext(run_id='run-ext-001', task_id='task-42') as ctx:\n"
        "        # Step 0: LLM Decision / Plan\n"
        "        with ctx.step(StepType.LLM_CALL, inputs={'query': user_query}) as step:\n"
        "            plan = llm.chat(f'Plan steps for: {user_query}')\n"
        "            step.set_output(plan)\n\n"
        "        # Step 1: Tool Call (e.g. database query, calculator, API)\n"
        "        with ctx.step(StepType.TOOL_CALL, tool='sql_db', inputs={'sql': 'SELECT ...'}) as step:\n"
        "            db_rows = database.execute('SELECT ...')\n"
        "            step.set_output(db_rows)\n"
        "            step.set_tool_call('sql_db', {'sql': 'SELECT ...'}, db_rows)\n\n"
        "        # Step 2: Final Model Synthesis\n"
        "        with ctx.step(StepType.LLM_CALL, inputs={'rows': db_rows}) as step:\n"
        "            final_ans = llm.chat(f'Summarize: {db_rows}')\n"
        "            step.set_output(final_ans)\n\n"
        "        # Build immutable trace\n"
        "        trace = ctx.build_trace(\n"
        "            task_type=TaskType.CUSTOM,\n"
        "            task_description=user_query,\n"
        "            expected_output='Target Answer',\n"
        "            final_output=final_ans,\n"
        "            success=(final_ans == 'Target Answer')\n"
        "        )\n"
        "        store.save(trace)\n"
        "        return final_ans",
        code_style
    )
    s2_box = Table([[s2_code]], colWidths=[504])
    s2_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(s2_box)
    story.append(Spacer(1, 8))

    # ── Step 3: Decorating Tool Functions ────────────────────────────────────
    story.append(Paragraph("Step 3: Auto-Capturing Tools with @capture_tool", h1_style))
    story.append(Paragraph(
        "For modular tools, simply decorate tool functions with `@capture_tool`:",
        body_style
    ))

    s3_code = Paragraph(
        "from blackbox.capture.instrument import capture_tool\n\n"
        "class AgentToolkit:\n"
        "    def __init__(self, trace_ctx):\n"
        "        self._trace_ctx = trace_ctx\n\n"
        "    @capture_tool('web_search')\n"
        "    def search(self, query: str):\n"
        "        return external_search_api(query)",
        code_style
    )
    s3_box = Table([[s3_code]], colWidths=[504])
    s3_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(s3_box)
    story.append(Spacer(1, 8))

    # ── Step 4: Running Diagnostics & Localizing Faults ──────────────────────
    story.append(Paragraph("Step 4: Running Automated AI Fault Diagnosis", h1_style))
    story.append(Paragraph(
        "When an agent run fails, call the local analyzer to pinpoint the root-cause step in &lt; 1 ms:",
        body_style
    ))

    s4_code = Paragraph(
        "from blackbox.attribution.model import LocalAttributionModel\n"
        "from blackbox.analysis.local import analyze_local\n"
        "from blackbox.debug.diagnose import create_diagnosis\n"
        "from blackbox.debug.suggestions import generate_suggestions\n"
        "from blackbox.analysis.consensus import ConsensusResult\n\n"
        "model = LocalAttributionModel()\n"
        "model.load('data/artifacts/model.pkl')\n\n"
        "# 1. Run local ML diagnosis\n"
        "local_res = analyze_local(trace, model)\n"
        "consensus = ConsensusResult(local_res.top_step, local_res.scores, True, 'local_only', local_res.confidence)\n"
        "diagnosis = create_diagnosis(trace, consensus)\n\n"
        "print(f'Culprit Step: {diagnosis.likely_source}')\n"
        "print(f'Confidence:   {diagnosis.confidence}')\n"
        "print(f'Rationale:    {diagnosis.rationale}')\n\n"
        "# 2. Retrieve actionable fix suggestions\n"
        "suggestions = generate_suggestions(trace, diagnosis.likely_source)\n"
        "for s in suggestions:\n"
        "    print(f'Fix: {s.title} -> {s.description}')",
        code_style
    )
    s4_box = Table([[s4_code]], colWidths=[504])
    s4_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(s4_box)
    story.append(Spacer(1, 8))

    # ── Step 5: Checkpointed Replay & Verification ───────────────────────────
    story.append(Paragraph("Step 5: Testing Fixes with Time-Travel Replay", h1_style))
    story.append(Paragraph(
        "Apply the recommended patch at the suspect step and resume downstream execution without re-running past steps:",
        body_style
    ))

    s5_code = Paragraph(
        "from blackbox.intervene.patch import StepPatch\n"
        "from blackbox.intervene.branch import create_branch\n"
        "from blackbox.compare.divergence import find_divergence\n\n"
        "# Apply patch to culprit step (e.g. override faulty calculation or SQL)\n"
        "patch = StepPatch(\n"
        "    step_index=diagnosis.likely_source,\n"
        "    patch_kind='override_output',\n"
        "    new_output=suggestions[0].patch_payload.get('output'),\n"
        "    description=suggestions[0].title\n"
        ")\n\n"
        "# Resume branch from checkpoint\n"
        "repaired_trace = create_branch(trace, patch)\n"
        "print(f'Repaired Run Status: {repaired_trace.success}')\n"
        "print(f'Savings: {repaired_trace.meta.get(\"replay_savings_pct\")}% computation avoided!')\n\n"
        "# Compare side-by-side\n"
        "diff = find_divergence(trace, repaired_trace)\n"
        "print(f'Divergence point: Step {diff.earliest_step_index}')",
        code_style
    )
    s5_box = Table([[s5_code]], colWidths=[504])
    s5_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(s5_box)
    story.append(Spacer(1, 10))

    # ── Best Practices ───────────────────────────────────────────────────────
    story.append(Paragraph("💡 Best Practices for Production Agent Debugging", h1_style))
    story.append(Paragraph("• <b>Always Record Checkpoints:</b> Attach intermediate memory state so the agent is resumable at any step.", bullet_style))
    story.append(Paragraph("• <b>Track Input & Output Tokens:</b> Ensures full visibility into token and cost savings during replay.", bullet_style))
    story.append(Paragraph("• <b>Use Local ML for Fast Filtering:</b> Local attribution runs in &lt; 1 ms, filtering 90%+ of traces before invoking expensive LLM judges.", bullet_style))
    story.append(Paragraph("• <b>Review Trace Diffs:</b> Always inspect the earliest divergence in the Streamlit UI to verify fix validity.", bullet_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {PDF_PATH.resolve()}")


if __name__ == "__main__":
    build_pdf()
