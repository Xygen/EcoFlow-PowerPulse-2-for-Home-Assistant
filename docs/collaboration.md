# Working with two agents

Two agents work on this repository: Codex and Claude. They never run at the
same terminal and cannot see each other's reasoning, so everything they need
from one another has to survive the gap between sessions. This document says
where that happens and who owns what.

It describes coordination only. The [backlog](backlog.md) remains the single
authoritative list of open work, the [validation status](validation.md) the
record of what has been observed, and the [decision log](decisions.md) the
record of decisions.

## Coordination happens on GitHub, not in a file

Issues and pull requests carry the coordination. They are timestamped and
threaded, both agents reach them through `gh`, and the maintainer sees
everything without opening the repository.

A file in the repository was considered and rejected. On 2026-09-10 and
2026-09-11, every document both agents touched produced a merge conflict:
`CHANGELOG.md`, `docs/backlog.md`, `docs/validation.md`. A coordination file
would be the most frequently written file here, so it would conflict most
often — and a conflict in the channel is worse than a conflict in the content,
because it blocks the means of resolving it.

## One owner per work item

Each item has exactly one implementing agent, fixed when the item starts and
named in its issue. The branch prefix carries it: `codex/…` or `claude/…`.
That convention already holds across every branch in the repository.

The split is per item, not per activity. "Complex work here, everything else
there" cannot be decided without an argument each time: the authentication
classification, the broker addressing and the Home Assistant fixture harness
would all need adjudication. Naming an owner per item takes one sentence.

## Check the seam before starting

Before touching a file, check whether an open branch already edits it:

```
gh pr list --state open
git log --oneline --all -- <path>
```

If another item owns a file you need, say so in the issue instead of editing in
parallel. The same seam broke three times on 2026-09-10 and 2026-09-11 — the
Home Assistant stub in `tests/test_coordinator_transactions.py` against the
coordinator's imports — and every time it broke at the merge rather than on the
branch that opened it, because each branch passed alone.

When a seam breaks twice, add a check that detects it. That is what
`tests/test_ha_stub_coverage.py` does for this one: it compares the
coordinator's Home Assistant imports against what the harness stubs, and names
the missing entry instead of failing later with an unexplained `ImportError`.

## Releases have one owner

Only the release owner raises the version in `manifest.json` and opens a new
release section in the changelog. Either agent adds entries under
`## Unreleased`.

On 2026-09-10 two builds were prepared as `1.0.5-beta.5` from two lines within
the hour. The published one was kept and the other became `1.0.5-beta.6`, per
[D-06](decisions.md#d-06--a-published-build-is-never-renamed-or-replaced). A
single owner for version numbers is what prevents the next one. Before raising
a version, check `gh release list` and `git tag`.

## The pull request is the handover

No second format. A pull request description in this repository already states
what was done, what was deliberately left out, what remains unverified and
where the evidence is. That is exactly what an agent picking the work up next
needs, and it is already reviewed by the maintainer.

For work that has no pull request yet, the handover is a comment on the issue.
Write it to be read without a reply: name the assumptions, because the reader
cannot ask.

## Review runs both ways

Each agent reads the other's changes before they merge. This has already paid
for itself in both directions. Codex's fixture tests found five defects in
Claude's credential-renewal code, including a path that would have asked the
user for a password immediately after proving that password correct. Claude
found the stub seam in Codex's branch, which would otherwise have failed 93
tests on `main`.

Review is not secondary work. It is the part that caught both.

## Disagreement goes to the maintainer

Neither agent overrides the other silently. A review finding the author
disagrees with stays in the pull request thread, and the maintainer decides.
An agent that reverts or rewrites the other's work without that decision
destroys the record of why the work was the way it was.

## What each agent is placed for

Claude reaches the maintainer's Home Assistant instance through a connector.
On 2026-09-11 that made the difference between "the dialog showed the right
message" and reading back that `modified_at` still equalled `created_at`,
proving the aborted flow performed no write at all. That is a tooling
difference, not a judgement about code, and it suggests Claude carries live
acceptance, verification and release work.

Everything else follows the per-item owner, not a standing rule.

## What this rests on

This model assumes Codex can read and write GitHub issues and pull requests in
this repository. If it cannot, the coordination channel has to be reconsidered
before anything else here applies.
