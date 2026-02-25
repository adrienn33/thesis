# WebArena Vanilla Agent — Failure Analysis Report

**Tasks Analyzed:** 21, 22, 23, 24, 25, 47, 48, 49, 50, 51, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234  
**Failed Tasks:** 21, 22, 25, 48, 50, 51, 225, 226, 228, 229, 230 (11 failures)  
**Passed Tasks:** 23, 24, 47, 49, 227, 231, 232, 233, 234 (9 passes)  
**Pass Rate:** 45% (9/20)

---

## Per-Task Failure Analyses

### Task 21
- **Goal:** List reviewers who mention ear cups being small for the 6S Wireless Headphones product.
- **Expected Answer:** Joseph Brzezinski, Catso, Dibbins, Anglebert Dinkherhump, Michelle Davis
- **Agent's Answer:** Catso, Dibbins, Anglebert Dinkherhump, Michelle Davis
- **Trace:** Agent navigated both review pages, saw all reviews including Joseph Brzezinski's. Agent correctly excluded him because his review states "type fits are a bit small for my tired ancient eyes" — referring to font size in the written instructions, not ear cup size.
- **Failure Category:** Ground Truth Error
- **Root Cause:** The ground truth misclassifies Joseph Brzezinski as mentioning ear cups being small. His review is about font size. The agent's semantic interpretation was correct.
- **Ground Truth Assessment:** Questionable — Joseph Brzezinski's review does not mention ear cups.
- **Confidence:** 95%

---

### Task 22
- **Goal:** List reviewers who mention "under water photo" for the Fujifilm FinePix Z200fd camera.
- **Expected Answer:** N/A — no reviewers mention underwater photography.
- **Agent's Answer:** No final answer provided.
- **Trace:** Agent navigated to the Reviews tab, scrolled through page 1 and page 2 across 10 steps. Agent observed no underwater photo mentions but never stated a conclusion. Task hit step limit.
- **Failure Category:** Goal Completion — No Answer Delivered
- **Root Cause:** Agent correctly explored all reviews and found no underwater photo mentions, but lacked a task-closure mechanism to report the "N/A" finding before exhausting its step budget.
- **Ground Truth Assessment:** Correct — database confirms 17 reviews with zero underwater mentions.
- **Confidence:** 95%

---

### Task 25
- **Goal:** List reviewers who mention average print quality for the Epson WorkForce WF-3620 printer.
- **Expected Answer:** Goldfish, Roxanne Brandon Coffey
- **Agent's Answer:** No matches / unable to retrieve reviewer names.
- **Trace:** Agent clicked the Reviews tab correctly but review content failed to load in the accessibility tree. Agent attempted browser search (Ctrl+F) inefficiently. MCP tools were not available. Agent concluded no reviews existed.
- **Failure Category:** Environment / Dynamic Content Failure
- **Root Cause:** Dynamic review content did not render in the accessibility tree after tab click. With no fallback (MCP unavailable), the agent made a false-negative conclusion. Both Goldfish and Roxanne Brandon Coffey do exist in the database with qualifying reviews.
- **Ground Truth Assessment:** Correct — database confirms both reviewers mention average print quality.
- **Confidence:** 95%

---

### Task 48
- **Goal:** Count fulfilled orders over the past three days (6/9/2023–6/12/2023) and report total spend.
- **Expected Answer:** 0 orders, $0 total spend.
- **Agent's Answer:** No final answer provided.
- **Trace:** Agent navigated to My Account → View All Orders. Observed that all 37 orders were from May 2023 or earlier — none in the target range. Agent then entered a scroll loop (clicking date column, scrolling up and down repeatedly) and hit the step limit without concluding.
- **Failure Category:** Goal Completion — No Answer Delivered
- **Root Cause:** Agent correctly observed that no orders existed in the target date range but failed to recognize that absence of data is itself a valid answer. Continued searching instead of concluding with "0 orders, $0."
- **Ground Truth Assessment:** Correct — no orders exist in the 6/9–6/12/2023 window.
- **Confidence:** 90%

---

### Task 50
- **Goal:** Count fulfilled orders over the past year (6/12/2022–6/12/2023) and report total spend.
- **Expected Answer:** 24 orders, $6,560.69 total spend.
- **Agent's Answer:** 21 orders, $6,560.69 total spend.
- **Trace:** Agent navigated to My Orders, changed pagination to 50 per page, manually transcribed all 37 orders from the accessibility tree, filtered for "Complete" status and dates within range, and summed totals.
- **Failure Category:** Data Extraction — Incomplete Collection
- **Root Cause:** Manual transcription from the accessibility tree missed exactly 3 orders. The total amount is correct ($6,560.69), indicating the 3 missing orders were likely zero-value (refunds or cancelled-then-reprocessed). Manual transcription is inherently fragile compared to programmatic DOM parsing.
- **Ground Truth Assessment:** Correct — 24 complete orders exist in the target window.
- **Confidence:** 90%

