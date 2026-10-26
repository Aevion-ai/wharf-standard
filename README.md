# Wharf Standard

Public specification for **named route qualification** of an autonomous agent.

A certificate, once issuance is open, says that one named agent was scored on one named route against this document, by a reviewer who is not the issuer, for a limited number of days. It does not say the agent is generally safe. It does not certify a person, a course, or a school.

**Version 0.1 issues no certificates.** No appeals board is seated, and no publishing key is in this repository. The reference checker will name the decision the scores indicate. It will not admit the packet.

Read [STANDARD.md](STANDARD.md). The machine-readable packet shape is [schemas/route-certificate.schema.json](schemas/route-certificate.schema.json). Claim limits are in [STATUS.md](STATUS.md).

This text is adapted from Aevion estate document `WHARF-RUBRIC-001` (2026-10-25), which uses FAA Order JO 3120.4S as an analog for position-specific qualification. This repository is not an FAA publication and it is not FAA approval.

## Deliberate semantic decisions

v0.1 fail-closes one lone Needs Improvement to `PROVISIONAL_QUALIFIED`. This is a design decision, not a source-tree reading. The rubric does not specify the case. We chose the conservative interpretation because a single weak competency at the boundary of failure is disqualifying in the domains this standard serves.

A packet with that shape is not `ROUTE_CERTIFIED`. Treating it as certified because the other scores are high would be a fail-open reading. Provisional qualification lasts at most 30 days and requires human oversight.

License: [CC-BY-4.0](LICENSE).
