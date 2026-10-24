# MYRA — Phase 26 validation report

## Scope
Phase 26 completes the autonomous task cycle: plan one action, execute it, observe the result, verify the goal, recover from failures, and persist state.

## Implemented
- SQLite task store for objective, step, history, status, final result, errors and audit events.
- Pause/resume and restart recovery through `/task_pause`, `/task_resume`, `/task_pendentes` and `/task_detalhe/{task_id}`.
- Bounded recovery with alternative-strategy guidance and action-signature blocking to avoid repeating the same failed action.
- Observer captures the primary display in memory and sends screenshot + action result to the local vision endpoint. If capture or vision inference fails, it falls back to the local text model.
- Observer parsing does not interpret arbitrary strings as success; ambiguous responses remain indeterminate.
- Workspace path validation resolves paths before containment checks and rejects traversal and symlink escapes.
- GitHub Actions test workflow runs unit and HTTP-contract tests in a virtual display, without connecting to the user's real services.

## Tests
Run locally from the repository root:

```powershell
venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

The real-service tests are opt-in with `MYRA_TEST_INTEGRATION=1`; they are intentionally not run by CI.

## Validation boundary
A green CI run verifies the deterministic tests and mocked service contracts. It does not prove that the local Windows desktop, Chrome Extension Bridge, Ollama and llm-eyes work together in the user's current installation. That final live end-to-end check must be performed on the target PC.

## Live Chrome Bridge validation (2026-10-24)

- Confirmed the authenticated `/browser_bridge/next` route rejects requests without the bridge token (HTTP 401).
- Called `get_tabs` through the running Chrome MV3 extension; the bridge returned the live tab list.
- End-to-end smoke test passed: opened a new `https://example.com/` tab, read the page DOM/text through `read_page_url`, and closed the test tab. The close result explicitly confirmed `closed=true`; pre-existing user tabs were left untouched.
- Hardened the shared URL validator for `read_page_url`, `navigate_active_tab`, and `new_tab`: rejects non-string inputs, malformed hosts/ports, whitespace/control characters, embedded credentials, and URLs over 2,000 characters before enqueueing. Promoted the invalid-URL regression test from expected failure to a passing test.
- Full local unittest suite after the fix: 1,049 tests in 238.4 seconds, exit code 0 (`OK`; 9 skipped, 34 expected failures). `git diff --check` passed.

This validates the live Chrome extension queue and navigation/read/cleanup path. It does not replace the separate live validation of desktop vision + Ollama + the complete autonomous planner on a real task.

## Remaining security work
The workspace guard is not a sandbox. Arbitrary Python/code execution still needs dedicated sandboxing and authorization controls before exposing MYRA to untrusted users or remote clients.
