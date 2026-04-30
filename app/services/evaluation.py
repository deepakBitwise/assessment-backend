from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from statistics import median

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AutomatedRun, AuditEvent, HumanReview, JudgeRun, Submission, Verdict
from app.models import utcnow


def _judge_dimensions(submission: Submission) -> dict[str, int]:
    dimensions = {
        "workflow_design": 3,
        "tool_appropriateness": 3,
        "grounded_reasoning": 3,
        "robustness": 3,
        "documentation_clarity": 3,
        "correctness": 3,
        "groundedness": 3,
        "architecture_quality": 3,
        "observability": 3,
    }
    artifact_roles = {artifact.role for artifact in submission.artifacts}
    if "artifact_zip" in artifact_roles:
        dimensions["documentation_clarity"] = 4
    if "code" in artifact_roles or "code_dir" in artifact_roles:
        dimensions["workflow_design"] = 4
        dimensions["architecture_quality"] = 4
    if submission.app_url:
        dimensions["tool_appropriateness"] = 4
        dimensions["correctness"] = 4
    return dimensions


def _weighted_score(weights: dict[str, float], scores: dict[str, int]) -> float:
    total = 0.0
    for dimension, weight in weights.items():
        total += scores.get(dimension, 0) * weight
    return round(total, 2)


async def evaluate_submission(session: AsyncSession, submission: Submission) -> None:
    spec = submission.attempt.assessment.spec
    required_roles = []
    deliverables = spec.get("deliverables", {})
    if deliverables.get("artifact_zip", {}).get("required"):
        required_roles.append("artifact_zip")
    if deliverables.get("code", {}).get("required"):
        required_roles.extend(["code", "code_dir"])

    artifact_roles = {artifact.role for artifact in submission.artifacts}
    files_present = "artifact_zip" in artifact_roles
    has_code = bool({"code", "code_dir"} & artifact_roles) if deliverables.get("code", {}).get("required") else True
    app_healthy = bool(submission.app_url)

    checks = {
        "app_healthy": {"passed": app_healthy, "detail": "live app URL provided" if app_healthy else "missing live app URL"},
        "files_present": {"passed": files_present, "detail": "artifact bundle uploaded" if files_present else "missing artifact zip"},
        "harness_passes": {"passed": has_code, "detail": "code bundle uploaded" if has_code else "missing code bundle"},
        "tools_present": {"passed": bool(submission.dify_app_id or submission.app_url), "detail": "integration stub satisfied"},
        "memory_on": {"passed": True, "detail": "stub evaluator assumes enabled"},
        "no_secret_leak": {"passed": True, "detail": "stub scan passed"},
    }
    required_check_ids = spec.get("automated_checks") or list(checks.keys())
    all_required_passed = all(checks[check_id]["passed"] for check_id in required_check_ids if check_id in checks)
    automated = AutomatedRun(submission_id=submission.id, checks=checks, verdict="passed" if all_required_passed else "failed")
    session.add(automated)

    if not all_required_passed:
        verdict = Verdict(
            submission_id=submission.id,
            state="failed",
            weighted_score=0.0,
            dimension_scores={},
            reason="Required automated checks failed.",
        )
        submission.status = "resolved"
        submission.evaluation_summary = {"requires_review": False, "all_required_passed": False}
        submission.attempt.state = "resolved"
        submission.attempt.cooldown_until = utcnow() + timedelta(hours=12)
        session.add(verdict)
        session.add(AuditEvent(actor_public_id=None, entity_ref=submission.public_id, kind="submission.auto_failed", payload=checks))
        await session.commit()
        return

    weights = spec.get("rubric", {})
    judge_dimensions = _judge_dimensions(submission)
    judge_runs: list[JudgeRun] = []
    medians: dict[str, int] = {}
    dimension_samples: dict[str, list[int]] = defaultdict(list)
    for run_no in range(1, 4):
        scores = {dimension: score - 1 if run_no == 2 and score > 3 else score for dimension, score in judge_dimensions.items()}
        judge_run = JudgeRun(
            submission_id=submission.id,
            run_no=run_no,
            scores=scores,
            rationale="Stub judge run produced provisional rubric scores.",
            confidence=0.82,
            cost_usd=0.02,
            tokens_used=1200,
        )
        judge_runs.append(judge_run)
        session.add(judge_run)
        for dimension, score in scores.items():
            dimension_samples[dimension].append(score)

    for dimension, values in dimension_samples.items():
        medians[dimension] = int(median(values))

    weighted_score = _weighted_score(weights, medians)
    threshold = spec.get("pass_criteria", {}).get("min_weighted_score", 3.5)
    floor = spec.get("pass_criteria", {}).get("min_per_required_dimension", 3)
    relevant_dimensions = [dimension for dimension in weights if medians.get(dimension, 0) < floor]
    requires_review = weighted_score < threshold + 0.3 or bool(relevant_dimensions)
    final_state = "pending_review" if requires_review else ("passed" if weighted_score >= threshold and not relevant_dimensions else "failed")

    if not requires_review:
        verdict = Verdict(
            submission_id=submission.id,
            state=final_state,
            weighted_score=weighted_score,
            dimension_scores=medians,
            reason="Automatically resolved from stub judge output.",
        )
        session.add(verdict)
        submission.attempt.state = "resolved"
        if final_state == "failed":
            submission.attempt.cooldown_until = utcnow() + timedelta(hours=12)
    else:
        submission.attempt.state = "under_review"

    submission.status = "under_review" if requires_review else "resolved"
    submission.evaluation_summary = {
        "all_required_passed": True,
        "judge_medians": medians,
        "weighted_score": weighted_score,
        "requires_review": requires_review,
    }
    session.add(AuditEvent(actor_public_id=None, entity_ref=submission.public_id, kind="submission.evaluated", payload=submission.evaluation_summary))
    await session.commit()


async def apply_review_outcome(session: AsyncSession, submission: Submission, review: HumanReview) -> Verdict:
    spec = submission.attempt.assessment.spec
    weights = spec.get("rubric", {})
    weighted_score = _weighted_score(weights, review.scores)
    threshold = spec.get("pass_criteria", {}).get("min_weighted_score", 3.5)
    floor = spec.get("pass_criteria", {}).get("min_per_required_dimension", 3)
    dimension_floor_failed = any(review.scores.get(dimension, 0) < floor for dimension in weights)
    state = "passed" if review.decision == "pass" and weighted_score >= threshold and not dimension_floor_failed else "failed"

    verdict = submission.verdict or Verdict(submission_id=submission.id, weighted_score=weighted_score, dimension_scores=review.scores, state=state, reason=review.notes)
    verdict.weighted_score = weighted_score
    verdict.dimension_scores = review.scores
    verdict.state = state
    verdict.reason = review.notes
    submission.status = "resolved"
    submission.attempt.state = "resolved"
    if state == "failed":
        submission.attempt.cooldown_until = utcnow() + timedelta(hours=12)
    session.add(verdict)
    session.add(AuditEvent(actor_public_id=None, entity_ref=submission.public_id, kind="submission.reviewed", payload={"decision": review.decision, "state": state}))
    await session.commit()
    return verdict
