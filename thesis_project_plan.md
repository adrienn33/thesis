# Thesis Project Plan: MCP + ASI on WebArena

**Last updated**: 2025-03-25
**Status**: Implementation in progress

---

## What This Document Is

This is the single source of truth for completing the thesis. It replaces the handoff spec with a clean, phased plan that captures every remaining deliverable. Each phase has explicit inputs, outputs, and acceptance criteria.

---

## Thesis In One Paragraph

This thesis studies how MCP-based tool execution changes the effectiveness-efficiency tradeoff of Agent Skill Induction (ASI) on the WebArena benchmark. Four experimental conditions (Vanilla, Vanilla+ASI, MCP, MCP+ASI) are compared across 187 Magento shopping tasks. The core finding is that MCP dramatically reduces token consumption and step count while preserving or modestly improving task success, and that ASI provides greater benefit in the MCP regime than the browser regime. A secondary analysis demonstrates that strict benchmark evaluation systematically undercounts functionally correct MCP behavior, and a manually annotated correctness layer recovers additional successes. Elasticsearch integration for MCP search tools provides parity with the browser agent's built-in search capabilities.

---

## Current State

### What exists and works

- **Four conditions** runnable via `run_online.py --experiment {vanilla, vanilla_asi, mcp, mcp_asi}`
- **5 MCP servers** (11 active tools) running inside Docker container
- **Full ASI pipeline**: trajectory collection, validation, skill induction, skill reuse
- **Metrics logging**: `research_metrics.json` per task with success, steps, tokens, elapsed time
- **Failure taxonomy**: 94 hand-analyzed failures in `thesis_taxonomy.csv`

### What has been run

| Condition | Tasks Run | Benchmark Coverage | Notes |
|-----------|-----------|-------------------|-------|
| MCP | 187 | Full benchmark | 95/187 = **50.8%** success (cohort_23) |
| Vanilla | 20 | Subset only | 70% on 20-task subset (cohort_17) |
| Vanilla+ASI | 20 | Subset only | 65% on 20-task subset (cohort_17) |
| MCP+ASI | 20 | Subset only | 75% on 20-task subset (cohort_17) |

### The gap

The thesis requires all four conditions run on the **full 187-task benchmark**. Currently only MCP has this. Additionally, MCP's search tooling uses SQL `LIKE` matching while the browser agent benefits from Elasticsearch — an unfair disadvantage that must be fixed before final runs.

---

## Phase Plan

### Phase 1: Implement Elasticsearch Search
**Priority**: Non-negotiable. Must complete before any benchmark reruns.
**Estimated effort**: 1 session

Replace SQL `LIKE '%keyword%'` matching in `search_products()` with Elasticsearch queries using the same ES instance that powers the Magento storefront. Full drop-in replacement, no toggle.

**Detailed plan**: See `semantic-implementation.md` in the ASI directory.

**Summary of changes**:
- Add ES query builder (`_build_es_query`) and HTTP client (`_es_search`) to `magento_products.py`
- Replace `search_products()` body: ES handles text search + filters, SQL enriches matched entity_ids
- Only `magento_products.py` changes. Other 4 MCP servers untouched (confirmed by audit).

**Acceptance criteria**:
- [ ] `test_mcp_server.py` and `test_magento_mcp.py` pass
- [ ] "UGREEN" query returns ~20 results, zero contain "Beaugreen"
- [ ] "Nintendo Switch game card case" returns >0 relevant results (was 0 with SQL LIKE)
- [ ] "Nike slide slipper" returns Nike Benassi (was 0 with SQL LIKE)
- [ ] "Sony Bluetooth headphones" finds wireless models not named "Bluetooth"
- [ ] Price range and category filters still work
- [ ] Return format identical to current (no downstream changes)

---

### Phase 2: Rerun MCP on Full Benchmark
**Priority**: Critical. Produces the definitive MCP numbers.
**Estimated effort**: ~1.5 hours runtime + spot-check

Run MCP condition on the full 187-task benchmark with ES-backed search.

```bash
python3 run_online.py --experiment mcp --website shopping \
  --task_ids 21-26,47-51,96,117-118,124-126,141-150,158-167,188-192,225-235,238-242,260-264,269-286,298-302,313,319-338,351-355,358-362,368,376,384-388,431-440,465-469,506-521,528-532,571-575,585-589,653-657,689-693,792-798
```

