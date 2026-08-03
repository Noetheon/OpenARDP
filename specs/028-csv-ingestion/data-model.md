# Data Model: Stable CSV Ingestion

## Existing models extended

- `TextMediaType.CSV = "text/csv"` expands the closed local text media enum.
- `ParsedTextDocument` remains the parser envelope and accepts CSV table blocks.
- `ParsedBlock` remains text-backed; CSV text is canonical JSON so FTS and exact context delivery require no schema change.

## Canonical block projection

Header record:

```json
{"header":["cveID","dueDate"],"record":1,"type":"csv_header"}
```

Data record:

```json
{"fields":[["cveID","CVE-2021-44228"],["dueDate","2021-12-24"]],"record":2,"type":"csv_record"}
```

For a data cell beyond header width, the first pair item is `null`. A short row simply has fewer pairs. The separate header
block preserves columns even for a header-only file. Every string is the exact decoded CSV-reader value.

## Provenance

- `kind`: `table`
- `order`: zero-based global logical-record order
- `structural_path`: `("root", "table:<order>")`
- `line_start` / `line_end`: inclusive one-based physical lines consumed by that logical record
- extraction: `openardp-csv-v1`
- extension: `openardp.csv = {"record": <one-based logical record>}`
- internal compatibility extension: `openardp.text = {"line_start": ..., "line_end": ...}`

## Limits

| Limit | Value | Effect |
|---|---:|---|
| source bytes | 104,857,600 | existing source/worker limit |
| physical line characters | 1,048,576 | existing line bound |
| normalized records | 100,000 | existing block bound |
| cells per record | 256 | reject excessive width |
| decoded field characters | 1,048,576 | reject oversized logical fields |
| canonical record characters | 1,048,576 | bound derived block and context size |

## Identity

CSV uses `name="openardp-csv"`, `version="1"`, `profile="default"`. Its configuration hash includes the accepted media
type, dialect, header policy and limits. `openardp-text` remains exactly unchanged. Existing source and block identifier
algorithms are unchanged, and CSV representation IDs cannot collide with historical text recipe output.
