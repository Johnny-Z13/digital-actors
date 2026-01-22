# Message Synchronization Analysis & Fix Plan

**Issue:** User input and NPC replies get out of sync in submarine scene

**Date:** 2026-01-22

---

## Current System Architecture

### Message Flow

```
User Types Message
    ↓
WebSocket receives 'user_message'
    ↓
handle_message() called
    ↓
① current_response_id = NEW_ID (cancels old responses)
② npc_responding = True
③ Add user message to dialogue_history
④ Call LLM (BLOCKING - takes 2-5 seconds!)
⑤ Check if current_response_id still matches
⑥ If stale: discard. If current: queue response
    ↓
ResponseQueue processes (2s min gap)
    ↓
NPC speaks
```

---

## Problems Identified

### 🔴 Problem 1: Multiple In-Flight LLM Calls

**File:** `web_server.py` Line 813-878

**Current Code:**
```python
async def handle_message(self, message: str) -> None:
    self.current_response_id = my_response_id  # ① Set cancellation token
    # ...
    chain = prompt_llm(prompt, DIALOGUE_MODEL)
    character_response = chain.invoke({})  # ② BLOCKING LLM CALL (2-5 seconds)

    if my_response_id != self.current_response_id:  # ③ Check if stale
        return  # Discard
```

