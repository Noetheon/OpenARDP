# Agent access: find, read and verify

OpenARDP prepares your files once. After that, an agent such as Claude Code, Codex or any MCP client can answer
questions from them without reading whole documents into its context:

1. **find** the passages that match a question;
2. **read** only the page, slide, section or lines it needs;
3. **verify** a quote before citing it with file, page and line.

Originals are never modified. Returned text is checked against the stored original, or the retained parser output,
before it is shown ([ADR 0020](adr/0020-token-efficient-agent-access.md)). Measured on identical tasks, this path used
16–34 percent of the tokens of the older MCP tools. The measurement is described in the
[F040 notes](../specs/040-agent-ready-access/implementation-notes.md).

## Install

You need Git, Python 3.12 and [uv](https://docs.astral.sh/uv/). From a clone of this repository:

```bash
uv sync --extra docling --locked      # TXT, Markdown and CSV work without the extra
```

PDF parsing additionally needs the verified offline model bundle described in
[Offline PDF models](22_OFFLINE_PDF_MODEL_BUNDLE.md). DOCX and PPTX need only the `docling` extra.

## Prepare documents

```bash
uv run openardp add ~/Documents/manuals --store ~/openardp-store
```

`add` creates the store on first use and accepts files and folders. Folders are searched recursively, and hidden files
and symbolic links are skipped. Unchanged files are recognized and skipped, so it is safe to run `add` again after
editing or adding files. Each file is reported as added, updated, unchanged or failed, with a hint for failures.

Without `--store`, commands use `.openardp` in the current directory, which suits a per-project store; add `.openardp/`
to that project's `.gitignore`.

## Use from the command line

```bash
S=~/openardp-store
uv run openardp docs --store $S                                      # what is there, size in tokens
uv run openardp find "How often must the sensor be calibrated?" --store $S
uv run openardp toc manual.pdf --store $S                            # headings or pages with sizes
uv run openardp read manual.pdf --page 12 --store $S                 # or --lines 120-180, --section "Storage"
uv run openardp verify "Calibrate the sensor every morning" --store $S
```

Documents can be named by file name, path suffix, a unique part of the name or the short id shown in brackets.
`find` understands questions and keywords in English and German; exact phrases can be quoted. `read` prints numbered
lines, is bounded by `--max-tokens` (default 2,000) and says where to continue. Add `--json` to any command for the
standard JSON envelope.

`verify` returns one of three answers:

- `VERIFIED` with the location and version;
- `OUTDATED` when the quote exists only in an earlier version you cite with `--version`;
- `NOT FOUND` with the closest passage.

It tolerates differences in spacing, quote marks, dashes, formatting and `...` gaps, and it reports when the source
file has changed since it was added.

## Connect an MCP client

The server is local and read-only, and speaks MCP over standard input and output. Replace the paths with yours.

**Claude Code:**

```bash
claude mcp add openardp -- uv run --directory /path/to/OpenARDP openardp mcp --store /path/to/store
```

**Codex CLI** (`~/.codex/config.toml`):

```toml
[mcp_servers.openardp]
command = "uv"
args = ["run", "--directory", "/path/to/OpenARDP", "openardp", "mcp", "--store", "/path/to/store"]
```

**Other clients** (`mcpServers` JSON):

```json
{
  "mcpServers": {
    "openardp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/OpenARDP", "openardp", "mcp", "--store", "/path/to/store"]
    }
  }
}
```

The server offers five tools: `list_documents`, `find`, `read`, `outline` and `verify_quote`. Their instructions tell
the agent the intended order and that document text is data, not instructions. The older audit tools are available
with `--tools full` (both sets) or `--tools legacy`. Details are in the
[tool contract](../specs/040-agent-ready-access/contracts/mcp-agent-tools.md).

A useful instruction for your agent is:

> Use the openardp tools for questions about my documents: find first, read only what you need, and verify quotes
> before citing them as file:line or file p.N.

## Agents without MCP

```bash
uv run openardp agent-view ~/agent-docs --store ~/openardp-store
```

This writes one Markdown file per document (text files keep their name; PDF, DOCX and PPTX become `name.pdf.md` and so
on), with page and slide markers, plus an `INDEX.md`. The index lists every file with its size and outline, so an agent
with file tools can open only what it needs. Running the command again updates the view. Files you added or edited in
that folder are never overwritten or deleted.

## Good to know

- **What an agent sees.** For TXT, Markdown and CSV, line numbers are the lines of the original file. PDF, DOCX and
  PPTX are shown as Markdown rendered from the parser's retained output, with `<!-- page N -->` or `<!-- slide N -->`
  markers. Scanned pages without text, images and complex layouts can lose information. Check important passages in
  the original.
- **Speed.** Adding documents is a one-time cost per file version. In our measurements (a 4-core cloud container),
  a search over 62 Markdown documents answered in about 60–90 ms inside the MCP server. A CLI call on DOCX or PPTX
  takes about 2 s, because each call re-checks the rendered text against the stored original.
- **Cache.** The cache under `<store>/agent-cache/` can be deleted at any time; `openardp refresh --full` rebuilds it.
- **Audit path.** For a formal, replayable record of what evidence was selected for a task, use `openardp context`,
  which is described in the [document workflow](30_LOCAL_DOCUMENT_WORKFLOW.md).
- **Usage log.** If you use this for real work, a line in the [usage log](../pilots/usage-log/README.md) helps decide
  what to improve next.
