# Elasticsearch Integration for MCP Product Search

## Context & Goals

### Problem
The MCP `search_products()` tool uses SQL `LIKE '%keyword%'` for text matching, while the browser-based agent benefits from Magento's built-in Elasticsearch integration. This creates an unfair disadvantage for MCP conditions in the WebArena benchmark:

- **Under-matching**: SQL LIKE misses products where terms don't appear as exact substrings (e.g., "Nintendo Switch game card case" returns 0 results; "Nike slide slipper" returns 0; "PS4 Accessories" returns 0 because the category is "PlayStation 4")
- **Over-matching**: SQL LIKE matches unrelated substring hits (e.g., "UGREEN" matches "Beaugreen" products)
- **No relevance ranking**: SQL returns results in arbitrary order; ES ranks by TF-IDF relevance score

### Impact on Thesis
The `thesis_taxonomy.csv` identifies 16 of 94 analyzed failures (17%) as semantic-search-related. Categories include "MCP Search Under-matching" and "MCP Search Over-matching". Fixing these could recover ~8-10 tasks on the 187-task benchmark.

### Goal
Replace SQL LIKE text matching in `search_products()` with Elasticsearch queries, using the same ES instance and index that the browser-based Magento storefront uses. This is a **full drop-in replacement** — no toggle, no fallback to SQL for text search.

### Non-Goals
- `list_categories()` — structural query returning all categories; no text search to replace
- `get_product_details()` — exact ID/SKU lookup; no text search
- Other MCP servers (review, checkout, wishlist, account) — all use structured lookups only
- Installing new Python packages in the Docker container (must use `urllib.request`)

---

## Infrastructure Verified

| Component | Status | Details |
|-----------|--------|---------|
| ES running in container | Confirmed | `localhost:9200` inside `shopping` container |
| ES version | 7.x | `docker exec shopping curl -s localhost:9200` |
| Index name | `magento2_product_1_v4` | 104K documents, 689 fields |
| HTTP client in container | `urllib.request` only | `aiohttp`, `requests`, `httpx` all unavailable |
| `aiomysql` in container | Available | Already used by all MCP servers |

### ES Field Mapping (relevant fields)

| ES Field | Type | Maps To | Notes |
|----------|------|---------|-------|
| `_id` | — | `entity_id` | Document ID = Magento product entity_id |
| `name` | text (+ keyword) | `name` | Has `copy_to: _search`, tokenized |
| `sku` | text (custom `sku` analyzer) | `sku` | Has `copy_to: _search` |
| `description` | text | `description` | Has `copy_to: _search`, full product description |
| `short_description` | text | — | Also `copy_to: _search` |
| `price_0_1` | double (stored) | `price` | Store 1, customer group 0 |
| `category_ids` | integer array | category filter | e.g., `[2, 11, 53, 194]` |
| `is_out_of_stock` | integer | `is_in_stock` (inverted) | 1 = out of stock, 0 = in stock |
| `url_key` | text | URL construction | Slug, e.g., `"sennheiser-hd-202"` → `http://localhost:7770/sennheiser-hd-202.html` |
| `status` | integer | product status | 1 = enabled |
| `visibility` | integer | product visibility | 4 = catalog+search |

### Fields NOT in ES (require SQL enrichment)

| Field | Source | Needed? |
|-------|--------|---------|
| `qty` (exact inventory quantity) | `cataloginventory_stock_item` | Yes — some tasks check exact stock count |
| `url_rewrite.request_path` | `url_rewrite` table | Preferred for canonical URLs, but `url_key` + `.html` works as fallback |

---

## Architecture Decision: Hybrid ES + SQL

**Approach**: Use ES for search/filtering, SQL for data enrichment.

1. **ES query** handles text matching (name, sku, description) + structured filters (category_ids, price range)
2. **ES returns** entity_ids ranked by relevance score
3. **SQL query** fetches full product details for matched entity_ids (`WHERE entity_id IN (...)`)
4. **Results** returned in ES relevance order with all original fields preserved

**Why hybrid instead of pure ES?**
- ES lacks `qty` (exact inventory quantity) — needed by some tasks
- `url_key` + `.html` works for most URLs but `url_rewrite` is more reliable for edge cases (category-prefixed URLs, custom rewrites)
- SQL enrichment is trivially fast on primary key lookups (`IN` clause)
- Return format stays **identical** — no downstream changes needed

**Why not pure SQL with ES entity_ids?**
- Also viable, but we'd lose the ability to use ES for price/category filtering
- Hybrid gives us ES relevance ranking AND full data fidelity

---

