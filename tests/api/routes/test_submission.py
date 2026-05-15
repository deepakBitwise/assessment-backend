from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import Assessment, Submission, SubmissionEvents


def test_create_submission_events(client: TestClient, db: Session) -> None:
    assessment_id = f"assessment-{uuid4()}"
    submission_id = f"submission-{uuid4()}"

    assessment = Assessment(
        id=assessment_id,
        problem_statement="Test problem statement",
        deliverables=["archive.zip"],
        attachment_object_name="archive.zip",
    )
    submission = Submission(
        id=submission_id,
        assessment_id=assessment_id,
        attachment_object_name="archive.zip",
    )

    db.add(assessment)
    db.add(submission)
    db.commit()

    response = client.post(
        f"{settings.API_V1_STR}/submission/{submission_id}/events",
        json={"type": "SUCCESS", "value": "Automated checks passed"},
    )

    assert response.status_code == 200
    content = response.json()
    assert content["id"] == submission_id
    assert content["submission_id"] == submission_id
    assert content["events"] == [
        {"type": "SUCCESS", "value": "Automated checks passed"}
    ]

    second_response = client.post(
        f"{settings.API_V1_STR}/submission/{submission_id}/events",
        json={"type": "WARNING", "value": "Retry completed"},
    )

    assert second_response.status_code == 200
    second_content = second_response.json()
    assert second_content["id"] == submission_id
    assert second_content["submission_id"] == submission_id
    assert second_content["events"] == [
        {"type": "SUCCESS", "value": "Automated checks passed"},
        {"type": "WARNING", "value": "Retry completed"},
    ]


def test_create_submission_events_submission_not_found(client: TestClient) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/submission/submission-missing/events",
        json={"type": "SUCCESS", "value": "This should not be stored"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Submission not found"


def test_read_submission_events(client: TestClient, db: Session) -> None:
    assessment_id = f"assessment-{uuid4()}"
    submission_id = f"submission-{uuid4()}"

    assessment = Assessment(
        id=assessment_id,
        problem_statement="Another test problem statement",
        deliverables=["archive.zip"],
        attachment_object_name="archive.zip",
    )
    submission = Submission(
        id=submission_id,
        assessment_id=assessment_id,
        attachment_object_name="archive.zip",
    )
    submission_events = SubmissionEvents(
        id=submission_id,
        submission_id=submission_id,
        events=[
            {"type": "SUCCESS", "value": "Uploaded successfully"},
            {"type": "WARNING", "value": "Formatting issue detected"},
        ],
    )

    db.add(assessment)
    db.add(submission)
    db.add(submission_events)
    db.commit()

    response = client.get(f"{settings.API_V1_STR}/submission/{submission_id}/events")

    assert response.status_code == 200
    content = response.json()
    assert content["id"] == submission_id
    assert content["submission_id"] == submission_id
    assert content["events"] == [
        {"type": "SUCCESS", "value": "Uploaded successfully"},
        {"type": "WARNING", "value": "Formatting issue detected"},
    ]
