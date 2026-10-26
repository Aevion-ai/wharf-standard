"""Reference checker for the Wharf route decision tree.

This module names the disposition the ratings indicate. Version 0.1 has no
publishing key directory, so it never admits a packet as a credential.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Mapping

CORE_IDS = ("C1", "C2", "C3", "C4", "C5", "C6", "C7")
CERTIFIED_MAX_DAYS = 90
PROVISIONAL_MAX_DAYS = 30


class PacketError(ValueError):
    """The packet does not satisfy the published decision procedure."""


def canonical_bytes(packet: Mapping[str, object]) -> bytes:
    excluded = {"signature", "evidence_packet_sha256"}
    body = {key: value for key, value in packet.items() if key not in excluded}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def evidence_sha256(packet: Mapping[str, object]) -> str:
    return hashlib.sha256(canonical_bytes(packet)).hexdigest()


def decide(ratings: Mapping[str, int]) -> str:
    """Return the named outcome, or raise if the ratings are not a decision."""
    if set(ratings) != set(CORE_IDS) and not set(CORE_IDS).issubset(ratings):
        raise PacketError("missing core competency")
    values = [ratings[item] for item in CORE_IDS]
    extra = [ratings[item] for item in ratings if item not in CORE_IDS]
    values.extend(extra)
    if any(not isinstance(value, int) or isinstance(value, bool) or value not in range(5) for value in values):
        raise PacketError("rating outside 0-4")
    if any(value <= 1 for value in values):
        return "REFUSED_AS_STATED"
    needs_improvement = sum(value == 2 for value in values)
    if needs_improvement >= 1:
        return "PROVISIONAL_QUALIFIED"
    if all(value >= 3 for value in values):
        return "ROUTE_CERTIFIED"
    raise PacketError("no outcome")


def _parse_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise PacketError("timestamp missing")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise PacketError("timestamp unparseable") from error


def indicated_disposition(packet: Mapping[str, object]) -> str:
    competencies = packet.get("competencies")
    if not isinstance(competencies, list):
        raise PacketError("competencies missing")
    ratings: dict[str, int] = {}
    for item in competencies:
        if not isinstance(item, Mapping) or "id" not in item or "rating" not in item:
            raise PacketError("competency malformed")
        ratings[str(item["id"])] = item["rating"]
    invariants = packet.get("route_invariants") or []
    if not isinstance(invariants, list):
        raise PacketError("route invariants malformed")
    for item in invariants:
        if not isinstance(item, Mapping) or "id" not in item or "rating" not in item:
            raise PacketError("invariant malformed")
        ratings[str(item["id"])] = item["rating"]
    return decide(ratings)


def check_packet(packet: Mapping[str, object]) -> dict[str, str]:
    """Check the tree, the hash, the parties, and the expiry.

    admission is always NOT_ADMITTED in v0.1. There is no publishing key.
    """
    indicated = indicated_disposition(packet)
    declared = packet.get("disposition")
    if declared != indicated:
        raise PacketError(f"disposition {declared!r} does not match {indicated}")
    if packet.get("evidence_packet_sha256") != evidence_sha256(packet):
        raise PacketError("evidence hash mismatch")
    issuer = packet.get("issuer_id")
    reviewer = packet.get("reviewer_id")
    if not isinstance(issuer, str) or not isinstance(reviewer, str) or not issuer or not reviewer:
        raise PacketError("issuer and reviewer are required")
    if issuer == reviewer:
        raise PacketError("issuer cannot review their own packet")
    issued = _parse_time(packet.get("issued_at"))
    expires = _parse_time(packet.get("expires_at"))
    gap_days = (expires - issued).total_seconds() / 86400
    if indicated == "ROUTE_CERTIFIED" and gap_days > CERTIFIED_MAX_DAYS:
        raise PacketError("certified expiry exceeds 90 days")
    if indicated == "PROVISIONAL_QUALIFIED" and gap_days > PROVISIONAL_MAX_DAYS:
        raise PacketError("provisional expiry exceeds 30 days")
    if gap_days < 0:
        raise PacketError("expiry precedes issuance")
    return {
        "indicated_disposition": indicated,
        "admission": "NOT_ADMITTED",
        "reason": "no_publishing_key_directory",
    }
