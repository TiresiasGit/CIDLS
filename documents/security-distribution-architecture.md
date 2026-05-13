# CIDLS Security Distribution Architecture

## Scope

This policy applies to CIDLS deliverables produced with LLMs, local `.exe`
packages, prompt kits, ToB enablement packages, minimal license servers, and
future SaaS variants.

The design assumption is that anything exposed outside the local machine can be
probed by high-capability AI and automation. Distribution, billing, privilege,
artifact generation, and executable packaging must therefore remain separated.

## Root Rule: Keep Secrets Off Clients

The following values must never be placed in an `.exe`, frontend bundle,
distribution ZIP, public GitHub repository, `public/` directory, static sample
HTML, or customer-facing template:

- Stripe Secret Key
- Stripe Webhook Secret
- Operator-owned LLM API key
- License signing private key
- Administrator API token
- Database connection string
- Raw customer PII
- Internal prompt text that increases attack surface when disclosed

Permitted client-side distribution values are limited to:

- License verification public key
- Public sales page URL or Stripe Payment Link URL
- Demonstration data that cannot identify a real person or customer
- Static acceptance-test HTML without secrets
- Templates and prompts that contain no secret material

## Distribution Order

Initial distribution must prefer lower-risk options in this order:

1. Prompt, template, and setup instructions
2. ToB enablement, internal standardization, and customer-specific template work
3. Local `.exe` using the user's own LLM environment/key and local storage
4. Local `.exe` with a minimal license server
5. Web SaaS with authentication, billing, authorization, LLM proxying, and audit logs

Web SaaS is prohibited unless all of the following are implemented:

- Identity authentication and session/JWT signature verification
- Owner checks for every project, node, and generated artifact
- Stripe Webhook signature verification
- LLM API rate limits, quotas, and cost ceilings
- Server-side secret management
- Audit logs
- XSS and HTML export escaping/sanitization
- Production exclusion for acceptance files and specifications under public paths
- Dependency vulnerability audit
- Incident stop and key rotation procedure

## Local `.exe` Boundary

The initial `.exe` design decision for CIDLS is:

Decision: prefer "no operator secret, no cloud artifact storage, no shared link,
local-first execution" for early personal and small-scale distribution.
Reason: publishing a web server exposes Stripe secrets, webhook secrets,
operator LLM keys, license signing keys, customer/order/artifact data, shared
links, admin screens, and APIs to continuous automated probing.
Review condition: switch to Web SaaS only after the SaaS gate above passes with
evidence.

A local `.exe` may:

- Render UI
- Store project data locally
- Export local Excel, HTML, PNG, JSON, or similar files
- Use the user's own LLM environment or key
- Verify a signed license
- Verify distribution package integrity

A local `.exe` must not:

- Store an operator-owned LLM API key
- Store a Stripe Secret Key
- Treat client-local subscription state as authoritative
- Unlock paid features based only on `localStorage`, JSON, SQLite, or editable plan values
- Bundle a license signing private key

## License Boundary

Offline licenses cannot fully prevent copying. If copying is unacceptable, the
product needs first activation or short-lived token refresh.

Recommended stages:

- Low operations: signed `license.json` plus public-key verification and manual reissue
- Medium operations: first activation plus `device_hash` plus seat limits
- High operations: periodic online checks plus revocation list plus short-lived signed token

Even when a minimal license server exists, LLM processing, generated artifacts,
project text, and customer project bodies must stay off that server. The server
role is limited to purchase confirmation, license issuance, `device_hash`
registration, and revocation checks.

## Authority Boundary

- `customer_id` is not proof of identity.
- Client-submitted `plan`, `role`, `customer_id`, and `device_id` are not trusted.
- If a server handles billing or licensing, the authoritative state is the server
  database plus Stripe Webhook events with verified signatures.
- Administrators must not be able to view user LLM API keys or secrets in plain text.

## LLM Boundary

Using an operator-owned LLM API key means the system is an LLM proxy SaaS, not a
minimal license server. The following are mandatory before that mode is used:

- Authentication
- Billing verification
- Rate limits
- Token and cost ceilings
- Audit logs
- Prompt-injection controls
- Output sanitization
- Abnormal-use shutdown

For personal or small-scale release, prefer a prompt/template package that the
user runs in their own ChatGPT, Codex, Claude, or local LLM environment.

## Quality Gate

Distribution and release checks must cover:

- Secret string leakage
- `NEXT_PUBLIC_*` variable names containing `SECRET`, `API_KEY`, `WEBHOOK`, or `PRIVATE`
- `.bat` files encoded as ASCII-compatible CRLF text
- Sensitive documents under public paths
- Distribution ZIP contents containing `.env`, private keys, API keys, or webhook secrets
- Specification leftovers such as `TODO`, `TBD`, `placeholder`, `項目1`, `詳細項目1`, or `証跡1`
- OWASP API Top 10, OWASP ASVS, and NIST CSF checks when Web SaaS is selected

The executable gate implementation is `scripts/audit_distribution_security.py`.

## Done Criteria

- AGENTS.md contains this boundary.
- Distribution ZIPs contain zero secrets.
- Release packaging can select the 1/2/3/4 distribution modes above before SaaS.
- Every distribution package includes the secret boundary, authority boundary,
  and `.exe` design decision.
- A security design document and risk checklist exist.
- The distribution security quality gate passes.
