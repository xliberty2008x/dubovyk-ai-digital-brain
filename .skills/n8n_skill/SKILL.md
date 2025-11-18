---
name: n8n-workflow-creator
description: Expert guidance for creating, debugging, and optimizing advanced n8n workflows. Use when users need to build n8n automations, integrate complex APIs, debug workflow failures, implement error handling, optimize performance, or handle any n8n-related tasks including data integration, event-driven workflows, ETL/ELT patterns, and production deployment.
---

# n8n Workflow Creator

Expert system for building production-grade n8n workflows with advanced debugging and API integration capabilities.

## Core Workflow Methodology

### When Building New Workflows

**Start with architecture decisions.** Choose pattern based on requirements:
- **Linear workflows**: Simple sequential processes (API data fetch → transform → store)
- **Multi-agent orchestration**: Hub-and-spoke with specialized sub-workflows
- **Event-driven**: Real-time webhooks with async processing
- **Scheduled**: Recurring batch operations with overlap prevention
- **ETL/ELT**: Data pipeline with bronze/silver/gold layers

**Design modular from day one.** Break complex logic into sub-workflows using Execute Workflow nodes. Benefits: independent testing, 65-70% less maintenance time, faster troubleshooting. On Cloud, sub-workflows don't add execution costs.

**Plan for failure before success.** Configure error handling during initial build, not after deployment:
- Node-level: Retry On Fail (3-5 attempts, 5s delays for APIs)
- Workflow-level: Error Trigger workflow for centralized monitoring
- System-level: Dead-letter queues for permanently failed items

## API R&D Methodology (Critical for Complex Integrations)

**Prototype complex APIs in Python BEFORE implementing in n8n.** This is non-negotiable for unfamiliar APIs. Python development is 10-20x faster for exploration.

### Python Prototyping Workflow

When encountering a complex or unfamiliar API:

1. **Create Python prototype script** (see `scripts/api_prototype_template.py`)
2. **Test authentication** - Verify credentials and token retrieval work
3. **Explore endpoints** - Make sample requests to understand response structures
4. **Document behavior** - Note field names, data types, nested structures
5. **Test error scenarios** - Trigger errors to understand error response formats
6. **Validate rate limits** - Test how API responds to rapid requests
7. **Move to n8n** - Implement with confidence based on validated understanding

**Typical R&D timeline:**
- Discovery (1-2 days): Review docs, identify auth requirements, map endpoints
- Prototyping (2-4 hours): Test in Python, analyze responses
- Validation (1-2 days): Create Postman collection, validate all endpoints
- n8n Implementation (1-3 days): Build workflows with confidence

### API Testing Checklist

Before building in n8n:
- [ ] Authentication working in Postman/Python
- [ ] All required endpoints tested
- [ ] Response structures documented
- [ ] Rate limits understood
- [ ] Error responses mapped
- [ ] Pagination strategy confirmed

## Debugging Strategy (When Workflows Fail)

### Debug in Editor Feature (Most Powerful Tool)

When production workflow fails:
1. Go to Executions tab
2. Select failed execution
3. Click "Debug in editor"
4. Exact failure data pins to canvas (blue/purple indicator)
5. Fix issue with real-world data
6. Only one pinned dataset active at a time

### Systematic Error Investigation

**Step 1: Classify the error type**
- **Transient**: Network timeouts, 429 rate limits, 503 unavailable → Retry with backoff
- **Permanent**: 401 auth, 400 bad request, 404 not found → Route to error workflow
- **Data**: Validation failures, schema mismatches → Early validation needed

**Step 2: Isolate the problem**
- Disable all nodes except trigger + first node
- Test execution
- Enable nodes one at a time
- Identify exact failing node

**Step 3: Inspect execution logs**
- Click through failed execution nodes sequentially
- Examine Input and Output tabs
- Look for: null values, unexpected types, missing fields, structure changes

### Common Error Solutions

**401/403 Authentication Failures**
- Verify credentials in node settings
- Check API key permissions and scopes
- Re-authenticate from Credentials tab
- For Google Workspace: Enable "Impersonate a User" in service account

