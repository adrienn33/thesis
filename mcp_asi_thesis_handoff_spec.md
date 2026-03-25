# Spec: MCP + ASI Thesis Project Completion

## 1. Project Context

I am working on an MS thesis based on the Agent Skill Induction (ASI) paper/repo:

- Reference repo: `https://github.com/zorazrw/agent-skill-induction`

The goal is **not** to reproduce the original project exactly, but to adapt the same general **ASI pipeline** to an **MCP-based tool execution environment** and evaluate the effects of replacing browser-mediated interaction with MCP tooling.

The current thesis direction is:

- Use the ASI pipeline as the base methodology
- Apply it to MCP tooling
- Compare against browser-based execution
- Measure whether MCP improves:
  - task success rate
  - step count
  - token usage
- Current evidence suggests:
  - **token usage drops dramatically**
  - **step count also drops**
  - **strict benchmark success rate does not clearly improve**
- There are known confounds:
  - the evaluation framework is extremely strict and appears to require near-literal matches
  - tasks may not be difficult enough to fully expose meaningful differences
  - many MCP trajectories are very short, sometimes effectively one-shot, which lowers tokens but may flatten success-rate gains
- A final planned addition is **semantic search for MCP tooling**, intended to provide parity with desktop/browser-style search and hopefully recover some currently lost success cases

The desired paper framing is likely:

> MCP + ASI substantially improves execution efficiency while preserving or slightly improving effectiveness, and strict benchmark evaluation may undercount functionally correct MCP behavior.

This spec is for helping complete the implementation, evaluation, analysis, and paper-supporting artifacts in a rigorous way.

---

## 2. High-Level Desired Outcomes

The final outcome should support a thesis/paper with the following claims, assuming results cooperate:

### Primary target claims
1. **MCP + ASI significantly reduces token usage** relative to browser-based ASI
2. **MCP + ASI reduces step count**
3. **MCP + ASI preserves or modestly improves success rate**
4. **Adding semantic search to MCP tooling recovers some currently missing retrieval capability and may produce a small success-rate bump**
5. **Strict benchmark evaluation may undercount functional correctness**, especially for MCP-style trajectories

### Secondary target claims
1. MCP changes the execution regime from browser navigation to direct tool interaction
2. Even when strict success is tied, MCP may dominate on efficiency
3. Some benchmark “failures” are really evaluator mismatches or near-misses rather than genuine inability

### Deliverable expectations
By the end, I want:
- working code for the relevant agent variants
- reproducible evaluation scripts
- tables/plots for the thesis
- a small but rigorous secondary evaluation for near-miss / functional correctness
- a clear failure analysis
- concise documentation of how to run everything

---

## 3. What I Need You to Do

You will have access to my working repo/materials. Your job is to inspect the existing codebase and adapt this spec to the actual implementation.

I want you to:
1. understand the current repo structure and what is already implemented
2. identify gaps between the current state and the desired thesis outcomes
3. implement the highest-value missing pieces with minimal project drift
4. preserve the existing project direction instead of reinventing it
5. produce clean, reproducible, thesis-friendly outputs

Do **not** radically change the research question or replace the benchmark/project unless absolutely necessary.

---

## 4. Required Workstreams

## A. Repository + System Audit

First, inspect the repo/materials and produce a short project audit.

### Audit goals
- Identify the current ASI pipeline components
- Identify how browser execution is currently implemented
- Identify how MCP execution is currently implemented
- Identify how evaluation currently works
- Identify what metrics are already logged
- Identify where semantic search should be integrated
- Identify what experimental conditions are already runnable vs missing

### Required output
Produce a concise internal project audit that answers:
- What experiments are currently possible?
- What is missing for the thesis?
- What code paths are fragile / incomplete?
- What minimal implementation plan gets us to thesis-ready?

Do this before major refactors.

---

## B. Experimental Conditions

The project should support clean comparison across the following conditions, subject to what is feasible in the repo:

1. **Browser + ASI**
2. **MCP + ASI**
3. **MCP + ASI + semantic search**

If a non-ASI baseline or browser non-ASI baseline already exists and is low-cost to keep, great, but do **not** let optional baselines delay the core thesis comparisons.

### Requirement
There must be a consistent, documented way to run the three core conditions above on the same task set / benchmark split.

---

## C. Semantic Search for MCP Tooling

This is the most important remaining system addition.

### Goal
Add semantic search to MCP tooling so the agent can perform retrieval closer to desktop/browser search behavior rather than relying only on brittle exact lexical matching.

### Desired behavior
The agent should be able to issue flexible retrieval queries that support semantically related matches, akin to:
- fuzzy lookup
- embedding-based retrieval
- elastic-style relevance ranking
- natural language search queries over available MCP resources/data

### Constraints
- Keep implementation practical and thesis-friendly
- Do not build an overengineered retrieval stack unless necessary
- Prefer something that can be clearly described in methods
- It should be easy to ablate:
  - MCP without semantic search
  - MCP with semantic search

