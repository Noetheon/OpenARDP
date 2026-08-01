# Release and adoption strategy

**Status:** Planned adoption and release gates; no external adoption is implied.

## v0.1 objective

Useful local open-source software, not a standards announcement.

## Adoption ladder

1. single reference implementation;
2. stable CLI/Python/MCP user experience;
3. public fixtures and benchmarks;
4. external users and issue feedback;
5. one independent consumer or validator;
6. candidate contract extraction;
7. neutral governance discussion only if adoption warrants it.

## Naming

`OpenARDP` remains a working project name. Do not register `.ardp`, a media type or a standards namespace until IETF/name/trademark checks are completed.

## Community success metrics

- successful independent installs;
- external bug reports and PRs;
- integrations with at least two agent hosts;
- one alternate parser profile;
- one independent contract consumer;
- benchmark reproduction by a third party.


## Release engineering gate

A release requires supported workspace migration, rollback/restore evidence, dependency/license review, SBOM and checksums, clean installation in fresh environments, upgrade testing from the previous release, and a documented support matrix.

## Feature 015 candidate state

The application candidate is `0.1.0rc1`; final `0.1.0` is prohibited until a newly
generated current decision is `GO`. `release/evidence/v0.1.0/decision.json` is the
authoritative machine result, `report.md` is its human projection and `claim-map.json`
is the only allowed public-claim projection.

The present decision is `NO-GO`. The committed local reference capture verifies
candidate artifacts, offline installation, security/privacy controls and the supported
previous-open plus revision-9 backup–migration–restore drill. It still lacks complete
three-platform evidence, resolved license/current-vulnerability review and demonstrated
bounded-context value. No tag, GitHub Release, package publication, signing or external
announcement is authorized by Feature 015. To recover, complete the remaining evidence,
regenerate all platform bundles against the same source-tree identity and rerun the
gate; never edit blockers or reports manually.
