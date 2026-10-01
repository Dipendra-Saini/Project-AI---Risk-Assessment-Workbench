# ADR-006: The AI drafts analysis and suggested conditions, never an outcome

Status: Accepted

## Context
"The system prepares, humans decide." A drafted "Recommend: approve" anchors
the committee (automation bias) even if a human technically clicks the button.

## Decision
The drafting prompt and its output schema have no outcome field. The drafter
may propose *conditions to consider* (e.g. transaction limits, enhanced
monitoring for 90 days). Outcomes exist only in `committee_votes` and `decisions`.

## Consequences
Committee members form their own view from scores, trace and citations.
Accepted cost: slightly more committee reading time.
