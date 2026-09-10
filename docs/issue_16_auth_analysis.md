# Issue #16 / V2-AUTH-01: authentication failure analysis

Baseline: `1.0.4`, branch `claude/issue-16-reauth`, analysis commit base `678303a`.
This document records the verified current behaviour and the planned change.
It does not describe delivered functionality; see
[CHANGELOG.md](../CHANGELOG.md) for released changes.

Related: [Issue #16](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/16),
roadmap item `V2-AUTH-01` in [the backlog](backlog.md#meilenstein-b--ausfallerholung-und-ha-lebenszyklus-ziel-1112),
audit finding F04 in the [2026-09-09 review](review_2026-09-09.md).

## Verified current behaviour

Each item below was read in the source at the stated location, not inferred.

### F04-A: every login failure collapses into one outcome

`enhanced_login` returns `None` for all failure modes: a transport exception, a
timeout, a non-JSON body, a rejected credential (`code != 0`) and a well-formed
response missing `token`/`userId`. `PowerPulse2ApiClient.async_login` converts
that single `None` into `ConnectionError("EcoFlow login failed")`. The
distinction between a wrong password and an unreachable endpoint is therefore
already lost inside the transport module and cannot be recovered above it.

### F04-B: the config flow reports a transport problem for every failure

`async_step_user` wraps login and discovery in a bare `except Exception` and
always sets `cannot_connect`. A user with expired or changed EcoFlow
credentials is told the integration could not connect.

### F04-C: no reauthentication path exists

`ConfigEntryAuthFailed` does not appear anywhere in the component, and the
config flow implements neither `async_step_reauth` nor
`async_step_reconfigure`. Home Assistant consequently never offers the
credential repair dialog. The only user-visible recovery is deleting and
re-adding the config entry, which discards exactly what the project commits to
preserving: entity IDs, statistics history, user entity activations and local
Smart drafts.

### F04-D: the token is obtained once and never renewed

`_async_update_data` performs login and discovery only under
`if not self._initialized`, and `_initialized` is never reset to `False`. The
JWT acquired at the first successful refresh is reused for the entire lifetime
of the config entry, so token expiry is only ever resolved by a Home Assistant
restart or a manual integration reload.

### F04-E: an expired token silently disables the provider path

`_async_read_detail` catches `aiohttp.ClientError`, `TimeoutError` and
`ValueError`, logs at debug level and returns `None`. `raise_for_status()`
turns HTTP 401 into `ClientResponseError`, a `ClientError` subclass, so an
expired token is indistinguishable from a temporary outage and never surfaces.
The bounded PowerOcean HTTP fallback stops contributing data permanently while
the integration continues to report a successful update.

### F04-F: the MQTT layer detects credential expiry and nothing consumes it

`cloud_mqtt.py` classifies connect reason codes `4`, `5`, `134` and `135` as
authentication failures and logs `scheduling credential refresh`, then invokes
`self._auth_error_handler`. `_async_setup_mqtt` never passes
`auth_error_handler`, so the handler is `None` and no refresh is scheduled. The
log message currently promises recovery that is not implemented.

`_async_maintain_mqtt` retries `_async_setup_mqtt` on every coordinator cycle.
With an expired token `async_get_mqtt_credentials` keeps failing, so the retry
loop continues indefinitely at debug level without re-login and without any
user-visible state.

## Planned change

The work is split so that the user-visible repair path can be released and
validated before automatic renewal is added.

### Stage 1 — classify failures and offer reauthentication (implemented)

1. Add a pure `auth_classification` module holding the typed errors
   (`PowerPulse2AuthError`, `PowerPulse2ConnectionError`) and a decision
   function that maps an HTTP status and parsed body to one of them. The rule
   is evidence-based rather than guessed:
   - transport exception, timeout or unparsable body → connection error;
   - HTTP 429 or 5xx → connection error, even with a parsable body;
   - HTTP 401 or 403 → authentication error;
   - HTTP 200 with a non-zero `code` from every attempted endpoint → the server
     received and decisively rejected the credentials → authentication error;
   - HTTP 200, zero `code`, but missing `token`/`userId` → connection error.
     Unexpected server behaviour is not evidence of a wrong password, so this
     case must not raise a credential prompt.
2. Propagate the classification through `enhanced_login`,
   `get_enhanced_credentials` and `PowerPulse2ApiClient`. Both functions are
   called only from `api.py`, so the contract change is contained.
3. Raise `ConfigEntryAuthFailed` from the coordinator on an authentication
   error and `UpdateFailed` on a connection error. This ends the retry loop for
   a wrong password and starts the Home Assistant reauthentication flow.
4. Implement `async_step_reauth` / `async_step_reauth_confirm` and
   `async_step_reconfigure`, add the `invalid_auth` error string, and keep the
   existing unique ID so the entry is updated instead of replaced.
5. Update `strings.json` and both translations together; the repository
   consistency check enforces key parity.
6. Build failure reasons from the response's own status and result code and
   leave the server's free-text message at debug level. A reason travels into
   exception text, which reaches the Home Assistant interface and the warning
   log, and a log is what people attach to a public issue. A status and a code
   cannot identify an account; text written by EcoFlow is not something this
   integration can vouch for.
7. Sign in again once before reporting a refusal to the user, rate limited to
   one attempt every five minutes. This belongs in stage 1 rather than stage
   2: the token is obtained once at setup and never renewed on its own, so
   without this step an ordinary expired session would open a password
   dialog for a password that still works, which is the failure this item
   exists to prevent. Only a refused sign-in reaches `ConfigEntryAuthFailed`.

### Stage 2 — credential refresh (implemented)

8. Wire `auth_error_handler` in `_async_setup_mqtt` so the transport's own
   detection is consumed. It fires on the paho network thread, so the work is
   handed to the event loop rather than done there. The refresh fetches a
   certificate, renewing the session once if the endpoint refuses it, and
   hands the result to every live client. It is rate limited so a broker that
   keeps refusing cannot turn each reconnect into a certificate request, and
   it never raises, because one caller is a task with nothing above it to
   catch anything. A refused sign-in opens the repair dialog directly, since
   there is no update cycle here to carry a `ConfigEntryAuthFailed`.
9. Replace a still-working certificate once it reaches a set age, checked on
   the existing coordinator cycle rather than a separate timer. Waiting for
   the first refusal means every expiry costs a stream outage.
10. Take the broker address from the credential response. A renewed
    certificate can be issued for a different server, and keeping the previous
    address while adopting the credentials fails without a CONNACK and without
    anything naming a cause. A session is rebuilt only when the certificate or
    the address actually changed, because tearing down a healthy connection
    costs a data gap for nothing.

## Cross-project review

The sister project [ecoflow-energy-ha](https://github.com/shuette42/ecoflow-energy-ha)
binds the same EcoFlow cloud and is MIT licensed, as is this repository, which
already credits it in `NOTICE`. Its credential lifecycle was reviewed for this
item. Designs were adopted; no source was copied.

Adopted into the stage 1 design:

- Updating the existing config entry through the repair flow rather than
  creating a new one, which is what preserves entity IDs and user state.
- The step, error and abort key vocabulary, so both integrations name the same
  situations the same way.

Recorded for stage 2 rather than adopted now:

- `ConfigEntry.async_start_reauth` to begin a repair from outside the update
  cycle. The MQTT auth callback needs exactly this, because it fires on the
  transport thread and not inside `_async_update_data`.
- A proactive refresh driven by credential age, instead of waiting for the
  first failure.
- Taking the broker address out of the credential response. Their issue #184
  records that a refreshed certificate can name a different server, and that
  adopting the credentials while keeping a compile-time host fails silently and
  permanently. This repository still connects to the constant `MQTT_HOST` and
  never reads `url` from the certification response, so it carries the same
  latent fault. It is not reachable through stage 1 and is recorded here rather
  than fixed in passing.

Deliberately not adopted: their login helper also collapses every failure into
a single `None`, and their reactive refresh starts a re-authentication whenever
a re-login fails, including when it failed because the network was down. That
is the false-prompt behaviour this item exists to avoid, so the classification
in `auth_classification.py` has no counterpart there.

Separately noted while reading this repository's auth module:
`get_app_device_list` in `ecoflow/enhanced_auth.py` has no callers. It is
untouched by this change.

## Validation limits

- Unit tests cover the classification decisions and the transport error
  mapping against a doubled network boundary, plus the config flow's
  structural contract. They are not a Home Assistant runtime test; the
  component still has no HA fixture harness (roadmap `V2-QA-02`), so the
  dialog itself and the reload after a repair are established live.
- No vehicle is required for any part of this item.
- The live acceptance test needs deliberately invalidated credentials. It is
  performed by the maintainer, not by the automated suite, and must confirm
  that entity IDs, user activations and local Smart drafts survive
  re-authentication.
- No control-path behaviour, freshness rule or entity contract changes.
