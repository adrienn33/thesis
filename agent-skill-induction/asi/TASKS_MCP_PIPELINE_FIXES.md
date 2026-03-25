# Task List: MCP Pipeline Reliability Fixes

**Spec:** `TECH_SPEC_MCP_PIPELINE_FIXES.md`
**Generated:** 2026-03-06
**Last Updated:** 2026-03-09 (Rev 2 — post smoke test round 2)

---

## Phase 1: Fix `.isdigit()` Type Coercion Bug (Spec §4.1)

- [x] **Task 1: Fix type coercion in `magento_review_data.py`**

  **Description:** Add `str()` coercion to the `product_id` parameter at the top of the `get_product_reviews` function, before the `.isdigit()` call on line 202. Also coerce the `product_id` parameter in `create_review` (line 292) for consistency.

  **Files to touch:** `mcp_servers/magento_review_data.py`

  **Definition of Done:** The function body begins with `product_id = str(product_id)`. Grep the file for bare `.isdigit()` calls — every one must be preceded by a `str()` coercion of that variable. No other logic is changed.

---

- [x] **Task 2: Fix type coercion in `magento_products.py`**

  **Description:** Add `str()` coercion to the `product_id` parameter at the top of `get_product_details` (line 376, before the `.isdigit()` call). Also coerce `limit` in `search_products` (used in `int(limit)` on line 278) and coerce `min_price`/`max_price` before `float()` calls on lines 269–273.

  **Files to touch:** `mcp_servers/magento_products.py`

  **Definition of Done:** `get_product_details` begins with `product_id = str(product_id)`. `search_products` coerces `limit` with `str()` before `int()` conversion. Grep for `.isdigit()` — all are on `str`-coerced variables. No other logic is changed.

---

- [x] **Task 3: Fix type coercion in `magento_checkout.py`**

  **Description:** Add `str()` coercion to: (a) `order_id` at the top of `get_order_details` (line 394, before `.isdigit()` and `len()` calls); (b) `product_id` at the top of `add_to_cart` (line 641, before `.isdigit()` call); (c) `item_id` in `update_cart_item` and `remove_from_cart` before `int()` casts; (d) `limit` and `qty` params in any function that casts them to `int()`/`float()`.

  **Files to touch:** `mcp_servers/magento_checkout.py`

  **Definition of Done:** Every function that receives an ID-type parameter (`order_id`, `product_id`, `item_id`) begins with `param = str(param)`. Every function that casts `limit` or `qty` to numeric type coerces with `str()` first if the value might be passed as `int`. Grep for `.isdigit()` — all on `str`-coerced variables. No other logic is changed.

---

- [x] **Task 4: Fix type coercion in `magento_wishlist.py`**

  **Description:** Add `str()` coercion to: (a) `product_id` at the top of `add_to_wishlist` (line 365, before `.isdigit()` call); (b) `wishlist_item_id` in `remove_from_wishlist` before the `int()` cast; (c) `qty` in `add_to_wishlist` before `float()` cast.

  **Files to touch:** `mcp_servers/magento_wishlist.py`

  **Definition of Done:** `add_to_wishlist` begins with `product_id = str(product_id)`. `remove_from_wishlist` coerces `wishlist_item_id = str(wishlist_item_id)`. Grep for `.isdigit()` — all on `str`-coerced variables. No other logic is changed.

---

- [x] **Task 5: Fix type coercion in `magento_account.py`**

  **Description:** Audit `magento_account.py` for any `.isdigit()` calls or bare `int()`/`float()` casts on parameters that could receive non-string types. The `get_account_info` and `update_account_info` functions take `customer_email` (always a string) and optional update fields. Coerce `customer_email = str(customer_email)` defensively in both functions. If `gender` is passed as an int, guard the `.lower()` call.

  **Files to touch:** `mcp_servers/magento_account.py`

  **Definition of Done:** Both `get_account_info` and `update_account_info` coerce `customer_email = str(customer_email)` at function entry. If `gender` param is used, it is coerced with `str()` before `.lower()`. No crashes when any parameter is passed as an `int`.

