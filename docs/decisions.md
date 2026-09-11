# Decision log

Decisions that shape how this repository is built and what its claims mean.
Each entry states the decision, why it was taken, and where it already lives.

This log **collects**; it does not replace. The [backlog](backlog.md) stays the
single authoritative list of open work, the [validation status](validation.md)
stays the record of what has been observed, and the entries below point at the
document that carries each decision in full. When a decision changes, change it
in its home document and amend the entry here; do not let the two drift.

Entries marked *predates this log* were in force before it was written on
2026-09-11 and are recorded from the documents that already stated them.

## D-01 · The backlog is the single authoritative list of open work

*Predates this log.*

README files describe current scope, protocol documents retain evidence, and
the changelog records delivered changes. All of them link to the backlog rather
than keeping parallel TODO or roadmap lists, because parallel lists disagree
and the disagreement is discovered late.

Home: [backlog.md](backlog.md).

## D-02 · Evidence archives are preserved, not rewritten

*Predates this log.*

Dated analyses and observation reports are records of what was seen at a time.
Later findings are added and labelled; past observations are not edited to read
as current facts, because nobody can afterwards tell what the record originally
said.

Home: [index.md](index.md#maintenance-rules).

## D-03 · Acceptance rests on observation, not on passing tests

*Predates this log, reinforced 2026-09-10.*

A control counts as successful only after acknowledgement **and** a newer
qualified readback. A live observation documents only the condition actually
exercised. A step whose condition could not be produced is recorded as *not
tested*, never as passed. Green tests and a merged pull request are not
evidence about device behaviour.

Home: [validation.md](validation.md#test-principles) and the
[acceptance checklist](acceptance_checklist.md).

## D-04 · User state survives every change

*Predates this log.*

Existing entity IDs, user activations, recorded history and local Smart drafts
are preserved across upgrades and repairs. Automatic transport stays
listen-only; new controls are opt-in and evidence-bound.

Home: [backlog.md](backlog.md#roadmap-bis-version-20).

## D-05 · Merging and acceptance are separate gates

*2026-09-10.*

`main` accepts finished work whose live acceptance is still open, provided
pytest, Ruff, the consistency checks, HACS and Hassfest pass. Acceptance is a
**release** gate.

Before this, the two were one gate, and finished branches aged unmerged waiting
for a physical condition. `V2-SAFE-02` reached the worst form of it: complete,
reviewed, and in no test build at all, so it could not be accepted even in
principle. Code on `main` is code that compiles, passes its tests and has been
reviewed — never a claim that it was observed working on the device.

Home: [backlog.md](backlog.md#merge-and-release-gates).

## D-06 · A published build is never renamed or replaced

*2026-09-10.*

When two builds were prepared as `1.0.5-beta.5` from different lines, the
published one was left alone and the other moved to `1.0.5-beta.6`. A name that
once meant one thing and later means another makes every later report about
that build unreliable. A skipped version number costs less.

Home: [CHANGELOG.md](../CHANGELOG.md), `1.0.5-beta.6` section.

## D-07 · Failure reasons carry the status and result code only

*2026-09-10.*

A reason reaches the Home Assistant interface and the warning log, and a log is
what people attach to a public issue. There is no way to establish for every
EcoFlow error code that its free text names no account, so that text is
produced for debug output only. A test enforces the rule against both transport
modules.

Home: [validation.md](validation.md#unreleased-authentication-failure-handling).

## D-08 · Credential repair updates the config entry

*2026-09-10.*

Re-authentication and reconfiguration update the existing entry rather than
creating a new one, and refuse credentials belonging to a different EcoFlow
account. Replacing the entry would discard exactly the state D-04 protects.

Home: [validation.md](validation.md#unreleased-authentication-failure-handling),
analysis in [issue_16_auth_analysis.md](issue_16_auth_analysis.md).

## D-09 · Borrowed designs are credited, and reimplemented rather than copied

*2026-09-10.*

The credential lifecycle and the broker-address handling follow
`ecoflow-energy-ha`, which is MIT licensed as this repository is. The decision
rules were reimplemented, and `NOTICE` names what was taken and from where.
This project's direct MQTT path with a bounded HTTP fallback remains project
evidence, not a prescription for another repository.

Home: [NOTICE](../NOTICE), [backlog.md](backlog.md).

## D-10 · English is the project language

*2026-09-11.*

Documentation, filenames, code comments, commit messages and pull request text
are written in English. The repository is a public Home Assistant integration
with an international audience and already carries English code, changelog and
release notes; German sections read as an inconsistency to any outside reader
and exclude contributors who cannot read them.

Existing German content is not converted for its own sake — that was decided
explicitly. When a German passage has to be edited for another reason, it is
rewritten in English rather than extended in German. German remains in
[backlog.md](backlog.md) and in six evidence archives, which D-02 protects
from rewriting in any case.

One German string stays deliberately: the fixture in
`tests/test_repository_consistency.py` exists to verify umlaut handling in
Markdown anchors, and is test data rather than prose.

## D-11 · Two agents coordinate on GitHub, with one owner per work item

*2026-09-11.*

Issues and pull requests carry the coordination between Codex and Claude. A
coordination file in the repository was considered and rejected: every document
both agents touched on 2026-09-10 and 2026-09-11 produced a merge conflict, and
a conflict in the channel blocks the means of resolving it.

Each work item has exactly one implementing agent, named when it starts and
carried by the branch prefix. The split is per item rather than per activity,
because "complex work here, everything else there" needs adjudication every
time. A release names its owner before any version is raised; two builds were
prepared as `1.0.5-beta.5` within one hour without that rule. Review runs both
ways and does not transfer ownership, and disagreement goes to the maintainer
rather than to whoever writes last.

Capability never creates a standing role. A first draft gave Claude permanent
ownership of live acceptance and releases because of its Home Assistant access;
Codex objected in issue #42 that the access is not exclusive and that assigning
activities by agent is the very split this decision rejects. Both points held,
and the rule now applies to capability as it does to everything else: it can
decide who owns an item, recorded in that item's issue.

Home: [collaboration.md](collaboration.md).
