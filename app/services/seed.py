from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import new_public_id
from app.models import Assessment, Cohort, LearningPath, Level, User

LEVEL_SPECS = [
    {
        "public_id": "level-1-basic-llm-agent",
        "ordinal": 1,
        "slug": "basic-llm-agent",
        "title": "Basic LLM Agent",
        "capability": "Prompting, model params, persona",
        "course_anchor": "LLM APIs & Model Integration",
        "summary": "Build and publish a grounded chatbot with a clear persona and parameter discipline.",
        "assessment": {
            "scenario": "Create a customer-ready assistant with clear persona, grounding, and response discipline.",
            "deliverables": {"live_app": {"required": True}, "artifact_zip": {"required": True}, "code": {"required": False}},
            "pass_criteria": {"min_weighted_score": 3.4, "min_per_required_dimension": 3, "max_attempts": 3},
            "rubric": {"correctness": 0.35, "architecture_quality": 0.15, "documentation_clarity": 0.20},
        },
    },
    {
        "public_id": "level-2-rag-powered-agent",
        "ordinal": 2,
        "slug": "rag-powered-agent",
        "title": "RAG-Powered Agent",
        "capability": "Knowledge bases, chunking, retrieval",
        "course_anchor": "Retrieval Augmented Generation (RAG)",
        "summary": "Attach a domain corpus and demonstrate faithful cited answers with tuned retrieval.",
        "assessment": {
            "scenario": "Build a retrieval-backed assistant that cites the source evidence it used.",
            "deliverables": {"live_app": {"required": True}, "artifact_zip": {"required": True}, "code": {"required": False}},
            "pass_criteria": {"min_weighted_score": 3.4, "min_per_required_dimension": 3, "max_attempts": 3},
            "rubric": {"correctness": 0.30, "groundedness": 0.30, "documentation_clarity": 0.10},
        },
    },
    {
        "public_id": "level-3-tool-calling-agent",
        "ordinal": 3,
        "slug": "tool-calling-agent",
        "title": "Tool-Calling Agent",
        "capability": "Tools, workflows, memory",
        "course_anchor": "Agentic AI - Tool Calling & Multi-step Reasoning",
        "summary": "Design a workflow that uses built-in and custom tools to complete a multi-step task.",
        "assessment": {
            "scenario": "You are assisting engineering leadership with a repo health readout across five public GitHub repositories.",
            "learning_objectives": [
                "Design a multi-step workflow with tool orchestration.",
                "Combine built-in and custom tools.",
                "Use conversation memory for follow-up queries.",
            ],
            "deliverables": {
                "live_app": {"required": True, "must_expose_api": True},
                "artifact_zip": {
                    "required": True,
                    "required_files": [
                        "workflow_diagram.png",
                        "custom_tool.openapi.yaml",
                        "five_test_runs.md",
                        "reflection.md",
                    ],
                },
                "code": {"required": True, "language": "python", "entrypoint": "run_harness.py"},
            },
            "automated_checks": ["app_healthy", "tools_present", "memory_on", "harness_passes", "files_present", "no_secret_leak"],
            "pass_criteria": {"min_weighted_score": 3.5, "min_per_required_dimension": 3, "max_attempts": 3},
            "rubric": {
                "workflow_design": 0.25,
                "tool_appropriateness": 0.25,
                "grounded_reasoning": 0.20,
                "robustness": 0.15,
                "documentation_clarity": 0.15,
            },
        },
    },
    {
        "public_id": "level-4-evaluation-observability",
        "ordinal": 4,
        "slug": "evaluation-observability",
        "title": "Evaluation & Observability",
        "capability": "Eval datasets, tracing, A/B prompts",
        "course_anchor": "LLM Evaluation & Output Quality",
        "summary": "Instrument an agent with Langfuse, build a gold set, and interpret A/B test results.",
        "assessment": {
            "scenario": "Instrument an existing agent with observability and evaluator workflows.",
            "deliverables": {"live_app": {"required": True}, "artifact_zip": {"required": True}, "code": {"required": True}},
            "pass_criteria": {"min_weighted_score": 3.5, "min_per_required_dimension": 3, "max_attempts": 3},
            "rubric": {"observability": 0.35, "correctness": 0.15, "architecture_quality": 0.15},
        },
    },
    {
        "public_id": "level-5-mcp-connected-agent",
        "ordinal": 5,
        "slug": "mcp-connected-agent",
        "title": "MCP-Connected Agent",
        "capability": "MCP client and server, multi-server flows",
        "course_anchor": "Framework - MCP",
        "summary": "Consume an external MCP server and expose the learner agent as an MCP endpoint.",
        "assessment": {
            "scenario": "Integrate a customer workflow with MCP server and client capabilities.",
            "deliverables": {"live_app": {"required": True}, "artifact_zip": {"required": True}, "code": {"required": True}},
            "pass_criteria": {"min_weighted_score": 3.5, "min_per_required_dimension": 3, "max_attempts": 3},
            "rubric": {"tool_appropriateness": 0.25, "architecture_quality": 0.20, "robustness": 0.15},
        },
    },
    {
        "public_id": "level-6-multi-agent-orchestration",
        "ordinal": 6,
        "slug": "multi-agent-orchestration",
        "title": "Multi-Agent Orchestration",
        "capability": "LangChain / LangGraph, HITL",
        "course_anchor": "Framework - LangChain / LangGraph",
        "summary": "Ship a supervised three-agent pipeline with human approval and state recovery.",
        "assessment": {
            "scenario": "Deliver a resilient multi-agent workflow with supervisory controls.",
            "deliverables": {"live_app": {"required": True}, "artifact_zip": {"required": True}, "code": {"required": True}},
            "pass_criteria": {"min_weighted_score": 3.6, "min_per_required_dimension": 3, "max_attempts": 3},
            "rubric": {"architecture_quality": 0.30, "robustness": 0.20, "correctness": 0.15},
        },
    },
    {
        "public_id": "level-7-responsible-ai-safety",
        "ordinal": 7,
        "slug": "responsible-ai-safety",
        "title": "Responsible AI & Safety",
        "capability": "Moderation, guardrails, red-team",
        "course_anchor": "Responsible AI & Safety",
        "summary": "Harden the prior agent with moderation, guardrails, and bias testing.",
        "assessment": {
            "scenario": "Harden a production-grade agent against unsafe content and operational failures.",
            "deliverables": {"live_app": {"required": True}, "artifact_zip": {"required": True}, "code": {"required": True}},
            "pass_criteria": {"min_weighted_score": 3.7, "min_per_required_dimension": 3, "max_attempts": 3},
            "rubric": {"robustness": 0.30, "architecture_quality": 0.20, "groundedness": 0.15},
        },
    },
]


