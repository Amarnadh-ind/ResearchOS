# DEBUG_REPORT.md

## Frontend Click Flow Analysis

### 1. Start Button Rendered By
**File:** `frontend/src/components/research/PromptInput.tsx`  
**Line:** 48-60  
**Component:** `<button type="submit" id="research-submit-btn">` inside a `<form onSubmit={handleSubmit}>`

### 2. Click Handler Chain

| Step | File | Line | Function | Purpose |
|------|------|------|----------|---------|
| 1 | PromptInput.tsx | 18-24 | `handleSubmit(e)` | Form submit handler - calls `e.preventDefault()`, validates prompt length ≥ 10, opens confirm modal |
| 2 | PromptInput.tsx | 26-32 | `handleConfirm()` | Confirm modal "start" button - calls `onSubmit()` prop with hardcoded params |
| 3 | useResearch.ts | 221-250 | `startResearch()` | Calls `api.startResearch()`, stores session ID, sets status to "pending" |
| 4 | api.ts | 34-38 | `api.startResearch()` | POST to `/api/research` via `fetcher()` |
| 5 | api.ts | 6-31 | `fetcher()` | Generic fetch wrapper with timeout, error handling |

### 3. Debug Logs Added

```
[DEBUG] BUTTON_CLICKED           - PromptInput.tsx:20  - Form submit button clicked
[DEBUG] MODAL_OPENING            - PromptInput.tsx:22  - Confirm modal opened
[DEBUG] MODAL_RENDERED           - PromptInput.tsx:102 - Confirm modal rendered
[DEBUG] START_RESEARCH_CALLED    - PromptInput.tsx:27  - handleConfirm() invoked
[DEBUG] START_RESEARCH_CALLED    - useResearch.ts:223  - useResearch.startResearch() invoked
[DEBUG] API_REQUEST_SENT         - useResearch.ts:234  - api.startResearch() called
[DEBUG] FETCH START              - api.ts:12           - fetch() initiated
[DEBUG] FETCH RESPONSE           - api.ts:18           - fetch() response received
[DEBUG] FETCH SUCCESS            - api.ts:24           - JSON parsed successfully
[DEBUG] API_RESPONSE_RECEIVED    - useResearch.ts:236  - Response processed
```

### 4. Potential Failure Points Identified

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **Modal doesn't open** - `showConfirm` state not updating | PromptInput.tsx:16,22 | HIGH |
| 2 | **Modal closes before request** - `setShowConfirm(false)` before `onSubmit()` | PromptInput.tsx:30 | MEDIUM |
| 3 | **isRunning stale** - Prop not updated in time | PromptInput.tsx:21,28 | HIGH |
| 4 | **Button disabled** - `prompt.trim().length < 10` check | Prompt | PromptInput.tsx:21,51 | HIGH |
| 5 | **API error swallowed** - catch block only sets status failed | useResearch.ts:244 | MEDIUM |
| 6 | **Wrong params passed** - Hardcoded layout "Double Column IEEE (Default)" vs expected "2 Column" | PromptInput.tsx:27 | LOW |

### 5. Root Cause Hypothesis

The flow is:
1. User types prompt → clicks "research" button (type="submit")
2. `handleSubmit()` fires → checks `prompt.trim().length >= 10 && !isRunning`
3. If valid → `setShowConfirm(true)` opens modal
4. User clicks "start" in modal → `handleConfirm()` fires
5. `handleConfirm()` calls `onSubmit(prompt, depth, maxSources, 12, "2 Column", "Times New Roman", "Auto Generate")`
6. This invokes `useResearch.startResearch()` which calls `api.startResearch()`

**Critical Issues Found & Fixed:**

| Issue | Location | Fix Applied |
|-------|----------|-------------|
| **CORS mismatch** | settings.py:34 | ✅ Added `http://localhost:3001` and `http://127.0.0.1:3001` |
| **Layout param mismatch** | PromptInput.tsx:27 | ✅ Changed to `"2 Column"` |
| **Modal closes before request** | PromptInput.tsx:30 | Not fixed yet - but `setShowConfirm(false)` is after `onSubmit()` call |

### 6. Fixes Applied

1. ✅ **CORS origins** - Added `http://localhost:3001` and `http://127.0.0.1:3001` to settings.py:34 (backend restart required)
2. ✅ **Layout parameter** - Changed `"Double Column IEEE (Default)"` to `"2 Column"` in PromptInput.tsx:27
3. ✅ **Debug instrumentation** - Added console logs at every step of the click flow
4. ✅ **Build verified** - Frontend builds successfully

### 7. Current Status

**Backend:** Running on port 8000 with CORS fix  
**Frontend:** Running on port 3001 with debug logs  
**Build:** ✅ Successful

### 8. Test Instructions

1. Open http://localhost:3001 in browser
2. Open DevTools → Console
3. Type a prompt ≥10 characters (e.g., "transformer architectures")
4. Click "research" button
5. Click "start" in the confirm modal
6. Observe console logs in order:
   ```
   [DEBUG] BUTTON_CLICKED
   [DEBUG] MODAL_OPENING
   [DEBUG] MODAL_RENDERED
   [DEBUG] START_RESEARCH_CALLED from handleConfirm
   [DEBUG] START_RESEARCH_CALLED in useResearch
   [DEBUG] API_REQUEST_SENT
   [DEBUG] FETCH START
   [DEBUG] FETCH RESPONSE
   [DEBUG] FETCH SUCCESS
   [DEBUG] API_RESPONSE_RECEIVED
   ```

### 9. If Still Not Working

Check for these failure modes in console:
- **No logs at all** → Button click not captured (check form submission)
- **Stops at BUTTON_CLICKED** → Prompt too short or isRunning=true
- **Stops at MODAL_OPENING** → Modal state issue
- **Stops at START_RESEARCH_CALLED** → onSubmit prop not connected
- **Stops at FETCH START** → Network error / CORS
- **Stops at FETCH RESPONSE with error** → Backend error (check backend logs)

---

**Status:** All critical frontend fixes applied. Ready for live testing.