**429 Rate Limiting**
- Use Loop Over Items node with batch size 10-50
- Add Wait nodes between batches (1000ms = 1 req/sec)
- Or use HTTP Request node built-in batching: Items per Batch + Batch Interval
- Enable Retry On Fail: 3-5 max tries

**Code Node Errors**
- Must return: `[{json: {key: "value"}}, {json: {key2: "value2"}}]`
- The `json` key must be an object, not array or primitive
- Use `require()` not `import`/`export` (ES6 modules unsupported)
- Self-hosted: Install modules via npm + configure `NODE_FUNCTION_ALLOW_EXTERNAL`

**Expression Errors**
- Check node executed: `if ($('NodeName').item) { ... }`
- Use optional chaining: `$json.customer?.address?.city`
- Provide fallbacks: `{{$json.title || "Untitled"}}`
- Ternary operators: `{{$json.status === 'active' ? 'Process' : 'Skip'}}`

**Webhook Unreachability**
- Set `WEBHOOK_URL` to public domain (never localhost)
- Configure reverse proxy with SSL + proper headers
- Ensure webhook ports mapped in Docker (default 5678)
- Allow incoming connections in firewall
- Test with curl from external server

**Memory Errors (Out of Memory)**
- Symptoms: "n8n may have run out of memory", "503 Unavailable", "Connection Lost"
- Solutions:
  - Split into sub-workflows (counter-intuitively uses less memory)
  - Use Loop Over Items to batch data (200-500 items at a time)
  - Process data in smaller chunks, not all at once
  - Disable execution history for high-volume workflows
  - Self-hosted: Increase `--max-old-space-size=10240` (in MB)
  - Use filesystem mode for binary data: `N8N_DEFAULT_BINARY_DATA_MODE=filesystem`

## When Stuck in Debugging Iteration

**If workflow fails repeatedly after multiple fix attempts:**

1. **Ask user for execution outputs**
   - Request screenshots of failed node Input/Output tabs
   - Ask for error message text
   - Get execution ID for further investigation

2. **If still stuck, prototype in Python to verify logic**
   - Recreate the exact data transformation in Python
   - Verify logic works outside n8n
   - Use working Python code to inform n8n implementation
   - Use `scripts/debug_prototype_template.py` as starting point
   - Common pattern:
     ```python
     # Test the exact transformation causing issues
     test_data = {...}  # Data from failed execution
     result = transform(test_data)  # Your logic
     print(result)  # Verify it works
     ```

## Performance Optimization

**Optimize node execution order:**
- Place filters at workflow start (fail fast)
- Run validation before expensive operations
- Filter before transformation
- One retail implementation: 45 min → 3 min via reordering

**Implement intelligent batching:**
- Use Loop Over Items for large datasets
- Typical batch sizes: 10-100 items depending on complexity
- Manufacturing example: 65% execution time reduction
- Align batch size with API rate limits

**Leverage parallel processing:**
- Execute non-dependent nodes concurrently
- Use multiple branches for independent tasks
- Merge results with Merge nodes
- Multi-source gathering: 66% time reduction (3 APIs simultaneously vs sequential)

**Cache strategically:**
- Use Function nodes for in-memory config data (30-50% time reduction)
- Production: Redis/Memcached via HTTP Request nodes
- Cache expensive operations and external API calls
- Implement TTL strategies for invalidation

## Error Handling Patterns

**Layered approach:**

1. **Node-level**: Retry On Fail (3-5 attempts, 5s delays)
2. **Workflow-level**: Error Trigger workflows receive:
   - Workflow name
   - Failed node
   - Error message
   - Execution ID
   - Timestamp
3. **System-level**: Dead-letter queues for permanent failures

**Exponential backoff implementation:**
- First retry: 5 seconds
- Second retry: 10 seconds
- Third retry: 20 seconds
- Prevents overwhelming recovering services