**Acceptance criteria**:
- [ ] All 187 tasks produce `research_metrics.json` files
- [ ] No MCP server connectivity errors in logs
- [ ] Spot-check 5 previously-failing semantic tasks (158, 229, 238, 279, 282) — verify improved behavior

---

### Phase 3: Verify Results and Spot-Check Taxonomy Failures
**Priority**: Critical. Validates that ES integration helped.
**Estimated effort**: 1 session

Compare Phase 2 results against the pre-ES MCP run (cohort_23).

**Deliverables**:
- [ ] Quick comparison table: pre-ES vs post-ES success rate on full 187 tasks
- [ ] Check each of the 16 `Semantic?=Yes` tasks from taxonomy — did they flip to success?
- [ ] Note any regressions (tasks that passed before but fail now)
- [ ] If regressions exist, diagnose and fix before proceeding

---

### Phase 4: Run All Four Conditions on Full Benchmark
**Priority**: Critical. This is the primary thesis dataset.
**Estimated effort**: ~6 hours runtime (can parallelize some)

Run each condition on the full 187-task benchmark. Each run takes ~1.5 hours.

```bash
# Run these sequentially or in parallel if resources allow
python3 run_online.py --experiment vanilla     --website shopping --task_ids <full_set>
python3 run_online.py --experiment vanilla_asi  --website shopping --task_ids <full_set>
python3 run_online.py --experiment mcp_asi      --website shopping --task_ids <full_set>
# MCP already done in Phase 2
```

**Acceptance criteria**:
- [ ] All 4 conditions x 187 tasks = 748 `research_metrics.json` files
- [ ] Per-condition success rates computed and recorded
- [ ] No condition has anomalous error rates (>5% infrastructure failures)

**Note**: MCP+ASI uses the induced skill library from `results/final/shopping.mcp.asi.py`. Vanilla+ASI uses `actions/shopping.py`. Verify both are in place before running.

---

### Phase 5: Update Failure Taxonomy Post-Semantic
**Priority**: High. Required for the secondary correctness analysis.
**Estimated effort**: 1 session

Re-analyze failures from the Phase 2 MCP run. Update `thesis_taxonomy.csv`.

**What to do**:
1. Identify all tasks that still fail under MCP with ES search
2. For tasks that were `Semantic?=Yes` in the old taxonomy:
   - Did ES fix them? Mark `Resolved?=Yes` if so
   - If still failing, re-categorize (the failure cause may have shifted)
3. For new failures not in the current taxonomy, add entries
4. Add the **`secondary_label`** column to every entry using this rubric:

| Label | Definition | Example |
|-------|-----------|---------|
| `strict_success` | Benchmark says correct | Task passed |
| `functional_success` | Benchmark says wrong, but agent clearly satisfied task intent | Task 144: answered "$0.00", eval expects "0" |
| `near_miss` | Correct strategy, minor mismatch prevented success | Task 283: correct data via MCP, reported via message instead of navigating |
| `genuine_failure` | Agent was genuinely wrong | Task 333: applied discount to wrong orders |

**Mapping guide from existing categories**:

| Existing Category | Default Secondary Label |
|-------------------|----------------------|
| Ground Truth / Reference Error | `functional_success` |
| Strict Benchmark Eval (correct answer, wrong format) | `functional_success` |
| Wishlist Pagination (item was added) | `functional_success` |
| MCP Makes Unachievable Achievable | `functional_success` |
| URL Mismatch (correct page, different path) | `functional_success` |
| Agent Instruction Mismatch (had correct answer) | `near_miss` |
| Agent Navigation Failure (correct strategy, ran out of steps) | `near_miss` |
| Incomplete Product Search (found some, not all) | `near_miss` |
| Agent Reasoning Failure | `genuine_failure` |
| MCP Search Over-matching | `genuine_failure` |
| Unachievable Task Not Recognized | `genuine_failure` |

**Acceptance criteria**:
- [ ] Every failing task in the MCP run has a row in `thesis_taxonomy.csv`
- [ ] Every row has a `secondary_label` value
- [ ] Counts are tallied: how many `functional_success`, `near_miss`, `genuine_failure`

**Key thesis number**: "Manually annotated" success rate = `strict_success` + `functional_success` count / 187. This resolves the over-strict benchmark eval issue with a defensible, human-reviewed number.

---

### Phase 6: Build `thesis_analysis.py`
**Priority**: High. Produces all tables, figures, and statistical tests for the paper.
**Estimated effort**: 1 session

A single script that reads all `research_metrics.json` files + `thesis_taxonomy.csv` and produces every quantitative artifact the thesis needs.