---

### Task 51
- **Goal:** Count fulfilled orders over the past 6 months (12/12/2022–6/12/2023) and report total spend.
- **Expected Answer:** 12 orders, $1,603.69 total spend.
- **Agent's Answer:** 9 orders, $1,774.62 total spend.
- **Trace:** Agent navigated to My Orders, changed pagination to 50 items per page, then hardcoded a list of 37 orders (claimed to extract from DOM). Filtering logic was mathematically correct but applied to an incomplete dataset missing 3 qualifying orders.
- **Failure Category:** Data Extraction — Incomplete Collection
- **Root Cause:** Agent claimed to have extracted all 37 orders but screenshots show only ~10 were visible in the viewport. The hardcoded data was incomplete. No validation was performed against the "37 Item(s)" total shown in the UI. Both the count and the total amount are wrong.
- **Ground Truth Assessment:** Correct — 12 complete orders exist in the target window.
- **Confidence:** 90%

---

### Task 225
- **Goal:** Report what customers say about brushes from Sephora.
- **Expected Answer:** The Sephora brushes don't have reviews.
- **Agent's Answer:** No final answer provided.
- **Trace:** Agent searched "sephora brush", navigated to two Sephora brush product pages, clicked the Reviews tab on each, saw "Be the first to review this product" on both, then navigated back without concluding. Task hit step limit.
- **Failure Category:** Goal Completion — No Answer Delivered
- **Root Cause:** Agent correctly discovered that both major Sephora brush products had zero reviews but lacked a synthesis step to report this finding. Found the answer; never delivered it.
- **Ground Truth Assessment:** Correct — neither Sephora brush product has customer reviews.
- **Confidence:** 90%

---

### Task 226
- **Goal:** Find the price range for Amazon Basics products.
- **Expected Answer:** $5.49 – $375.19
- **Agent's Answer:** $5.49 – $216.32
- **Trace:** Agent searched "Amazon Basics", reached results showing "Items 1–12 of 7,332." Scrolled through the first 12 products, extracted their prices, and computed a range. Pagination links to pages 2–5+ were visible but not used.
- **Failure Category:** Data Extraction — Incomplete Collection (Pagination)
- **Root Cause:** Agent sampled only 12 of 7,332 products. Correctly found the minimum ($5.49) but the true maximum ($375.19) appears on a later page. Agent acknowledged the limitation in its reasoning but still provided a partial answer.
- **Ground Truth Assessment:** Correct — $375.19 maximum exists in the full product catalog.
- **Confidence:** 95%

---

### Task 228
- **Goal:** Find the price range for Sephora products.
- **Expected Answer:** $18.18 – $94.99
- **Agent's Answer:** $10.99 – $94.99
- **Trace:** Agent searched "Sephora", found 8 results, enumerated all products and prices. Correctly identified the Sephora Collection Ultra Shine Lip Gel at $18.18 (the true minimum) but also included two non-Sephora beauty accessories ($10.99 and $13.97) that appeared in search results. Agent noted these were "appears to be Sephora-related" yet still included them.
- **Failure Category:** Semantic / Brand Filtering Error
- **Root Cause:** Agent applied too-broad a filter for "Sephora products," including third-party items returned by the search algorithm. The $18.18 item was correctly identified but overridden by the non-Sephora $10.99 item.
- **Ground Truth Assessment:** Correct — genuine Sephora products range from $18.18 to $94.99.
- **Confidence:** 95%

---

### Task 229
- **Goal:** Find the price range for UGREEN products.
- **Expected Answer:** $6.99 – $38.99
- **Agent's Answer:** $9.99 – $38.99
- **Trace:** Agent searched "ugreen," correctly navigated to page 1 (12 items) and page 2 (9 items). In its step 3 notes, the agent observed several $6.99 items on page 1. However, in the final calculation (step 7), only page 2 prices were used — and duplicated — producing an 18-item array instead of combining both pages.
- **Failure Category:** Data Extraction — Cross-Page Integration Failure
- **Root Cause:** Agent did not maintain a persistent data structure across page navigations. Page 1 prices (including the $6.99 minimum) were observed but not retained for the final calculation. Page 2 data was duplicated instead.
- **Ground Truth Assessment:** Correct — $6.99 minimum exists on page 1 of UGREEN results.
- **Confidence:** 95%

---

### Task 230
- **Goal:** Find the price range for Perricone MD products.
- **Expected Answer:** $35 – $149
- **Agent's Answer:** No final answer provided.
- **Trace:** Agent searched "Perricone MD," applied Beauty & Personal Care filter, found 13 products including the $35 and $149 items. Agent stated the correct range ("$35.00 to $149.00") explicitly in its step 3 reasoning and again in steps 5 and 7. Continued exploring all 13 products to be thorough and hit the step limit without providing a final answer.
- **Failure Category:** Goal Completion — No Answer Delivered
- **Root Cause:** Agent identified the correct answer early but over-prioritized exhaustive data collection over task closure. The correct price range was stated in internal reasoning three times but never delivered as a final response.
- **Ground Truth Assessment:** Correct — $35 and $149 are the actual min and max Perricone MD prices.
- **Confidence:** 95%