## Implementation Plan

### Phase 1: Add ES Client Helper

**File**: `mcp_servers/magento_products.py`

**What**: Add an async method to `MagentoProductServer` that executes ES queries via `urllib.request` from inside the Docker container.

- [ ] Add `_es_search(self, body: dict, size: int = 500) -> dict` method
  - Uses `urllib.request.urlopen` to POST to `http://localhost:9200/magento2_product_1_v4/_search`
  - Sends JSON body, returns parsed JSON response
  - Handles connection errors gracefully (returns empty hits)

**Instructional snippet**:
```python
import urllib.request
import urllib.error

async def _es_search(self, body: dict, size: int = 500) -> dict:
    """Execute an Elasticsearch query against the Magento product index."""
    url = "http://localhost:9200/magento2_product_1_v4/_search"
    payload = json.dumps({**body, "size": size}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
        logger.error(f"Elasticsearch query failed: {e}")
        return {"hits": {"hits": [], "total": {"value": 0}}}
```

**Note**: `urllib.request.urlopen` is synchronous, but since ES queries return in <50ms and the MCP server is single-request-at-a-time, this is acceptable. Wrapping in `asyncio.to_thread()` is optional but not required for correctness.

### Phase 2: Build ES Query from Search Parameters

**File**: `mcp_servers/magento_products.py`

**What**: Add a method that constructs an ES `bool` query from the `search_products` parameters.

- [ ] Add `_build_es_query(self, sku, name, description, category, min_price, max_price) -> dict` method
  - Text params (name, description) → `must` clauses with `multi_match` + `fuzziness: "AUTO"`
  - SKU param → `must` clause with `match` on `sku` field (uses custom SKU analyzer)
  - Category param (numeric) → `filter` clause with `terms` on `category_ids`
  - Category param (text) → resolve to category ID(s) via SQL first, then `terms` filter
  - Price range → `filter` clause with `range` on `price_0_1`
  - Always filter: `status: 1` (enabled products only)

**Instructional snippet**:
```python
async def _build_es_query(self, sku=None, name=None, description=None,
                           category=None, min_price=None, max_price=None) -> dict:
    """Build an Elasticsearch bool query from search parameters."""
    must = []
    filter_clauses = [{"term": {"status": 1}}]

    # Text search: name and/or description
    if name and description:
        must.append({
            "multi_match": {
                "query": f"{name} {description}",
                "fields": ["name^3", "description", "short_description"],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        })
    elif name:
        must.append({
            "multi_match": {
                "query": name,
                "fields": ["name^3", "short_description"],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        })
    elif description:
        must.append({
            "multi_match": {
                "query": description,
                "fields": ["description", "short_description", "name"],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        })

    # SKU search
    if sku:
        must.append({"match": {"sku": str(sku)}})

    # Category filter
    if category:
        category = str(category)
        if category.isdigit():
            filter_clauses.append({"term": {"category_ids": int(category)}})
        else:
            # Resolve category name to ID(s) via SQL
            cat_ids = await self._resolve_category_ids(category)
            if cat_ids:
                filter_clauses.append({"terms": {"category_ids": cat_ids}})

    # Price range filter
    price_range = {}
    if min_price:
        price_range["gte"] = float(str(min_price))
    if max_price:
        price_range["lte"] = float(str(max_price))
    if price_range:
        filter_clauses.append({"range": {"price_0_1": price_range}})

    # If no text search terms provided, match all (filtered)
    if not must:
        return {"query": {"bool": {"filter": filter_clauses}}}

    return {
        "query": {
            "bool": {
                "must": must,
                "filter": filter_clauses
            }
        }
    }
```

### Phase 3: Add Category Name Resolution Helper

**File**: `mcp_servers/magento_products.py`

**What**: Add a helper that resolves a category name string to matching category IDs via SQL. This is needed because ES only stores `category_ids` as integers, not category names.

- [ ] Add `_resolve_category_ids(self, category_name: str) -> List[int]` method
  - SQL query: `SELECT entity_id FROM catalog_category_entity_varchar WHERE value LIKE %s AND attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'name' AND entity_type_id = 3)`
  - Returns list of matching category entity_ids