---

- [x] **Task 6: Copy fixed MCP servers to Docker container**

  **Description:** Copy all 5 fixed MCP server files from the host into the running `shopping` Docker container at `/tmp/`. This makes the fixes live for the next task execution.

  **Files to touch:** (shell commands only)

  **Definition of Done:** Run the following and verify exit code 0 for each:
  ```
  docker cp mcp_servers/magento_review_data.py shopping:/tmp/magento_review_data.py
  docker cp mcp_servers/magento_products.py shopping:/tmp/magento_products.py
  docker cp mcp_servers/magento_checkout.py shopping:/tmp/magento_checkout.py
  docker cp mcp_servers/magento_wishlist.py shopping:/tmp/magento_wishlist.py
  docker cp mcp_servers/magento_account.py shopping:/tmp/magento_account.py
  ```
  Then verify each file exists in the container: `docker exec shopping ls -la /tmp/magento_*.py` shows all 5 files with today's timestamp.

---

## Phase 2: Disable Cart Write-Tools (Spec §4.2)

- [x] **Task 7: Comment out cart write-tool registrations in `magento_checkout.py`**

  **Description:** In `MagentoCheckoutServer.__init__()`, comment out the three tool registrations for `add_to_cart`, `update_cart_item`, and `remove_from_cart`. Keep `get_cart` active (read-only). Do NOT delete the function implementations — only disable their registration. Add a comment explaining why they are disabled (browser session incompatibility).

  **Files to touch:** `mcp_servers/magento_checkout.py`

  **Definition of Done:** The `__init__` method contains exactly these active tool registrations: `list_orders`, `get_order_details`, `get_cart`. The lines for `add_to_cart`, `update_cart_item`, `remove_from_cart` are commented out with a brief rationale comment. The function bodies for all three remain intact (not deleted). The file has no syntax errors (`python3 -c "import ast; ast.parse(open('mcp_servers/magento_checkout.py').read())"` succeeds).

---

- [x] **Task 8: Copy updated checkout server to Docker container**

  **Description:** Copy the updated `magento_checkout.py` (with cart write-tools disabled) to the Docker container.

  **Files to touch:** (shell commands only)

  **Definition of Done:** `docker cp mcp_servers/magento_checkout.py shopping:/tmp/magento_checkout.py` exits with code 0. Verify the file in the container contains the commented-out tool registrations: `docker exec shopping grep "add_to_cart" /tmp/magento_checkout.py` shows the commented-out line.

---

## Phase 2b: Disable Wishlist Write-Tools (Spec §4.5) ← New

- [x] **Task 20: Comment out wishlist write-tool registrations in `magento_wishlist.py`**

  **Description:** In `MagentoWishlistServer.__init__()`, comment out the tool registrations for `add_to_wishlist` and `remove_from_wishlist`. Retain `get_wishlist` as an active read-only tool. Do NOT delete the function implementations — only disable the registrations. Add a comment with the same session isolation rationale used for the cart tools.

  **Files to touch:** `mcp_servers/magento_wishlist.py`

  **Definition of Done:** The `__init__` method contains exactly one active tool registration: `get_wishlist`. The lines for `add_to_wishlist` and `remove_from_wishlist` are commented out with a brief rationale comment. The function bodies for both remain intact (not deleted). The file has no syntax errors (`python3 -c "import ast; ast.parse(open('mcp_servers/magento_wishlist.py').read())"` succeeds).

---

- [x] **Task 21: Copy updated wishlist server to Docker container**

  **Description:** Copy the updated `magento_wishlist.py` (with write-tools disabled) to the Docker container.

  **Files to touch:** (shell commands only)

  **Definition of Done:** `docker cp mcp_servers/magento_wishlist.py shopping:/tmp/magento_wishlist.py` exits with code 0. Verify the disabled registrations are in the container: `docker exec shopping grep "add_to_wishlist" /tmp/magento_wishlist.py` shows only the commented-out line. The server still starts cleanly: `docker exec shopping python3 /tmp/magento_wishlist.py --help` (or equivalent smoke) exits without error.

