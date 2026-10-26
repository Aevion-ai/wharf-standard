from __future__ import annotations

import json
from pathlib import Path

import pytest

from verify_decision import PacketError, check_packet, decide, evidence_sha256

ROOT = Path(__file__).parent


def ratings(score: int, **overrides: int) -> dict[str, int]:
    base = {item: score for item in ("C1", "C2", "C3", "C4", "C5", "C6", "C7")}
    base.update(overrides)
    return base


def packet_for(scores: dict[str, int], disposition: str, *, days: int = 30) -> dict:
    competencies = [{"id": key, "rating": value} for key, value in scores.items() if key.startswith("C")]
    invariants = [
        {"id": key, "rating": value} for key, value in scores.items() if not key.startswith("C")
    ]
    body: dict = {
        "schema": "aevion.wharf.route_certificate.v0.1",
        "certificate_id": "fixture",
        "subject_id": "agent-under-test",
        "route_id": "ROUTE_EXAMPLE",
        "issuer_id": "issuer-a",
        "reviewer_id": "reviewer-b",
        "issued_at": "2026-10-26T00:00:00Z",
        "expires_at": f"2026-11-{days:02d}T00:00:00Z" if days > 26 else "2026-11-25T00:00:00Z",
        "disposition": disposition,
        "competencies": competencies,
        "admission": "NOT_ADMITTED",
        "fixture_status": "FIXTURE_NOT_A_CREDENTIAL",
    }
    if days == 90:
        body["expires_at"] = "2027-01-24T00:00:00Z"
    if days == 10:
        body["expires_at"] = "2026-11-05T00:00:00Z"
    if invariants:
        body["route_invariants"] = invariants
    body["evidence_packet_sha256"] = evidence_sha256(body)
    return body


def test_unsatisfactory_is_refused() -> None:
    assert decide(ratings(4, C4=1)) == "REFUSED_AS_STATED"


def test_two_needs_improvement_is_provisional() -> None:
    assert decide(ratings(3, C1=2, C2=2)) == "PROVISIONAL_QUALIFIED"


def test_one_needs_improvement_fail_closes_to_provisional() -> None:
    assert decide(ratings(4, C7=2)) == "PROVISIONAL_QUALIFIED"


def test_all_satisfactory_indicates_certified() -> None:
    assert decide(ratings(3)) == "ROUTE_CERTIFIED"


def test_missing_competency_has_no_outcome() -> None:
    scores = ratings(3)
    del scores["C6"]
    with pytest.raises(PacketError, match="missing core"):
        decide(scores)


def test_issuer_cannot_review_self() -> None:
    body = packet_for(ratings(3), "ROUTE_CERTIFIED", days=90)
    body["reviewer_id"] = body["issuer_id"]
    body["evidence_packet_sha256"] = evidence_sha256(body)
    with pytest.raises(PacketError, match="issuer cannot review"):
        check_packet(body)


def test_perfect_scores_are_still_not_admitted() -> None:
    result = check_packet(packet_for(ratings(4), "ROUTE_CERTIFIED", days=90))
    assert result == {
        "indicated_disposition": "ROUTE_CERTIFIED",
        "admission": "NOT_ADMITTED",
        "reason": "no_publishing_key_directory",
    }


def test_refusal_fixture_matches_the_tree() -> None:
    fixture = json.loads((ROOT / "examples" / "refusal.fixture.json").read_text(encoding="utf-8"))
    result = check_packet(fixture)
    assert result["indicated_disposition"] == "REFUSED_AS_STATED"
    assert result["admission"] == "NOT_ADMITTED"


def test_route_invariant_failure_refuses() -> None:
    scores = ratings(4)
    scores["RUNWAY_SAFETY_AREA_LOCK"] = 0
    assert decide(scores) == "REFUSED_AS_STATED"


def test_certified_expiry_over_90_days_is_rejected() -> None:
    body = packet_for(ratings(4), "ROUTE_CERTIFIED", days=90)
    body["expires_at"] = "2027-04-01T00:00:00Z"
    body["evidence_packet_sha256"] = evidence_sha256(body)
    with pytest.raises(PacketError, match="90 days"):
        check_packet(body)
