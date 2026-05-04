---
name: conversation-monitor
description: Monitor ongoing conversations, decide when to reply vs continue monitoring vs ignore
trigger: When in MONITOR state after extracting a message, to determine next action
---

## Conversation Monitoring Strategy

### Decision Flow
After extracting a message, decide one of:
1. **REPLY** - Generate and send a response
2. **MONITOR** - Stay on current chat, wait for more messages
3. **IGNORE** - Move on, no action needed

### When to REPLY
- Customer asked a direct question
- Customer provided information that requires acknowledgment
- There's an unresolved issue or pending action item
- The conversation is active (messages within last 2 minutes)

### When to MONITOR
- Customer seems to be typing more (frequent new messages)
- The last message is ambiguous or incomplete
- You're in the middle of a multi-step interaction
- Less than 30 seconds since the last message

### When to IGNORE
- Message is spam, advertisement, or irrelevant
- Customer clearly ended the conversation (e.g., "谢谢", "好的", "再见")
- The same message has already been handled
- Contact is not in the active contact list

### Timeout
Return to CLEANUP after `monitor_timeout` seconds (default: 300s) of no new messages.