**The Race Condition:**
1. User types "help" → LLM starts generating (response_id=1)
2. **While waiting 3 seconds for LLM...**
3. User types "oxygen valve" → LLM starts generating (response_id=2, cancels #1)
4. **While waiting 3 seconds for LLM...**
5. User types "ballast" → LLM starts generating (response_id=3, cancels #2)
6. LLM #1 finishes → sees stale response_id → discards
7. LLM #2 finishes → sees stale response_id → discards
8. LLM #3 finishes → current → sends

**Result:**
- 3 LLM API calls made (wasteful, expensive)
- User waits 9 seconds (3+3+3) before seeing ANY response
- Dialogue feels laggy and unresponsive

**Root Cause:** No mechanism to CANCEL in-flight LLM calls.

---

### 🔴 Problem 2: Background Responses Not Cancelled

**File:** `web_server.py` Line 1346-1382

Background responses can be triggered by:
- **Director hints** (line 1386)
- **Director events** (line 1390)
- **Waiting complete** (line 1346)

These use **ResponsePriority.BACKGROUND** but:
```python
if item.priority == ResponsePriority.BACKGROUND:
    self._queue = [r for r in self._queue if r.priority != ResponsePriority.BACKGROUND]
```

This only removes OTHER background responses, not responses already being generated.

**Scenario:**
1. Player waits 5 seconds (dots appear)
2. `handle_waiting_complete()` starts generating LLM response
3. Player types message
4. Waiting response finishes, gets queued
5. Player's response queues AFTER waiting response
6. NPC speaks about waiting, THEN responds to player message
7. **Out of sync!**

---

### 🔴 Problem 3: Opening Speech Can Be Interrupted

**File:** `web_server.py` Line 817

```python
if self.opening_speech_playing:
    logger.debug("Ignoring player message during opening speech")
    return
```

User CAN type during opening speech, but messages are silently dropped. Then:
- Opening speech finishes
- User doesn't know their message was dropped
- User types again
- Now TWO messages queue up
- Confusion ensues

---

### 🔴 Problem 4: Response Queue Doesn't Cancel In-Progress Generation

**File:** `response_queue.py` Line 149-162

```python
if supersede_lower_priority and item.priority <= ResponsePriority.NORMAL:
    self._queue = [r for r in self._queue if r.priority <= item.priority or not r.cancellable]
```

This removes items FROM THE QUEUE, but doesn't stop:
- LLM calls currently in-flight
- Responses currently being generated

**The ResponseQueue only manages delivery, not generation.**

---

### 🔴 Problem 5: No User Feedback During Generation

When user types a message:
- No "typing..." indicator
- No "generating response..." message
- User doesn't know if their input was received
- So they type again → creates more out-of-sync messages

---

## System State Diagram (Current)

```
[User]
  ↓ types "help"
[WebSocket] ─→ handle_message(response_id=1)
  ↓                        ↓
[LLM Call #1 starts]    [3 seconds...]
  ↓                        ↓
User types "valve"  ←──────┘
  ↓
[WebSocket] ─→ handle_message(response_id=2)
  ↓                        ↓
[LLM Call #2 starts]    [3 seconds...]
  ↓                        ↓
User types "ballast" ←─────┘
  ↓
[WebSocket] ─→ handle_message(response_id=3)
  ↓                        ↓
[LLM Call #3 starts]    [3 seconds...]
  ↓                        ↓
[LLM #1 done] → stale → discard
[LLM #2 done] → stale → discard
[LLM #3 done] → current → queue → send

TOTAL TIME: 9 seconds before first response!
```

---

## Solution Design

### ✅ Solution 1: Disable User Input During NPC Generation

**Simple, immediate fix:**

```python
# web_server.py - handle_message()
async def handle_message(self, message: str) -> None:
    # PREVENT RAPID-FIRE MESSAGES
    if self.npc_responding:
        await self.ws.send_json({
            'type': 'error',
            'message': 'Please wait for response...'
        })
        return

    self.npc_responding = True  # Block further input

    try:
        # ... existing code ...
    finally:
        self.npc_responding = False  # Re-enable input
```

**Pros:**
- Simple to implement
- Prevents ALL out-of-sync issues
- Eliminates wasted LLM calls

**Cons:**
- User can't interrupt NPC
- Less dynamic feeling

---

### ✅ Solution 2: Send "Typing..." Indicator Immediately

```python
async def handle_message(self, message: str) -> None:
    # Show typing indicator to user
    await self.ws.send_json({
        'type': 'npc_thinking',
        'character_name': self.character_config['name']
    })

    # ... rest of existing code ...
```

**Frontend change needed:**
```javascript
case 'npc_thinking':
    showTypingIndicator(data.character_name);
    break;
```

---

### ✅ Solution 3: Cancel Background Responses on User Input

```python
async def handle_message(self, message: str) -> None:
    # Clear all background responses immediately
    await self.response_queue.clear_background_responses()

    # Also cancel any waiting/director responses
    # ... existing code ...
```

---

### ✅ Solution 4: Disable Input During Opening Speech (UI-level)

Instead of silently dropping messages, disable the input field:

```python
# When sending opening speech:
await self.ws.send_json({
    'type': 'opening_speech',
    'disable_input': True,  # NEW
    'lines': lines_data
})

# When opening speech ends:
await self.ws.send_json({
    'type': 'enable_input'  # NEW
})
```

**Frontend:**
```javascript
case 'opening_speech':
    document.getElementById('userInput').disabled = true;
    break;
case 'enable_input':
    document.getElementById('userInput').disabled = false;
    break;
```

---

### ✅ Solution 5: Use LangChain Callbacks for Early Cancellation (Advanced)

```python
from langchain.callbacks.base import BaseCallbackHandler

class CancellableCallback(BaseCallbackHandler):
    def __init__(self, response_id_getter):
        self.response_id_getter = response_id_getter
        self.my_id = response_id_getter()

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        if self.my_id != self.response_id_getter():
            raise ValueError("Response cancelled")

# Usage:
chain = prompt_llm(prompt, DIALOGUE_MODEL)
callback = CancellableCallback(lambda: self.current_response_id)
character_response = chain.invoke({}, callbacks=[callback])
```

**This cancels LLM mid-generation!**

---

## Recommended Implementation (Phased Approach)

### Phase 1: Quick Wins (Immediate)

1. ✅ **Disable input during NPC response** (Solution 1)
   - Prevents all out-of-sync issues
   - Simple, 5-line change

2. ✅ **Add "typing..." indicator** (Solution 2)
   - User feedback
   - Shows system is working

3. ✅ **Cancel background responses** (Solution 3)
   - Prevents director/waiting responses from queuing up

4. ✅ **Disable input during opening speech** (Solution 4)
   - Better UX than silent drops

### Phase 2: Advanced (Future Enhancement)

5. ⚠️ **Early LLM cancellation** (Solution 5)
   - Requires LangChain streaming support
   - More complex implementation
   - Significant performance improvement

---

## Implementation Code

### Fix 1: Block User Input During NPC Response

```python
# web_server.py - line 813
async def handle_message(self, message: str) -> None:
    """Handle a user message and generate a response."""
    try:
        # Don't respond if opening speech is still playing
        if self.opening_speech_playing:
            logger.debug("[OPENING_SPEECH] Ignoring message during opening speech")
            return

        # IMPORTANT: Block rapid-fire messages while NPC is responding
        if self.npc_responding:
            logger.debug("[SYNC] Ignoring message - NPC still responding to previous message")
            await self.ws.send_json({
                'type': 'system_notification',
                'message': '⏳ Please wait for response...'
            })
            return

        # Show typing indicator
        await self.ws.send_json({
            'type': 'npc_thinking',
            'character_name': self.character_config['name']
        })

        # Claim a new response ID - this cancels any pending responses
        self.response_sequence += 1
        my_response_id = self.response_sequence
        self.current_response_id = my_response_id

        # Clear any background responses (director hints, waiting responses)
        await self.response_queue.clear_background_responses()

        self.npc_responding = True  # Mark that NPC is responding

        # ... rest of existing code unchanged ...
```

### Fix 2: Opening Speech Disables Input

```python
# web_server.py - send_opening_speech()
await self.ws.send_json({
    'type': 'opening_speech',
    'character_name': self.character_config['name'],
    'lines': lines_data,
    'disable_input': True  # NEW
})

# After opening speech finishes:
async def reset_opening_speech_flag():
    await asyncio.sleep(total_blocking_time)
    self.opening_speech_playing = False

    # Re-enable input
    await self.ws.send_json({
        'type': 'enable_input'
    })
```

### Fix 3: Frontend Changes

```javascript
// app.js
case 'npc_thinking':
    showTypingIndicator(data.character_name);
    break;

case 'opening_speech':
    userInput.disabled = data.disable_input || false;
    // ... existing opening speech handling ...
    break;

case 'enable_input':
    userInput.disabled = false;
    hideTypingIndicator();
    break;

function showTypingIndicator(characterName) {
    const indicator = document.createElement('div');
    indicator.id = 'typing-indicator';
    indicator.className = 'typing-indicator';
    indicator.textContent = `${characterName} is thinking...`;
    chatMessages.appendChild(indicator);
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
}
```

---

## Testing Plan

### Test 1: Rapid Message Entry
1. Start submarine scene
2. Type "help" + Enter
3. IMMEDIATELY type "oxygen valve" + Enter
4. IMMEDIATELY type "ballast" + Enter

**Expected:**
- Second and third messages show "Please wait..." notification
- Only first message gets response
- No out-of-sync

### Test 2: Opening Speech
1. Start Crown Court scene
2. Try to type during Judge's opening remarks

**Expected:**
- Input field is disabled
- Cannot type until speech ends
- Clear UX

### Test 3: Background Responses
1. Start submarine scene
2. Wait 5 seconds (trigger waiting_complete)
3. IMMEDIATELY type message

**Expected:**
- Waiting response is cancelled
- User message gets response
- No out-of-sync

---

## Success Criteria

✅ User cannot type while NPC is generating response
✅ User sees "typing..." indicator during generation
✅ Background responses are cancelled when user sends message
✅ Opening speech blocks input with clear UI feedback
✅ No wasted LLM API calls
✅ Responses always match most recent user input
✅ System feels responsive and predictable

---

*Analysis Complete - Ready for Implementation*
