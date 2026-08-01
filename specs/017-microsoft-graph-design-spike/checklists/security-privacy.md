# Security and Privacy Checklist

- [x] Composite tenant/site/drive authority binds every stateful record.
- [x] Provider item identity is case-sensitive and path-independent.
- [x] Raw cursors, tokens, client state, URLs and provider IDs stay outside core records.
- [x] Upserts require complete permission snapshot references; tombstones are explicit.
- [x] Delta pagination, duplicates, 410 reset, cycles and atomic publication are defined.
- [x] Retry-After, fallback backoff and all resource limits are bounded.
- [x] Notification authenticity uses constant-time comparison and wakeup-only semantics.
- [x] Cross-tenant dedupe and observable equality shortcuts are prohibited.
- [x] Threat model covers spoofing, disclosure, drift, replay, deletion, DoS, SSRF and injection.
- [x] Data inventory, minimization, residency, retention, rights and incident handling are covered.
- [x] Permission consent, resource assignment and token scope are distinguished.
- [x] Production blockers cannot be waived by mock success.
