# Permission Matrix

| Candidate | Consent and assignment | Reach | F017 assessment |
|---|---|---|---|
| Delegated file access | User/admin consent according to selected delegated scope | Caller-authorized resources | Preferred where an interactive user and product model permit it; not tested here |
| `Sites.Selected` application | Entra admin consent plus explicit site permission assignment plus matching token | Assigned sites | Preferred application candidate for a later synthetic pilot; compatibility not yet proven |
| `Lists.SelectedOperations.Selected` / item/file selected scopes | Entra consent plus explicit resource assignment; lower-level assignment can break inheritance | Assigned resource | Potentially narrower, but operational and inheritance consequences require live validation |
| `Files.Read.All` application | Admin consent | All files in all site collections | Too broad for default/pilot fallback; NO-GO without separately justified controller decision |
| `Sites.FullControl.All` application | Admin consent | Tenant-wide full site control | Incompatible with the current read-only least-privilege goal; delta sharing-change guidance creates an unresolved blocker |

## Mandatory rules for any future pilot

1. Dedicated synthetic tenant and explicit resource allowlist.
2. Delegated access first when the use case supports it; otherwise the narrowest selected scope.
3. No automatic permission widening when permission snapshots are incomplete.
4. Entra consent, resource assignment and runtime token scope are independently verified.
5. Effective permission reads are treated as caller-relative/incomplete until proven otherwise.
6. Permission changes revoke local visibility before content becomes queryable.
7. Tenant-wide application scopes require a separate ADR, threat-model revision and controller sign-off.

## Decision

No permission is granted or requested by F017. A selected-scope synthetic pilot is conditionally
researchable later. Production permission configuration is NO-GO.
