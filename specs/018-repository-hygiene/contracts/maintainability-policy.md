# Maintainability Policy Contract

## Purpose

The policy is a developer-quality contract, not a public OpenARDP interchange schema. It prevents structural debt from
growing while keeping current exceptions honest and removable.

## Deterministic input

The audit receives a repository root and a strict UTF-8 JSON policy. It recursively evaluates tracked-style `.py` files
under the configured production source root, ordered by normalized relative path. It parses source through Python's AST
and does not import modules, evaluate decorators or execute repository code.

## Measurement

- A module is measured as its physical UTF-8 line count.
- A function/method is measured from its first decorator, or its definition when undecorated, through `end_lineno`,
  inclusive.
- Qualified names include enclosing classes and functions.
- Default ceilings apply to every measured item not present in the corresponding exception mapping.
- Exception ceilings may equal or improve on the recorded baseline but may never be exceeded.

## Closed validation

The audit fails for malformed/duplicate JSON, an unsupported policy version, unsafe paths, missing exception targets,
new default-limit exceedances, exception growth or an exception that has become unnecessary. Diagnostics contain only a
stable code, normalized source key and numeric bounds.

## Integration

`python scripts/audit_maintainability.py` is the focused command. `scripts/validate_repository.py` invokes the same pure
validation function so local and CI repository validation cannot drift. Tests prove two-run determinism and each
failure class with synthetic repositories.

## Compatibility

This contract adds no installed entry point, runtime dependency, public schema, persisted state or version axis. Removing
or lowering an exception is compatible. Raising one requires an explicit review and violates F018's normal policy.