**Instructional snippet**:
```python
async def _resolve_category_ids(self, category_name: str) -> List[int]:
    """Resolve a category name to category IDs via SQL."""
    try:
        conn = await self._get_db_connection()
        cursor = await conn.cursor(aiomysql.DictCursor)
        await cursor.execute("""
            SELECT ccev.entity_id
            FROM catalog_category_entity_varchar ccev
            WHERE ccev.value LIKE %s
              AND ccev.attribute_id = (
                  SELECT attribute_id FROM eav_attribute
                  WHERE attribute_code = 'name' AND entity_type_id = 3
              )
        """, (f"%{category_name}%",))
        rows = await cursor.fetchall()
        await cursor.close()
        conn.close()
        return [row["entity_id"] for row in rows]
    except Exception as e:
        logger.error(f"Error resolving category '{category_name}': {e}")
        return []
```

### Phase 4: Rewrite `search_products()` to Use ES + SQL Enrichment

**File**: `mcp_servers/magento_products.py`

**What**: Replace the body of `search_products()`. The function signature and return format stay **identical**.

- [ ] Replace `search_products()` implementation (lines 208-314)
  - Step 1: Build ES query via `_build_es_query()`
  - Step 2: Execute via `_es_search()`
  - Step 3: Extract entity_ids from ES hits (preserving relevance order)
  - Step 4: Fetch full product details via SQL `WHERE entity_id IN (...)`
  - Step 5: Merge SQL results back in ES relevance order
  - Step 6: Return same format as before

- [ ] Update docstring: remove the `WARNING` about LIKE matching and the fuzzy-matching caveats (lines 165-170)

**Instructional snippet** (the new `search_products` body):
```python
async def search_products(self, sku=None, name=None, description=None,
                           category=None, min_price=None, max_price=None,
                           limit="500") -> List[Dict]:
    """Search for products by SKU, product name, description, category, and/or price range.

    Uses Elasticsearch for text matching with tokenization, TF-IDF ranking, and fuzzy
    matching — the same search engine that powers the Magento storefront.

    Args:
        sku: Product SKU (tokenized match via ES)
        name: Product name (ES full-text search with fuzziness)
        description: Product description text (ES full-text search)
        category: Category name or ID
        min_price: Minimum price
        max_price: Maximum price
        limit: Maximum number of results (default 500)

    Returns:
        List of product dictionaries (same format as before)
    """
    try:
        limit_value = int(str(limit)) if limit is not None else 500

        # Step 1-2: Build and execute ES query
        es_body = await self._build_es_query(sku, name, description,
                                              category, min_price, max_price)
        es_result = await self._es_search(es_body, size=limit_value)

        hits = es_result.get("hits", {}).get("hits", [])
        if not hits:
            logger.info("ES query returned 0 hits")
            return []

        # Step 3: Extract entity_ids in relevance order
        entity_ids = [int(hit["_id"]) for hit in hits]
        logger.info(f"ES returned {len(entity_ids)} hits")

        # Step 4: Fetch full product details via SQL
        conn = await self._get_db_connection()
        cursor = await conn.cursor(aiomysql.DictCursor)

        placeholders = ",".join(["%s"] * len(entity_ids))
        sql = f"""
            SELECT DISTINCT
                cpe.entity_id,
                cpe.sku,
                cpev_name.value as name,
                cpev_desc.value as description,
                cpd_price.value as price,
                csi.qty,
                csi.is_in_stock,
                ur.request_path as url_path
            FROM catalog_product_entity cpe
            LEFT JOIN catalog_product_entity_varchar cpev_name
                ON cpe.entity_id = cpev_name.entity_id
                AND cpev_name.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'name' AND entity_type_id = 4)
            LEFT JOIN catalog_product_entity_text cpev_desc
                ON cpe.entity_id = cpev_desc.entity_id
                AND cpev_desc.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'description' AND entity_type_id = 4)
            LEFT JOIN catalog_product_entity_decimal cpd_price
                ON cpe.entity_id = cpd_price.entity_id
                AND cpd_price.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'price' AND entity_type_id = 4)
            LEFT JOIN cataloginventory_stock_item csi ON cpe.entity_id = csi.product_id
            LEFT JOIN url_rewrite ur
                ON ur.entity_id = cpe.entity_id
                AND ur.entity_type = 'product'
                AND ur.redirect_type = 0
                AND ur.store_id = 1
                AND ur.metadata IS NULL
            WHERE cpe.entity_id IN ({placeholders})
        """
        await cursor.execute(sql, tuple(entity_ids))
        rows = await cursor.fetchall()
        await cursor.close()
        conn.close()

        # Step 5: Index by entity_id for O(1) lookup, preserve ES order
        row_map = {row["entity_id"]: row for row in rows}

        base_url = "http://localhost:7770/"
        products = []
        for eid in entity_ids:
            row = row_map.get(eid)
            if not row:
                continue
            url_path = row.get("url_path")
            products.append({
                "entity_id": row["entity_id"],
                "sku": row["sku"],
                "name": row["name"],
                "description": (row["description"][:200] + "...") if row["description"] and len(row["description"]) > 200 else row["description"],
                "price": float(row["price"]) if row["price"] else None,
                "qty": float(row["qty"]) if row["qty"] else 0,
                "is_in_stock": bool(row["is_in_stock"]),
                "url": (base_url + url_path) if url_path else f"{base_url}catalog/product/view/id/{row['entity_id']}"
            })

        logger.info(f"Found {len(products)} products matching search criteria")
        return products

    except Exception as e:
        logger.error(f"Error searching products: {e}")
        return []
```

