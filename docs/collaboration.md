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

## Finding out that something waits for you

Neither agent runs between sessions. There is no process polling issues, so
nothing here is a notification service and none of it promises a response time.

A session that touches this repository begins with one query, before any other
repository-specific action:

```
gh issue list --label "needs:claude"     # or needs:codex
```

Three labels carry the baton. They say whose action is awaited, which is not the
same as who owns the implementation — the branch prefix already carries that.

| Label | Meaning |
| --- | --- |
| `needs:claude` | waiting on Claude |
| `needs:codex` | waiting on Codex |
| `needs:maintainer` | waiting on the maintainer: a decision, an authorisation, a live action |

An item with no pending handover carries **no** `needs:` label. Absence means
nothing is waiting, not that nobody has looked.

Whoever acts moves the label to whoever is next, or removes it when nothing is
pending. A label left behind is worse than none, because it reports something
false rather than nothing, and the queue is only worth querying if it is true.

If a label sits unmoved, nothing happens automatically. The maintainer sees it
in the issue list, and that is the whole of the recovery path. Neither agent
should add a scheduled check to compensate: it spends sessions that mostly find
nothing, it covers one side only, and one-sided cover is the false assurance
this rule exists to avoid.

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

Several worktrees exist under `dist/`, on `codex/*` branches, left from earlier
work; their tidying is issue #74 and belongs to their owner. A count is not
recorded here because the last one was wrong within a day of being written. Do
not commit into them, rebase, force-push, delete or move their branches, and do
not repurpose one as scratch space: on 2026-09-11 a push to
`codex/issue-19-stream-timeline` left `timeline-merge` stale without anyone
noticing. Only the owner removes an obsolete one, and only after confirming it
is no longer needed.

New worktrees go under `/.worktrees/`, which is ignored like `dist/` but is not
the directory `scripts/build_release.ps1` writes releases into. Coupling working
copies to the release output was safe only because that script happens to touch
a single file; a future change to it should not be able to cost anyone their
work.

## The primary checkout belongs to nobody

Both agents work in their own worktrees. The primary checkout remains on `main`
with a clean tree and is not used for feature work or branch reviews.

```text
.worktrees/
  claude/
    issue-XX/
    review-YY/
  codex/
    issue-ZZ/
    review-AA/
```

A review that needs to run another agent's branch takes a temporary worktree
there and removes it when the review ends. On 2026-09-12 Claude twice checked
out a `codex/*` branch at the repository root to run the suite and mutation
checks against it, for pull requests #64 and #68. Nothing broke, only because
Codex was in its own worktrees at the time; a checkout at the root changes
`HEAD` for anyone standing in it.

The rule is symmetric on purpose. An earlier draft protected the worktrees from
checkouts made at the root and left the asymmetry that created the exposure.
Codex objected in issue #77 that this makes the shared resource safer to use
rather than unused, and that the asymmetry is itself the problem. The change
falls mainly on Claude, which had been working at the root.

A fresh worktree has no `.venv`, since that is ignored and lives in the primary
checkout. Invoke that interpreter by absolute path with the worktree as the
working directory rather than building a second environment per worktree.

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
