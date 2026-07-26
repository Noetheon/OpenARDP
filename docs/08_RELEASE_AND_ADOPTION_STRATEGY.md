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
