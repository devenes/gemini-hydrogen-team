"""Built-in multi-agent scenarios and ready-to-launch prompt templates for Hydrogen Team."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CollaborationMode = Literal["orchestrated", "peer_mesh", "pipeline_loop"]


class AgentBlueprint(BaseModel):
    name: str
    role: str
    specialty: str
    instruction: str
    include_code_runner: bool = True
    include_video_tools: bool = False
    include_finance_tools: bool = False
    thinking_level: str | None = None


class PromptTemplate(BaseModel):
    id: str
    title: str
    badge: str
    prompt: str
    expected_deliverables: list[str] = Field(default_factory=list)


class ScenarioSpec(BaseModel):
    id: str
    name: str
    category: str
    icon: str
    tagline: str
    description: str
    recommended_mode: CollaborationMode = "peer_mesh"
    recommended_orchestrator: str = "gemini-4-argon"
    agents: list[AgentBlueprint]
    templates: list[PromptTemplate]


SCENARIOS: dict[str, ScenarioSpec] = {
    "video_vfx": ScenarioSpec(
        id="video_vfx",
        name="Code-First Video & VFX Studio",
        category="Creative & Motion",
        icon="film",
        tagline="Animate, composite, and render videos purely with code — zero After Effects or Premiere.",
        description=(
            "A collaborative squad of Hydrogen creative coders that storyboards motion graphics, "
            "writes procedural Python/Pillow + HTML5 Canvas VFX animations, and renders real playable "
            "MP4 videos with FFmpeg right inside your browser workspace."
        ),
        recommended_mode="peer_mesh",
        recommended_orchestrator="gemini-4-argon",
        agents=[
            AgentBlueprint(
                name="CreativeDirector",
                role="Creative Director & Storyboarder",
                specialty="Visual narrative, pacing, color palette, typography timing, and shot specs",
                include_code_runner=False,
                include_video_tools=False,
                instruction=(
                    "You are CreativeDirector in a code-first Video & VFX Hydrogen Team.\n"
                    "Design a tight, visually striking motion-graphics storyboard (timing in seconds, "
                    "color tokens, kinetic typography beats, camera eases, and visual motifs) suitable "
                    "for pure-code rendering (Python Pillow + FFmpeg MP4 AND an interactive HTML5 Canvas player).\n"
                    "1. Save a concise production brief to `storyboard.md` via `write_workspace_file`.\n"
                    "2. Call `post_to_blackboard` with `to_agent='all'` and `kind='proposal'` sharing exact "
                    "resolution (960x540 at 24fps for crisp fast rendering), duration (4-6 seconds), palette, and beat sheet."
                ),
            ),
            AgentBlueprint(
                name="MotionCoder",
                role="Interactive HTML5 Motion Engineer",
                specialty="Self-contained HTML5 Canvas/SVG kinetic typography, easing curves, interactive timeline player",
                include_code_runner=False,
                include_video_tools=False,
                instruction=(
                    "You are MotionCoder in a code-first Video & VFX Hydrogen Team.\n"
                    "Read the Team Blackboard (`read_blackboard`) to align with CreativeDirector and peers.\n"
                    "Build a stunning, self-contained interactive motion-graphics studio file `motion_studio.html` "
                    "(zero external CDN dependencies!) using HTML5 `<canvas>` + smooth cubic-bezier easing, "
                    "kinetic typography, glowing particle/orbital VFX, play/pause/restart controls, timeline scrubber, "
                    "and speed selector so users can watch and inspect the animation live in the browser.\n"
                    "Post a `finding` to the blackboard describing the implemented scenes and controls."
                ),
            ),
            AgentBlueprint(
                name="VFXAndShaderEngineer",
                role="Procedural Python VFX & Frame Renderer",
                specialty="Procedural Pillow frame synthesis, glow blooms, particle physics, procedural graphics",
                include_code_runner=True,
                include_video_tools=True,
                instruction=(
                    "You are VFXAndShaderEngineer in a code-first Video & VFX Hydrogen Team.\n"
                    "Check `read_blackboard` for CreativeDirector's storyboard and MotionCoder's visual cues.\n"
                    "Write a clean, fast Python script `render_frames.py` using `PIL` (Pillow) + `math` that generates "
                    "a crisp 960x540 @ 24fps (96 to 120 frames, ~4-5 seconds) procedural animation into `frames/frame_%04d.png` "
                    "featuring smooth easing, glowing gradients, orbital rings/particles, and bold title typography "
                    "(use `ImageFont.load_default(size=...)` safely with fallback so it never crashes on missing fonts).\n"
                    "Execute `render_frames.py` using `run_python_script`, verify zero errors, then call "
                    "`post_to_blackboard` with `to_agent='VideoEditorAndRenderer'` and `kind='handoff'` reporting the frame count and fps."
                ),
            ),
            AgentBlueprint(
                name="VideoEditorAndRenderer",
                role="Video Editor, Compositor & Mastering Lead",
                specialty="FFmpeg H.264 mastering, audio synthesis, quality inspection, and final assembly",
                include_code_runner=True,
                include_video_tools=True,
                instruction=(
                    "You are VideoEditorAndRenderer in a code-first Video & VFX Hydrogen Team.\n"
                    "Read the blackboard (`read_blackboard`) and check `list_workspace_files`.\n"
                    "If `frames/frame_0001.png` exists, call `render_video_from_frames` with "
                    "`frames_pattern='frames/frame_%04d.png'`, `output_filename='hydrogen_studio_render.mp4'`, "
                    "`fps=24`, `add_ambient_audio=True` to master a real web-playable MP4 video! "
                    "If frames are missing, inspect or fix `render_frames.py` and run it first.\n"
                    "Also review `motion_studio.html` and post a peer critique/sign-off to the blackboard (`kind='decision'`). "
                    "Summarize all rendered video & interactive studio deliverables clearly."
                ),
            ),
        ],
        templates=[
            PromptTemplate(
                id="hydrogen_launch_teaser",
                title="Hydrogen AI Kinetic Launch Teaser (MP4 + Canvas)",
                badge="MP4 + HTML5",
                prompt=(
                    "Create a 4-second kinetic typography & glowing atomic-orbital product launch teaser "
                    "for 'Gemini 4 Hydrogen — Multi-Agent Speed'. Use deep space slate (#070B14), electric "
                    "hydrogen cyan (#38BDF8), and neon violet (#A78BFA) accents. Deliver BOTH a real rendered "
                    "MP4 video (`hydrogen_studio_render.mp4`) via Python+Pillow+FFmpeg AND an interactive "
                    "HTML5 Canvas animation studio (`motion_studio.html`) with playback controls."
                ),
                expected_deliverables=["storyboard.md", "motion_studio.html", "render_frames.py", "hydrogen_studio_render.mp4"],
            ),
            PromptTemplate(
                id="data_story_video",
                title="Animated Benchmark Race Data Video",
                badge="Data Motion",
                prompt=(
                    "Produce a 4-second code-driven animated data visualization video comparing multi-agent "
                    "throughput & cost efficiency across Hydrogen, Neon, Argon, and Carbon tiers. "
                    "Render smooth growing bars, animated counter tickers, and a clean title card into "
                    "an MP4 (`hydrogen_studio_render.mp4`) plus an interactive HTML5 Canvas playback studio (`motion_studio.html`)."
                ),
                expected_deliverables=["storyboard.md", "motion_studio.html", "render_frames.py", "hydrogen_studio_render.mp4"],
            ),
            PromptTemplate(
                id="scifi_hud_vfx",
                title="Sci-Fi Telemetry HUD VFX Sequence",
                badge="Procedural VFX",
                prompt=(
                    "Create a 4-second sci-fi mission-control HUD visual effects sequence with rotating "
                    "reticle rings, live telemetry waveforms, scanning laser sweep, and 'HYDROGEN TEAM ONLINE' "
                    "glitch lock-on typography — completely coded without After Effects or Premiere. "
                    "Deliver both `hydrogen_studio_render.mp4` and interactive `motion_studio.html`."
                ),
                expected_deliverables=["storyboard.md", "motion_studio.html", "render_frames.py", "hydrogen_studio_render.mp4"],
            ),
        ],
    ),
    "coding": ScenarioSpec(
        id="coding",
        name="Software Engineering Squad",
        category="Engineering",
        icon="code",
        tagline="Architect, implement, test, and security-review production code collaboratively.",
        description=(
            "Four specialized Hydrogen engineering agents work together across architecture design, "
            "clean implementation, automated unit testing executed live, and adversarial code review."
        ),
        recommended_mode="orchestrated",
        recommended_orchestrator="gemini-4-argon",
        agents=[
            AgentBlueprint(
                name="SystemsArchitect",
                role="Principal Systems Architect",
                specialty="API contracts, modular design, concurrency invariants, edge cases",
                include_code_runner=False,
                instruction=(
                    "You are SystemsArchitect. Design a clean, idiomatic Python module structure, public interfaces, "
                    "data structures, and edge-case invariants for the user's technical problem.\n"
                    "Write `ARCHITECTURE.md` with clear module boundaries and post a `proposal` on the blackboard "
                    "addressed to `CoreDeveloper` and `TestAndSecurityEngineer`."
                ),
            ),
            AgentBlueprint(
                name="CoreDeveloper",
                role="Senior Implementation Engineer",
                specialty="Clean typed Python implementation, algorithmic efficiency, zero-dependency clarity",
                include_code_runner=True,
                instruction=(
                    "You are CoreDeveloper. Read `read_blackboard` and `ARCHITECTURE.md` before coding.\n"
                    "Implement the complete, production-quality, well-typed solution inside workspace source files "
                    "(e.g. `solution.py` or package files) using `write_workspace_file`. Run a quick smoke script via "
                    "`run_python_script` if helpful, and post a `handoff` to `TestAndSecurityEngineer` on the blackboard."
                ),
            ),
            AgentBlueprint(
                name="TestAndSecurityEngineer",
                role="QA Automation & Security Engineer",
                specialty="Comprehensive unittest suites, stress/concurrency tests, boundary & security checks",
                include_code_runner=True,
                instruction=(
                    "You are TestAndSecurityEngineer. Inspect the blackboard and source files written by CoreDeveloper.\n"
                    "Write a comprehensive `test_solution.py` using Python's `unittest` covering happy paths, edge cases, "
                    "concurrency/boundary conditions, and input validation. Execute it LIVE via `run_python_script`! "
                    "If tests fail, report exact failures to the blackboard (`kind='critique'`, `to_agent='CoreDeveloper'`) "
                    "or apply a clean fix and re-run until all tests pass."
                ),
            ),
            AgentBlueprint(
                name="CodeReviewer",
                role="Staff Code Reviewer",
                specialty="Maintainability, complexity analysis, documentation polish, final verification",
                include_code_runner=True,
                instruction=(
                    "You are CodeReviewer. Read the blackboard, inspect all files (`list_workspace_files`), "
                    "verify tests pass by running `test_solution.py` if not already verified, write a crisp `REVIEW.md` "
                    "summarizing complexity, security posture, and test verification, and post your final `decision` "
                    "to the blackboard."
                ),
            ),
        ],
        templates=[
            PromptTemplate(
                id="rate_limiter",
                title="Distributed-Ready Rate Limiter Library + Tests",
                badge="Python + Tests",
                prompt=(
                    "Build a thread-safe Python rate-limiting library (`rate_limiter.py`) implementing BOTH "
                    "Token Bucket and Sliding Window Log algorithms with pluggable storage, injectable clock "
                    "for deterministic tests, burst handling, and retry-after headers. Include a full `test_solution.py` "
                    "suite, execute the tests live, and deliver `ARCHITECTURE.md` and `REVIEW.md`."
                ),
                expected_deliverables=["ARCHITECTURE.md", "rate_limiter.py", "test_solution.py", "REVIEW.md"],
            ),
            PromptTemplate(
                id="async_race_debug",
                title="Diagnose & Fix Async Worker Pool Race Condition",
                badge="Concurrency",
                prompt=(
                    "Design and implement an async job queue & bounded worker pool (`job_pool.py`) with "
                    "graceful shutdown, per-job timeouts, exponential backoff retries, and dead-letter queue "
                    "preventing duplicate execution under high concurrency. Prove correctness with an automated "
                    "stress test suite (`test_solution.py`) executed live."
                ),
                expected_deliverables=["ARCHITECTURE.md", "job_pool.py", "test_solution.py", "REVIEW.md"],
            ),
            PromptTemplate(
                id="jsonl_analyzer",
                title="High-Speed Streaming Log & Telemetry Analyzer",
                badge="CLI + Bench",
                prompt=(
                    "Build a zero-dependency streaming JSONL log analyzer (`log_analyzer.py`) supporting "
                    "percentile latency estimation (p50/p95/p99), error-rate anomaly detection, and Markdown/JSON "
                    "report export. Generate synthetic sample logs, run an automated benchmark + test suite "
                    "(`test_solution.py`), and summarize findings."
                ),
                expected_deliverables=["ARCHITECTURE.md", "log_analyzer.py", "test_solution.py", "REVIEW.md"],
            ),
        ],
    ),
    "company_ops": ScenarioSpec(
        id="company_ops",
        name="Company Monetization & Executive War Room",
        category="Business & Strategy",
        icon="briefcase",
        tagline="Model revenue, optimize pricing tiers, and craft board-ready operating plans.",
        description=(
            "A cross-functional leadership squad powered by Hydrogen that runs verified unit-economics "
            "simulations, designs monetization tiers, builds interactive executive dashboards, and aligns OKRs."
        ),
        recommended_mode="orchestrated",
        recommended_orchestrator="gemini-4-carbon",
        agents=[
            AgentBlueprint(
                name="StrategyLead",
                role="Chief Strategy Officer",
                specialty="Market positioning, competitive moat, strategic narrative, quarterly OKRs",
                include_code_runner=False,
                include_finance_tools=True,
                instruction=(
                    "You are StrategyLead in the Executive War Room.\n"
                    "Frame the core strategic thesis, ICP segments, competitive positioning, and top 3 quarterly OKRs. "
                    "Save `strategy_brief.md` and post a `proposal` to the blackboard for MonetizationEconomist, "
                    "GrowthStrategist, and OperationsCFO."
                ),
            ),
            AgentBlueprint(
                name="MonetizationEconomist",
                role="Pricing & Unit Economics Lead",
                specialty="SaaS pricing architecture, LTV:CAC modeling, usage-based tiers, margin analysis",
                include_code_runner=True,
                include_finance_tools=True,
                instruction=(
                    "You are MonetizationEconomist. Read the blackboard and call `compute_financial_model` for at least "
                    "2 scenarios (e.g. Current Baseline vs Optimized Monetization) so every number is mathematically exact!\n"
                    "Write `pricing_and_economics.md` with clear pricing tiers, value metrics, and financial tables, "
                    "plus export `financial_projection.csv`. Post exact LTV, CAC, payback, and Year-1 ARR results to the blackboard."
                ),
            ),
            AgentBlueprint(
                name="GrowthStrategist",
                role="VP of Growth & Go-To-Market",
                specialty="Acquisition funnels, PLG loops, activation milestones, churn mitigation",
                include_code_runner=False,
                include_finance_tools=False,
                instruction=(
                    "You are GrowthStrategist. Read the blackboard to align with StrategyLead and MonetizationEconomist.\n"
                    "Design the concrete 90-day GTM execution plan, acquisition channels, PLG self-serve conversion triggers, "
                    "and churn-reduction experiments. Save `gtm_playbook.md` and post peer feedback (`kind='critique'` or `'finding'`) "
                    "on pricing friction and conversion assumptions."
                ),
            ),
            AgentBlueprint(
                name="OperationsCFO",
                role="CFO & Executive Dashboard Builder",
                specialty="Capital allocation, risk controls, board reporting, interactive HTML executive dashboards",
                include_code_runner=False,
                include_finance_tools=True,
                instruction=(
                    "You are OperationsCFO. Read the blackboard and all workspace reports (`list_workspace_files`).\n"
                    "Synthesize every teammate's verified numbers into a sleek, self-contained interactive executive "
                    "board dashboard `executive_dashboard.html` (with styled KPI cards, pricing comparison matrix, "
                    "inline SVG/Canvas ARR trajectory chart, and 90-day OKR tracker — zero external CDN dependencies!). "
                    "Post a `decision` on the blackboard summarizing capital allocation and go/no-go guardrails."
                ),
            ),
        ],
        templates=[
            PromptTemplate(
                id="saas_monetization",
                title="AI SaaS Monetization Overhaul ($0 → $10M ARR)",
                badge="Unit Economics",
                prompt=(
                    "We run an AI developer-productivity SaaS with 250 paying customers at $49/mo flat pricing, "
                    "12% monthly gross customer growth, 4.5% monthly churn, and $380 CAC. Design a modernized "
                    "hybrid seat + usage-credit monetization model to reach strong LTV:CAC (>5x) and accelerate "
                    "ARR growth. Model baseline vs optimized scenarios with `compute_financial_model`, export "
                    "`financial_projection.csv`, and build an interactive `executive_dashboard.html`."
                ),
                expected_deliverables=["strategy_brief.md", "pricing_and_economics.md", "financial_projection.csv", "gtm_playbook.md", "executive_dashboard.html"],
            ),
            PromptTemplate(
                id="churn_turnaround",
                title="High-Churn Startup 90-Day Turnaround Plan",
                badge="Turnaround",
                prompt=(
                    "Our B2B workflow startup has 180 customers paying $199/mo, 8% monthly churn, 9% monthly "
                    "gross growth, and $950 CAC. Build a 90-day executive turnaround plan cutting churn below 3%, "
                    "re-packaging annual plans, modeling financial impact, and producing a board-ready "
                    "`executive_dashboard.html` and `gtm_playbook.md`."
                ),
                expected_deliverables=["strategy_brief.md", "pricing_and_economics.md", "gtm_playbook.md", "executive_dashboard.html"],
            ),
            PromptTemplate(
                id="open_core_company",
                title="Open-Core DevTools Company Operating Plan",
                badge="Open-Core",
                prompt=(
                    "Design the monetization strategy, open-source vs enterprise feature matrix, hiring budget, "
                    "and 18-month financial projection for an open-source multi-agent platform launching a "
                    "managed cloud tier ($299/mo team plan starting from 60 design partners, 18% monthly growth, "
                    "2.5% churn, $600 CAC). Deliver full docs + `executive_dashboard.html`."
                ),
                expected_deliverables=["strategy_brief.md", "pricing_and_economics.md", "financial_projection.csv", "executive_dashboard.html"],
            ),
        ],
    ),
    "research": ScenarioSpec(
        id="research",
        name="Deep Research & Intelligence Lab",
        category="Analysis & Research",
        icon="microscope",
        tagline="Investigate complex questions with quantitative modeling and adversarial peer critique.",
        description=(
            "A rigorous multi-agent research team where investigators, quantitative analysts, and a "
            "skeptical peer reviewer challenge assumptions before synthesizing an interactive research dossier."
        ),
        recommended_mode="pipeline_loop",
        recommended_orchestrator="gemini-4-argon",
        agents=[
            AgentBlueprint(
                name="LeadInvestigator",
                role="Principal Research Investigator",
                specialty="Structured decomposition, hypothesis framing, comparative landscape analysis",
                include_code_runner=False,
                instruction=(
                    "You are LeadInvestigator. Break the research question into clear dimensions, hypotheses, "
                    "tradeoff axes, and evaluation criteria. Save `research_notes.md` and post a structured `finding` "
                    "to the blackboard."
                ),
            ),
            AgentBlueprint(
                name="QuantitativeAnalyst",
                role="Quantitative Analyst & Simulation Builder",
                specialty="Python modeling, sensitivity tables, benchmarks, structured CSV datasets",
                include_code_runner=True,
                include_finance_tools=True,
                instruction=(
                    "You are QuantitativeAnalyst. Read the blackboard and build a reproducible Python analysis script "
                    "`analysis.py` that computes concrete comparative metrics, sensitivity tables, and saves `metrics.csv`. "
                    "Run `analysis.py` with `run_python_script` and post verified quantitative findings to the blackboard."
                ),
            ),
            AgentBlueprint(
                name="SkepticalCritic",
                role="Adversarial Peer Reviewer",
                specialty="Bias detection, counterarguments, methodology stress-testing, evidence gaps",
                include_code_runner=False,
                instruction=(
                    "You are SkepticalCritic. Scrutinize LeadInvestigator's claims and QuantitativeAnalyst's model "
                    "from the blackboard and workspace files. Identify hidden assumptions, edge cases, failure modes, "
                    "and missing tradeoffs. Post a candid `critique` on the blackboard and save `peer_review.md`."
                ),
            ),
            AgentBlueprint(
                name="ReportSynthesizer",
                role="Chief Research Editor",
                specialty="Executive synthesis, decision matrices, publication-grade interactive HTML reports",
                include_code_runner=False,
                instruction=(
                    "You are ReportSynthesizer. Incorporate every finding AND SkepticalCritic's counterpoints into "
                    "a publication-grade `research_report.md` AND an interactive visual brief `research_brief.html` "
                    "(self-contained HTML/CSS/SVG charts, zero external dependencies). Post final `decision` to the blackboard."
                ),
            ),
        ],
        templates=[
            PromptTemplate(
                id="hydrogen_economics_study",
                title="Multi-Agent Token Economics: Hydrogen vs Flagship Tiers",
                badge="Quant Research",
                prompt=(
                    "Conduct a deep technical and economic study comparing 3 multi-agent architectures: "
                    "(A) All-Flagship Neon/Carbon team, (B) Hybrid Rank-Up (Neon orchestrator + 4 Hydrogen workers), "
                    "and (C) Pure Peer-Mesh Hydrogen collective across 10k-500k token workloads. Write & run `analysis.py` "
                    "to compute exact cost/latency tradeoffs, stress-test assumptions, and deliver `research_report.md` + `research_brief.html`."
                ),
                expected_deliverables=["research_notes.md", "analysis.py", "metrics.csv", "peer_review.md", "research_report.md", "research_brief.html"],
            ),
            PromptTemplate(
                id="kv_cache_study",
                title="LLM Inference & Prefix Caching Optimization Dossier",
                badge="Systems Study",
                prompt=(
                    "Analyze KV-cache memory pressure, durable implicit prefix caching (>4k tokens), and "
                    "speculative decoding tradeoffs for long-context multi-agent teams. Build a Python simulation "
                    "in `analysis.py`, peer-review the methodology, and publish `research_report.md` + `research_brief.html`."
                ),
                expected_deliverables=["research_notes.md", "analysis.py", "peer_review.md", "research_report.md", "research_brief.html"],
            ),
            PromptTemplate(
                id="edge_ai_market",
                title="Edge AI Hardware Market Entry Feasibility",
                badge="Market Analysis",
                prompt=(
                    "Evaluate the technical, supply-chain, and go-to-market feasibility of launching a $299 local "
                    "developer AI inference appliance in 2026-2027. Model BOM & margin sensitivities in `analysis.py`, "
                    "apply skeptical risk analysis, and output `research_report.md` + `research_brief.html`."
                ),
                expected_deliverables=["research_notes.md", "analysis.py", "peer_review.md", "research_report.md", "research_brief.html"],
            ),
        ],
    ),
    "trip_planning": ScenarioSpec(
        id="trip_planning",
        name="Global Trip Planner & Travel Concierge",
        category="Travel & Lifestyle",
        icon="compass",
        tagline="Coordinate itinerary design, transit logistics, local culinary gems, and backup plans.",
        description=(
            "Four travel-specialist Hydrogen agents collaborate in parallel to craft realistic day-by-day "
            "itineraries, exact budget spreadsheets, neighborhood food picks, rain-day contingencies, and an interactive travel guide."
        ),
        recommended_mode="peer_mesh",
        recommended_orchestrator="gemini-4-hydrogen",
        agents=[
            AgentBlueprint(
                name="ItineraryDesigner",
                role="Master Route & Pacing Architect",
                specialty="Geographic clustering, realistic transit times, balanced pacing, daily flow",
                include_code_runner=False,
                instruction=(
                    "You are ItineraryDesigner. Craft a geographically sensible, unhurried day-by-day route minimizing "
                    "backtracking. Save `itinerary_draft.md` and post a `proposal` to the blackboard with each day's "
                    "neighborhood anchors so BudgetAndLogisticsAgent and LocalCultureAndFoodScout can align."
                ),
            ),
            AgentBlueprint(
                name="BudgetAndLogisticsAgent",
                role="Travel Finance & Transit Specialist",
                specialty="Rail/flight passes, itemized daily budgets, neighborhood hotel picks, booking timelines",
                include_code_runner=True,
                include_finance_tools=False,
                instruction=(
                    "You are BudgetAndLogisticsAgent. Read the blackboard (`read_blackboard`) and build an itemized "
                    "cost model (`budget_breakdown.csv` and `logistics.md`) staying strictly within the user's budget, "
                    "including transit passes, accommodation ranges, meals, and buffer. Post budget checks (`kind='finding'`) "
                    "and flag any pacing or budget overruns to teammates."
                ),
            ),
            AgentBlueprint(
                name="LocalCultureAndFoodScout",
                role="Local Food, Culture & Hidden Gems Curator",
                specialty="Authentic regional dishes, local etiquette, off-the-beaten-path walks, timing tips",
                include_code_runner=False,
                instruction=(
                    "You are LocalCultureAndFoodScout. Read the blackboard to match ItineraryDesigner's daily neighborhoods.\n"
                    "Add specific authentic food experiences, morning/sunset timing secrets, cultural etiquette notes, "
                    "and non-touristy gems into `local_gems.md`. Post top recommendations to the blackboard (`kind='finding'`)."
                ),
            ),
            AgentBlueprint(
                name="ContingencyPlanner",
                role="Resilience Planner & Interactive Guide Publisher",
                specialty="Weather backups, packing checklists, emergency tips, interactive HTML travel handbook",
                include_code_runner=False,
                instruction=(
                    "You are ContingencyPlanner. Read the blackboard and all saved travel drafts (`list_workspace_files`).\n"
                    "Add rain-day swaps, jet-lag recovery tips, and a smart packing checklist, then assemble the complete "
                    "polished, interactive travel handbook `trip_guide.html` (beautiful day-tabs, interactive checklist, "
                    "budget summary cards — zero external dependencies!) plus `final_itinerary.md`. Post final `decision` to the blackboard."
                ),
            ),
        ],
        templates=[
            PromptTemplate(
                id="tokyo_kyoto_7d",
                title="7-Day Culinary & Hidden-Gem Tokyo + Kyoto ($3,500)",
                badge="Japan • 7 Days",
                prompt=(
                    "Plan a 7-day trip to Tokyo (4 days) and Kyoto (3 days) for 2 travelers with a total on-ground "
                    "budget of $3,500 (excluding international flights). Focus on standout local food markets, "
                    "artisan coffee, architectural walks, shrines at quiet hours, and seamless Shinkansen transit. "
                    "Deliver `final_itinerary.md`, `budget_breakdown.csv`, and an interactive `trip_guide.html`."
                ),
                expected_deliverables=["final_itinerary.md", "budget_breakdown.csv", "local_gems.md", "trip_guide.html"],
            ),
            PromptTemplate(
                id="italy_roadtrip_10d",
                title="10-Day Amalfi Coast & Dolomites Scenic Journey",
                badge="Italy • 10 Days",
                prompt=(
                    "Plan a 10-day Italy adventure pairing coastal relaxation on the Amalfi Coast with dramatic "
                    "mountain drives and alpine lakes in the Dolomites for 2 travelers ($4,800 budget). Include "
                    "train + rental car handoff logistics, local trattorias, weather backup swaps, `budget_breakdown.csv`, "
                    "and an interactive `trip_guide.html`."
                ),
                expected_deliverables=["final_itinerary.md", "budget_breakdown.csv", "trip_guide.html"],
            ),
            PromptTemplate(
                id="istanbul_workation_5d",
                title="5-Day Istanbul Culture, Bosphorus & Workation",
                badge="Istanbul • 5 Days",
                prompt=(
                    "Design a 5-day Istanbul workation itinerary balancing 4 hours/day of remote work (great specialty "
                    "coffee & reliable Wi-Fi neighborhoods across Karaköy, Kadıköy, and Cihangir) with Bosphorus ferries, "
                    "historic peninsula highlights, and unforgettable Turkish cuisine on a $1,600 budget. "
                    "Deliver `final_itinerary.md`, `budget_breakdown.csv`, and `trip_guide.html`."
                ),
                expected_deliverables=["final_itinerary.md", "budget_breakdown.csv", "trip_guide.html"],
            ),
        ],
    ),
    "product_launch": ScenarioSpec(
        id="product_launch",
        name="Open-Source & Product Launch Studio",
        category="Product & DevRel",
        icon="rocket",
        tagline="Ship landing pages, documentation, launch messaging, and interactive demos together.",
        description=(
            "A cross-functional product launch team that collaborates on positioning, developer docs, "
            "a live interactive HTML product microsite, and a multi-channel launch playbook."
        ),
        recommended_mode="peer_mesh",
        recommended_orchestrator="gemini-4-argon",
        agents=[
            AgentBlueprint(
                name="ProductManager",
                role="Product Positioning & Scope Lead",
                specialty="Value proposition, target personas, feature prioritization, narrative arc",
                include_code_runner=False,
                instruction=(
                    "You are ProductManager. Define the crisp value proposition, 3 killer differentiators, user personas, "
                    "and hero copy. Save `positioning.md` and post a `proposal` to the blackboard for teammates."
                ),
            ),
            AgentBlueprint(
                name="DeveloperAdvocate",
                role="DevRel & Documentation Architect",
                specialty="Quick-start tutorials, code examples, architecture explainers, README craft",
                include_code_runner=False,
                instruction=(
                    "You are DeveloperAdvocate. Read the blackboard and write a compelling developer quickstart guide "
                    "`quickstart.md` with copy-pasteable examples and troubleshooting notes. Post key messaging hooks to the blackboard."
                ),
            ),
            AgentBlueprint(
                name="InteractiveDemoBuilder",
                role="Frontend & Interactive Microsite Engineer",
                specialty="Self-contained interactive HTML/CSS/JS product landing pages and live interactive demos",
                include_code_runner=False,
                instruction=(
                    "You are InteractiveDemoBuilder. Read the blackboard and build a stunning, self-contained product "
                    "launch landing page `launch_page.html` featuring hero messaging, interactive feature switcher, "
                    "live simulated demo widget, and crisp dark/light styling (zero external CDN dependencies!). "
                    "Post a `finding` to the blackboard describing the interactive sections."
                ),
            ),
            AgentBlueprint(
                name="LaunchStrategist",
                role="Launch Campaign & Community Strategist",
                specialty="Launch-day choreography, social threads, HN/GitHub framing, success KPIs",
                include_code_runner=False,
                instruction=(
                    "You are LaunchStrategist. Review all teammate assets (`read_blackboard`, `list_workspace_files`), "
                    "create `launch_plan.md` with Show HN / GitHub / social launch copy, launch-week checklist, and KPIs, "
                    "and post a final `decision` to the blackboard."
                ),
            ),
        ],
        templates=[
            PromptTemplate(
                id="oss_launch",
                title="Open-Source AI Framework GitHub Launch Kit",
                badge="DevRel + Site",
                prompt=(
                    "Prepare a complete open-source GitHub launch kit for an AI developer framework called "
                    "'PulseGrid' (sub-50ms distributed agent telemetry). Deliver `positioning.md`, `quickstart.md`, "
                    "a polished interactive landing page `launch_page.html`, and `launch_plan.md`."
                ),
                expected_deliverables=["positioning.md", "quickstart.md", "launch_page.html", "launch_plan.md"],
            ),
            PromptTemplate(
                id="keynote_demo",
                title="Conference Keynote Storyboard & Interactive Slides",
                badge="Interactive Deck",
                prompt=(
                    "Create a developer conference keynote package titled 'Small Fast Models Working Together: "
                    "Why Multi-Agent Teams Beat Monoliths'. Deliver `positioning.md`, `quickstart.md`, an interactive "
                    "keyboard-navigable HTML slide deck (`launch_page.html`), and `launch_plan.md`."
                ),
                expected_deliverables=["positioning.md", "launch_page.html", "launch_plan.md"],
            ),
            PromptTemplate(
                id="api_product_launch",
                title="Video-as-Code Cloud API Launch Campaign",
                badge="GTM + Demo",
                prompt=(
                    "Plan and build the launch assets for 'FrameScript', an open-source Video-as-Code rendering API "
                    "replacing manual video editing for marketing teams. Deliver `positioning.md`, `quickstart.md`, "
                    "`launch_page.html`, and `launch_plan.md`."
                ),
                expected_deliverables=["positioning.md", "quickstart.md", "launch_page.html", "launch_plan.md"],
            ),
        ],
    ),
}


def list_scenarios() -> list[ScenarioSpec]:
    return list(SCENARIOS.values())


def get_scenario(scenario_id: str) -> ScenarioSpec:
    if scenario_id not in SCENARIOS:
        raise KeyError(f"Unknown scenario '{scenario_id}'. Valid options: {list(SCENARIOS.keys())}")
    return SCENARIOS[scenario_id]
