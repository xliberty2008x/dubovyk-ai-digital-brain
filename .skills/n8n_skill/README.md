# n8n Workflow Creator Skill

A comprehensive skill for building, debugging, and optimizing production-grade n8n workflows.

## Overview

This skill provides expert guidance for creating advanced n8n automations, including:
- Complex API integrations
- Event-driven workflows
- Multi-agent orchestration
- Production deployment best practices
- Debugging methodologies
- Performance optimization

## Structure

```
n8n-workflow-creator/
├── SKILL.md                           # Main skill document
├── scripts/
│   ├── api_prototype_template.py      # Template for API prototyping
│   └── debug_prototype_template.py    # Template for debugging logic
└── references/
    ├── advanced_patterns.md           # Advanced workflow patterns
    └── troubleshooting_guide.md       # Comprehensive troubleshooting
```

## When to Use This Skill

Use this skill when:
- Building n8n workflows from scratch
- Integrating complex or unfamiliar APIs
- Debugging workflow failures
- Implementing error handling and retries
- Optimizing workflow performance
- Setting up production deployments
- Designing event-driven architectures
- Creating ETL/ELT data pipelines

## Core Methodology

### 1. Building Workflows

**Start with architecture decisions:**
- Choose the right pattern (linear, event-driven, scheduled, ETL)
- Design modular sub-workflows from day one
- Plan error handling before implementation

**Follow best practices:**
- Use Execute Workflow nodes for reusable logic
- Implement node-level and workflow-level error handling
- Test incrementally as you build

### 2. API Integration (Critical)

**For unfamiliar APIs, prototype in Python first:**

1. Use `scripts/api_prototype_template.py`
2. Test authentication and endpoints
3. Document response structures
4. Validate rate limits and error formats
5. Move to n8n with confidence

This approach is 10-20x faster for API discovery.

### 3. Debugging Workflows

**When workflows fail:**

1. Use "Debug in editor" feature (Executions → Failed execution → Debug)
2. Classify error type (transient/permanent/data)
3. Isolate the problem by disabling nodes
4. Inspect execution logs carefully

**If stuck after multiple attempts:**
- Use `scripts/debug_prototype_template.py` to test logic in Python
- Ask user for execution screenshots
- Prototype transformations outside n8n

### 4. Production Readiness

Before deploying, verify:
- [ ] Error Trigger workflow configured
- [ ] Retry logic with exponential backoff
- [ ] Memory optimization via batching/sub-workflows
- [ ] Rate limiting handled
- [ ] Credentials use encrypted storage
- [ ] Webhook authentication enabled
- [ ] Monitoring and alerting configured

## Key Resources

### Scripts

**api_prototype_template.py**
- Quick API testing before n8n implementation
- Test authentication, endpoints, pagination, rate limits
- Document findings for n8n implementation

**debug_prototype_template.py**
- Debug complex transformations in Python
- Test with exact data from failed n8n executions
- Verify logic before translating to n8n

### Reference Documents

**advanced_patterns.md**
- Multi-agent orchestration
- State machines
- Event sourcing
- Saga pattern for distributed transactions
- Circuit breaker
- Fan-out/fan-in
- Priority queue processing
- Idempotent workflows

**troubleshooting_guide.md**
- Authentication errors (401/403)
- HTTP request failures (400/404/429/500)
- Expression errors
- Code node errors
- Webhook issues
- Performance problems
- Memory errors
- Data transformation issues

## Common Scenarios

### Scenario 1: Building a New Workflow

1. Read SKILL.md "Core Workflow Methodology"
2. Choose architectural pattern
3. Design sub-workflow structure
4. Implement incrementally
5. Add error handling as you build

### Scenario 2: API Integration

1. Use `scripts/api_prototype_template.py` first
2. Test authentication and endpoints
3. Document response structures
4. Implement in n8n with confidence
5. Reference SKILL.md "API R&D Methodology"

### Scenario 3: Debugging Failures

1. Use "Debug in editor" feature
2. Follow SKILL.md "Systematic Error Investigation"
3. Check `references/troubleshooting_guide.md` for specific errors
4. If stuck, use `scripts/debug_prototype_template.py`

### Scenario 4: Performance Issues

1. Check `references/troubleshooting_guide.md` → Performance Problems
2. Profile execution to find slow nodes
3. Apply optimizations from SKILL.md "Performance Optimization"
4. Consider patterns from `references/advanced_patterns.md`

### Scenario 5: Memory Errors

1. Check `references/troubleshooting_guide.md` → Memory Errors
2. Implement batching with Loop Over Items
3. Use sub-workflows to release memory
4. Consider paginated queries

## Installation

To use this skill with Claude:

1. Upload the entire `n8n-workflow-creator` folder to your Claude skills
2. Reference the skill when working on n8n projects
3. Claude will automatically use appropriate resources based on your needs

## Best Practices Summary

**Architecture:**
- Design modular from day one
- Use sub-workflows for reusable logic
- Plan for failure before success

**API Integration:**
- Prototype unfamiliar APIs in Python first
- Test thoroughly before implementing
- Document response structures and rate limits

**Error Handling:**
- Node-level: Retry On Fail (3-5 attempts)
- Workflow-level: Error Trigger workflows
- System-level: Dead-letter queues

**Performance:**
- Filter early in workflows
- Implement intelligent batching
- Leverage parallel processing
- Cache expensive operations

**Production:**
- Never hardcode credentials
- Use environment variables
- Implement monitoring and alerting
- Test in staging before production

## Version

- **Version:** 1.0
- **Last Updated:** 2025-01-27
- **Compatibility:** n8n v1.0+

## Support

For n8n-specific questions:
- n8n Documentation: https://docs.n8n.io
- n8n Community Forum: https://community.n8n.io
- n8n GitHub: https://github.com/n8n-io/n8n

## License

This skill is provided as-is for use with Claude. The templates and guides are free to use and modify for your n8n projects.
