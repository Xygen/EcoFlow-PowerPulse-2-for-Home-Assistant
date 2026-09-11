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

Either agent may review any item. Reviewing does not transfer ownership, and a
review comment is not a licence to take the work over.

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

## Worktrees belong to the agent that made them

Three worktrees exist under `dist/`, on `codex/issue-19-*` branches. They are
historical and currently clean. Do not commit into them, rebase, force-push,
delete or move their branches, and do not repurpose one as scratch space: on
2026-09-11 a push to `codex/issue-19-stream-timeline` left `timeline-merge`
stale without anyone noticing. A new item gets a fresh branch and, if needed, a
fresh worktree under its own owner. Only the owner removes an obsolete one, and
only after confirming it is no longer needed.

## Releases have one owner

A release names its owner in its issue before any version is raised. Only that
owner raises the version in `manifest.json`, opens a new release section in the
changelog, and creates the tag and the GitHub release. Either agent adds factual
entries under `## Unreleased` at any time.

On 2026-09-10 two builds were prepared as `1.0.5-beta.5` from two lines within
the hour. The published one was kept and the other became `1.0.5-beta.6`, per
[D-06](decisions.md#d-06--a-published-build-is-never-renamed-or-replaced). A
single owner for version numbers is what prevents the next one. Before raising
a version, check `gh release list` and `git tag`.

## The pull request is the handover

No second format. A pull request description in this repository already carries
what an agent picking the work up next needs, and the maintainer reads it
anyway. It states:

- the owner, and the head and base it applies to;
- the scope of what changed;
- the checks that were run and what they reported;
- what was deliberately left untested, and what only live evidence can settle;
- the remaining risk;
- any file seam or release-owner dependency it creates for the next item.

For work that has no pull request yet, the handover is a comment on the issue
carrying the same facts. Write it to be read without a reply: name the
assumptions, because the reader cannot ask.

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

## Capability decides an item, never a standing role

Both agents reach the maintainer's Home Assistant instance through connected
tools. Claude used that on 2026-09-11 to read back that `modified_at` still
equalled `created_at`, proving an aborted flow performed no write at all; Codex
used it to install `1.0.5-beta.7` and verify both MQTT streams after a restart.

An earlier draft of this document gave Claude standing ownership of live
acceptance, verification and release work on the strength of that access. Codex
objected in issue #42 and was right on both counts: the access is not
exclusive, and assigning activities permanently by agent is exactly the
activity-based split the previous sections reject. Capability may well make one
agent the right owner of a particular item — that belongs in the item's issue,
with the access it needs named there, and never as a general rule.

## Live tests need explicit authority

Reading state is ordinary work. A live test that disturbs the installation is
not: deliberately invalidating credentials, changing device settings, restarting
Home Assistant. Those happen on the maintainer's explicit request for that test,
recorded in the item's issue.

Neither agent can rely on an unattended observation continuing after its session
ends. Anything that needs a long window — an idle-gap observation, waiting for a
real token expiry — needs an arrangement made for it, not an assumption.

## These rules can be changed

Working here will show where they are wrong. Either agent may propose an
improvement, and the way to do it is the way this document was settled: open an
issue with the proposal, let the other answer there, and only then open a pull
request amending this document and its entry in the decision log. Agreement
between the agents comes before the change, not after it. The maintainer merges,
as with anything else.

Two things do not change quietly. Every rule here came from something that
actually went wrong — a seam that broke three times, two builds with one version
number, a document that contradicted itself. Relaxing one needs a reason at
least as concrete as the failure that produced it. And the failure stays
recorded even when the rule around it changes, because a rule whose origin has
been edited away is one nobody can weigh later.

## Reach, as verified

Codex confirmed in issue #42 that it reads and writes issues, creates and edits
them, reads pull request descriptions, changed files and review comments,
comments on pull requests and reads labels, and that it has merged and released
here. The comment itself was the check. Network availability and session
authorization remain the operational dependencies for both agents.
