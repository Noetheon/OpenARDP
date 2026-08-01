# Research: Alternate Parser Conformance Spike

## Decision 1 — Independence boundary

**Decision**: Execute one standalone standard-library program with Python `-I -S`, an
explicit fixture root and JSON request. It must not import OpenARDP, Pydantic, RFC8785 or
any project module.

**Rationale**: The feature prompt permits another language *or process*. `-I` removes user
site and environment path influence; `-S` prevents site-package loading. An import probe
and subprocess environment test make the boundary observable on all three platforms while
avoiding a new compiler/runtime supply-chain dependency.

**Alternatives considered**: Node.js would add cross-platform toolchain and canonical JSON
differences without strengthening the provider test. A second Python module in `src/` would
not be meaningfully independent. A container would exceed the spike and local-first scope.

## Decision 2 — Alternate producer

**Decision**: Use deterministic standard-library TXT and RFC 4180-style CSV parsing. The
CSV producer declares a simple page view and emits text, page-region and table-cell anchors
under provider `stdlib-text-csv`, profile `deterministic-grid` `0.1.0`.

**Rationale**: It is a genuine non-Docling producer with independently shaped native data,
yet small enough to audit. Explicit geometry avoids pretending that CSV possesses physical
layout truth.

**Alternatives considered**: A second PDF/Office parser would turn the spike into a
production adapter and introduce licensing/native-binary concerns. Consuming fixtures only
would leave producer-side friction untested.

## Decision 3 — Canonical identities

**Decision**: Implement the safe subset required by current identity envelopes: null,
booleans, Unicode strings, arrays, objects and integers within the interoperable safe range.
Reject floats, non-string keys, unsafe integers and invalid surrogate values. Serialize
UTF-8 JSON with recursively sorted keys, compact separators and no ASCII escaping, and prove
it against every F006 golden vector.

**Rationale**: Current identity payloads contain no floating-point numbers. Limiting the
independent implementation is safer and more honest than claiming full RFC 8785 numeric
conformance without a dedicated number serializer.

**Alternatives considered**: Vendoring a JCS library undermines independence and adds a
dependency. Accepting floats based on the standard JSON encoder would be non-conformant.

## Decision 4 — Validation depth

**Decision**: Validate both closed structural rules and the semantic invariants encoded by
the reference models: versions, exact fields, namespaced extensions, scalar bounds,
identity allowlists, scope binding, record-set membership and trust non-escalation.

**Rationale**: JSON Schema alone cannot prove recomputed identities or cross-record scope.
A schema-only pass would not test the actual public contract.

**Alternatives considered**: Loading the published JSON Schemas into a third-party validator
would violate the dependency-free boundary and still require separate semantic code.

## Decision 5 — Path and resource boundary

**Decision**: Constrain all declared relative POSIX paths beneath one resolved regular-file
root, reject links and undeclared files, cap the tree at 128 files/8 MiB, each file/request/
response at 1 MiB and subprocess time at 10 seconds.

**Rationale**: Fixtures are untrusted inputs. These bounds make the spike deterministic and
prevent it from becoming arbitrary filesystem reach.

**Alternatives considered**: Trusting committed paths is insufficient for a conformance
tool that future contributors will extend. OS-specific sandbox claims are not portable.

## Decision 6 — Decision and claims

**Decision**: Generate a deterministic fail-closed report with exact observation/input/
executable/output digests, verified scope, friction, leakage, limitations and required
changes. A pass supports only the experimental thin-contract surface and never changes
contract stability.

**Rationale**: Constitution III, IV, IX and XII require measured claims and external-use
plus migration evidence before stabilization. This internal implementation supplies only
one part of that evidence.

**Alternatives considered**: A prose-only conclusion is not reproducible. Automatically
stabilizing `0.1.0` would contradict governance.
