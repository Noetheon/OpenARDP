# Quickstart: Stable CSV Ingestion

```bash
uv run openardp init --store /tmp/openardp-csv
uv run openardp ingest corpora/realworld/v0.1.0/sources/cisa-known-exploited-vulnerabilities.csv --store /tmp/openardp-csv --json
uv run openardp search 'CVE-2021-44228 2021-12-24' --store /tmp/openardp-csv --json
```

Run the bounded F028 evaluation and independent validator:

```bash
uv run python scripts/run_csv_ingestion_benchmark.py --output /tmp/f028-csv
uv run python scripts/validate_csv_ingestion_benchmark.py --result /tmp/f028-csv
```

The benchmark selects only the frozen CSV source and Q15/Q16 from the unchanged F025 inputs. It requires no PDF model
bundle and its committed result is body-free.
