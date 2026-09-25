# Prospective local document pilot protocol

> [!NOTE]
> Since constitution 4.0.0 ([F041](../../041-lean-governance/spec.md)) this protocol no longer gates development.
> It remains a valid method for a deliberate formal comparison.

**Status:** Prepared for a future manual pilot; no real tasks, results or user benefit are asserted.
**Scope:** One person's recurring local document workflow. This is an investment decision aid, not a release gate,
population study or adoption claim. Historical benchmark inputs, evaluators, identities and results remain unchanged.

## 1. Start, freeze and stop

Before running a trial, identify the actual recurring job, participant, local document folder and expected deliverable.
Register 30 distinct, genuinely needed tasks as ten matched triplets. Do not invent replacements or recycle development
questions. Without this intake, the state is `awaiting_real_tasks`; preparation or synthetic smoke tests are not a trial.

Freeze the task register, source snapshots, matching rationale, assignments, execution order, tool configuration,
reviewer assignment, judging rubric and this protocol before viewing trial outputs. Record the freeze time, timezone
and exact file hashes.
Corrections after freezing remain visible as deviations; no task or failure may be silently replaced. A material
capability, task, source-version or measurement change prevents a confirmed verdict from the mixed observations.

The cumulative additional-work cap is **1,200 active person-minutes**. It includes readiness development, installation,
baseline preparation, task intake, execution, repair, independent review and administration, including work before the
freeze. Record opening effort already incurred and its basis; unknown effort is not zero and prevents GO. Concurrent
work by two people counts both people's minutes. Machine waiting is recorded separately.

The calendar cap is **ten working days**, starting on the earlier of the real-task register freeze or first task trial.
Record the ten eligible dates before execution using the participant's normal work calendar. Readiness development
alone does not start this calendar clock. Stop additional work at whichever cap is reached first. No completed decision
meeting all gates by then means `pause_expansion`, with missing evidence or unmet gates listed. No automatic extension.

## 2. Three usable comparison paths

| Arm | Actual work method |
| --- | --- |
| `current` | The participant's existing way of completing this job, recorded before the trial. |
| `cache` | Parse once, persist the complete native output and reuse it with established text search and source navigation. |
| `openardp` | The existing local ingest, lexical search/context, explicit readable evidence and source/version verification path. |

The first pilot uses lexical retrieval. For TXT/Markdown, the cache can retain immutable original text with a manifest
of source name/version, SHA-256 and line-numbered `rg` search; these formats need no costly parser. For rich documents,
use the same pinned parser/profile as OpenARDP, persist its complete native artifact once, and search its deterministic
text export while retaining navigation to the original. Record the exact commands/tools before trial. A baseline that
cannot actually search or locate its sources is not ready; do not replace it with repeated raw parsing or an identifier-only
dummy. No new benchmark runner or general retrieval framework is needed.

All arms receive the same available originals and immutable versions for their tasks. The matched tasks have comparable
access to documents. Use the same parser, model, agent host, prompts and answer/context budgets wherever those components
apply. Human search reformulation and source checking are available to every arm and timed. Preserve the actual current
workflow rather than quietly handicapping it. Record existing setup as existing; count the incremental setup needed now,
without reconstructing sunk historical costs. Fresh cache/OpenARDP setup is counted fully, not amortized over imagined use.

No optional semantic model may be enabled only for OpenARDP while calling this a matched retrieval comparison. If a real
workflow requires unequal model capabilities or an unavailable baseline component, document the difference and keep the
comparison exploratory; it cannot satisfy the confirmed GO gates in this protocol.

## 3. Ten matched triplets, without repeated answers

Match each triplet before solving any task by language, document size/count, task type, expected difficulty, required
evidence and version sensitivity. Include unsupported questions, conflicting sources or changed versions only when they
occur in the real job. Tasks within a triplet must be distinct and must not reveal each other's answers or locations.