#### Tables

| # | Table | Source |
|---|-------|--------|
| 1 | **Success rate** across 4 conditions (187 tasks, with 95% CI) | `research_metrics.json` |
| 2 | **Adjusted success rate** (strict + functional) across 4 conditions | `thesis_taxonomy.csv` secondary_label |
| 3 | **Step count** across 4 conditions (mean, median, with CI) | `research_metrics.json` |
| 4 | **Token usage** across 4 conditions (mean, median, with CI) | `research_metrics.json` |
| 5 | **Per-task paired comparison** (187 rows: task_id, success per condition, steps, tokens) | `research_metrics.json` |
| 6 | **Failure taxonomy frequency** by category | `thesis_taxonomy.csv` |
| 7 | **Semantic search impact** (pre-ES vs post-ES on the 16 flagged tasks) | Comparison of cohort_23 vs Phase 2 |
| 8 | **ASI interaction effect** (does ASI help more in MCP vs browser?) | Derived from Table 1 |

#### Figures

| # | Figure | Type |
|---|--------|------|
| 1 | **Efficiency frontier**: success rate vs avg tokens (4 points + error bars) | Scatter |
| 2 | **Per-task token reduction**: MCP vs Vanilla delta distribution | Violin/box plot |
| 3 | **Failure taxonomy breakdown** | Stacked bar or pie |
| 4 | **Strict vs adjusted success** side-by-side (4 conditions) | Grouped bar |
| 5 | **Step count distribution** by condition | Violin/box plot |

#### Statistical Tests

| Test | Comparison | Method |
|------|-----------|--------|
| Success rate (binary, paired) | All pairwise condition comparisons | McNemar's test |
| Token usage (continuous, paired) | MCP vs Vanilla, MCP+ASI vs Vanilla+ASI | Wilcoxon signed-rank |
| Step count (continuous, paired) | Same as above | Wilcoxon signed-rank |
| Confidence intervals | All metrics | Bootstrap (1000 resamples) or normal approx |

#### Additional Analyses

| Analysis | Purpose |
|----------|---------|
| **Task difficulty** | Distribution of step counts, % of one-shot completions, ceiling effects |
| **ASI interaction** | 2x2 table: {Vanilla, MCP} x {no ASI, ASI} with success rates, test for interaction |
| **Cost per success** | Tokens per successful task by condition |
| **Win/loss/tie** | Per-task paired counts: condition A wins, B wins, or tie |

**Acceptance criteria**:
- [ ] Script runs end-to-end from `research_metrics.json` + `thesis_taxonomy.csv`
- [ ] All 8 tables render to stdout or CSV
- [ ] All 5 figures save as PDF/PNG
- [ ] Statistical tests report test statistic + p-value
- [ ] Script is re-runnable (no manual steps)

---

### Phase 7: Case Studies and Write-Up Support
**Priority**: Medium. Strengthens the discussion section.
**Estimated effort**: 1 session

#### 3-5 Case Study Vignettes

Select illustrative failures that demonstrate key thesis points:

| Vignette | Task | Point It Makes |
|----------|------|---------------|
| Evaluator strictness | 144 | Agent answered "$0.00", eval expects token "0" — correct answer penalized |
| Search over-matching (pre-ES) | 229 | "Beaugreen" matched as UGREEN substring — ES eliminates this |
| Ground truth error | 286 | Agent found actual cheapest SSD; benchmark expected a non-SSD hard drive |
| Navigation ceiling | 436-440 | MCP research succeeds, checkout navigation exhausts step budget |
| MCP exceeds benchmark | 792-793 | MCP solves "unachievable" tasks the benchmark says can't be done |

Each vignette: 1 paragraph context, what happened, what it means for the thesis.

#### Run Documentation

Update `README` or create `RUNNING.md` with:
- [ ] Commands for all 4 conditions
- [ ] Full 187-task ID string
- [ ] How to regenerate all tables/figures
- [ ] Docker container prerequisites
- [ ] ES dependency note (must be running)

---

## Critical Data Analysis Components (Checklist)

These are the specific analysis outputs the thesis needs. Checked items exist; unchecked are TODO.

### Primary Metrics (per condition, full 187-task benchmark)
- [ ] Success rate with 95% CI
- [ ] Adjusted (annotated) success rate with 95% CI
- [ ] Mean and median step count with CI
- [ ] Mean and median input token usage with CI
- [ ] Mean elapsed time