---

## Phase 2c: Fix `qty` Alias in `get_order_details` Response (Spec §4.6) ← New

- [x] **Task 22: Add `qty` alias to item dict in `get_order_details`**

  **Description:** In `magento_checkout.py`, find the item serialization loop inside `get_order_details`. Each item dict currently has a `qty_ordered` key but no `qty` key. Add `'qty': float(item.qty_ordered or 0)` as an alias immediately after the `qty_ordered` line so both keys are present in every returned item.

  **Files to touch:** `mcp_servers/magento_checkout.py`

  **Definition of Done:** The item dict in the `get_order_details` serialization block contains both `'qty_ordered'` and `'qty'` keys with the same value. A quick test call against the container — `docker exec shopping python3 -c "import asyncio; ..."` — returns items with both keys. The file has no syntax errors. No other fields or logic are changed.

---

- [x] **Task 23: Copy updated checkout server to Docker container**

  **Description:** Copy `magento_checkout.py` (now containing the `qty` alias fix in addition to the cart tool disables from Task 8) to the Docker container.

  **Files to touch:** (shell commands only)

  **Definition of Done:** `docker cp mcp_servers/magento_checkout.py shopping:/tmp/magento_checkout.py` exits with code 0. Verify the alias is present: `docker exec shopping grep "'qty'" /tmp/magento_checkout.py` shows the alias line inside the item serialization block.

---

## Phase 3: Update Agent System Prompt (Spec §4.3 + §4.7)

- [x] **Task 9: Rewrite the MCP-enabled branch of `_get_skill_instructions()` in `agent.py`**

  **Description:** In `agent.py`, method `_get_skill_instructions()` (line 191), replace the entire MCP-enabled return string (the `if has_mcp:` branch) with the new task-type-aware prompt from Spec §4.3 and §4.7. The new prompt must include: (1) all three task-type categories (INFORMATION RETRIEVAL, NAVIGATION/"SHOW ME", STATE-CHANGE) with concrete examples; (2) explicit instruction that cart operations must use browser actions and that cart MCP tools are disabled; (3) explicit instruction that wishlist write tools are disabled — agent must use browser to add to wishlist; (4) instruction that forms must be filled AND submitted via browser (not just filled); (5) instruction that navigation tasks must not call `send_msg_to_user` — just leave the browser on the correct page. Retain the existing `{available_skills}` interpolation. Retain the "Only use ASI skills that are listed above" guard. Retain the semantic review search instruction.

  **Files to touch:** `agent.py`

  **Definition of Done:** The `if has_mcp:` branch returns a string containing all three task-type sections (INFORMATION RETRIEVAL, NAVIGATION, STATE-CHANGE). The string does NOT contain "STRONGLY PREFER using these skills over low-level browser actions" (the old blanket instruction). The `{available_skills}` variable is still interpolated. The semantic review search instruction is still present. The file has no syntax errors (`python3 -c "import ast; ast.parse(open('agent.py').read())"` succeeds).

---

- [x] **Task 10: Update the non-MCP branch of `_get_skill_instructions()` in `agent.py`**

  **Description:** In `agent.py`, update the `else:` branch (lines 224–229, the Vanilla+ASI path) to include parallel task-type awareness. Since there are no MCP tools in this branch, the rules are simpler: (1) ASI skills are preferred for information retrieval; (2) browser actions are required for navigation and state-change tasks; (3) ASI skills can assist but cannot replace browser actions for nav/state tasks. Retain the `{available_skills}` interpolation and semantic review search instruction.

  **Files to touch:** `agent.py`

  **Definition of Done:** The `else:` branch returns a string that mentions task-type awareness for navigation and state-change tasks. The string does NOT contain "STRONGLY PREFER using these ASI skills over low-level browser actions" as a blanket rule. The `{available_skills}` variable is still interpolated. The file has no syntax errors.

