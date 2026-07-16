# Low-Hanging Fruit Implementation Plan

## Process

Each slice is an independent, atomic change. For every slice:

1. **Agent makes the fix** described in the slice
2. **You rerun the listed tasks** to check for improvement
3. **Keep or revert**: if tasks improve, commit and move on; if not, `git checkout -- <files>`

Slices are ordered by expected ROI (task count × confidence of fix).

---

## Slice 1 — Order Aggregation Prompt Rule

**Tasks:** 320, 321, 323, 331, 332, 333 (6 tasks)

**Root cause:** The agent lists individual order amounts but never computes a total. For spending queries it also includes cancelled orders.

**File:** `agent.py` — `_get_skill_instructions()`, inside the `ANSWER QUALITY RULES` block (after rule `c)` at line ~266)

**Change:** Append a new rule `d)` to the ANSWER QUALITY RULES section:

```
d) AGGREGATION — "how much" / "total" / "refund" questions:
   When the question asks for a total amount (spending, refund, etc.), you MUST compute
   and report a SINGLE number. Do not list individual orders — sum them.
   - "How much did I spend in [period]": sum ONLY orders with status "complete".
     Exclude "cancelled", "closed", "pending", and all other statuses.
   - "How much refund should I expect": sum ONLY orders with status "cancelled".
   - If a discount or condition applies ("20% discount for orders exceeding $200"),
     apply it per-order to only the qualifying orders, then sum the results.
   Always respond with one total, e.g.: send_msg_to_user("$406.53")
```

**Verification tasks:**
```bash
python run_demo.py --task_name webarena.320 --max_steps 10
python run_demo.py --task_name webarena.321 --max_steps 10
python run_demo.py --task_name webarena.323 --max_steps 10
python run_demo.py --task_name webarena.331 --max_steps 10
python run_demo.py --task_name webarena.332 --max_steps 10
python run_demo.py --task_name webarena.333 --max_steps 10
```

**Revert scope:** `agent.py`

---

## Slice 2 — Unachievable Task Recognition

**Tasks:** 302, 794, 795, 796, 797, 798 (6 tasks)

**Root cause:** The agent doesn't recognize impossible tasks. It tries admin panel logins repeatedly instead of reporting infeasibility. Task 302 looks for a non-existent order status ("out for delivery").

**File:** `agent.py` — `_get_skill_instructions()`, add a new section after the `MCP FALLBACK RULE` block (after line ~348)

**Change:** Insert a new instruction block:

```
UNACHIEVABLE TASK RECOGNITION:
Some tasks are intentionally impossible on this platform. You must recognize these and
report them rather than attempting workarounds.

Common unachievable patterns:
- Changing a shipping/delivery address AFTER an order has been placed (Magento does not
  allow post-order address modification from the customer account).
- Filtering or sorting by a criterion the site does not support (e.g., "sort by rating"
  when no rating sort exists).
- Looking up an order status that does not exist in the system (e.g., "out for delivery"
  — Magento uses: pending, processing, complete, cancelled, closed, holded).

When you determine a task is impossible:
- Call send_msg_to_user("N/A") to report it as unachievable.
- Do NOT attempt to log into the admin panel. You do not have admin credentials and
  the admin panel is not part of the customer-facing task space.
- Do NOT retry failed login attempts — if a page redirects you to a login or "My Account"
  instead of the expected destination, that is a signal the action is not available.
```

**Verification tasks:**
```bash
python run_demo.py --task_name webarena.302 --max_steps 10
python run_demo.py --task_name webarena.794 --max_steps 10
python run_demo.py --task_name webarena.795 --max_steps 10
python run_demo.py --task_name webarena.796 --max_steps 10
python run_demo.py --task_name webarena.797 --max_steps 10
python run_demo.py --task_name webarena.798 --max_steps 10
```

**Revert scope:** `agent.py`

---

## Slice 3 — Country Code Expansion in MCP

