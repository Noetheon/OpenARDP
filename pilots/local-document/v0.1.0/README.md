# Private local-document pilot records

These are empty templates, not a completed study. No user tasks, measurements, judgments or benefit are claimed.
The [prospective protocol](../../../specs/038-local-document-pilot-readiness/contracts/pilot-protocol.md) is normative.
Use the [local workflow guide](../../../docs/30_LOCAL_DOCUMENT_WORKFLOW.md) for the product steps.

## Prepare a private run

1. Copy this directory to a new private location **outside the repository**, for example a folder under your Documents
   directory that is not synced or published unless you explicitly choose that. Fill only the private copy. Retain the
   protocol used for the run alongside it; copying a link alone does not freeze the protocol.
2. Open `decision.md`. Its initial state is `awaiting_real_tasks` and its verdict is `pending`. Record the actual recurring
   workflow, participant and independent reviewer. Opening effort from F037/F038 and other pilot readiness is **unknown
   until accounted for**, not zero. Preserve an honest basis and uncertainty; missing effort prevents GO.
3. Create private source/configuration manifests. Record exact original file hashes, version references, available
   locators and unchanged source snapshots; record tool/parser/model/agent versions, commands and budgets for all arms.
   The first comparison is lexical. For TXT/Markdown the cache retains immutable text and uses line-numbered `rg` search;
   rich documents use the same pinned parser's persisted complete native artifact plus searchable text and original
   navigation. Prove the baseline is usable before freezing; capability mismatch prevents confirmed GO.
4. Enter 30 genuine, distinct tasks in `tasks.csv`, ten matched triplets. Each triplet has one `current`, one `cache`
   and one `openardp` assignment. Draw assignments and order before any results; each arm occupies each within-triplet
   position three or four times across the study. Record the matching rationale, draw/seed and private assignment key.
5. Freeze the register, source/configuration manifests, rubric, reviewer and schedule. Enter hashes and UTC RFC 3339
   freeze time in `decision.md`, along with timezone and all ten working dates. Preserve the frozen files; later operational
   status changes belong to a working copy and never overwrite the frozen snapshot. Trials may begin only after this step.

Do not put source files, task text, outputs or filled records in Git. Pseudonymous person IDs suffice. Do not count
synthetic smoke tasks as genuine requests. No tool here uploads data, times work or judges answers automatically.

## Enter observations

The five CSVs contain headers only. Do not generate 30 placeholder rows and count them as tasks. Quote CSV fields that
contain commas, quotes or newlines; an ordinary spreadsheet or text editor is enough. Numeric blanks mean **missing**;
zero requires a real observation or explicit confirmation with a note. All active times are nonnegative person-minutes.

| File | How to use it |
| --- | --- |
| `tasks.csv` | One row per preregistered task. `origin_at` identifies a real request; private text can live at `task_reference`. `execution_position` is 1, 2 or 3 within its triplet. Begin phase/outcome fields as `pending`; link the last submitted assigned-phase output in `assigned_terminal_attempt_id`, or explain why none exists after failure. |
| `attempts.csv` | One row per attempt or retry, including failures and rescue. `phase` is `assigned` or `rescue`; `assigned_arm` never changes even if `actual_method` does. Record who worked, start/end, disjoint work/check/repair times and separate waiting. `submitted_final` records the participant's submission, not a quality pass. |
| `overhead.csv` | Record non-task work once. Categories are `development`, `setup`, `import`, `maintenance`, `intake`, `review`, `administration`. `allocation_scope` is an arm, `study`, or `shared`; the four allocation-minute columns must sum to `active_minutes`. Development/intake/independent assessment/administration are study effort. Explain predeclared allocation of shared operational costs. |
| `reviews.csv` | Record every submitted final output, including earlier outputs later corrected, and an explicit review of failed/no-output trials. All judgments and flags begin `pending`; final rubric values are `pass`, `fail`, or explained `not_applicable`. Independence/blinding flags are `yes` or `no` once known. Missing output must be explained as a failure, never fabricated. |
| `repeat-use.csv` | Record two further real tasks on different days only if freely chosen. These are outside the original 30. Link effort to new `attempts.csv` rows using `repeat_use_id` as `task_id`; include their time in the overall cap but exclude it from the original comparison totals. |

Within each original task, the 20-minute assigned-phase limit is cumulative across retries and all active time categories.
Do not reset the timer for a new attempt. Rescue time is recorded in its own attempt and charged to the original arm;
never enter it again as overhead. Task-specific repairs go in attempts; shared setup/maintenance goes in overhead.
With multiple people, give each person's effort its own non-overlapping time record. Keep failed/superseded records.

For each reviewed output, `supporting_passages_reference` points to private notes mapping **every material claim** to an
exact passage, source snapshot/version and locator. Source/version checks must use the frozen manifest. A matching word,
title or valid technical citation is insufficient. Record justified abstention explicitly. Mark `false_final_source_version`
as `yes` for a false final source/version claim even when corrected later; it is never erased by selecting a later output.
Use `no` only after review. Self-review or lost blinding is exploratory and cannot establish confirmed GO.

The reviewer receives outputs without arm/tool labels and cannot see the private assignment key during grading. Review
and trial outcome are distinct: a closed, reviewed failure is a complete observation but contributes no quality success.
An open trial, missing outcome or pending review blocks GO.

## Manual validation and decision

Before totaling, check 30 distinct genuine tasks, ten complete triplets, one assignment per arm per triplet, balanced order,
frozen manifests/configurations and valid links between records. Preserve all deviations. For each task confirm cumulative
assigned time at most 20 minutes, the terminal assigned output is the chronologically last final submission before rescue,
and every final submission and failed trial has a review. Missing required judgments/accounting prevent GO.

For each original task, `A_i = sum(active_work_minutes + active_source_check_minutes + active_repair_minutes)` over all its
attempts, including rescue. For each arm, `O_a` is the sum of its operational allocation column in overhead, and
`T_a = O_a + sum(A_i)` for its ten assigned tasks. Report overhead, repair/rescue, waiting and study effort separately.
Savings against each baseline are `1 - T_openardp / T_baseline`; a zero baseline denominator is invalid, not a saving.
Use only the protocol-defined successful terminal assigned output for `Q_a` and `S_a`; failed/missing results count zero.

Count a triplet win only when OpenARDP's assigned phase succeeds and its `A_i` is strictly less than the cache task's
`A_i`; ties/failures are not wins. This comparison excludes setup; the total-time gates include all allocated setup.
For the overall cap, sum opening effort not repeated in these records, **all** attempt effort (including repeat use), and
each overhead entry's `active_minutes` once. Do not sum allocation columns again. Include every person's contribution;
machine waiting remains separate. Record accounting completeness and uncertainty.

Complete every pending gate in `decision.md` manually against the protocol. Stop at 1,200 additional person-minutes or
the end of working day ten, whichever comes first. Missing evidence at the cap means `pause_expansion`. Even a confirmed
limited-GO establishes only one person's bounded workflow benefit; release NO-GO and external-adoption requirements remain.