---

- [x] **Task 11: Verify the agent prompt renders correctly end-to-end**

  **Description:** Read `agent.py` in full. Verify that the prompt string in the `get_action` method (lines 382–425, the "Action Space" section) correctly interpolates `self._get_skill_instructions()`. Confirm that the existing CRITICAL rules about data processing, code execution, and `send_msg_to_user` are unchanged. Confirm no duplicate or conflicting instructions exist between the new task-type block and the existing rules.

  **Files to touch:** `agent.py` (read-only verification)

  **Definition of Done:** The agent prompt contains exactly one call to `self._get_skill_instructions()`. There are no duplicate TASK-TYPE sections. The three existing CRITICAL blocks (data processing, complete code, report results) are unchanged. No contradictory instructions (e.g., one block saying "always use MCP" and another saying "use browser for cart").

---

## Phase 4: Update Documentation (Spec §4.4)

- [x] **Task 12: Add Checkout Server documentation to `CLAUDE.md`**

  **Description:** In the `## MCP Servers` section of `CLAUDE.md`, add a new subsection documenting the Checkout Server (`mcp_servers/magento_checkout.py`). List the 3 active tools (`list_orders`, `get_order_details`, `get_cart`) with brief descriptions. Note that `add_to_cart`, `update_cart_item`, and `remove_from_cart` are disabled due to browser session incompatibility, with a reference to the tech spec.

  **Files to touch:** `CLAUDE.md`

  **Definition of Done:** `CLAUDE.md` contains a "Checkout Server" subsection listing all 3 active tools. The disabled cart write-tools are mentioned with rationale. No existing documentation sections are removed or corrupted.

---

- [x] **Task 13: Add Wishlist Server documentation to `CLAUDE.md`**

  **Description:** Add a subsection documenting the Wishlist Server (`mcp_servers/magento_wishlist.py`). List all 3 tools (`get_wishlist`, `add_to_wishlist`, `remove_from_wishlist`) with brief descriptions.

  **Files to touch:** `CLAUDE.md`

  **Definition of Done:** `CLAUDE.md` contains a "Wishlist Server" subsection listing all 3 tools with descriptions.

---

- [x] **Task 14: Add Account Server documentation to `CLAUDE.md`**

  **Description:** Add a subsection documenting the Account Server (`mcp_servers/magento_account.py`). List both tools (`get_account_info`, `update_account_info`) with brief descriptions.

  **Files to touch:** `CLAUDE.md`

  **Definition of Done:** `CLAUDE.md` contains an "Account Server" subsection listing both tools with descriptions.

---

- [x] **Task 15: Update Phase Status and tool counts in `CLAUDE.md`**

  **Description:** Update the "Phase 1 Status" section at the bottom of `CLAUDE.md` to reflect 5 active MCP servers and the correct active tool count (14 tools: 2 review + 3 product + 3 checkout + 3 wishlist + 2 account, with 1 review tool disabled/commented). Correct the count to match reality. Remove or update any outdated statements that only reference 2 servers.

  **Files to touch:** `CLAUDE.md`

  **Definition of Done:** The Phase status section lists all 5 servers by name. The total active tool count is accurate (count the actual registered tools across all 5 server files). No references to "2 servers" remain unless explicitly noting history.

---

## Phase 5: Smoke Test — Round 2

- [x] **Task 16: Verify wishlist tasks now use browser path (tasks 511, 465)**

  **Description:** Re-run tasks 511 and 465 using `run_online.py --experiment mcp --website shopping --task_ids 511,465`. The agent should NOT call `magento_wishlist_server_add_to_wishlist` (tool no longer available). It should navigate to the product page and click "Add to Wish List" via browser.

  **Files to touch:** (shell commands and result inspection only)

  **Definition of Done:** For both tasks: `experiment.log` does NOT contain `magento_wishlist_server_add_to_wishlist`. The log DOES contain `click(` browser action targeting a wishlist button. The `research_metrics.json` `cum_reward` is non-zero OR the agent visibly attempted the browser wishlist flow (even if it fails due to other reasons).