### Paired Comparisons
- [ ] Per-task success (binary): McNemar's test for each condition pair
- [ ] Per-task tokens: Wilcoxon signed-rank for each condition pair
- [ ] Per-task steps: Wilcoxon signed-rank for each condition pair
- [ ] Win/loss/tie counts per condition pair

### Efficiency Analysis
- [ ] Tokens per successful task by condition
- [ ] Cost per success (if reporting dollar cost)
- [ ] Success rate vs token usage frontier plot

### Secondary Correctness Layer (Manually Annotated)
- [ ] Every MCP failure has a `secondary_label` in taxonomy CSV
- [ ] Strict success rate vs annotated success rate comparison table
- [ ] Count of `functional_success` cases (correct answer, eval rejected)
- [ ] Count of `near_miss` cases (close but not quite)
- [ ] This analysis applied to all 4 conditions (at minimum MCP and MCP+ASI)

### Failure Taxonomy
- [ ] Final category counts with percentages
- [ ] Breakdown by condition (do failure modes differ between MCP and browser?)
- [ ] Semantic search impact: which taxonomy entries were resolved by ES?
- [ ] Stacked bar chart of failure categories

### ASI Interaction Analysis
- [ ] 2x2 table: {Browser, MCP} x {No ASI, ASI} success rates
- [ ] Does ASI help MCP more than it helps browser? (interaction effect)
- [ ] Hypothesis: MCP's compressed trajectories produce cleaner skill induction signal

### Task Difficulty / Benchmark Suitability
- [ ] Distribution of step counts across conditions
- [ ] Percentage of tasks completed in 1 step (one-shot rate)
- [ ] Evidence for ceiling effects (tasks too easy to differentiate conditions)
- [ ] Evidence for floor effects (tasks impossible for all conditions)
- [ ] Argument: MCP benefits are more visible on efficiency than raw success under this task distribution

### Semantic Search Ablation
- [ ] Pre-ES vs post-ES success on the 16 `Semantic?=Yes` taxonomy tasks
- [ ] Pre-ES vs post-ES success on the full 187-task benchmark
- [ ] Which specific failures were resolved? Which persisted?

---

## Suggested Thesis Claims (Updated)

### Well-supported (expect strong evidence)

1. **MCP reduces token consumption by ~75%** relative to browser execution
2. **MCP reduces step count by ~4x**
3. **ASI provides greater benefit in the MCP regime** than the browser regime
4. **Strict benchmark evaluation undercounts functionally correct MCP behavior** — manually annotated success rate is higher than strict rate

### Supported with caveats

5. **MCP preserves or modestly improves success rate** — depends on full benchmark results
6. **Elasticsearch integration recovers retrieval-related failures** — expect ~5% improvement on flagged tasks

### Limitations to acknowledge

- Single domain (Magento shopping) — generalization untested
- Single model (Claude) — results may differ with other LLMs
- Input tokens only (completion tokens not logged) — input dominates cost but should be stated
- Fixed 10-step budget disproportionately affects browser execution
- Secondary correctness labels are human-annotated (subjective, though defensible)

---

## Timeline Estimate

| Phase | Effort | Blocking? |
|-------|--------|-----------|
| 1. Implement ES | 1 session | Blocks everything |
| 2. Rerun MCP | ~1.5hr runtime | Blocks Phase 3 |
| 3. Verify results | 1 session | Blocks Phase 4 (if regressions) |
| 4. Run other conditions | ~6hr runtime | Blocks Phase 6 |
| 5. Update taxonomy | 1 session | Blocks Phase 6 |
| 6. Build analysis script | 1 session | Blocks Phase 7 |
| 7. Case studies + docs | 1 session | Non-blocking |

Phases 4 and 5 can overlap (taxonomy work while runs execute). Total: ~4-5 focused sessions + runtime.

---

## File Map

| File | Purpose |
|------|---------|
| `thesis_project_plan.md` | This document (project plan) |
| `semantic-implementation.md` | Detailed ES implementation plan (Phase 1) |
| `thesis_taxonomy.csv` | Failure taxonomy with secondary labels (Phase 5) |
| `thesis_analysis.py` | Tables, figures, statistical tests (Phase 6) |
| `mcp_servers/magento_products.py` | ES-backed product search (Phase 1 target) |
| `run_online.py` | Experiment runner for all 4 conditions |
| `results/final/` | All benchmark run data |
| `CLAUDE.md` | Developer reference for the ASI project |