### Phase 5: Update Docstring and Imports

**File**: `mcp_servers/magento_products.py`

- [ ] Add `import urllib.request` and `import urllib.error` at top of file
- [ ] Remove the `WARNING` block from `search_products()` docstring (lines 165-170) — no longer applicable since ES handles relevance properly
- [ ] Keep `Examples:` section in docstring unchanged

### Phase 6: Copy Updated Server to Docker Container

- [ ] Run: `docker cp mcp_servers/magento_products.py shopping:/tmp/magento_products.py`

### Phase 7: Smoke Test — ES Connectivity

- [ ] Verify ES is reachable from the MCP server context:
  ```bash
  docker exec shopping python3 -c "
  import urllib.request, json
  req = urllib.request.Request(
      'http://localhost:9200/magento2_product_1_v4/_search',
      data=json.dumps({'size': 1, 'query': {'match_all': {}}}).encode(),
      headers={'Content-Type': 'application/json'},
      method='POST'
  )
  resp = urllib.request.urlopen(req, timeout=10)
  data = json.loads(resp.read())
  print(f'ES reachable: {data[\"hits\"][\"total\"][\"value\"]} docs')
  "
  ```
  **Expected**: `ES reachable: 104233 docs` (or similar count)

### Phase 8: Regression Tests — Known Queries

Run each test via `test_mcp_server.py` or manual `docker exec` invocations. Compare against known SQL results.

- [ ] **Test 1: "headphones"** — should return results (SQL also returns results; ES should return more relevant ones ranked by score)
  ```bash
  docker exec -i shopping python3 /tmp/magento_products.py <<< '{"method":"tools/call","params":{"name":"search_products","arguments":{"name":"headphones","limit":"10"}}}'
  ```
  **Pass criteria**: Returns > 0 results, top results have "headphones" prominently in name

- [ ] **Test 2: "UGREEN"** — should NOT include "Beaugreen" products
  ```bash
  docker exec -i shopping python3 /tmp/magento_products.py <<< '{"method":"tools/call","params":{"name":"search_products","arguments":{"name":"UGREEN","limit":"30"}}}'
  ```
  **Pass criteria**: No result has "Beaugreen" in the name; count ~20-21 (not 23 as SQL returned)

- [ ] **Test 3: "Nintendo Switch game card case"** — previously returned 0 from SQL
  ```bash
  docker exec -i shopping python3 /tmp/magento_products.py <<< '{"method":"tools/call","params":{"name":"search_products","arguments":{"name":"Nintendo Switch game card case","limit":"10"}}}'
  ```
  **Pass criteria**: Returns > 0 results containing Nintendo Switch cases

- [ ] **Test 4: "Nike slide slipper"** — previously returned 0 from SQL
  ```bash
  docker exec -i shopping python3 /tmp/magento_products.py <<< '{"method":"tools/call","params":{"name":"search_products","arguments":{"name":"Nike slide slipper","limit":"10"}}}'
  ```
  **Pass criteria**: Returns > 0 results; should include Nike Benassi or similar

- [ ] **Test 5: "Sony Bluetooth headphones"** — SQL missed non-"Bluetooth"-named models
  ```bash
  docker exec -i shopping python3 /tmp/magento_products.py <<< '{"method":"tools/call","params":{"name":"Sony Bluetooth headphones","limit":"10"}}}'
  ```
  **Pass criteria**: Returns Sony WH-1000XM3 or similar wireless headphones

- [ ] **Test 6: Price range filter** — min_price + max_price
  ```bash
  docker exec -i shopping python3 /tmp/magento_products.py <<< '{"method":"tools/call","params":{"name":"search_products","arguments":{"name":"headphones","min_price":"20","max_price":"50","limit":"10"}}}'
  ```
  **Pass criteria**: All returned products have price between 20 and 50

