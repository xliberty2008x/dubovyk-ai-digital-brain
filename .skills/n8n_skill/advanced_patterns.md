# Advanced n8n Workflow Patterns

This document covers advanced workflow architectures and patterns for complex use cases.

## Table of Contents
1. [Multi-Agent Orchestration](#multi-agent-orchestration)
2. [State Machines](#state-machines)
3. [Event Sourcing](#event-sourcing)
4. [Saga Pattern](#saga-pattern)
5. [Circuit Breaker](#circuit-breaker)
6. [Fan-Out/Fan-In](#fan-outfan-in)
7. [Priority Queue Processing](#priority-queue-processing)
8. [Idempotent Workflows](#idempotent-workflows)

---

## Multi-Agent Orchestration

**Use case**: Complex business processes requiring multiple specialized sub-workflows.

### Architecture

```
Main Orchestrator Workflow
├── Agent 1: Data Validation
├── Agent 2: External API Integration
├── Agent 3: Data Transformation
├── Agent 4: Notification Service
└── Agent 5: Audit Logging
```

### Pattern Structure

**Main Orchestrator**:
- Webhook or Schedule Trigger
- IF nodes for routing logic
- Multiple Execute Workflow nodes
- Merge node to consolidate results
- Final processing and response

**Sub-Workflow Template**:
- Execute Workflow Trigger
- Input validation
- Core processing logic
- Error handling
- Standardized output format

### Example: Order Processing System

**Main Workflow**: Order Orchestrator
```
1. Webhook Trigger (receive order)
2. Execute Workflow → Validate Order Data
3. Execute Workflow → Check Inventory
4. IF (inventory available)
   ├─ Yes → Execute Workflow → Process Payment
   └─ No → Execute Workflow → Notify Out of Stock
5. Execute Workflow → Send Confirmation
6. Execute Workflow → Update Analytics
7. Respond to Webhook
```

**Benefits**:
- Each agent can be tested independently
- Teams can work on different agents simultaneously
- Easy to add new agents without touching main flow
- Memory efficient (sub-workflow memory freed after execution)

### Best Practices

1. **Standardize communication format** between agents:
   ```javascript
   {
     "status": "success|error|warning",
     "data": {...},
     "metadata": {
       "agent_name": "inventory_checker",
       "execution_time_ms": 234,
       "timestamp": "2024-01-15T10:30:00Z"
     },
     "errors": []
   }
   ```

2. **Implement circuit breakers** for each agent (see Circuit Breaker pattern)

3. **Pass minimal data** between agents - only what's needed

4. **Version your sub-workflows** using workflow names like `validate_order_v2`

---

## State Machines

**Use case**: Workflows with multiple states and complex state transitions (approval workflows, order lifecycle, onboarding processes).

### Pattern Structure

**State Storage**:
- Use workflow static data or external database
- Store: current_state, previous_state, state_history, metadata

**State Transition Logic**:
```
1. Load current state
2. Validate transition is allowed
3. Execute state-specific logic
4. Update state
5. Log transition
6. Trigger next actions
```

### Example: Document Approval Workflow

**States**: `draft → pending_review → approved → published` or `rejected`

**Transitions**:
- draft → pending_review: Submit for Review
- pending_review → approved: Approve
- pending_review → rejected: Reject
- pending_review → draft: Request Changes
- approved → published: Publish
- rejected → draft: Revise

**Implementation**:

```javascript
// State transition validator (Function node)
const allowed_transitions = {
  'draft': ['pending_review'],
  'pending_review': ['approved', 'rejected', 'draft'],
  'approved': ['published'],
  'rejected': ['draft'],
  'published': []
};

const current_state = $json.current_state;
const next_state = $json.requested_state;

const is_allowed = allowed_transitions[current_state]?.includes(next_state);

return [{
  json: {
    transition_allowed: is_allowed,
    current_state: current_state,
    next_state: next_state,
    error: is_allowed ? null : `Invalid transition: ${current_state} → ${next_state}`
  }
}];
```

### State History Tracking

Store complete history for audit trails:

```javascript
{
  "document_id": "DOC-123",
  "current_state": "approved",
  "state_history": [
    {
      "from": null,
      "to": "draft",
      "timestamp": "2024-01-15T10:00:00Z",
      "user": "john@example.com",
      "reason": "Created"
    },
    {
      "from": "draft",
      "to": "pending_review",
      "timestamp": "2024-01-15T14:30:00Z",
      "user": "john@example.com",
      "reason": "Submitted for review"
    },
    {
      "from": "pending_review",
      "to": "approved",
      "timestamp": "2024-01-16T09:15:00Z",
      "user": "manager@example.com",
      "reason": "Approved - looks good"
    }
  ]
}
```

---

## Event Sourcing

**Use case**: Maintaining complete audit trail, time-travel debugging, event replay, CQRS architecture.

### Core Concept

Instead of storing current state, store all events that led to that state.

**Traditional**:
```javascript
{
  "account_id": "ACC-123",
  "balance": 1000
}
```

**Event Sourced**:
```javascript
// Event stream
[
  {"event": "AccountCreated", "amount": 0, "timestamp": "..."},
  {"event": "FundsDeposited", "amount": 500, "timestamp": "..."},
  {"event": "FundsDeposited", "amount": 700, "timestamp": "..."},
  {"event": "FundsWithdrawn", "amount": 200, "timestamp": "..."}
]
// Current balance = sum of events = 1000
```

### Implementation Pattern

**Event Schema**:
```javascript
{
  "event_id": "uuid",
  "event_type": "UserRegistered",
  "aggregate_id": "USER-123",
  "aggregate_type": "User",
  "event_data": {
    "email": "user@example.com",
    "name": "John Doe"
  },
  "metadata": {
    "timestamp": "2024-01-15T10:30:00Z",
    "user_id": "admin",
    "ip_address": "192.168.1.1",
    "correlation_id": "COR-456"
  },
  "version": 1
}
```

**Write Path (Command)**:
```
1. Webhook Trigger (command received)
2. Validate command
3. Load current state (from events)
4. Apply business logic
5. Generate event(s)
6. Store event in event store (database/S3)
7. Publish event (webhook/queue)
8. Update read model (optional)
```

**Read Path (Query)**:
```
1. Query trigger
2. Read from read model (fast, denormalized)
3. OR rebuild state from events (slower, always accurate)
```

### Benefits

- **Complete audit trail**: Every change is recorded
- **Time travel**: Replay events to see state at any point
- **Event replay**: Rebuild state if corrupted
- **Multiple views**: Create different read models from same events
- **Debugging**: See exact sequence that led to current state

### Best Practices

1. **Events are immutable**: Never modify or delete events
2. **Events are facts**: Name events in past tense (UserRegistered, not RegisterUser)
3. **Version events**: Include schema version for evolution
4. **Idempotent event handlers**: Handle duplicate events gracefully
5. **Snapshot aggregates**: Periodically save state snapshots for performance

---

## Saga Pattern

**Use case**: Distributed transactions across multiple services/APIs where all steps must succeed or all must roll back.

### Problem

You need to:
1. Create order in Order Service
2. Reserve inventory in Inventory Service
3. Process payment in Payment Service
4. Send confirmation via Email Service

If payment fails, you must rollback the order and inventory reservation.

### Pattern Structure

**Forward transactions** + **Compensating transactions**

Each step has a compensation action:
- Create Order → Cancel Order
- Reserve Inventory → Release Inventory
- Process Payment → Refund Payment
- Send Email → Send Cancellation Email

### Implementation: Orchestration-Based Saga

**Main Workflow**:
```
1. Execute step 1 (Create Order)
   └─ IF success: continue
   └─ IF fail: end with error

2. Execute step 2 (Reserve Inventory)
   └─ IF success: continue
   └─ IF fail: compensate step 1, end

3. Execute step 3 (Process Payment)
   └─ IF success: continue
   └─ IF fail: compensate step 2, compensate step 1, end

4. Execute step 4 (Send Confirmation)
   └─ IF success: complete
   └─ IF fail: compensate step 3, compensate step 2, compensate step 1
```

**Function Node for Saga State**:
```javascript
// Track completed steps for compensation
const saga_state = $json.saga_state || {
  completed_steps: [],
  compensations_needed: []
};

const step = $json.current_step;
const success = $json.step_success;

if (success) {
  saga_state.completed_steps.push(step);
} else {
  // Failure: mark all completed steps for compensation in reverse
  saga_state.compensations_needed = saga_state.completed_steps.reverse();
}

return [{json: saga_state}];
```

**Compensation Workflow**:
```
1. Receive failed saga state
2. Loop through compensations_needed
3. For each step, call compensation API
4. Log compensation results
5. Send failure notification
```

### Best Practices

1. **Design compensations first**: Not all operations can be compensated
2. **Compensations must be idempotent**: May run multiple times
3. **Use unique transaction IDs**: For deduplication across retries
4. **Log everything**: Saga state, each step, compensations
5. **Set timeouts**: Don't wait forever for a step
6. **Handle partial failures**: What if compensation fails?

---

## Circuit Breaker

**Use case**: Prevent cascading failures when external service is down. Stop calling failing service to allow recovery.

### States

1. **Closed**: Normal operation, requests pass through
2. **Open**: Service failing, requests fail immediately (no calls made)
3. **Half-Open**: Testing if service recovered

### Pattern Implementation

**Using Workflow Static Data**:
```javascript
// Function node: Check Circuit Breaker State
const circuit_state = $workflow.staticData.circuit_breaker || {
  state: 'closed',
  failure_count: 0,
  last_failure_time: null,
  last_success_time: null
};

const failure_threshold = 5;  // Open after 5 failures
const timeout = 60000;  // Try recovery after 60 seconds
const now = Date.now();

// Determine current state
if (circuit_state.state === 'open') {
  // Check if timeout elapsed
  if (now - circuit_state.last_failure_time > timeout) {
    circuit_state.state = 'half-open';
  } else {
    // Circuit still open, fail fast
    return [{
      json: {
        circuit_open: true,
        allow_request: false,
        error: 'Circuit breaker is OPEN - service unavailable'
      }
    }];
  }
}

// Allow request
return [{
  json: {
    circuit_open: false,
    allow_request: true,
    state: circuit_state.state
  }
}];
```

**After API Call - Update Circuit State**:
```javascript
const circuit_state = $workflow.staticData.circuit_breaker;
const request_success = $json.api_success;
const now = Date.now();

if (request_success) {
  // Success: reset or close circuit
  circuit_state.failure_count = 0;
  circuit_state.last_success_time = now;
  
  if (circuit_state.state === 'half-open') {
    circuit_state.state = 'closed';
  }
} else {
  // Failure: increment count
  circuit_state.failure_count += 1;
  circuit_state.last_failure_time = now;
  
  if (circuit_state.failure_count >= 5) {
    circuit_state.state = 'open';
  }
}

$workflow.staticData.circuit_breaker = circuit_state;

return [circuit_state];
```

### Flow

```
1. Check Circuit Breaker state
2. IF circuit closed or half-open:
   ├─ Make API request
   ├─ Update circuit based on result
   └─ Return response
3. IF circuit open:
   └─ Return cached data or error immediately
```

---

## Fan-Out/Fan-In

**Use case**: Process data in parallel across multiple services/endpoints and aggregate results.

### Pattern Structure

**Fan-Out**: Split single input into multiple parallel paths
**Fan-In**: Merge multiple outputs back into single stream

### Example: Multi-Source Data Enrichment

Enrich customer data from multiple sources simultaneously:

```
1. Receive customer ID
2. Fan-Out (parallel execution):
   ├─ Get CRM data
   ├─ Get support ticket history
   ├─ Get payment history
   └─ Get social media data
3. Fan-In (Merge node)
4. Combine all data sources
5. Return enriched profile
```

**Benefits**:
- 3-4 APIs in parallel vs sequential: 66-75% time reduction
- Example: 4 APIs × 2 seconds each = 8s sequential, 2s parallel

### Implementation with n8n

**Method 1: Multiple branches from one node**
- Split → Branch 1, Branch 2, Branch 3, Branch 4
- Each branch processes independently
- Merge node combines results

**Method 2: Loop Over Items with parallel sub-workflows**
```
1. Loop Over Items (batch size = 1)
2. For each item:
   └─ Execute Workflow (sub-workflow handles parallel calls)
3. Aggregate results
```

**Merge Strategies**:

1. **Wait for all** (Merge node, Keep Only Set):
   - Only proceed when all branches complete
   - Use when all data is required

2. **First responder** (Merge node, Wait):
   - Proceed with first response
   - Use for redundancy or fastest source

3. **Merge on key** (Merge node, Merge By Key):
   - Combine objects with matching ID
   - Use for data enrichment

### Error Handling

**Problem**: If one branch fails, what happens?

**Solutions**:

1. **Continue on failure** at branch level:
   - Enable "Continue On Fail" for each HTTP Request
   - Check for errors in merge step
   - Proceed with partial data

2. **Timeout branches**:
   - Set reasonable timeouts (5-10s)
   - Don't wait forever for slow service

3. **Default values**:
   - If branch fails, use cached or default data
   - Include data freshness indicator

---

## Priority Queue Processing

**Use case**: Process items based on priority, not just arrival order.

### Pattern Structure

**Data Model**:
```javascript
{
  "id": "TASK-123",
  "priority": 1,  // 1 = highest, 5 = lowest
  "created_at": "2024-01-15T10:30:00Z",
  "data": {...}
}
```

### Implementation

**Option 1: Database-Backed Queue**

```
1. Schedule Trigger (every 1 minute)
2. HTTP Request → Query database
   - SELECT * FROM queue
     WHERE status = 'pending'
     ORDER BY priority ASC, created_at ASC
     LIMIT 10
3. Loop Over Items
4. Process each item
5. Update status to 'completed'
```

**Option 2: Webhook with Priority Sorting**

```
1. Webhook Trigger (receive item)
2. Store in workflow static data array
3. On separate Schedule Trigger (every 30s):
   ├─ Load queue from static data
   ├─ Sort by priority
   ├─ Process top N items
   └─ Remove from queue
```

**Function Node - Priority Sort**:
```javascript
let queue = $workflow.staticData.priority_queue || [];

// Add new item
if ($json.action === 'enqueue') {
  queue.push({
    id: $json.id,
    priority: $json.priority || 5,
    created_at: new Date().toISOString(),
    data: $json.data
  });
}

// Sort by priority (1 = highest), then by age
queue.sort((a, b) => {
  if (a.priority !== b.priority) {
    return a.priority - b.priority;
  }
  return new Date(a.created_at) - new Date(b.created_at);
});

$workflow.staticData.priority_queue = queue;

// Return top 10 for processing
return queue.slice(0, 10).map(item => ({json: item}));
```

### Best Practices

1. **Prevent starvation**: Low priority items eventually get processed
   - Age boost: Increase priority over time
   - Timeout: Auto-process after X minutes regardless

2. **Batch by priority**:
   - Process all P1 items first
   - Then P2, then P3, etc.

3. **Priority inheritance**:
   - Child tasks inherit parent's priority

---

## Idempotent Workflows

**Use case**: Ensure workflows can be safely retried without side effects (duplicate charges, multiple emails, etc.).

### Core Principle

**Same input + same operation = same output, regardless of how many times executed**

### Implementation Strategies

**1. Unique Request IDs**

```
1. Webhook receives request
2. Generate/extract unique ID
3. Check if ID already processed:
   ├─ Yes → Return cached result
   └─ No → Process request
4. Store ID + result in cache/database
5. Return result
```

**Function Node - Idempotency Check**:
```javascript
const request_id = $json.idempotency_key || $json.id;
const processed_requests = $workflow.staticData.processed || {};

if (processed_requests[request_id]) {
  // Already processed
  return [{
    json: {
      already_processed: true,
      result: processed_requests[request_id],
      message: 'Request already processed'
    }
  }];
}

// Not processed yet
return [{
  json: {
    already_processed: false,
    request_id: request_id
  }
}];
```

**2. Database Unique Constraints**

- Use database unique constraints on business keys
- Attempt INSERT, catch duplicate key errors
- If duplicate: return existing record

**3. Conditional Updates**

- Only update if current value matches expected
- Use WHERE clauses: `UPDATE ... WHERE version = ?`
- Prevents lost updates in concurrent scenarios

**4. State Checks Before Actions**

For APIs that aren't idempotent:

```javascript
// Check current state before acting
const current_status = await getOrderStatus(order_id);

if (current_status === 'paid') {
  // Already paid, skip payment
  return cached_result;
} else {
  // Not paid, process payment
  const result = await processPayment(order_id);
  return result;
}
```

### Best Practices

1. **Generate idempotency keys client-side**: Let clients provide UUIDs
2. **Cache results temporarily**: Store for 24 hours minimum
3. **Return same status code**: Always 200 for processed, even if cached
4. **Include metadata**: Indicate if result is from cache
5. **Handle race conditions**: Use database locks or atomic operations

---

## Advanced Tips

### Memory Management for Large Datasets

**Problem**: Processing 10,000+ items causes memory errors

**Solution - Chunked Processing**:
```
1. Database query with LIMIT/OFFSET
2. Process chunk (500 items)
3. Clear execution data
4. Repeat until no more records
```

**Function Node - Chunked Query**:
```javascript
const chunk_size = 500;
const offset = $json.offset || 0;

// This would be your actual query
const query = {
  limit: chunk_size,
  offset: offset
};

return [{
  json: {
    query: query,
    next_offset: offset + chunk_size,
    has_more: true  // Set based on actual results
  }
}];
```

### Distributed Locks

**Use case**: Prevent concurrent execution of same workflow

```javascript
// Acquire lock
const lock_key = `workflow:${$workflow.id}`;
const lock_acquired = await redis.set(lock_key, 'locked', 'NX', 'EX', 300);

if (!lock_acquired) {
  return [{json: {error: 'Workflow already running'}}];
}

// Process...

// Release lock
await redis.del(lock_key);
```

### Correlation IDs

Track requests across multiple workflows:

```javascript
const correlation_id = $json.correlation_id || uuidv4();

// Pass to all sub-workflows and external APIs
// Include in all log messages
// Use for debugging and tracing
```

---

This covers the most important advanced patterns. Combine these patterns as needed for complex enterprise workflows.