---

- [x] **Task 17: Verify `qty` alias fixes order item computation (task 142)**

  **Description:** Re-run task 142 (`How much I spent on hair care Jan 2023`) using `run_online.py --experiment mcp --website shopping --task_ids 142`. Inspect the experiment log — the REPL should NOT hit the `KeyError: 'qty'` fallback. The agent should successfully iterate over items and compute a total.

  **Files to touch:** (shell commands and result inspection only)

  **Definition of Done:** `results/webarena.142/experiment.log` does NOT contain `REPL-style execution failed, falling back to exec: 'qty'`. The log DOES show a `send_msg_to_user` call with a dollar amount. The task may or may not pass (answer quality is a separate concern), but the crash must be gone.

---

- [x] **Task 18: Verify navigation tasks leave browser on page (tasks 298, 269)**

  **Description:** Re-run tasks 298 and 269 using `run_online.py --experiment mcp --website shopping --task_ids 298,269`. Task 298 expects the browser to be on the order detail URL (`/sales/order/view/order_id/180/`). Task 269 expects the browser on the women shoes filtered URL. The agent should navigate to the correct page and stop — it must NOT call `send_msg_to_user` as its primary completion action.

  **Files to touch:** (shell commands and result inspection only)

  **Definition of Done:** For task 298: `experiment.log` contains a `goto(` or `click(` action targeting an order detail URL and does NOT end with `send_msg_to_user` as the sole action. For task 269: the log shows navigation to the shoes category with a price filter applied. Both tasks' `cum_raw_reward` should be non-zero if the correct page is reached.

---

- [x] **Task 19: Verify contact form is submitted (task 653)**

  **Description:** Re-run task 653 (`Fill the contact us form for a refund`) using `run_online.py --experiment mcp --website shopping --task_ids 653`. The agent should: (1) call `get_order_details("000000180")` to retrieve the correct SKU `B087QJN9W1`, (2) navigate to `/contact/`, (3) fill name, email, phone, and message including the SKU and order number, (4) **click the Submit button**.

  **Files to touch:** (shell commands and result inspection only)

  **Definition of Done:** `experiment.log` contains a `click(` action after the `fill(` actions (the submit button click). The log does NOT end with `send_msg_to_user` as a substitute for submitting. The `program_html` evaluator check on the comment textarea (looking for `B087QJN9W1`, `000000180`, `refund`, and `it broke after three days of use`) should pass or get closer to passing.

---

---

## Phase 6: Fix Evaluator URL Scheme Bug (Spec §4.8) ← New (Rev 2)

- [x] **Task 25: Add scheme normalization to `clean_url` in `evaluators.py`**

  **Description:** In the `clean_url` inner function of `URLEvaluator.__call__`, add a check: if the URL does not contain `://`, prepend `http://`. This ensures `urllib.parse.urlparse` correctly identifies `localhost:7770` as the netloc (not the scheme) for all 52 `url_match` reference URLs that omit the scheme. The fix must come before the existing `url.rstrip("/")` call.

  **CRITICAL:** The fix must be applied to **both** copies of this file:
  1. `webarena/evaluation_harness/evaluators.py` (repo copy)
  2. `venv/lib/python3.12/site-packages/webarena/evaluation_harness/evaluators.py` (installed copy — **this is the one Python actually loads at runtime**)

  After patching both, delete `__pycache__/evaluators.cpython-*.pyc` in both locations to prevent stale bytecode.

  **Files to touch:** `webarena/evaluation_harness/evaluators.py`, `venv/lib/python3.12/site-packages/webarena/evaluation_harness/evaluators.py`

  **Definition of Done:** Both copies of `clean_url` contain scheme normalization AND double-slash normalization. No stale `.pyc` cache files remain. The function body is:
  ```python
  def clean_url(url: str) -> str:
      url = str(url)
      if "://" not in url:
          url = "http://" + url
      url = url.rstrip("/")
      scheme_end = url.find("://") + 3
      url = url[:scheme_end] + url[scheme_end:].replace("//", "/")
      return url
  ```
  The file has no syntax errors (`python3 -c "import ast; ast.parse(open('webarena/evaluation_harness/evaluators.py').read())"` succeeds). A quick unit test: `clean_url("localhost:7770/sales/order/view/order_id/180")` returns `"http://localhost:7770/sales/order/view/order_id/180"`. `clean_url("http://localhost:7770/sales/order/view/order_id/180/")` still returns `"http://localhost:7770/sales/order/view/order_id/180"` (trailing slash stripped, no double scheme).