async def seed_initial_data(session: AsyncSession) -> None:
    existing_path = await session.scalar(select(LearningPath).where(LearningPath.version == "2026.v1"))
    if existing_path is not None:
        return

    cohort = Cohort(
        slug="2026-fde-ramp",
        name="2026 FDE Ramp Cohort",
        starts_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        rubric_version="rubv_042",
    )
    path = LearningPath(version="2026.v1", title="DIFY FDE Learning Path", active_from=datetime(2026, 4, 1, tzinfo=timezone.utc))
    session.add_all([cohort, path])
    await session.flush()

    levels: list[Level] = []
    for spec in LEVEL_SPECS:
        level = Level(
            public_id=spec["public_id"],
            path_id=path.id,
            ordinal=spec["ordinal"],
            slug=spec["slug"],
            title=spec["title"],
            capability=spec["capability"],
            course_anchor=spec["course_anchor"],
            summary=spec["summary"],
        )
        levels.append(level)
        session.add(level)
    await session.flush()

    for level, spec in zip(levels, LEVEL_SPECS, strict=True):
        assessment = Assessment(
            public_id=spec["public_id"],
            level_id=level.id,
            version="v1.0",
            title=f"{spec['title']} Assessment",
            active_from=datetime(2026, 4, 1, tzinfo=timezone.utc),
            is_published=True,
            rubric_version="rubv_042",
            spec=spec["assessment"],
        )
        session.add(assessment)

    users = [
        User(
            public_id=new_public_id("usr"),
            email="learner1@example.com",
            full_name="Shivam Learner",
            role="learner",
            cohort_id=cohort.id,
            dify_workspace_id="ws_learner_1",
        ),
        User(
            public_id=new_public_id("usr"),
            email="reviewer1@example.com",
            full_name="Priya Reviewer",
            role="reviewer",
            cohort_id=cohort.id,
            dify_workspace_id="ws_reviewer_1",
        ),
        User(
            public_id=new_public_id("usr"),
            email="admin1@example.com",
            full_name="Alex Admin",
            role="admin",
            cohort_id=cohort.id,
            dify_workspace_id="ws_admin_1",
        ),
    ]
    session.add_all(users)
    await session.commit()