**Design for idempotency:**
- Use unique identifiers for deduplication
- Check before state-changing operations
- Prevents: duplicate records, double-charging, multiple notifications

## Authentication Patterns

**OAuth 2.0 (most common):**
- Authorization Code: Standard user flow (Auth URL + Token URL + Client ID/Secret + Scopes)
- Client Credentials: Machine-to-machine (no user interaction)
- PKCE: Enhanced security for mobile/SPA (prevents CSRF)

**Token refresh:**
- n8n's OAuth2 credential auto-refreshes using refresh tokens
- For custom JWT: implement refresh logic detecting 401 → get new token → retry

**Webhook security:**
- Enable Basic Auth or Header Auth on webhook nodes
- Implement IP whitelisting
- Always use HTTPS
- For payment webhooks: Implement signature verification in Code nodes

## Credential & Environment Management

**Never hardcode credentials:**
- Use n8n's encrypted credential management exclusively
- Enterprise: Integrate AWS Secrets Manager, Google Secret Manager, HashiCorp Vault, Azure Key Vault
- Credentials encrypted at rest in database

**Environment separation (dev/staging/production):**
- Use Git integration with branch-based workflows
- Single-branch (simpler) or multi-branch (better for teams with PR reviews)
- Flow: development → staging → production branches
- Enable "Protected instance" on production (prevents direct editing)

**Use n8n Variables for environment-specific values:**
- API endpoints, timeouts, feature flags
- Access with: `$vars.variableName`
- Credentials pushed to Git contain only structure (stubs), never values

**Credential rotation:**
- 90-day rotation cycles for API keys
- Separate keys per application
- Delete unused keys immediately
- Monitor usage for anomalies

## Advanced Features

### Conditional Logic

**IF vs Switch:**
- IF: Binary decisions (true/false), simple conditions
- Switch: 3+ outcomes, cleaner than chained IFs
- Switch supports: string, number, boolean, date with operations (equals, contains, regex, ranges)
- Always configure fallback output

### Loops and Batching

**Loop Over Items node (only when needed):**
- Most nodes auto-process all items
- Use Loop Over Items for:
  - Rate limiting (batch size 10, 1s wait between)
  - Memory management (batch size 50-100)
  - Sequential processing (batch size 1)
  - Dynamic pagination

**Configuration:**
- Batch size: 1-100 based on use case
- Enable Reset for pagination
- Context variables: `$node["Loop Over Items"].context["noItemsLeft"]`

### Data Transformation

**Expression syntax:**
- Current item: `$json["fieldName"]`
- Specific node: `$("NodeName").first().json`
- All items: `$("NodeName").all()`
- Built-in libraries: Luxon (dates), JMESPath (JSON querying)

**Built-in functions (use instead of Code nodes):**
- Strings: `.toBase64()`, `.extractDomain()`, `.hash()`, `.parseJson()`
- Arrays: `.chunk(size)`, `.compact()`, `.unique()`, `.merge(arr, key)`, `.difference(arr)`
- Dates: `.format(format)`, `.beginningOf(unit)`, `.isBetween(date1, date2)`

**Transformation best practices:**
- Transform as early as possible
- Filter before transformation
- Use built-in functions over custom code
- Break complex transformations into multiple steps
- Set node for simple mapping; Code node for unavailable logic

### Sub-workflows

**When to use:**
- Reusable logic across workflows
- Complex operations needing isolation
- Memory optimization (sub-workflow memory freed after execution)
- Independent testing of components

**Benefits:**
- No execution cost on Cloud
- Easier maintenance
- Reduced cognitive load
- Testable in isolation

**Usage:**
- Execute Workflow node calls sub-workflows
- Pass data as parameters
- Receive processed results
- Return minimal data to parent

### Custom Code

**Function vs Function Item:**
- Function: Processes all items together (`$input.all()`)
- Function Item: Processes each item individually (`$input.item.json`)
- Use Function for: aggregations, comparisons across items
- Use Function Item for: per-item transformations

