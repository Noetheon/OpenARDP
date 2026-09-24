# Usage log

Real use is the primary evidence for OpenARDP ([Article XIII](../../.specify/memory/constitution.md)). This log is
deliberately small: add one line whenever you, or an agent working for you, use OpenARDP for an actual task. Record
failures and "used something else instead" too; they are the most useful entries.

Keep the filled-in log **private** (for example `~/openardp-usage.csv`) when tasks or file names are confidential.
Share only what you choose to share, for example in an issue or a pull-request description.

## Columns

| Column | Meaning |
|---|---|
| `date` | UTC date, `YYYY-MM-DD` |
| `task` | What you needed, in a few words, for example "find the calibration limit in the vendor manual" |
| `documents` | Number and kinds of files involved, for example "12 PDF, 3 DOCX" |
| `path` | `cli`, `mcp:<client>` (for example `mcp:claude-code`), `agent-view` or `other` |
| `outcome` | `solved`, `partly`, `failed` or `gave-up` |
| `minutes` | Your own active time, including setup and repairs; leave machine waiting out |
| `instead` | What you would have used otherwise, for example "open PDFs by hand" or "grep" |
| `friction` | The most annoying thing, or `-` |

Copy [`usage-log.csv`](usage-log.csv) to start your own log.

## Reading the log

Look for repeated friction and for tasks that keep coming back. A feature request should point to log lines. A missing
capability that never shows up in real use is not a priority, however interesting it is.