---

## Phase 7: Fix Reference URL Data Quality (Spec §4.9) ← New (Rev 2)

- [x] **Task 26: Remove leading `%20` from `q=` param in tasks 327 and 328 config files**

  **Description:** In the following config files, find the `reference_url` field and change `q=%20iphone%2012%20phone%20case` to `q=iphone+12+phone+case` (remove the leading `%20` space and normalize space encoding to `+`).

  **CRITICAL:** BrowserGym loads task configs from `venv/lib/python3.12/site-packages/webarena/test.raw.json`, NOT from local `config_files/`. Both must be fixed:

  Local config files:
  - `config_files/327.json`
  - `config_files/327-mcp-container.json`
  - `config_files/328.json`
  - `config_files/328-mcp-container.json`

  Webarena package config (used by BrowserGym evaluator at runtime):
  - `venv/lib/python3.12/site-packages/webarena/test.raw.json` (tasks 327 and 328)

  **Files to touch:** `config_files/327.json`, `config_files/327-mcp-container.json`, `config_files/328.json`, `config_files/328-mcp-container.json`, `venv/lib/python3.12/site-packages/webarena/test.raw.json`

  **Definition of Done:** All local config files and the webarena package `test.raw.json` have `q=iphone+12+phone+case` (no leading `%20`). Verify the package config with: `venv/bin/python3 -c "import importlib.resources, json, webarena, urllib.parse; configs=json.loads(importlib.resources.files(webarena).joinpath('test.raw.json').read_text()); [print(c['task_id'], urllib.parse.parse_qs(urllib.parse.urlparse('http://x' + c['eval']['reference_url'].replace('__SHOPPING__','')).query).get('q')) for c in configs if c['task_id'] in [327,328]]"` — all `q` values should be `['iphone 12 phone case']` with no leading space.

---

## Phase 8: Smoke Test — Round 3 (Spec §4.8 + §4.9 Validation) ← New (Rev 2)

- [ ] **Task 27: Verify url_match evaluator fix on tasks 298, 269, 327**

  **Description:** Re-run tasks 298, 269, and 327 using `run_online.py --experiment mcp --website shopping --task_ids 298,269,327`. These three tasks were confirmed in Smoke Test Round 2 to have correct agent navigation but scored `reward=0.0` due to the evaluator scheme-parsing bug (298, 269) and the leading `%20` data quality issue (327). After the §4.8 and §4.9 fixes, all three should now pass.

  **Files to touch:** (shell commands and result inspection only)

  **Definition of Done:** All three tasks show `reward=1.0` (or at minimum `cum_reward > 0`) in their `research_metrics.json`. If any task still fails, inspect the evaluator log to determine if the failure is a new agent reasoning issue vs. a remaining evaluator bug.

---

- [x] **Task 24: Document task 327 as a known evaluator limitation** ← SUPERSEDED by Tasks 25-27

  **Description:** Originally documented task 327 as an out-of-scope evaluator edge case. Smoke Test Round 2 revealed the root cause is a combination of the schemeless URL bug (§4.8, affecting all 52 url_match tasks) and a leading `%20` typo (§4.9, specific to tasks 327/328). Both are now fixable. This task is superseded by Tasks 25–27.

  **Files to touch:** N/A

  **Definition of Done:** Tasks 25–27 are completed. This task is retired.
