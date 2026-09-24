# Work with local document evidence

> [!TIP]
> For everyday questions over many documents, the shorter agent workflow (`add`, `find`, `read`, `verify`) in
> [Agent access](32_AGENT_ACCESS.md) is faster and uses far fewer tokens. This page remains the audit path for
> context bundles, receipts and exact replay.

Use this workflow when you repeatedly need to check a passage against its exact source version. OpenARDP retrieves
evidence; it does not write an answer or establish that the evidence is correct or complete. Start with a few TXT,
Markdown or CSV files. The commands below use a synthetic Markdown file and a POSIX shell on macOS or Linux; they are
a functionality check, not evidence of user value.

## 1. Install the locked core and create a separate workspace

From a clone of this repository, with Git, Python 3.12 and the required `uv` version installed:

```bash
uv sync --locked
openardp_demo=$(mktemp -d "$HOME/openardp-demo.XXXXXX")
mkdir "$openardp_demo/documents"
openardp_source="$openardp_demo/documents/review.md"
openardp_store="$openardp_demo/store"
cat > "$openardp_source" <<'EOF'
# Review note

The review date is 2026-10-15.
The review owner is the local research team.
EOF
uv run --locked openardp init --store "$openardp_store"
```

This creates a fresh directory under your home folder without overwriting existing files. Source documents and derived
workspace data live in separate sibling directories. For your own workflow, choose the real source files explicitly;
do not put the store inside a folder you intend to watch.

## 2. Import, check reuse, and find the document

```bash
openardp_original_sha=$(uv run --locked python -c \
  'import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())' \
  "$openardp_source")
uv run --locked openardp ingest "$openardp_source" --store "$openardp_store" \
  --json > "$openardp_demo/ingest.json"
openardp_document=$(uv run --locked python -c \
  'import json,sys; print(json.load(open(sys.argv[1]))["data"]["scope"]["document_id"])' \
  "$openardp_demo/ingest.json")
uv run --locked openardp ingest "$openardp_source" --store "$openardp_store"
uv run --locked openardp list --store "$openardp_store"
uv run --locked openardp status "$openardp_source" --store "$openardp_store" --full-integrity --json
```

The second ingest should report `CACHE_HIT` for this unchanged file. This proves reuse in this example; it does not measure
time saved in your work. `list` maps the document ID to its registered source. The status command reports source
freshness and persisted integrity coverage; it is not a judgment about the document's claims.

## 3. Read selected passages and inspect their source

```bash
openardp_task='Which review date is documented?'
uv run --locked openardp context "$openardp_task" \
  --document "$openardp_document" --budget 12000 --unit tokens --mode verification \
  --include-bundle --store "$openardp_store"
uv run --locked openardp context "$openardp_task" \
  --document "$openardp_document" --budget 12000 --unit tokens --mode verification \
  --include-bundle --store "$openardp_store" --json > "$openardp_demo/context.json"
openardp_receipt=$(uv run --locked python -c \
  'import json,sys; print(json.load(open(sys.argv[1]))["data"]["receipt_id"])' \
  "$openardp_demo/context.json")
openardp_block=$(uv run --locked python -c \
  'import json,sys; print(json.load(open(sys.argv[1]))["data"]["bundle"]["items"][0]["provenance"]["block_id"])' \
  "$openardp_demo/context.json")
uv run --locked openardp get "$openardp_block" --store "$openardp_store" --json
cat "$openardp_source"
```

The human output now includes the selected text, exact document/version/representation IDs and the available source
locator. For this core example, `source.extensions["openardp.text"]` contains line numbers. Compare the retrieved
passage with those lines in the original. All excerpts are untrusted data; terminal control characters are escaped.
The JSON file preserves the original structured values. Without `--include-bundle`, context output remains body-free.

The block-ID extraction above is deliberately specific to this successful text example. In real work, inspect whether
any evidence was selected before extracting an item. An empty result is reported explicitly. A returned passage still
needs a human check for relevance, meaning, completeness and the correct version; a keyword hit alone is insufficient.

Rich document results instead identify evidence projections and references. Use
`openardp get-evidence PROJECTION_ID --document DOCUMENT_ID --store STORE --json` to inspect their actual anchors.
Do not infer a PDF page number from an ID. Visual handles identify already materialized evidence; they do not display
or generate a page image automatically.

## 4. Inspect the receipt, replay, and confirm the original is unchanged

```bash
uv run --locked openardp context-receipt "$openardp_receipt" --store "$openardp_store" --json
uv run --locked openardp context "$openardp_task" \
  --replay "$openardp_receipt" --unit tokens --include-bundle --store "$openardp_store"
openardp_final_sha=$(uv run --locked python -c \
  'import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())' \
  "$openardp_source")
test "$openardp_original_sha" = "$openardp_final_sha" && printf '%s\n' 'Original unchanged.'
printf 'Example workspace: %s\n' "$openardp_demo"
```

Replay requires the **same task and budget unit** used to create the receipt. It reproduces the recorded evidence
snapshot, which can differ from the current source after an edit. To work with an updated source, ingest it again and
compile a new context; retain both version IDs when comparing changes. The example files and store remain available
at the printed location.

## Optional capabilities, after the core workflow

- **Existing agent host:** launch `uv run --locked openardp mcp --store /absolute/path/to/store` from the repository.
  Configure the client to launch that command with an absolute repository working directory and store. The server
  requires an initialized compatible workspace and offers read-only evidence tools; ingestion remains an operator
  action. Ask the agent to list documents, check source status, inspect outlines, then compile a bounded selection with
  `include_bundle: true` and verify the returned passages. See [MCP operation](05_CONTEXT_COMPILER_AND_MCP.md).
- **PDF, DOCX and PPTX:** install the existing `docling` extra. PDF additionally needs the independently verified offline
  model bundle; DOCX/PPTX do not require that PDF model bundle. See the
  [PDF bundle guide](22_OFFLINE_PDF_MODEL_BUNDLE.md) and [bundle source lock](../model-bundles/pdf-docling-2.114.0-v1/README.md).
  The supported PDF profile disables OCR, so this is not a scanned-document workflow. For an already verified bundle,
  use `--docling-model-root /absolute/bundle/assets --docling-model-manifest /absolute/bundle/manifest.json` with `ingest`.
- **Semantic retrieval:** explicitly install the existing `semantic` extra and provision/verify its separate offline
  bundle. Pass `--retrieval-profile semantic`, `--semantic-bundle` and `--semantic-source-lock` together as documented in
  the [semantic guide](29_SEMANTIC_RETRIEVAL_PRODUCT_SURFACE.md). Replay also needs that same bundle identity. Lexical
  retrieval is the default; optional model setup has costs that must count in the pilot.

If both parsing and semantic capabilities are required, retain both extras in `uv sync --locked --extra docling
--extra semantic` and subsequent `uv run --locked --extra docling --extra semantic ...` commands. Provisioning is an
explicit connected operation; normal operation uses the verified local bundles. Do not install models merely to run
the core example.

Context compilation currently accepts at most 32 selected document scopes and discovers at most 10,000 blocks. Choose
a relevant bounded subset. For folder ingestion, `watch --once` performs one cycle and normally processes only one job;
see its `--stability-ms` and `--max-jobs-per-cycle` options and inspect `jobs` before treating an import as complete.

For a real usefulness decision, follow the [prospective pilot](../pilots/local-document/v0.1.0/README.md). Register real
recurring tasks and source versions before using any comparison method. This example cannot substitute for those tasks,
independent review or voluntary reuse.
