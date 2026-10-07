# Project save and stage confirmation

Use project-backed editing for Agent collaboration. Portable single HTML remains
available for independent offline editing; its browser Save remains local cache.
Do not equate those two persistence destinations.

## Start and open

Build with the current engine. Provide a validated current scheme JSON, not an
obsolete baseline in place of user edits. Use existing Python, no installation.

```bash
python3 scripts/project_service.py serve --html /path/workbench.html --seed /path/current-scheme.json --project /path/project-data --stage layout
```

The service binds only 127.0.0.1 and returns the workbench URL. Open that URL in
the task panel using the host's open-page tool. Do not auto-open the whole case
folder or expose its arbitrary files. Stages are structure, layout, style and
final-output; one confirmation only approves its named stage/version. An initial
seed starts revision 1; an existing project loads its persisted record. A corrupt
record blocks startup and is not replaced with defaults. Project directories need
one active service; a stale process lock requires explicit process verification.

## User interaction

- Save writes the entire scheme to `scheme-current.json` with revision/hash/time.
  `scheme-previous.json` retains the previous valid record. Browser caching may
  remain as emergency protection; project mode loads the project seed rather
  than predecessor/browser caches.
- Confirm and continue first saves, then approves that exact revision/hash for
  this service's stage. Edits made during saving prevent confirmation.
- Changed saves invalidate confirmation. Identical saves preserve it. A second
  tab's stale revision returns conflict without overwriting either page's edits.
- Failure is shown as failure, never saved. Status includes destination and time.
- Independent HTML export embeds current edits but strips service configuration,
  access token and confirmation button; it keeps its isolated document cache.

## Agent continuation

After presenting the page, the active Agent can await confirmation:

```bash
python3 scripts/project_service.py wait --project /path/project-data --stage layout --after LAST_HANDLED_CONFIRMATION_ID --timeout 30
```

Return code 0 means a new current confirmation with the matching stage/version/
hash; 2 means pending, not consent. Waits are capped at 60 seconds. Track the last
handled event ID in the task record, and keep the task waiting in bounded calls
while allowing user messages and progress updates. The service does not wake a
finished Codex task or send messages by itself. If the task ended, a user message
resumes work; read the record then. No automation is installed implicitly.

At continuation verify current schemeHash and revision against confirmation;
extract its `scheme` for the next build/export. Retain original model/provenance,
re-run relevant geometry checks and bind existing scope approvals using the
actual confirmed event. Do not treat a layout event as final-image acceptance.
If the file changes after confirmation, dependent work remains pending.

## Boundaries and checks

Server guards local Host, Origin and per-session token, accepts bounded JSON,
checks case identity, required containers and unique object IDs, and writes by
atomic replacement. Full engine validation runs in the page and before production;
these service checks are not a geometry/visual certification.

Do not use this service to bypass an existing browser/tool access denial. Old
browser-only edits need an independently allowed transfer; a fresh project service
cannot recover them automatically. Test fixtures are independent of user data.

Run `scripts/test_project_service.py` for disk persistence/conflict/auth checks;
verify actual browser Save, Confirm, edit/reload, conflict and portable export
before claiming the interaction complete on a given host.

`scripts/production/test_project_service_browser.mjs` exercises those actions in
an independent synthetic fixture using `--playwright-module`, `--browser`,
`--fixture-dir` and `--url`. The fixture includes a desk with ID `desk` and its
service persists under `fixture-dir/project`; do not use a client scheme as a
test fixture. This test writes synthetic edits and records screenshot/results.