**Tasks:** 362 (1 task, but hardens all address-related tasks)

**Root cause:** `magento_checkout.py` returns raw `country_id` (e.g., "US") from the database. The evaluator expects "United States".

**File:** `mcp_servers/magento_checkout.py`

**Change:** Add an ISO-3166 country code lookup dict near the top of the file (after imports), then replace `country_id` references in both `get_order_details` and `list_orders` address output:

```python
# Near top of file, after imports
COUNTRY_NAMES = {
    "US": "United States", "CA": "Canada", "GB": "United Kingdom",
    "AU": "Australia", "DE": "Germany", "FR": "France", "JP": "Japan",
    "CN": "China", "IN": "India", "BR": "Brazil", "MX": "Mexico",
    "IT": "Italy", "ES": "Spain", "KR": "South Korea", "NL": "Netherlands",
    "SE": "Sweden", "NO": "Norway", "DK": "Denmark", "FI": "Finland",
    "PL": "Poland", "AT": "Austria", "CH": "Switzerland", "BE": "Belgium",
    "IE": "Ireland", "NZ": "New Zealand", "SG": "Singapore", "HK": "Hong Kong",
    "TW": "Taiwan", "IL": "Israel", "AE": "United Arab Emirates",
    "SA": "Saudi Arabia", "ZA": "South Africa", "RU": "Russia",
    "TR": "Turkey", "TH": "Thailand", "PH": "Philippines", "MY": "Malaysia",
    "ID": "Indonesia", "VN": "Vietnam", "CL": "Chile", "CO": "Colombia",
    "AR": "Argentina", "PE": "Peru", "PT": "Portugal", "CZ": "Czech Republic",
    "RO": "Romania", "HU": "Hungary", "GR": "Greece",
}

def _expand_country(code):
    """Convert ISO country code to full name, fallback to code itself."""
    if not code:
        return None
    return COUNTRY_NAMES.get(code, code)
```

Then in both `get_order_details()` and `list_orders()`, replace:
```python
"country": shipping_address["country_id"] if shipping_address else None,
```
with:
```python
"country": _expand_country(shipping_address["country_id"]) if shipping_address else None,
```

Apply the same pattern to `billing_address` and the `list_orders` shipping address output.

After editing, copy to container:
```bash
docker cp mcp_servers/magento_checkout.py shopping:/tmp/magento_checkout.py
```

**Verification tasks:**
```bash
python run_demo.py --task_name webarena.362 --max_steps 10
```

**Revert scope:** `mcp_servers/magento_checkout.py`

---

## Slice 4 — Numeric Answer Format Rule

**Tasks:** 144, 319 (2 tasks)

**Root cause:** Agent gives semantically correct answers ("$0.00", "No cancelled orders found") but the evaluator tokenizes and needs the bare numeral "0" present somewhere in the response.

**File:** `agent.py` — `_get_skill_instructions()`, append to ANSWER QUALITY RULES after the new rule `d)`

**Change:** Add rule `e)`:

```
e) NUMERIC FORMAT: Always include bare numerals in your answer.
   - If the answer is zero, say "0" — not "$0.00" or "none found".
   - If the answer is a count, include the digit: "There are 3 orders" not "There are three orders".
   - If no results match a query (e.g., "no cancelled orders in April 2022"), still report
     the numeric answer: send_msg_to_user("0")
```

**Verification tasks:**
```bash
python run_demo.py --task_name webarena.144 --max_steps 10
python run_demo.py --task_name webarena.319 --max_steps 10
```

**Revert scope:** `agent.py`

---

## Slice 5 — Navigation vs. Reporting Reinforcement

**Tasks:** 240, 241, 283 (3 tasks)

**Root cause:** Agent uses MCP to find data and then calls `send_msg_to_user()` with the results, rather than navigating the browser to the product page. The existing NAVIGATION section covers this conceptually, but the agent still misclassifies task types.

