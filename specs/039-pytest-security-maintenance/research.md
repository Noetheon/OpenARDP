# Research: pytest development dependency maintenance

## Decision 1 — patched floor and bounded major version

**Decision**: Change the dev constraint from `pytest>=8.4,<9` to `pytest>=9.0.3,<10` and lock exactly 9.0.3 for this package.

**Rationale**: [GitHub reviewed advisory GHSA-6w46-j5rx-g56g](https://github.com/advisories/GHSA-6w46-j5rx-g56g) identifies all pytest releases before 9.0.3 as affected by CVE-2025-71176 and 9.0.3 as patched. A major cap preserves the repository's existing intentional upgrade boundary. Exact lock is reproducible and matches the previously observed full-suite overlay version.

**Alternatives considered**: Keeping the vulnerable 8.x cap leaves the finding unresolved; relaxing to any pytest 9 release without locking the tested version adds unnecessary drift; disabling pytest tmpdirs or ignoring the advisory weakens the gate.

## Decision 2 — supply-chain and compatibility

**Decision**: Retain existing pytest-cov and pytest-socket versions and validate their actual integration with the full suite. Retain PyPI origin and hashed lock artifacts. Do not change product extras.

**Rationale**: [PyPI's pytest project metadata](https://pypi.org/project/pytest/9.0.3/) identifies the maintained upstream package, MIT license and Python compatibility. [pytest 9.0.3 release notes](https://docs.pytest.org/en/stable/announce/release-9.0.3.html) and the repository's full gate are the appropriate migration checks. The existing plugins declare a pytest dependency; the complete suite is stronger evidence of actual compatibility than metadata alone.

**Alternatives considered**: Plugin upgrades or broad dependency refresh would enlarge review and lock drift without a demonstrated need.

## Decision 3 — claim and rollback boundary

**Decision**: Assert closure only of the pytest CVE after a locked audit. Report other optional findings separately. Roll back by reverting this scoped change if actual cross-platform checks reveal incompatibility; do not weaken test policy.

**Rationale**: The existing F038 expansion pause and F015 release NO-GO do not change with a dev-tool update. The local audit covers the selected lock but is not proof that all optional packages are safe. Windows/Linux compatibility requires CI proof before merge.

**Alternatives considered**: A blanket 'all vulnerabilities fixed' claim would be false because unrelated optional advisories remain.