### What I need from you
- inspect current MCP tooling/search flow
- identify where exact-match retrieval is failing
- implement semantic retrieval in the smallest clean way
- make it toggleable/configurable
- log when semantic retrieval is used
- make sure it is measurable in evals

### Nice-to-have
If possible, capture retrieval metadata such as:
- query text
- retrieved candidates
- ranking scores
- whether semantic search altered the top result
- whether the final answer depended on semantic retrieval

This is useful for failure analysis later.

---

## D. Metrics and Logging

The thesis lives or dies on clean metrics.

### Required metrics per run / per task
At minimum, log:
- task ID
- condition / model / config
- success/failure under official benchmark
- step count
- token usage
- prompt tokens
- completion tokens
- total tokens
- final answer / final action
- trajectory / trace metadata sufficient for debugging
- wall-clock time if easily available
- retrieval/tool usage metadata if relevant

### Derived metrics to support analysis
Need scripts or notebooks that compute:
- overall success rate
- average / median step count
- average / median token usage
- cost per success
- tokens per successful task
- step count per successful task
- paired task-level win/loss/tie summaries between conditions

### Important
Metrics must be comparable across conditions.
If the current logging is inconsistent, fix that.

---

## E. Evaluation Rigor: Secondary Correctness Layer

This is the **single highest-value analysis addition**.

The benchmark appears overly strict and may mark outputs incorrect even when they are functionally or semantically correct enough to satisfy the intent.

I want a **secondary evaluation layer** added on top of the official benchmark.

### Important principle
Do **not** replace the official metric.
Keep:
- **primary metric** = official benchmark success
- **secondary metric** = adjudicated functional correctness / near-miss analysis

### Desired rubric
Create a simple label scheme such as:
1. **Strict success**
2. **Functional success**
3. **Near miss**
4. **Failure**

Definitions can be refined after looking at the benchmark/task format, but roughly:
- **Strict success**: benchmark says correct
- **Functional success**: benchmark says wrong, but the agent clearly satisfied task intent or produced an acceptably correct result
- **Near miss**: mostly correct path, but minor mismatch / finalization issue / formatting issue / omitted detail
- **Failure**: genuinely wrong

### What I need from you
Inspect the evaluation framework and propose the lightest rigorous implementation path for this secondary layer.

Potential implementations:
- annotation-ready export of failed trajectories
- rubric template
- scripts to sample disagreements/failures
- optional judge-assisted labeling workflow if useful
- support for manual review

### Minimum acceptable outcome
Even if full automation is not realistic, produce:
- tooling to export candidate cases
- clear schema for annotation
- scripts to summarize annotation results

This does not need to be fully automatic. It does need to be clean and defensible.

---

## F. Failure Taxonomy

I need failure analysis that is thesis-usable, not just anecdotal.

### Desired failure buckets
Refine as needed after inspecting real traces, but start from:
- evaluator mismatch / literal match issue
- retrieval miss
- planning failure
- wrong one-shot answer
- tool limitation
- execution failure
- semantic ambiguity / partial correctness
- missing finalization / not completing last required action

### Required work
- propose final taxonomy after inspecting failures
- make it easy to tag sampled failures
- summarize frequencies by condition
- specifically assess whether semantic search reduces retrieval-related failures

---

## G. Task Difficulty / Benchmark Suitability Analysis

One concern is that the current tasks may be too easy or too shallow to expose advantages beyond token savings.

I do **not** want a brand new benchmark.
I do want a small analysis that makes this limitation explicit and evidence-based.

### What I want
Look for signs such as:
- very short successful trajectories
- many one-step or near-one-step attempts
- compressed variance in step counts
- tied success despite very different interaction modes
- benchmark tasks that do not demand deep search or long-horizon planning

### Deliverable
Produce a small analysis section or artifact that helps argue one of:
- task difficulty may ceiling out success differences
- current benchmark favors literal matching over process quality
- MCP benefits are more visible on efficiency than on raw success under this task distribution

This can be light, but it should be data-backed if possible.

---

## H. Statistical Analysis Support

I do not necessarily need a full publication-grade stats pipeline, but I do need something academically defensible.

### Desired tests
Where appropriate, support:
- paired comparison of success outcomes across conditions
- paired comparison of token usage
- paired comparison of step count

Suggested tests if feasible:
- McNemar’s test for paired binary success
- Wilcoxon signed-rank or bootstrap confidence intervals for paired step/token differences

### Requirement
At minimum, produce scripts or notebook cells that:
- compute paired deltas
- summarize confidence intervals or simple significance tests
- generate tables ready to paste into the thesis

---

## I. Figures and Thesis Artifacts

I need the project to produce paper-friendly outputs.

### Required figures/tables
At minimum:
1. success rate table across conditions
2. step count table across conditions
3. token usage table across conditions
4. paired comparison summary
5. one strong efficiency figure, ideally:
   - success vs token usage, or
   - Pareto-style comparison, or
   - per-task token delta distribution

### Nice-to-have
- failure taxonomy breakdown chart
- semantic search ablation table
- examples of benchmark strict-failure but functional-success cases

