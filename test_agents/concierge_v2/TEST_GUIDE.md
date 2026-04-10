# Phase 1d — Test Guide

Run the multi-agent system:
```bash
pip install google-adk --break-system-packages -q
cd ~/The-Continental-Concierge
git pull origin main          # stays clean after the reset above
adk web test_agents/
```

---

## What You're Testing

Each test query below targets a specific routing path.
Watch the **agent activity panel** on the left — you should see which
sub-agent was called for each query. That's how you confirm routing works.

---

## Step 1 — Archivist Routing

These queries should always transfer to the `archivist` first,
then hand off to the `narrator` for prose output.

```
Who is Winston Scott?
Tell me about Charon.
What is the rule about sanctuary?
What do we know about the Baba Yaga legend?
What happened to Santino D'Antonio?
What are the rules about markers?
```

**What to verify:**
- The agent panel shows `archivist` was invoked.
- The archivist calls a tool (`lookup_character`, `lookup_rule`, `search_lore`).
- The response is rich prose, NOT a JSON blob — that's the narrator finishing.
- John Wick's response always mentions "excommunicado."

---

## Step 2 — Narrator Discipline

These queries test that the **Orchestrator itself never produces prose**.
Every answer must go through the `narrator`.

```
What's going on?
Give me the situation report.
```

**What to verify:**
- The `narrator` is ALWAYS the last agent called before the response.
- The Orchestrator never directly answers — it always transfers.
- The prose uses second-person present tense ("You notice...", "The phone rings...").
- The response ends with 2-4 suggested actions the player can take.

---

## Step 3 — Ledger Routing

```
Does John Wick owe anyone a marker?
What markers are outstanding right now?
What's Sofia's reputation?
What's the relationship between John and Winston?
Should I trust Sofia?
```

**What to verify:**
- `ledger` is invoked with the right tool (`get_markers`, `check_marker_between`, etc.).
- The outstanding markers (John → Winston, Sofia → John) are mentioned.
- John's risk assessment returns "critical" due to excommunicado status.

---

## Step 4 — Timeline Routing

```
What's happening right now?
Where is John Wick?
Where is the Adjudicator?
What's the current crisis level?
Are there any dangerous situations I should know about?
What deadlines are coming up?
```

**What to verify:**
- `timeline` is invoked.
- `detect_collisions()` fires — it should flag severity 9 (John on grounds).
- The response reflects alert level 8 and the Adjudicator's presence.
- The Narrator's prose pacing should be tense/urgent (crisis ≥ 7).

---

## Step 5 — Multi-Agent Routing (The Real Test)

These queries require two or three specialists before the narrator:

```
Tell me everything about John Wick — who he is, what he owes, and where he is now.
```
Expected: `archivist` → `ledger` → `timeline` → `narrator`

```
A guest named Sofia has arrived. What do I need to know before I let her in?
```
Expected: `archivist` (who is she?) → `ledger` (reputation + markers) → `narrator`

```
What is the current situation with the Adjudicator investigation?
```
Expected: `timeline` (where is she, what's happening) → `archivist` (what is the adjudicator?) → `narrator`

**What to verify:**
- Multiple agents appear in the activity panel.
- The final narrative weaves data from multiple sources naturally.
- The suggested_actions in the response are coherent and grounded in the data.

---

## What Good Routing Looks Like

```
Player: "Who is Winston?"

Agent panel:
  concierge_orchestrator → routes to archivist
  archivist → calls lookup_character("winston") → returns structured data
  concierge_orchestrator → routes to narrator with archivist output
  narrator → calls get_character_voice("winston") → renders prose

Response (narrator output):
  "The elevator opens onto the manager's floor and you find yourself
   outside a door that the rest of the hotel pretends doesn't exist.
   Winston Scott has run this establishment since before most of your
   guests were born. His reputation in the community sits at ninety —
   the kind of number that accumulates only through a combination of
   genuine authority and the quiet willingness to use it..."
```

---

## What Bad Routing Looks Like (Bugs to Watch For)

| Symptom | Likely Cause | Fix |
|---|---|---|
| Orchestrator answers directly with facts | Routing prompt too weak | Add "YOU NEVER WRITE PROSE" more forcefully |
| Narrator outputs raw JSON | Narrator prompt not enforcing prose conversion | Strengthen narrator's prime directive |
| Wrong agent called (e.g., ledger for "who is Winston") | Routing table unclear | Add more routing examples to orchestrator prompt |
| Sub-agent called but no narrator follow-up | Orchestrator forgets to transfer to narrator | Add "always end with narrator" to orchestrator |
| Response ignores excommunicado status | Archivist not flagging it | Check `warnings` field is being passed to narrator |

---

## Iteration Notes

After each test, ask yourself:
1. **Did the right agent(s) get called?** (Check the agent panel)
2. **Did the narrator always speak last?** (Prose discipline test)
3. **Was the data accurate?** (Mock data verification)
4. **Were suggested actions sensible?** (Narrative quality)

Fix prompt issues here, in this test environment — before you touch AlloyDB
or Agent Engine. Every hour you spend here saves three hours debugging in prod.
