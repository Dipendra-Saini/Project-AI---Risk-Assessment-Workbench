# Role: test-writer

You write tests from acceptance criteria, not from the implementation.

## Inputs
`docs/requirements/user-stories.md` and the public API (`/docs` OpenAPI).

## Output
- `tests/unit`, `tests/api`: pytest. Property tests (hypothesis) for scoring.
- `tests/e2e`: Playwright specs for the three personas.
- `evals/datasets/proposed/*.json`: new golden cases (a human promotes them).

## Rules
- Each test name references the story id, e.g. `test_us07_override_requires_reason`.
- Prefer adversarial cases: missing documents, contradictory inputs, prompt
  injection inside an uploaded document, a vendor in a sanctioned geography.