**Return format:**
```javascript
return [{json: {key: "value"}}, {json: {key2: "value2"}}];
```

### HTTP Request Node

**Pagination modes:**
- Off: No pagination
- Update Parameter: Increment page numbers (`{{$pageCount + 1}}`)
- Response Contains Next URL: Follow next URL (`{{$response.body.next_page_url}}`)

**Configuration:**
- Custom headers for API requirements
- Body types: JSON (REST APIs), Form-Data (file uploads), Raw (custom)
- Enable "Full Response" to see headers + status codes for debugging

## Workflow Patterns by Use Case

### Data Integration
- **Bi-directional sync**: Two-way changes (CRM ↔ database)
- **One-way sync**: Single source of truth (master data distribution)
- **Multi-source consolidation**: Combine data from multiple sources
- **Best practices**: Early validation, deduplication (Merge nodes), incremental loading, idempotent design

### API Automation
- **Sequential chaining**: Linear flows (each API → next API)
- **Parallel execution**: Simultaneous calls + merge results
- **Rate limit management**: Loop Over Items + Wait nodes + exponential backoff

### Event-Driven
- **Webhook responses**:
  - "Immediately": Returns 200 OK instantly (async processing)
  - "When Last Node Finishes": Returns workflow results (sync)
  - "Using Respond to Webhook Node": Custom response logic
- **Best practices**: Idempotency via event IDs, signature verification, quick responses (<2s)

### Scheduled Jobs
- **Cron expressions**:
  - `0 9 * * 1`: Every Monday at 9 AM
  - `*/15 * * * *`: Every 15 minutes
  - `0 0 1 * *`: First day of each month
- **Set correct timezone** (workflow or instance level)
- **Implement overlap prevention** using workflow static data

### ETL/ELT
- **ETL**: Extract → Transform in n8n → Load (data warehousing)
- **ELT**: Extract → Load raw → Transform in destination (cloud warehouses)
- **Medallion architecture**: Bronze (raw) → Silver (cleaned) → Gold (aggregated)
- **Best practices**: Incremental loading, schema validation, error routing, metadata tracking

## Production Readiness Checklist

**Error Handling:**
- [ ] Error Trigger workflow configured
- [ ] Stop and Error nodes at critical points
- [ ] Retry logic with exponential backoff
- [ ] Timeout configurations set
- [ ] Notifications configured (Slack/email/SMS)

**Performance:**
- [ ] Memory optimization via batching/sub-workflows
- [ ] Data batching for large datasets
- [ ] Execution data retention policies set
- [ ] Rate limiting handled
- [ ] Execution times monitored

**Security:**
- [ ] Credentials use encrypted storage or external secrets manager
- [ ] Webhook authentication enabled
- [ ] Environment variables for sensitive config
- [ ] Access controls implemented
- [ ] Audit logging enabled

**Monitoring:**
- [ ] Logging level appropriate (info for prod, debug for troubleshooting)
- [ ] Execution history retention balanced
- [ ] Alerting for failures configured
- [ ] Cost tracking for AI nodes
- [ ] Health check workflows created

**Testing:**
- [ ] Unit tests passed
- [ ] Integration tests passed
- [ ] Edge cases tested (null values, boundaries)
- [ ] Load testing completed
- [ ] Staging environment validated

## Common Pitfalls to Avoid

**Never:**
- Create monolithic workflows (use sub-workflows instead)
- Hardcode values (use Variables and credentials)
- Skip error handling (implement Error Triggers)
- Process without filtering first (filter early)
- Make sequential API calls when batching possible
- Skip caching for expensive operations
- Hardcode credentials in Function nodes
- Give all users access to all credentials
- Test in production (use dev/staging environments)

## Resources

This skill includes:

### scripts/
- `api_prototype_template.py` - Template for prototyping new APIs before n8n implementation
- `debug_prototype_template.py` - Template for debugging complex logic outside n8n

### references/
- `advanced_patterns.md` - Advanced workflow patterns and architectures
- `troubleshooting_guide.md` - Comprehensive troubleshooting reference