---

## Failure Taxonomy

### Category 1: Goal Completion — No Answer Delivered
*Agent gathered correct data but never synthesized or reported it.*

| Task | Summary |
|------|---------|
| 22 | Found no underwater photo reviews; never stated "N/A" |
| 48 | Saw no orders in target date range; looped instead of concluding "0 orders" |
| 225 | Found no Sephora brush reviews; never reported the finding |
| 230 | Stated correct price range 3x in reasoning; never delivered the answer |

**Pattern:** Agent understands the task and reaches correct data but lacks a task-closure mechanism. Either "analysis paralysis" or step-limit exhaustion before answer delivery.

---

### Category 2: Data Extraction — Incomplete Collection
*Agent extracted partial data and computed wrong aggregates.*

| Task | Summary |
|------|---------|
| 50 | Manual transcription missed 3 zero-value orders; count wrong, total correct |
| 51 | Hardcoded order data was incomplete; both count and total wrong |
| 226 | Sampled 12 of 7,332 products; missed true max on later pages |
| 229 | Navigated both pages but dropped page 1 data in final calculation |

**Pattern:** Manual transcription and cross-page data accumulation are fragile. Agents lack persistent data structures and do not validate extracted counts against UI totals.

---

### Category 3: Semantic / Brand Filtering Error
*Agent included wrong items due to misinterpreting brand scope.*

| Task | Summary |
|------|---------|
| 228 | Included non-Sephora search results in price range; correct item seen but overridden |

**Pattern:** Search results include off-brand items. Agents need strict brand-name matching (e.g., product name must contain "Sephora" or "SEPHORA COLLECTION") rather than trusting search relevance alone.

---

### Category 4: Environment / Dynamic Content Failure
*Agent couldn't access content due to UI rendering limitations.*

| Task | Summary |
|------|---------|
| 25 | Review content failed to load in accessibility tree; MCP unavailable; false-negative conclusion |

**Pattern:** Dynamic content loading failures combined with absence of fallback data access (MCP) cause agents to make incorrect "no data found" conclusions.

---

### Category 5: Ground Truth Error
*The expected answer is questionable; agent reasoning was correct.*

| Task | Summary |
|------|---------|
| 21 | Joseph Brzezinski's review is about font size, not ear cups; agent correctly excluded him |

**Pattern:** Ambiguous natural language in reviews leads to annotation disagreement. Agent's semantic interpretation was defensible and likely correct.

---

## Summary Table

| Task | Category | Confidence |
|------|----------|-----------|
| 21 | Ground Truth Error | 95% |
| 22 | Goal Completion — No Answer Delivered | 95% |
| 25 | Environment / Dynamic Content Failure | 95% |
| 48 | Goal Completion — No Answer Delivered | 90% |
| 50 | Data Extraction — Incomplete Collection | 90% |
| 51 | Data Extraction — Incomplete Collection | 90% |
| 225 | Goal Completion — No Answer Delivered | 90% |
| 226 | Data Extraction — Incomplete Collection (Pagination) | 95% |
| 228 | Semantic / Brand Filtering Error | 95% |
| 229 | Data Extraction — Cross-Page Integration Failure | 95% |
| 230 | Goal Completion — No Answer Delivered | 95% |

---

## Systemic Issues and Recommendations

### 1. Goal Completion (4/11 failures — most common)
Agents find the answer but don't deliver it. This is the single largest failure mode.
- Implement explicit task-closure protocols (e.g., "once I have sufficient data, answer immediately")
- Add step-budget awareness so agents prioritize answering as the limit approaches
- Train on recognizing that "no results found" is a valid, complete answer

### 2. Data Extraction Fragility (4/11 failures)
Manual transcription and cross-page aggregation consistently lose data.
- Replace manual transcription with programmatic DOM/accessibility tree parsing
- Maintain persistent data structures across page navigations
- Validate extracted record counts against UI totals (e.g., "Items 1–12 of 7,332")

### 3. Brand / Scope Filtering (1/11 failures)
Search results include off-brand items that agents incorrectly include.
- Apply strict brand-name matching on product titles, not just search relevance
- Flag and exclude items with uncertain brand association

### 4. MCP Availability (1/11 failures)
When UI content fails to load, MCP database tools are the only reliable fallback.
- Ensure MCP tools are consistently available for tasks involving product reviews and orders
- Train agents to attempt MCP queries when UI content is inaccessible

### 5. Ground Truth Quality (1/11 failures)
At least one task has a questionable annotation.
- Review annotations for tasks involving subjective natural language interpretation
- Task 21's Joseph Brzezinski exclusion warrants re-annotation
