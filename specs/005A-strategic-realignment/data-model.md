# Data Model: Strategic Realignment and Contract Boundary

F005A changes no runtime or persisted data model. The entities below describe governance relationships that repository validation must keep consistent.

## GovernanceAuthority

| Field | Meaning | Validation |
|---|---|---|
| `path` | Stable repository-relative canonical path | Unique within its artifact class |
| `class` | Constitution, ADR, public schema, project documentation, feature artifact, prompt, or implementation | Must follow the documented precedence order |
| `status` | Active, historical, adoption-source, proposed, deferred, accepted, partly-superseded, or superseded | Active authority must be unambiguous |
| `version` | Independent semantic or document version when applicable | Required for constitution and public contracts |
| `supersedes` | Explicit links to affected earlier artifacts | Required when an earlier rule is displaced |

### Relationships

- One active constitution governs all feature artifacts.
- Accepted ADRs and public schemas constrain project documentation and future feature work.
- An adoption-source file points to exactly one canonical active artifact and cannot itself govern implementation.
- Historical feature specifications remain immutable records of delivered slices.

## Claim

| Field | Meaning | Validation |
|---|---|---|
| `subject` | Capability, quality, security, performance, interoperability, adoption, or sustainability | Must be specific enough to verify |
| `state` | Evidenced, planned, experimental, hypothesis, or unsupported | Exactly one state |
| `evidence` | Reproducible result or accepted repository record | Required for `evidenced` |
| `qualification` | Scope and limitations | Required for planned, experimental, and hypothesis states |
| `audience` | Contributor, operator, adopter, or release consumer | Determines entry-point visibility |

### State transitions

```text
hypothesis -> experimental -> evidenced
planned -> experimental -> evidenced
any non-evidenced state -> unsupported
```

No claim becomes “standard”, “secure”, “faster”, or “compatible” solely through documentation approval.

## ContractFamily

| Field | Meaning | Validation |
|---|---|---|
| `contract_version` | Provider-neutral contract evolution | Independent from application and storage versions |
| `application_version` | OpenARDP implementation release | Cannot imply contract stability |
| `workspace_version` | Persisted workspace/catalog layout | Migration rules apply independently |
| `provider_profile_version` | Provider-specific native artifact profile | Must not leak into provider-neutral identity |
| `export_profile_version` | Optional export experiment | Must not be treated as required before Feature 014 evidence |
| `maturity` | Experimental, candidate, stable, or deprecated | F005A examples are experimental only |

### Compatibility states

- **Compatible**: consumer can use the artifact without migration under the declared major version.
- **Migration required**: a documented deterministic migration and fixtures exist.
- **Unsupported**: consumer must reject the major version clearly.
- **Experimental/no guarantee**: shape may change in a later feature with documented notes.

## ArtifactAuthority

| Artifact | Authority | Provider dependence | Rebuildability |
|---|---|---|---|
| Original source bytes | Authoritative evidence | Provider-neutral | Not derived |
| Verified CAS object and immutable catalog fact | Authoritative stored record | Provider-neutral | Must preserve identity |
| Provider-native parser representation | Derived evidence artifact | Provider-specific | Reproducible when provider/version available |
| Thin evidence projection | Derived interoperability candidate | Provider-neutral | Reproducible and invalidatable |
| Search index/cache | Accelerator only | Implementation-specific | Fully rebuildable |
| Summary/OCR/caption/embedding | Derived artifact | Generator-specific | Reproducible and invalidatable |
| Selection receipt | Audit record for a context selection | Provider-neutral candidate | Deterministically reproducible where inputs remain available |

## RoadmapWorkPackage

| Field | Meaning | Validation |
|---|---|---|
| `order` | 005A, 006, …, 017 | Unique and strictly ordered |
| `slug` | Stable feature directory/prompt name | Matches prompt and roadmap |
| `outcome` | Independently demonstrable value | One bounded slice |
| `predecessor` | Immediately prior converged feature | Required except for 005A baseline |
| `compatibility_impact` | None, additive, migration, or breaking | Must be stated before implementation |
| `gate_state` | Draft, analyzed, implemented, converged, merged | Successor cannot start before predecessor converges and merges |

### State transitions

```text
draft -> specified -> clarified -> planned -> checked -> tasked
       -> analyzed -> implemented -> converged -> merged
```

Critical or high-severity analysis/convergence findings block forward transition.