- [ ] **Test 7: Category filter (numeric)** — category by ID
  ```bash
  docker exec -i shopping python3 /tmp/magento_products.py <<< '{"method":"tools/call","params":{"name":"search_products","arguments":{"category":"11","limit":"5"}}}'
  ```
  **Pass criteria**: Returns products in category 11 (Electronics)

- [ ] **Test 8: Category filter (text)** — category by name
  ```bash
  docker exec -i shopping python3 /tmp/magento_products.py <<< '{"method":"tools/call","params":{"name":"search_products","arguments":{"category":"Electronics","limit":"5"}}}'
  ```
  **Pass criteria**: Returns products in Electronics categories

- [ ] **Test 9: SKU search** — exact SKU lookup
  ```bash
  docker exec -i shopping python3 /tmp/magento_products.py <<< '{"method":"tools/call","params":{"name":"search_products","arguments":{"sku":"B006H52HBC"}}}'
  ```
  **Pass criteria**: Returns the exact product (Sennheiser HD 202)

- [ ] **Test 10: Empty/no params** — should return products (no text filter, just status=1)
  ```bash
  docker exec -i shopping python3 /tmp/magento_products.py <<< '{"method":"tools/call","params":{"name":"search_products","arguments":{"limit":"5"}}}'
  ```
  **Pass criteria**: Returns 5 products

### Phase 9: Full Integration Test

- [ ] Run existing test suite:
  ```bash
  python3 claude_utils/test_mcp_server.py
  python3 claude_utils/test_magento_mcp.py
  ```
  **Pass criteria**: All existing tests pass with same or better results

- [ ] Run agent MCP execution test:
  ```bash
  python3 claude_utils/test_agent_mcp_execution.py
  ```
  **Pass criteria**: MCP functions accessible in agent namespace, search calls succeed

### Phase 10: Update Documentation

- [ ] Update `CLAUDE.md` to reflect ES-backed search:
  - Note that `search_products` now uses Elasticsearch (not SQL LIKE)
  - Remove any references to LIKE-matching caveats
  - Add ES dependency note (ES must be running in container)

---

## Files Changed

| File | Change | Lines Affected |
|------|--------|----------------|
| `mcp_servers/magento_products.py` | Add imports (`urllib.request`, `urllib.error`) | Top of file |
| `mcp_servers/magento_products.py` | Add `_es_search()` method | New method after `_get_db_connection()` |
| `mcp_servers/magento_products.py` | Add `_build_es_query()` method | New method |
| `mcp_servers/magento_products.py` | Add `_resolve_category_ids()` method | New method |
| `mcp_servers/magento_products.py` | Rewrite `search_products()` body | Lines 208-314 (complete replacement) |
| `mcp_servers/magento_products.py` | Update `search_products()` docstring | Lines 163-207 |
| `CLAUDE.md` | Update search description, remove LIKE caveats | Product Server section |

**Files NOT changed**:
- `mcp_servers/magento_review_data.py` — no text search
- `mcp_servers/magento_checkout.py` — no text search
- `mcp_servers/magento_wishlist.py` — no text search
- `mcp_servers/magento_account.py` — no text search
- `mcp_servers/magento_products.py` `get_product_details()` — exact ID lookup
- `mcp_servers/magento_products.py` `list_categories()` — structural query, no text search

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| ES not running when agent starts | Low — ES starts with Docker container | `_es_search` returns empty on connection failure; agent sees 0 results (same as SQL miss) |
| `urllib.request` blocking event loop | Low — ES responds in <50ms | Acceptable for single-request MCP server; wrap in `asyncio.to_thread()` if needed |
| ES index name changes | Very low — hardcoded by Magento | Constant at top of file, easy to update |
| Price field `price_0_1` not populated | Low — verified populated for tested products | Falls back gracefully (price=None in output) |
| Category name resolution returns too many IDs | Low | LIKE match on category name is same behavior as current SQL; ES `terms` filter handles large arrays |

---

## Success Criteria

### Automated (run after implementation)
1. `python3 claude_utils/test_mcp_server.py` — all checks pass
2. `python3 claude_utils/test_magento_mcp.py` — product server tests pass
3. All 10 regression tests in Phase 8 pass

### Manual Verification
1. Run a single WebArena task that previously failed due to search:
   - Task 21 or any task from taxonomy flagged as `Semantic?=Yes`
   - Verify the agent finds the correct products via MCP search

### Quantitative (after full benchmark run)
1. Compare MCP success rate before/after ES integration on the 187-task benchmark
2. Specifically compare the 16 semantic-failure tasks from `thesis_taxonomy.csv`
3. Target: recover 8-10 of the 16 semantic failures (~5% benchmark improvement)