### Requirement
Prefer scripts that regenerate figures from result files.
Avoid manual spreadsheet-only workflows unless unavoidable.

---

## J. Reproducibility and Runability

I want this to be runnable by someone else later, including me.

### Required
Create or improve:
- a documented run script / commands for each condition
- config files or flags for:
  - browser vs MCP
  - semantic search on/off
  - model selection if relevant
  - benchmark split/sample selection
- result output directories with consistent naming
- basic README notes for running evals and regenerating analyses

### Important
Do not assume undocumented tribal knowledge.
If something is annoying to run, simplify it.

---

## 5. Specific Research Framing to Preserve

Please align implementation decisions with the following framing unless the repo forces a small adjustment.

### Core thesis framing
This project studies how **MCP-based tool execution changes the effectiveness-efficiency tradeoff** of Agent Skill Induction.

### What the paper is not
It is **not** mainly a claim that MCP massively improves raw success rate.
That may or may not happen.

### What the paper is
It is a claim that:
- MCP meaningfully reduces token usage
- MCP reduces step count
- semantic search may recover missing retrieval capability
- benchmark strictness may obscure functionally correct behavior
- therefore, evaluating tool-mediated web agents requires both strict and functionally aware analysis

This framing should guide implementation priorities.

---

## 6. Prioritized Checklist of Work

This is the actual working checklist to operationalize.

### Highest priority
- [ ] Audit repo and map current implementation to thesis needs
- [ ] Finalize clean runnable conditions for Browser + ASI, MCP + ASI, MCP + ASI + semantic search
- [ ] Implement semantic search for MCP tooling
- [ ] Standardize metrics/logging across conditions
- [ ] Run evals and generate comparable result files
- [ ] Add secondary evaluation support for functional correctness / near misses
- [ ] Produce task-level paired comparison outputs
- [ ] Generate thesis-ready tables/plots

### Medium priority
- [ ] Add failure taxonomy workflow
- [ ] Add task difficulty analysis
- [ ] Add statistical comparison scripts
- [ ] Improve reproducibility/documentation

### Lower priority
- [ ] Optional extra baselines if nearly free
- [ ] Wall-clock analysis if stable and low-noise
- [ ] More polished plotting / export tooling

---

## 7. Implementation Guidance / Constraints

### Preserve the spirit of the current project
Do not rewrite the whole system if smaller targeted changes get us there.

### Favor clarity over cleverness
This is for a thesis. Methods need to be explainable.

### Keep ablations easy
We need to cleanly compare:
- MCP search off
- MCP semantic search on

### Avoid scope creep
Do not introduce unrelated features or entirely new research questions.

### Be honest about results
If success rate remains tied, that is okay. The code and analysis should still support a strong efficiency-centered paper.

### Document assumptions
If you have to infer something from the repo or benchmark, write it down.

---

## 8. Concrete Deliverables I Expect Back

After reviewing the repo and implementing the needed pieces, I want the following.

### A. Repo audit note
A concise summary of:
- what exists
- what was missing
- what you changed
- what remains manual

### B. Code changes
Implemented and documented changes for:
- semantic search in MCP tooling
- logging/metrics standardization
- result generation
- secondary evaluation support
- analysis scripts / notebooks

### C. Run instructions
Concrete commands for running:
- Browser + ASI
- MCP + ASI
- MCP + ASI + semantic search

### D. Results artifacts
A clearly organized output structure containing:
- raw results
- aggregated metrics
- plots/tables
- annotation export files for secondary evaluation

### E. Suggested thesis wording
A short note describing:
- what claims are well-supported by the current evidence
- what claims would be overstated
- what limitations should be acknowledged

---

## 9. Questions You Should Answer After Inspecting the Repo

Once you’ve seen the actual implementation, I want you to answer these explicitly:

1. What exact components from ASI are already present and working?
2. What is the cleanest definition of the three core experimental conditions in this repo?
3. Where is MCP currently underperforming, and is semantic search the right fix?
4. What logging gaps currently prevent rigorous comparison?
5. What is the easiest defensible way to add the secondary correctness layer?
6. What result files and figures can be auto-generated now?
7. What is the minimum remaining work to get to thesis-ready evidence?

---

## 10. Success Criteria

I will consider this effort successful if, after your changes, I have:

1. a stable implementation of:
   - Browser + ASI
   - MCP + ASI
   - MCP + ASI + semantic search

2. consistent metrics showing:
   - success
   - steps
   - tokens

3. at least one rigorous analysis addition beyond raw benchmark score, ideally:
   - functional correctness / near-miss adjudication

4. enough plots/tables and methodological clarity to support a thesis chapter or paper draft without needing to reinvent the project framing

---

## 11. Final Instruction on Working Style

Please treat this as a **research engineering task**, not just a coding task.

That means:
- think in terms of thesis evidence
- prefer minimal, defensible changes
- preserve comparability between conditions
- optimize for clarity, reproducibility, and analysis quality
- flag risks early if some part of the current plan is weaker than it sounds

If something in this spec conflicts with the repo reality, adapt pragmatically — but explain why.