Randomly assign one task per triplet to each arm. Separately freeze the execution sequence so each arm appears in each
of the three within-triplet positions three or four times across the ten triplets. Record the draw or seed and the full
schedule; do not redraw after seeing results. A task is attempted only in its assigned arm unless it needs recorded rescue.
Never rerun the identical task in all three arms and treat remembered answers as independent measurements.

Each task's assigned-arm phase has a **20-minute cumulative active-work limit** across all assigned attempts, declared before execution; retries do not reset it. At that limit, or earlier if the
participant cannot proceed, record failure and any partial output. Necessary rescue may then use the current workflow;
its actual active effort remains charged to the originally assigned arm. Rescue does not turn an assigned-arm failure
into an assigned-arm success. A trial can close with a reviewed failure; closure does not imply a correct answer. An
unrecorded outcome, unreviewed failure or still-open rescue leaves the task incomplete and blocks GO.

## 4. Minimal private records

Copy empty records outside Git into a private local run directory. Store real tasks, documents, outputs, paths, reviewer
notes and timings there. Pseudonymous participant/reviewer IDs suffice. No telemetry, upload, remote model call or
publication is enabled by the protocol. Synthetic smoke fixtures and their outcomes must be labelled synthetic and
excluded from all pilot counts. Timestamps use UTC RFC 3339; the separately declared timezone governs working dates.

The records must carry the following information; blank numeric fields mean missing, not zero.

| Record | Required columns or fields |
| --- | --- |
| Run/decision | Run ID; workflow; participant ID; source/configuration manifest references; opening added-effort minutes and basis; freeze time; working dates; assignments/order; reviewer independence/blinding; accounting completeness; deviations; gate values; verdict and reasons. |
| Task | Task ID; triplet ID; genuine request/origin date; private task text/reference; language/type; matching rationale; assigned arm; execution position; required outcome; frozen source/version references; task state. |
| Attempt | Attempt ID; task ID; assigned arm; actual method; phase (`assigned` or `rescue`); start/end; active work minutes; active source-check minutes; active repair minutes; machine-wait minutes; status; failure reason; output reference; whether the participant submitted it as final. |
| Overhead | Entry ID; date; person ID; category (`development`, `setup`, `import`, `maintenance`, `intake`, `review`, `administration`); arm or `study`; active minutes; machine-wait minutes; work description; allocation basis if shared. |
| Review | Review ID; task/attempt/output reference; reviewer ID; independent flag; blinded-to-arm flag; status; correctness; sufficient completeness; semantic support; source correctness; version correctness; abstention justification if applicable; private supporting-passage/source/version references; explanation. |
| Repeat use | Task ID/reference; real origin; date; participant ID; freely selected method; reason for choosing it; outcome; active effort record reference. |

Attempt time categories are mutually exclusive: reading/checking a source goes in source-check time, repairing a tool in
repair time, and other task work in work time. A rescue attempt uses the same columns; do not add its minutes a second
time as an overhead entry. Task-specific retries remain separate attempts linked to the same task. Non-task-specific
setup/import/maintenance goes only in overhead. Keep failed, abandoned and superseded attempts.

Study-only development/intake/independent assessment/administration count toward the 1,200-minute cap but remain separate
from operational arm comparisons. Each arm's required operational setup/import/maintenance is charged to it. Shared
operational overhead must use a recorded predeclared allocation whose arm shares sum to the actual effort; never omit
it or charge the full amount repeatedly. Record a zero only when observed or explicitly confirmed, with an explanation.

## 5. Human quality and provenance grading

All review judgments start `pending`; allowed final judgments are `pass`, `fail`, or explained `not_applicable`. A confirmed
limited-GO requires an independent human reviewer who did not produce the outputs, with arm names and identifying tool
labels withheld during grading. Preserve the private assignment key and disclose any lost blinding. Self-review can
support an exploratory personal observation only; it cannot produce `confirmed_limited_go`.

For each material claim, the reviewer identifies the concrete passage and checks that it supports that specific claim,
not just its vocabulary. Then verify the original source, immutable version and locator against the frozen manifest.
The statement must be correct and the result sufficiently complete for the registered task. A title containing an answer
word, a different paragraph about the same subject, or a technically valid citation does not establish semantic support.
Automated substring rules and constant source-fitness scores cannot certify these judgments.

