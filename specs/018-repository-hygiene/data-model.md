# Data Model: Maintainability Policy

## MaintainabilityPolicy

- `version`: integer policy format, exactly `1`.
- `source_root`: repository-relative production source root, exactly `src/openardp` for this policy.
- `module_line_limit`: positive default ceiling for any production module.
- `function_line_limit`: positive default ceiling for any function or method.
- `module_exceptions`: sorted mapping from normalized repository-relative `.py` path to `HotspotAllowance`.
- `function_exceptions`: sorted mapping from stable `path:qualified.name` to `HotspotAllowance`.

Unknown keys, duplicate JSON keys, absolute/traversing paths, non-Python module paths and unbounded values are rejected.

## HotspotAllowance

- `maximum_lines`: positive inclusive ceiling fixed to the reviewed measured baseline or a later lower value.
- `reason`: short non-empty rationale that names the legacy responsibility, not source/body data.

An allowance is valid only while the measured item remains above the default limit and at or below its reviewed ceiling.
If an item disappears or improves to the default, the allowance becomes stale and the audit fails until it is removed.
This makes policy maintenance explicit and prevents allowlists from silently accumulating.

## SourceMetric

- `kind`: `module` or `function`.
- `key`: normalized module path or `path:qualified.name`.
- `line_count`: inclusive physical line span from parsed source.

Nested functions and methods use lexical qualified names. Decorator lines are included so adding decorators cannot hide
growth. Source files are read as UTF-8 and parsed without import or execution.

## AuditFinding

- `code`: stable category such as `module-limit`, `function-growth`, `stale-exception` or `invalid-policy`.
- `key`: body-free source metric key or policy field.
- `actual`: measured value when applicable.
- `allowed`: applicable default or exception ceiling.

Findings are sorted by code and key. Exit zero means no finding; non-zero means the policy or source violates the
contract. The audit never rewrites its own policy.
