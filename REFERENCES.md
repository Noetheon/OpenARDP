# Research references and implementation sources

Checked on 2026-07-22. Re-verify versions and licenses before implementation.

## Document parsing and agent access

- Docling supported formats and unified representation: https://docling-project.github.io/docling/usage/supported_formats/
- Docling repository: https://github.com/docling-project/docling
- Docling offline/prefetch options: https://docling-project.github.io/docling/usage/advanced_options/
- Docling Heron layout model: https://huggingface.co/docling-project/docling-layout-heron
- Docling model artifacts (`v2.3.0`): https://huggingface.co/docling-project/docling-models/tree/v2.3.0
- Docling MCP: https://github.com/docling-project/docling-mcp
- Docling Serve: https://github.com/docling-project/docling-serve
- Microsoft MarkItDown: https://github.com/microsoft/markitdown
- MinerU: https://github.com/opendatalab/MinerU
- MinerU Document Explorer: https://github.com/opendatalab/MinerU-Document-Explorer
- NASA NTRS OpenAPI: https://ntrs.nasa.gov/api/openapi/
- NASA NTRS ethical AI framework record: https://ntrs.nasa.gov/citations/20210012886
- NASA NTRS AI strategic-planning workshop record: https://ntrs.nasa.gov/citations/20210014231
- NASA NTRS Open Science and AI record: https://ntrs.nasa.gov/citations/20210025005
- Official CISA KEV data mirror: https://github.com/cisagov/kev-data
- CISA Known Exploited Vulnerabilities catalog: https://www.cisa.gov/known-exploited-vulnerabilities-catalog
- CC0 1.0 legal code: https://creativecommons.org/publicdomain/zero/1.0/legalcode

## Protocols and formats

- MCP specification (current stable at research date): https://modelcontextprotocol.io/specification/2025-11-25
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- OpenAI Codex MCP support: https://developers.openai.com/codex/mcp
- OpenAI Codex AGENTS.md: https://developers.openai.com/codex/agent-configuration/agents-md
- JSON Schema: https://json-schema.org/specification
- JSON-LD: https://www.w3.org/TR/json-ld11/
- W3C PROV and PROV-JSONLD: https://www.w3.org/submissions/2024/SUBM-prov-jsonld-20240825/
- RO-Crate: https://www.researchobject.org/ro-crate/specification.html
- BagIt RFC 8493: https://www.rfc-editor.org/rfc/rfc8493.html
- Semantic Versioning: https://semver.org/

F025's scoring contract uses only the committed JSON Schema/RFC 8785 identities and exact publisher sources above. Its
source-fitness rubric is a question-specific benchmark judgment, not an external credibility standard or legal opinion.
F026 reuses those unchanged local inputs and adds no external relevance library, model, dataset or standards claim.
F027 reuses the same identities and introduces no external ranking library, model, dataset or standards claim.

## Microsoft 365 and Office

- Open XML SDK: https://learn.microsoft.com/en-us/office/open-xml/about-the-open-xml-sdk
- PresentationML structure: https://learn.microsoft.com/en-us/office/open-xml/presentation/structure-of-a-presentationml-document
- Graph change notifications: https://learn.microsoft.com/en-us/graph/change-notifications-overview
- Drive delta: https://learn.microsoft.com/en-us/graph/api/driveitem-delta?view=graph-rest-1.0
- OneDrive/SharePoint scan guidance: https://learn.microsoft.com/en-us/onedrive/developer/rest-api/concepts/scan-guidance?view=odsp-graph-online

## Security, observability and supply chain

- OWASP Prompt Injection Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html
- OWASP AI Agent Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html
- OpenTelemetry: https://opentelemetry.io/docs/
- SPDX: https://spdx.dev/
- Community Data License Agreement: https://cdla.dev/
- Apache License 2.0: https://www.apache.org/licenses/LICENSE-2.0
- CycloneDX: https://cyclonedx.org/specification/overview/
- REUSE specification: https://reuse.software/spec/
- OpenSSF Scorecard: https://github.com/ossf/scorecard-action
- SLSA provenance: https://slsa.dev/spec/v1.0/provenance

## Build tooling

- uv project and lockfile guidance: https://docs.astral.sh/uv/guides/projects/

## Specification-driven implementation

- GitHub Spec Kit repository: https://github.com/github/spec-kit
- Spec Kit quick start and full production workflow: https://github.github.io/spec-kit/quickstart.html
- Spec Kit core CLI and initialization flags: https://github.github.io/spec-kit/reference/core.html
- Spec Kit Codex integration: https://github.github.io/spec-kit/reference/integrations.html
- Spec Kit upgrade guidance: https://github.github.io/spec-kit/upgrade.html