A justified abstention can pass only when it correctly describes the unanswered scope and available sources; it cannot
hide a missing answer that those sources contain. Source/claim judgments that genuinely do not apply to an abstention
need an explanation, not empty cells. Review all outputs submitted as final, including outputs later corrected. A false
source/version final claim remains an incident even after rescue. Draft errors that were corrected before submission are
retained in attempt notes and their correction time is counted.

## 6. Manual totals and prospective decision gates

For task `i`, let `A_i` be the sum of work, source-check and repair minutes across **all** its assigned and rescue attempts.
For arm `a`, let `O_a` be its operational overhead and `T_a = O_a + sum(A_i for its ten assigned tasks)`.
Report `O_a`, task work, repair/rescue, waiting and study-only effort separately as well as `T_a`. A rescued task is charged
to its original assignment even if another method performed the rescue. Baseline times must be positive and all effort
entries complete and nonnegative; otherwise savings are undefined and GO is unavailable.

For quality counting, the assigned-arm result is the chronologically last output submitted as final within that task's assigned phase and before any rescue. The phase must be recorded as successfully closed within its cumulative
20-minute cap; otherwise its result counts zero. Review all earlier final outputs as well, and retain every false
source/version incident regardless of which output is selected for quality counting.

Let `Q_a` count the ten tasks whose thus-defined assigned-arm result passes the entire applicable quality rubric; failed/missing
assigned-arm results count zero. Let `S_a` count those quality-passing tasks completed within their assigned phase without
rescue. Review any rescue result too; it cannot improve `Q_a` or `S_a`. A missing answer requires a recorded failure review,
not a fabricated output. For each triplet, compare `A_openardp` with `A_cache`; a tie or failed OpenARDP assigned-arm task
is not a win. This group comparison excludes shared setup,
which is already included fully in the separate `T` gates.

The manual decision may be `confirmed_limited_go` only when **every** gate passes:

1. All 30 frozen trials have a terminal recorded outcome and complete independent, blinded human reviews, including
   failures and any rescue. Assignments, configurations, deviations and effort accounting are valid. No task remains
   open and no required judgment is pending. This gate requires complete observations, not 30 correct answers.
2. `1 - T_openardp / T_cache >= 0.30` **and** `1 - T_openardp / T_current >= 0.30`.
3. `S_openardp >= 9`, `S_openardp >= S_cache`, and `S_openardp >= S_current`;
   also `Q_openardp >= Q_cache` and `Q_openardp >= Q_current`.
4. Zero false source/version claims in OpenARDP outputs that were submitted as final, including later-corrected outputs.
5. OpenARDP is strictly faster than the cache in at least seven of ten triplets.
6. The participant voluntarily chooses OpenARDP for two further real tasks on different days, with recorded outcomes.
   These tasks are outside the original 30 and do not improve the comparison totals; their effort counts toward the cap.
7. The full decision, including review and repeat-use evidence, is reached within both caps.

Until then use `awaiting_real_tasks`, `in_progress` or `pending_review` as appropriate; missing evidence is never a pass.
At either cap, or when the completed trial fails a gate, use `pause_expansion` and record why. `confirmed_limited_go`
authorizes only another bounded slice serving the demonstrated workflow. It does not establish commercial viability,
general performance, contract stability or release readiness. Broader open-source investment additionally requires at
least two independent users who voluntarily return; one person's repeat tasks are not two users.

## 7. Interpretation limits

There are only ten tasks per arm. Matching is approximate, tasks differ and blinding the operator is impossible.
Counterbalancing reduces but cannot eliminate document familiarity, fatigue or changes in user skill. Report these limits
and any deviations beside the result. Thresholds are predeclared investment rules, not statistical proof of a population
effect. A pause decision means further expansion lacks sufficient evidence under this bounded test, not that the retained
technical core is worthless. The existing release NO-GO remains unchanged regardless of the pilot outcome.
