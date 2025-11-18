# Comprehensive n8n Troubleshooting Guide

Quick reference for diagnosing and fixing common n8n issues.

## Table of Contents
1. [Authentication Errors](#authentication-errors)
2. [HTTP Request Failures](#http-request-failures)
3. [Expression Errors](#expression-errors)
4. [Code Node Errors](#code-node-errors)
5. [Webhook Issues](#webhook-issues)
6. [Performance Problems](#performance-problems)
7. [Memory Errors](#memory-errors)
8. [Data Transformation Issues](#data-transformation-issues)
9. [Credential Problems](#credential-problems)
10. [Execution Failures](#execution-failures)

---

## Authentication Errors

### 401 Unauthorized

**Symptoms**: HTTP Request returns 401, "Authentication failed" errors

**Common Causes**:
1. Expired or invalid API key/token
2. Wrong authentication method selected
3. Incorrect credential configuration
4. Missing required headers or parameters
5. Token not refreshed properly

**Solutions**:

**Check 1: Verify credential is active**
```
1. Go to Credentials section
2. Find your credential
3. Click Test
4. Re-authenticate if needed
```

**Check 2: Inspect the actual request**
```
1. Enable "Full Response" in HTTP Request node
2. Check Input tab for exact headers sent
3. Compare with API documentation
```

**Check 3: OAuth token refresh**
```
For OAuth credentials:
1. Check if refresh token is present
2. Manually trigger re-authentication
3. Check token expiry time
4. Verify redirect URLs match exactly
```

**Check 4: Header format**
```
Common issues:
❌ Authorization: token xyz
✅ Authorization: Bearer xyz

❌ X-API-Key xyz
✅ X-API-Key: xyz
```

### 403 Forbidden

**Symptoms**: Request authenticated but denied access

**Common Causes**:
1. Insufficient permissions/scopes
2. IP whitelist restrictions
3. Account limitations
4. Resource-level permissions

**Solutions**:

**Check 1: Verify API key permissions**
```
1. Log into API provider dashboard
2. Check API key settings
3. Verify scopes/permissions granted
4. Regenerate key if needed
```

**Check 2: Google Workspace specific**
```
For Google APIs with service account:
1. Enable "Impersonate a User" in credential
2. Add email address of user to impersonate
3. Verify domain-wide delegation enabled
4. Check scopes in Admin Console
```

**Check 3: IP restrictions**
```
1. Find your n8n instance public IP
2. Check API provider's IP whitelist
3. Add n8n IP if restricted
```

---

## HTTP Request Failures

### 400 Bad Request

**Symptoms**: API returns 400 error

**Common Causes**:
1. Invalid request body format
2. Missing required fields
3. Invalid data types
4. Malformed JSON

**Debugging Process**:

**Step 1: Check request body**
```
1. Click on failed HTTP Request node
2. Go to Input tab
3. Expand Body section
4. Compare with API documentation
```

**Step 2: Validate JSON**
```
Common issues:
- Trailing commas: {"name": "test",}
- Unquoted keys: {name: "test"}
- Single quotes: {'name': 'test'}
- Missing commas: {"a": 1 "b": 2}
```

**Step 3: Check data types**
```javascript
// Function node to validate data types
const data = $json;

// Expected: number, got: string
if (typeof data.quantity !== 'number') {
  data.quantity = parseInt(data.quantity);
}

// Expected: array, got: string
if (typeof data.tags === 'string') {
  data.tags = data.tags.split(',');
}

return [{json: data}];
```

### 404 Not Found

**Symptoms**: Resource not found errors

**Common Causes**:
1. Wrong endpoint URL
2. Resource ID doesn't exist
3. Missing URL parameters
4. API version in URL incorrect

**Solutions**:

**Check 1: Verify endpoint URL**
```
In HTTP Request node:
❌ {{$json.url}}/api/users
✅ Make sure $json.url already includes /api/users
OR
✅ https://api.example.com/v1/users/{{$json.id}}
```

**Check 2: URL encoding**
```javascript
// For IDs with special characters
const encoded_id = encodeURIComponent($json.id);
// Use: /users/{{encoded_id}}
```

### 429 Rate Limited

**Symptoms**: "Too Many Requests" error

**Solutions**:

**Solution 1: Loop Over Items with delays**
```
1. Add Loop Over Items node
2. Set batch size: 10-50 (depends on rate limit)
3. Add Wait node inside loop
4. Set wait time:
   - For 100 req/min: 600ms wait = ~6 req/10sec
   - For 1000 req/hour: 3.6s wait
```

**Solution 2: HTTP Request built-in batching**
```
In HTTP Request node options:
1. Enable "Batch Requests"
2. Items per Batch: 10
3. Batch Interval (ms): 1000
```

**Solution 3: Exponential backoff**
```javascript
// In Function node before HTTP Request
const attempt = $json.retry_attempt || 0;
const wait_time = Math.min(1000 * Math.pow(2, attempt), 32000);

return [{
  json: {
    ...$json,
    retry_attempt: attempt + 1,
    wait_ms: wait_time
  }
}];
```

**Then**: Use Wait node with expression `{{$json.wait_ms}}`

**Solution 4: Retry On Fail**
```
HTTP Request node settings:
1. Enable "Retry On Fail"
2. Max Tries: 3-5
3. Wait Between Tries: 5000ms (5 seconds)
```

### 500/502/503 Server Errors

**Symptoms**: Server-side errors from API

**Common Causes**:
1. API server temporarily down
2. Timeout on API side
3. Invalid data causing server error
4. API bug

**Solutions**:

**Solution 1: Implement retries**
```
Node settings:
- Retry On Fail: Yes
- Max Tries: 3
- Wait Between Tries: 10000ms
```

**Solution 2: Timeout configuration**
```
HTTP Request node:
- Timeout: 30000ms (30 seconds)
- Adjust based on API's typical response time
```

**Solution 3: Circuit breaker** (see Advanced Patterns doc)

---

## Expression Errors

### Cannot read property of undefined

**Symptoms**: `Cannot read property 'field' of undefined`

**Common Causes**:
1. Node not executed yet
2. Field doesn't exist in data
3. Wrong node reference
4. Array empty

**Solutions**:

**Solution 1: Check node executed**
```javascript
// ❌ Fails if node not executed
{{$('NodeName').first().json.field}}

// ✅ Safe with fallback
{{$('NodeName').first()?.json?.field || 'default'}}
```

**Solution 2: Optional chaining**
```javascript
// ❌ Fails if customer or address is null
{{$json.customer.address.city}}

// ✅ Safe navigation
{{$json.customer?.address?.city}}
```

**Solution 3: Check array length**
```javascript
// ❌ Fails if array is empty
{{$json.items[0].name}}

// ✅ Check length first
{{$json.items.length > 0 ? $json.items[0].name : 'No items'}}
```

**Solution 4: Provide defaults**
```javascript
// Simple default
{{$json.title || 'Untitled'}}

// Nested with default
{{$json.user?.name || 'Anonymous'}}
```

### Expression not resolving

**Symptoms**: Expression shows as literal text instead of resolved value

**Common Causes**:
1. Wrong delimiter used
2. Expression in wrong field type
3. Syntax error

**Solutions**:

**Check 1: Correct delimiters**
```
❌ ${json.field}    (Shell variable syntax)
❌ {json.field}     (Missing second brace)
✅ {{$json.field}}  (Correct n8n syntax)
```

**Check 2: Field must support expressions**
```
Look for "Expression" toggle button
If toggle not present, field doesn't support expressions
```

**Check 3: Syntax validation**
```javascript
// Test in Function node first
const value = $json.field;
console.log(value);
return [{json: {value}}];
```

### Type mismatch errors

**Symptoms**: "Expected string but got number" or similar

**Solutions**:

**Convert types explicitly**:
```javascript
// Number to string
{{$json.id.toString()}}
{{String($json.id)}}

// String to number
{{parseInt($json.quantity)}}
{{parseFloat($json.price)}}
{{Number($json.count)}}

// To boolean
{{Boolean($json.active)}}
{{$json.status === 'active'}}

// To array
{{$json.tags.split(',')}}
```

---

## Code Node Errors

### Cannot use import statement outside a module

**Symptoms**: Error when using `import` or `export`

**Cause**: n8n Code nodes use CommonJS, not ES6 modules

**Solution**:
```javascript
// ❌ Don't use ES6 imports
import axios from 'axios';

// ✅ Use require
const axios = require('axios');
```

### Module not found

**Symptoms**: `Cannot find module 'lodash'` or similar

**Solutions**:

**For n8n Cloud**:
- Limited set of pre-installed packages
- Use built-in functions instead
- Request new packages from n8n support

**For self-hosted**:
```bash
# Install package on server
npm install lodash

# Or in Docker container
docker exec -it n8n npm install lodash

# Configure environment variable
NODE_FUNCTION_ALLOW_EXTERNAL=lodash,axios,moment
```

### Return format errors

**Symptoms**: "Items must be an array" or "json property must be an object"

**Solution**:

```javascript
// ❌ Wrong formats
return $json;
return {data: "value"};
return ["item1", "item2"];

// ✅ Correct format
return [
  {json: {key: "value"}},
  {json: {key: "value2"}}
];

// ✅ For single item
return [{json: $json}];

// ✅ Transforming input items
return $input.all().map(item => ({
  json: {
    ...item.json,
    new_field: "value"
  }
}));
```

### Async/await issues

**Common mistakes**:

```javascript
// ❌ Forgot async keyword
const fetchData = () => {
  const response = await fetch(url);  // Error!
};

// ✅ Add async
const fetchData = async () => {
  const response = await fetch(url);
};

// ❌ Not awaiting async function
const result = fetchData();  // Returns Promise
return [{json: result}];

// ✅ Await the function
const result = await fetchData();
return [{json: result}];
```

---

## Webhook Issues

### Webhook not receiving requests

**Symptoms**: External service sends webhook but workflow doesn't trigger

**Checklist**:

**1. Check webhook URL**
```
Correct format: https://your-domain.com/webhook/path
Not: http://localhost:5678/webhook/path
```

**2. For self-hosted, check environment variable**
```env
# In .env or docker-compose.yml
WEBHOOK_URL=https://your-domain.com

# Not localhost or private IP
```

**3. Verify webhook is active**
```
1. Check workflow is activated (toggle ON)
2. Production webhook (not test webhook)
3. Webhook path is unique
```

**4. Test with curl**
```bash
curl -X POST https://your-domain.com/webhook/test \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

**5. Check firewall/security groups**
```
- Port 5678 (or 443 for HTTPS) open
- No IP restrictions blocking webhook sender
- Reverse proxy configured correctly
```

### Webhook responds with 404

**Causes**:
1. Workflow not activated
2. Wrong webhook path
3. n8n not running
4. Reverse proxy misconfigured

**Solutions**:

**Check webhook path**:
```
In Webhook Trigger node:
- Path: test-webhook
- Full URL: https://your-domain.com/webhook/test-webhook
- NOT: https://your-domain.com/test-webhook
```

**Check reverse proxy (Nginx example)**:
```nginx
location /webhook/ {
    proxy_pass http://localhost:5678/webhook/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Webhook times out

**Symptoms**: Webhook sender reports timeout, but workflow runs fine

**Cause**: Workflow takes too long, webhook sender timeout expires

**Solutions**:

**Solution 1: Return response immediately**
```
Webhook Trigger node settings:
- Response: "Immediately"
- Workflow runs async after responding
```

**Solution 2: Use sub-workflow for heavy processing**
```
Main workflow:
1. Webhook Trigger
2. Validate input
3. Respond to Webhook node
4. Execute Workflow (sub-workflow for processing)
```

**Solution 3: Queue for later processing**
```
1. Webhook receives request
2. Store in database/queue
3. Respond 202 Accepted
4. Separate scheduled workflow processes queue
```

### Webhook authentication failing

**Symptoms**: Legitimate webhooks rejected

**Solutions**:

**For signature verification**:
```javascript
// In first Function node after webhook
const signature = $json.headers['x-signature'];
const payload = JSON.stringify($json.body);
const crypto = require('crypto');

const expected = crypto
  .createHmac('sha256', 'YOUR_SECRET')
  .update(payload)
  .digest('hex');

const valid = signature === expected;

if (!valid) {
  // Reject webhook
  $response.status(401).json({error: 'Invalid signature'});
  return [];
}

return [{json: $json}];
```

**For basic auth on webhook**:
```
Webhook Trigger node:
- Authentication: Basic Auth
- Username: webhook_user
- Password: [secure password]
```

---

## Performance Problems

### Workflow runs slowly

**Diagnosis**:

**Step 1: Identify slow nodes**
```
1. Go to execution history
2. Check execution time per node
3. Sort nodes by duration
4. Focus on nodes taking >2 seconds
```

**Step 2: Check for serial execution**
```
Are you making API calls sequentially that could be parallel?
```

**Optimization strategies**:

**1. Parallelize API calls** (see Fan-Out/Fan-In pattern)

**2. Filter early**
```
❌ Fetch all 10,000 records → Filter → Process
✅ Filter in database query → Process only needed records
```

**3. Cache expensive operations**
```javascript
// Store in workflow static data
if (!$workflow.staticData.config) {
  // Expensive operation (API call, complex calculation)
  $workflow.staticData.config = await fetchConfig();
}

const config = $workflow.staticData.config;
```

**4. Optimize database queries**
```sql
-- ❌ Slow - No index
SELECT * FROM orders WHERE created_at > '2024-01-01';

-- ✅ Fast - Indexed column
CREATE INDEX idx_created_at ON orders(created_at);
```

**5. Use sub-workflows**
```
Break monolithic workflow into smaller sub-workflows
Each sub-workflow releases memory after completion
```

### High execution count

**Symptoms**: Workflow triggered too many times

**Causes**:
1. Polling trigger with too frequent interval
2. Webhook receiving duplicates
3. Infinite loops
4. Recursive workflow calls

**Solutions**:

**Check 1: Review trigger configuration**
```
Schedule Trigger:
- Is */1 * * * * (every minute) necessary?
- Can it be */15 * * * * (every 15 minutes)?
```

**Check 2: Implement deduplication**
```javascript
const event_id = $json.id;
const processed = $workflow.staticData.processed_ids || new Set();

if (processed.has(event_id)) {
  // Duplicate, skip processing
  return [];
}

processed.add(event_id);
$workflow.staticData.processed_ids = processed;

return [{json: $json}];
```

**Check 3: Prevent infinite loops**
```javascript
const max_iterations = 100;
const current = $json.iteration || 0;

if (current >= max_iterations) {
  throw new Error('Max iterations reached');
}

return [{json: {...$json, iteration: current + 1}}];
```

---

## Memory Errors

### "n8n may have run out of memory"

**Symptoms**: 
- Execution fails with memory error
- "503 Service Unavailable"
- "Connection Lost" in UI
- Docker container restarts

**Common Causes**:
1. Processing too many items at once
2. Large binary data (files/images)
3. Keeping entire dataset in memory
4. Not releasing memory between operations

**Solutions**:

**Solution 1: Batch processing**
```
Use Loop Over Items node:
1. Batch size: 200-500 items
2. Process batch
3. Memory released after each batch
4. Continue until complete
```

**Solution 2: Sub-workflows**
```
❌ Process 10,000 items in one workflow
✅ Main workflow calls sub-workflow per batch
   Memory freed after each sub-workflow completes
```

**Solution 3: Limit query size**
```sql
-- ❌ SELECT * FROM large_table;  (1M records)
-- ✅ Use pagination
SELECT * FROM large_table LIMIT 1000 OFFSET 0;
```

**Solution 4: Binary data mode** (self-hosted)
```env
# Store binary data on filesystem instead of memory
N8N_DEFAULT_BINARY_DATA_MODE=filesystem
```

**Solution 5: Increase memory** (self-hosted)
```bash
# For Node.js
NODE_OPTIONS=--max-old-space-size=4096  # 4GB

# Docker
docker run ... --env NODE_OPTIONS="--max-old-space-size=4096"
```

**Solution 6: Disable execution history**
```
Workflow settings:
- Save execution progress: No
- Saves memory by not storing execution data
- Use only for high-volume workflows
```

---

## Data Transformation Issues

### Nested object access errors

**Problem**: Can't access deeply nested properties

**Solutions**:

```javascript
// ❌ Brittle - fails if any level is null
const city = $json.customer.address.billing.city;

// ✅ Optional chaining
const city = $json.customer?.address?.billing?.city;

// ✅ Function to safely get nested value
function getNestedValue(obj, path, defaultValue = null) {
  return path.split('.').reduce((current, key) => {
    return current?.[key];
  }, obj) ?? defaultValue;
}

const city = getNestedValue($json, 'customer.address.billing.city', 'Unknown');
```

### Array manipulation challenges

**Common operations**:

```javascript
// Filter array
const active = $json.items.filter(item => item.status === 'active');

// Map/transform array
const names = $json.items.map(item => item.name);

// Find item
const item = $json.items.find(item => item.id === 123);

// Sum values
const total = $json.items.reduce((sum, item) => sum + item.price, 0);

// Remove duplicates
const unique = [...new Set($json.items.map(item => item.id))];

// Group by property
const grouped = $json.items.reduce((acc, item) => {
  const key = item.category;
  if (!acc[key]) acc[key] = [];
  acc[key].push(item);
  return acc;
}, {});

// Flatten nested arrays
const flat = $json.items.flatMap(item => item.tags);

// Chunk array
const chunks = [];
for (let i = 0; i < $json.items.length; i += 100) {
  chunks.push($json.items.slice(i, i + 100));
}
```

### Date/time manipulation

**Common issues and solutions**:

```javascript
// Use Luxon (built-in to n8n)
const DateTime = require('luxon').DateTime;

// Parse ISO date
const dt = DateTime.fromISO($json.created_at);

// Format date
const formatted = dt.toFormat('yyyy-MM-dd HH:mm:ss');

// Add time
const future = dt.plus({days: 7});

// Subtract time
const past = dt.minus({hours: 2});

// Get start/end of period
const startOfDay = dt.startOf('day');
const endOfMonth = dt.endOf('month');

// Compare dates
const isAfter = dt > DateTime.fromISO('2024-01-01');

// Get timezone
const inNY = dt.setZone('America/New_York');

// Get timestamp
const timestamp = dt.toMillis();

// From timestamp
const fromTs = DateTime.fromMillis(1704067200000);
```

---

## Credential Problems

### Credentials not found

**Symptoms**: "Credentials with name ... could not be found"

**Solutions**:

**1. Check credential name matches exactly**
```
In credential: "My API Key"
In node: Must be "My API Key" (case-sensitive)
```

**2. Verify credential type**
```
Using: OAuth2 credential
Node expects: HTTP Header Auth credential
```

**3. Credential not shared with workflow**
```
1. Go to Credentials
2. Find your credential
3. Check "Shared With" section
4. Add workflow/user if needed
```

### OAuth credentials keep expiring

**Symptoms**: Must re-authenticate frequently

**Causes**:
1. Refresh token not stored/used
2. Refresh token expired
3. OAuth configuration incorrect

**Solutions**:

**1. Check credential configuration**
```
OAuth2 credential must have:
- Client ID
- Client Secret  
- Authorization URL
- Access Token URL
- Refresh Token URL (if different)
- Correct scopes
```

**2. Verify redirect URLs match**
```
In OAuth app settings:
Redirect URL: https://your-domain.com/rest/oauth2-credential/callback

Common mistakes:
❌ http instead of https
❌ Missing /rest/oauth2-credential/callback
❌ Wrong domain
```

**3. Check refresh token expiry**
```
Some providers:
- Google: refresh tokens don't expire (unless revoked)
- Microsoft: refresh tokens expire after 90 days inactive
- Shopify: app must request offline access mode
```

---

## Execution Failures

### Workflow fails silently

**Symptoms**: Workflow shows as successful but didn't do what expected

**Debugging**:

**1. Check IF conditions**
```javascript
// Log condition evaluation
const condition = $json.status === 'active';
console.log('Condition result:', condition);
console.log('Status value:', $json.status);
console.log('Status type:', typeof $json.status);

// Common issue: type mismatch
'123' === 123  // false (string vs number)
```

**2. Check Switch node configuration**
```
In Switch node:
- Mode: Rules or Expression?
- Are all possible values covered?
- Is there a fallback route?
```

**3. Check Loop completion**
```
Loop Over Items:
- Is Reset enabled?
- Check Loop node output
- Verify all items processed
```

### Execution stuck/hanging

**Symptoms**: Workflow never completes, shows as "running" forever

**Causes**:
1. Waiting for condition that never becomes true
2. External API not responding (no timeout)
3. Infinite loop
4. Deadlock in sub-workflows

**Solutions**:

**1. Set timeouts**
```
HTTP Request node:
- Timeout: 30000ms (30 seconds)
```

**2. Add execution timeout** (workflow settings)
```
Workflow Settings:
- Execution Timeout: 300 (5 minutes)
```

**3. Check loop conditions**
```javascript
// Add safety counter
const max_loops = 1000;
const current = $json.loop_count || 0;

if (current >= max_loops) {
  throw new Error('Max loops exceeded - possible infinite loop');
}

return [{json: {...$json, loop_count: current + 1}}];
```

### Partial execution completion

**Symptoms**: Some items processed, others not

**Causes**:
1. Error in middle of batch
2. Rate limiting
3. Memory issues
4. Timeout

**Solutions**:

**1. Enable Continue On Fail**
```
For each node:
Settings → Continue On Fail: Yes

Failed items will have error property:
$json.error
```

**2. Process items individually**
```
Instead of batch HTTP request:
1. Loop Over Items (batch size: 1)
2. HTTP Request
3. Catch errors per item
4. Continue to next item
```

**3. Implement retry logic per item**
```javascript
const max_retries = 3;
const retry_count = $json.retry_count || 0;

if ($json.error && retry_count < max_retries) {
  // Retry this item
  return [{json: {...$json, retry_count: retry_count + 1}}];
} else if ($json.error) {
  // Max retries reached, move to dead letter queue
  return [];
} else {
  // Success
  return [{json: $json}];
}
```

---

## Quick Diagnosis Flowchart

```
Workflow failing?
│
├─> Authentication error (401/403)?
│   └─> Check credentials, re-authenticate, verify scopes
│
├─> API error (4xx/5xx)?
│   ├─> 400: Check request body format
│   ├─> 404: Verify endpoint URL
│   ├─> 429: Implement rate limiting
│   └─> 5xx: Add retries with backoff
│
├─> Expression error?
│   ├─> Use optional chaining: ?.
│   ├─> Provide defaults: || 'default'
│   └─> Check node executed
│
├─> Code node error?
│   ├─> Use require(), not import
│   ├─> Return correct format: [{json: {...}}]
│   └─> Check package availability
│
├─> Memory error?
│   ├─> Batch processing with Loop Over Items
│   ├─> Use sub-workflows
│   └─> Limit data volume
│
├─> Webhook not working?
│   ├─> Check WEBHOOK_URL env var
│   ├─> Verify workflow activated
│   ├─> Test with curl
│   └─> Check firewall/proxy
│
└─> Performance issue?
    ├─> Parallelize API calls
    ├─> Filter early
    ├─> Cache expensive operations
    └─> Use sub-workflows
```

---

## Getting Help

When asking for help on n8n community forum or GitHub:

**Include**:
1. n8n version
2. Hosting type (Cloud/self-hosted)
3. Node configuration (screenshot)
4. Error message (exact text)
5. Expected vs actual behavior
6. Steps to reproduce
7. Sample input data (sanitized)
8. Execution ID (if on Cloud)

**Don't share**:
- API keys or credentials
- Actual customer data
- Internal business logic (if sensitive)

**Template**:
```
## Problem Description
[What you're trying to achieve]

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- n8n version: [e.g., 1.0.0]
- Hosting: [Cloud / Self-hosted Docker / Self-hosted npm]
- Node: [e.g., HTTP Request]

## Error Message
```
[Paste error here]
```

## Steps to Reproduce
1. [First step]
2. [Second step]
3. [...]

## Configuration
[Screenshot or export of relevant nodes]
```

---

This troubleshooting guide covers 90% of common issues. For complex problems, consult n8n documentation or community forum.