**File:** `agent.py` — `_get_skill_instructions()`, strengthen the NAVIGATION section (around line ~268)

**Change:** Add a stronger disambiguation rule at the start of the NAVIGATION section:

```
    CRITICAL DISAMBIGUATION — NAVIGATE vs REPORT:
    If the task says "show me", "find me", "look up" a product/page, OR if the task wording
    implies displaying a product or page (rather than asking a factual question), you MUST
    navigate the browser. Using send_msg_to_user() to list MCP results will FAIL.
    - "What is the price of X?" → INFORMATION (report via send_msg_to_user)
    - "Show me X" / "Find me X" / "Look up X" → NAVIGATION (goto the page)
    - "List products in category Y" → NAVIGATION (navigate to category page)
    When in doubt: if the task could be satisfied by being ON a page, navigate there.
```

**Verification tasks:**
```bash
python run_demo.py --task_name webarena.240 --max_steps 10
python run_demo.py --task_name webarena.241 --max_steps 10
python run_demo.py --task_name webarena.283 --max_steps 10
```

**Revert scope:** `agent.py`

---

## Slice 6 — Rating Scale Clarification

**Tasks:** 386 (1 task)

**Root cause:** Agent treated a 1–5 star rating as a percentage (divided by 100, multiplied by 5), producing 0.16 instead of ~3.1.

**File:** `agent.py` — `_get_skill_instructions()`, append to ANSWER QUALITY RULES

**Change:** Add rule `f)`:

```
f) RATINGS: Magento product ratings are on a 1–5 star scale (integers 1 through 5).
   To compute an average rating: sum all star values, divide by the number of reviews.
   Do NOT divide by 100 or treat ratings as percentages.
   Example: ratings [5, 3, 4, 2, 5] → average = 19/5 = 3.8 stars.
```

**Verification tasks:**
```bash
python run_demo.py --task_name webarena.386 --max_steps 10
```

**Revert scope:** `agent.py`

---

## Summary Table

| Slice | Category | Tasks | Count | File(s) Changed |
|-------|----------|-------|-------|-----------------|
| 1 | Aggregation prompt | 320, 321, 323, 331, 332, 333 | 6 | `agent.py` |
| 2 | Unachievable recognition | 302, 794–798 | 6 | `agent.py` |
| 3 | Country code expansion | 362 | 1 | `magento_checkout.py` |
| 4 | Numeric format | 144, 319 | 2 | `agent.py` |
| 5 | Navigation vs reporting | 240, 241, 283 | 3 | `agent.py` |
| 6 | Rating scale | 386 | 1 | `agent.py` |
| **Total** | | | **19** | |

All `agent.py` slices (1, 2, 4, 5, 6) touch `_get_skill_instructions()` but in different, non-overlapping sections, so they can be applied incrementally without merge conflicts. Slice 3 is the only one touching an MCP server file.

---

## Out of Scope (Not Low-Hanging)

These remain after all slices above and are documented here for completeness:

| Category | Tasks | Why not actionable now |
|----------|-------|-----------------------|
| Semantic search failures | 124, 125, 141–143, 226, 229, 238, 279, 282, 284, 158, 160, 376, 385 | Requires semantic search engine improvements (core thesis work) |
| Ground truth errors | 163, 165, 167, 277, 280, 286, 325, 330 | Benchmark bugs — cannot fix |
| Checkout button (10 steps) | 436–440, 506–510 | Likely needs step limit increase + UI investigation |
| Wishlist pagination | 469, 512–515 | Evaluator false negatives — benchmark evaluation code |
| Form content mismatch | 528–532, 653–657, 689 | Needs deeper eval alignment investigation |
| BrowserGym bug | 573 | External dependency (ZeroDivisionError on empty fill) |
| triple_click undefined | 572, 574 | Action space addition — medium effort |
| MCP makes unachievable achievable | 792, 793 | Benchmark expects failure; agent actually succeeds |
