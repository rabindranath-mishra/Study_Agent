---
title: "Agent Architecture (C4+1)"
date: 2026-03-21
tags:
  - architecture
  - system
  - c4
type: system
note_type: system
generated_by: copilot
---

# Agent Architecture (C4+1)

> **Model:** C4 + Scenarios view  
> **Scope:** Study Agent System — all agents, stores, data flows, and write gates  
> **Last updated:** 2026-03-21

---

## Contents

1. [Level 1 — System Context](#level-1--system-context)
2. [Level 2 — Container Diagram](#level-2--container-diagram)
3. [Level 3 — Component Diagram](#level-3--component-diagram)
4. [Level 4 — Code / Module Map](#level-4--code--module-map)
5. [+1 — Key Scenarios](#1--key-scenarios)
6. [Architecture Decisions](#architecture-decisions)

---

## Level 1 — System Context

> *Who uses the system and what external systems does it depend on?*

```
┌─────────────────────────────────────────────────────────────────────┐
│                       STUDY AGENT SYSTEM                            │
│  (Obsidian vault + AI orchestration layer)              │
└───────┬──────────────────────────────────────┬──────────────────────┘
        │                                      │
        │ queries / commands                   │ vault writes / reads
        ▼                                      ▼
┌───────────────────┐                 ┌────────────────────┐
│   STUDENT         │                 │   OBSIDIAN VAULT   │
│  (primary user)   │                 │  (markdown + YAML) │
│                   │                 │  (vault root)      │
│  Grade 9–12       │                 │   Study_Agent\     │
│  Board: CBSE /    │                 └────────────────────┘
│  ICSE / IB /      │
│  Cambridge        │
└───────────────────┘

External Dependencies
─────────────────────────────────────────────────────────────────
  ┌─────────────────────┐     ┌──────────────────────────────┐
  │   TAVILY API        │     │  SENTENCE TRANSFORMERS       │
  │  (web search)       │     │  all-MiniLM-L6-v2            │
  │  tavily.com         │     │  (local, 384-dim embeddings) │
  └─────────────────────┘     └──────────────────────────────┘

  ┌─────────────────────┐     ┌──────────────────────────────┐
  │   FAISS             │     │  POWERSHELL                  │
  │  (vector index)     │     │  (vault write via            │
  │  local flat index   │     │   create_note_stdin.ps1)     │
  └─────────────────────┘     └──────────────────────────────┘

  ┌─────────────────────┐
  │  GITHUB COPILOT CLI │
  │  (orchestrator UI)  │
  │  study.agent.md     │
  └─────────────────────┘
```

### Actors

| Actor | Type | Description |
|-------|------|-------------|
| **Student** | Human | Primary user — queries, studies, takes practice tests |
| **System Administrator** | Human | Sets up vault, creates initial profile |
| **Copilot CLI** | External System | AI orchestration runtime; reads `study.agent.md` |
| **Tavily API** | External System | Web search engine for educational content |
| **Sentence Transformers** | External Library | Local embedding model (no network call at inference) |
| **FAISS** | External Library | Local vector similarity search |
| **PowerShell** | External Runtime | File system operations for vault writes |

---

## Level 2 — Container Diagram

> *What are the major deployable/runnable building blocks?*

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STUDY AGENT SYSTEM                                 │
│                                                                             │
│  ┌──────────────────────┐    ┌─────────────────────────────────────────┐   │
│  │  ORCHESTRATION LAYER │    │            PYTHON RUNTIME               │   │
│  │                      │    │   00 - System/.agent/venv/              │   │
│  │  study.agent.md      │───▶│                                         │   │
│  │                      │    │   ┌─────────────┐  ┌────────────────┐   │   │
│  │  Defines:            │    │   │  Agents     │  │  State Stores  │   │   │
│  │  • 17 tools          │    │   │  (tools/*.py│  │  (tools/*.py)  │   │   │
│  │  • Routing rules     │    │   │             │  │                │   │   │
│  │  • Write gates       │    │   └──────┬──────┘  └───────┬────────┘   │   │
│  │  • Pedagogy rules    │    │          │                  │            │   │
│  └──────────────────────┘    └──────────┼──────────────────┼────────────┘   │
│                                         │                  │                │
│  ┌──────────────────────────────────────▼──────────────────▼────────────┐   │
│  │                         DATA LAYER                                    │   │
│  │                                                                       │   │
│  │  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐ │   │
│  │  │  FAISS INDEX      │  │   STATE FILES      │  │  VAULT MARKDOWN   │ │   │
│  │  │  .agent/          │  │   .agent/state/    │  │  01 - 07, 99      │ │   │
│  │  │  faiss_store/     │  │   *.json / *.jsonl │  │  *.md with YAML   │ │   │
│  │  └───────────────────┘  └───────────────────┘  └───────────────────┘ │   │
│  │                                                                       │   │
│  │  ┌───────────────────┐                                                │   │
│  │  │  LOGS             │                                                │   │
│  │  │  .agent/logs/     │                                                │   │
│  │  │  *.jsonl          │                                                │   │
│  │  └───────────────────┘                                                │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Containers

| Container | Technology | Responsibility |
|-----------|-----------|----------------|
| **Orchestration Layer** | `study.agent.md` (Copilot CLI spec) | Routes student intent → tools; enforces pedagogy and gate rules |
| **Python Runtime** | Python 3.9+, venv at `.agent/venv/` | Executes all agents and stores |
| **FAISS Index** | FAISS flat index + `metadata.jsonl` | Semantic search over 500+ vault passages |
| **State Files** | JSON / JSONL in `.agent/state/` | Learner profile, mastery, revision queue, exam calendar |
| **Vault Markdown** | Markdown + YAML frontmatter | Persistent knowledge base (Obsidian-compatible) |
| **Logs** | JSONL in `.agent/logs/` | Session and activity audit trail |

---

## Level 3 — Component Diagram

> *What are the components inside the Python Runtime container?*

```
                    Student Query
                         │
                         ▼
              ┌──────────────────────┐
              │   classify_task.py   │  ← regex signal matching
              │   5 task types       │    confidence scoring
              │   auto-escalation    │    escalate if < 0.7
              └──────┬───────────────┘
                     │ task_type + confidence
          ┌──────────┼────────────────────┐
          │          │                    │
          ▼          ▼                    ▼
  [simple_lookup] [research]        [note_creation]
          │          │                    │
          ▼          ▼                    ▼
  ┌───────────┐  ┌──────────────────┐  ┌──────────────────────────────┐
  │  vault_   │  │  vault_search_   │  │  teach_concept  OR           │
  │  search_  │  │  agent.py        │  │  practice_agent.py           │
  │  agent.py │  │  + web_search_   │  │                              │
  └───────────┘  │  agent.py        │  │  → note_content              │
                 └──────────────────┘  └──────────────┬───────────────┘
                                                       │
                                                       ▼
                                            ┌──────────────────────┐
                                            │  GATE 1              │
                                            │  fact_checker_       │
                                            │  agent.py            │
                                            │  └─ contradiction_   │
                                            │     check.py         │
                                            │  pass? ──────────────┼──── NO → reject
                                            └──────────────────────┘
                                                       │ YES
                                                       ▼
                                            ┌──────────────────────┐
                                            │  GATE 2              │
                                            │  compliance_         │
                                            │  agent.py            │
                                            │  10 Constitution     │
                                            │  checks              │
                                            │  PASS? ──────────────┼──── NO → reject + violations
                                            └──────────────────────┘
                                                       │ YES
                                                       ▼
                                            ┌──────────────────────┐
                                            │  note_writer_        │
                                            │  agent.py            │  ← ONLY write endpoint
                                            │  └─ create_note_     │
                                            │     stdin.ps1        │
                                            │  └─ index_vault.py   │  ← re-indexes new note
                                            └──────────────────────┘
                                                       │
                                                       ▼
                                               Written to vault
                                               + FAISS updated
```

### Component Catalogue

#### Routing

| Component | File | Responsibility |
|-----------|------|----------------|
| **Task Classifier** | `classify_task.py` | Parses query → task type + confidence; auto-escalates if confidence < 0.7 |

#### Retrieval

| Component | File | Responsibility |
|-----------|------|----------------|
| **Vault Search Agent** | `vault_search_agent.py` | Semantic vault search; returns findings + recommends web fallback if score < 0.6 |
| **FAISS Query** | `query_vault.py` | Low-level FAISS wrapper; top-k cosine similarity search |
| **Web Search Agent** | `web_search_agent.py` | Tavily API wrapper; educational source filtering |
| **Web Fetch** | `web_fetch.py` | Fetches and normalises full web page content |

#### Content Generation

| Component | File | Responsibility |
|-----------|------|----------------|
| **Teaching Agent** | `teaching_agent.py` | Level-adapted concept explanation; adapts to grade + learning_style; vault-first → web fallback (threshold 0.6) |
| **Practice Agent** | `practice_agent.py` | Generates 5 question types (MCQ, short_answer, long_answer, fill_blank, true_false); board-aware marking scheme |
| **Marking Scheme Store** | `marking_scheme_store.py` | Single source of truth for marking rules across CBSE, ICSE, IB, Cambridge, Generic |

#### Write Gates

| Component | File | Gate | Pass Condition |
|-----------|------|------|----------------|
| **Fact Checker** | `fact_checker_agent.py` | Gate 1 | `pass: true` — no vault contradictions (negation, numeric mismatch) |
| **Contradiction Check** | `contradiction_check.py` | Gate 1 (sub) | CLEAR or REVIEW verdict; CONFLICT → fails Gate 1 |
| **Compliance Agent** | `compliance_agent.py` | Gate 2 | `status: PASS` — all 10 Constitution checks pass |

#### Vault Write

| Component | File | Responsibility |
|-----------|------|----------------|
| **Note Writer Agent** | `note_writer_agent.py` | Only vault write endpoint; validates both gates internally; routes by note_type |
| **Create Note** | `create_note.py` + `create_note_stdin.ps1` | Atomic file creation via PowerShell |
| **Vault Indexer** | `index_vault.py` | Rebuilds FAISS index from all vault markdown; runs post-write |

#### Profile & State

| Component | File | Responsibility |
|-----------|------|----------------|
| **Profile Agent** | `profile_agent.py` | Interactive profile CRUD; writes student card to `01 - Inbox/` |
| **Learner Profile Store** | `learner_profile_store.py` | Read/write `learner-profile.json`; exposes `get_board()`, `get_grade()` |
| **Exam Calendar Store** | `exam_calendar_store.py` | Read/write `exam-calendar.json`; upcoming exam queries |
| **Activity Log Store** | `activity_log_store.py` | Append-only JSONL event log to `.agent/logs/` |

#### Infrastructure

| Component | File | Responsibility |
|-----------|------|----------------|
| **Path Constants** | `paths.py` | Single source of truth for all file system paths; derived from `__file__` location — vault-portable |
| **Generate Presentation** | `generate_presentation.py` | Renders vault markdown notes as HTML slide presentations |
| **Archive & Reset** | `archive_and_reset.py` | Batch-archives content folders to `99 - Archive/`; re-indexes |

---

## Level 4 — Code / Module Map

> *Key internal structures for the most complex modules.*

### `classify_task.py` — Signal Routing

```
Input: query string
  │
  ├─ NOTE_SIGNALS     (weight 0.9–1.0)  → note_creation
  ├─ VAULT_SIGNALS    (weight 0.7–0.9)  → vault_only
  ├─ RESEARCH_SIGNALS (weight 0.6–0.8)  → multi_topic_research / verified_research
  └─ LOOKUP_SIGNALS   (weight 0.5–0.7)  → simple_lookup
         │
  Confidence = Σ(matched weights) / max_possible
         │
  if confidence < 0.7 → escalate one tier
         │
Output: { task_type, confidence, escalated, signals_matched }
```

### `note_writer_agent.py` — Gate Enforcement

```
Inputs: title, content, note_type, fact_check_result, compliance_result
  │
  ├─ validate_fact_check(fact_check_result)
  │    fact_check_result.pass must be True          → else exit(2)
  │
  ├─ validate_compliance(compliance_result)
  │    compliance_result.status must be "PASS"      → else exit(3)
  │
  ├─ resolve_folder(note_type, explicit_folder)
  │    type → folder map (concept→04, practice→05, etc.)
  │
  ├─ write_note(title, content, folder)
  │    PowerShell create_note_stdin.ps1             → else exit(4)
  │
  └─ Output: { path, indexed, index_time_ms, gate_state }
```

### `practice_agent.py` — Question Generation

```
Profile → _resolve_context() → (difficulty, grade, board)
                │
                ▼
  Board → marking_scheme_store.get_scheme(board)
                │
                ├─ q_scheme   (mark bands: 1/2/3/5/8)
                ├─ mcq        (marking rule)
                ├─ fill_blank (marking rule)
                └─ true_false (marking rule)
                │
  Vault search → extract sentences, key_terms, list_items
                │
  _distribute_questions(total, types)
                │
  Generators:
    ├─ _make_mcq()          → 3 strategies (definition, list-item, key-term)
    ├─ _make_short_answer() → SAQ with value points
    ├─ _make_long_answer()  → LAQ with value points
    ├─ _make_fill_blank()   → blank out key terms in sentences
    └─ _make_true_false()   → true statements from content + false negations
                │
  _build_answer_key()  → per-question marking scheme attached
  _build_note_content() → Obsidian-ready markdown with frontmatter
                │
Output: { questions[], answer_key[], note_content, board, difficulty, ... }
```

### `teaching_agent.py` — Level Adaptation

```
Profile → grade → _GRADE_LEVEL_MAP → level (junior/senior/advanced)
                                    │
                         _LEVEL_INSTRUCTIONS[level] → system_prompt suffix
                                    │
Vault search (threshold 0.6)        │
  ├─ score ≥ 0.6 → vault_content   │
  └─ score < 0.6 → web_search()    │
                │                  │
  Compose response:                 │
    explanation  ← adapted to level ┘
    examples     ← concrete, age-appropriate
    key_points   ← exam-focused
    exam_tips    ← board-specific
    pedagogy     ← suggested next steps
    sources      ← vault refs + web URLs
```

---

## +1 — Key Scenarios

> *End-to-end walkthroughs of the most important use cases.*

---

### Scenario 1: Student asks "Explain photosynthesis"

```
Student: "Explain photosynthesis"
    │
    ▼
classify_task.py
  → signals: ["explain"] → simple_lookup (confidence 0.65)
  → escalate to vault_only (confidence < 0.7)
  → task_type: "vault_only"
    │
    ▼
vault_search_agent.py
  → query: "photosynthesis"
  → FAISS top score: 0.72  (≥ 0.6 threshold)
  → returns 5 vault findings from 04 - Concepts/
    │
    ▼
teaching_agent.py
  → profile: Grade 11, CBSE, learning_style: balanced
  → level: "senior" (Grade 11)
  → vault_score: 0.72 → use vault content (no web fallback)
  → adapts: formal language, board exam focus, definition + explanation + examples
    │
    ▼
Response to student (no vault write — read-only flow)
```

---

### Scenario 2: Student asks "Create a concept note on osmosis"

```
Student: "Create a concept note on osmosis"
    │
    ▼
classify_task.py
  → signals: ["create", "note", "concept"] → note_creation (confidence 0.95)
    │
    ▼
vault_search_agent.py
  → query: "osmosis"
  → FAISS top score: 0.58 (< 0.6 threshold)
    │
    ▼
web_search_agent.py (fallback)
  → Tavily query: "osmosis CBSE class 11"
  → returns 3 educational sources
    │
    ▼
teaching_agent.py
  → compose note_content (explanation + examples + key_points)
  → frontmatter: type: concept, subject: Biology, topic: Osmosis
    │
    ▼
fact_checker_agent.py  [GATE 1]
  → contradiction_check.py: k=8 vault chunks retrieved
  → no numeric mismatches, no negation patterns
  → verdict: CLEAR, pass: true ✓
    │
    ▼
compliance_agent.py  [GATE 2]
  → 10 checks: frontmatter ✓, type: concept ✓, subject: Biology ✓,
               H1 matches title ✓, no date prefix ✓, generated_by ✓, ...
  → status: PASS ✓
    │
    ▼
note_writer_agent.py
  → both gates verified internally
  → folder: 04 - Concepts/
  → create_note_stdin.ps1 writes file
  → index_vault.py re-indexes (514 passages)
    │
    ▼
Response: { path: "04 - Concepts/Osmosis.md", indexed: true, ... }
```

---

### Scenario 3: Student adds a new subject

```
Student: "Add Physics to my subjects"
    │
    ▼
classify_task.py → simple_lookup or vault_only
    │
    ▼
Orchestrator detects "add subject" intent → profile management flow
    │
    ▼
check_profile (check_profile_exists)
  → exists: true, student_name: "Shaatvik Mishra"
    │
    ▼
add_subject("Physics", difficulty="intermediate")
  → learner_profile_store.add_subject()
  → creates Physics-mastery.json (empty)
  → creates Physics-revision-queue.json (empty)
  → activity_log_store.log_event("subject_added", subject="Physics")
    │
    ▼
write_student_card()  [AUTO-TRIGGERED]
  → _build_student_card_content(updated_profile)
  → PowerShell writes "01 - Inbox/Student Card - Shaatvik Mishra.md"
  → card now shows 6 subjects including Physics
    │
    ▼
Response: { status: success, subject: Physics, all_subjects: [...] }
```

---

### Scenario 4: Practice question generation (board-aware)

```
Student: "Generate practice questions on the French Revolution"
    │
    ▼
generate_practice --topic "French Revolution" --subject History
    │
    ▼
practice_agent.py
  → _resolve_context(profile) → difficulty: intermediate, grade: 11, board: CBSE
  → marking_scheme_store.get_scheme("CBSE")
      q_scheme: { 1:..., 2:..., 3:..., 5:..., 8:... }
      mcq:       { note: "Full mark for correct answer only." }
      true_false: { marks_answer: 0.5, marks_justification: 0.5 }
    │
    ▼
vault_search_agent.py
  → score: 0.41 (< 0.6) → web fallback
  → web_search("French Revolution History CBSE class 11")
    │
    ▼
  Extract: sentences[], key_terms[], list_items[]
    │
    ▼
  Generate:
    3 × MCQ         (1 mark each, CBSE scheme)
    4 × short_answer (3 marks each, value points)
    2 × long_answer  (5 marks each, value points)
    2 × fill_blank   (1 mark each)
    3 × true_false   (1 mark each: 0.5+0.5)
    │
    ▼
  _build_answer_key() → CBSE value-point format per question
  _build_note_content() → Obsidian markdown ready for vault
    │
    ▼
Output: note_content written to 05 - Practice/ (after gates)
```

---

## Architecture Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| **AD-1** | `paths.py` as single source of truth for all paths | Vault-portable: moving the vault to any directory requires zero code changes |
| **AD-2** | Sequential fail-fast gates (Fact → Compliance → Write) | Prevents bad data from entering vault; Gate 2 never runs if Gate 1 fails |
| **AD-3** | `note_writer_agent.py` as the only vault write endpoint | Single point of enforcement; no agent can bypass gates |
| **AD-4** | Vault score threshold 0.6 for web fallback | Below 0.6 the vault content is not reliably relevant; web search adds marginal value above it |
| **AD-5** | Task auto-escalation at confidence < 0.7 | Low-confidence classification should err toward more thorough processing |
| **AD-6** | Board-aware marking via `marking_scheme_store.py` | Supporting multiple boards (CBSE, ICSE, IB, Cambridge) requires centralised scheme data |
| **AD-7** | Student card auto-refreshed on every profile mutation | Obsidian vault always reflects current profile without a separate sync step |
| **AD-8** | State in JSON/JSONL, not a database | Obsidian-first philosophy: all learner state lives inside the vault and is human-readable |
| **AD-9** | FAISS flat index (no IVF/HNSW) | Vault size (< 10,000 passages) makes exact search faster than approximate; no training step |
| **AD-10** | all-MiniLM-L6-v2 cached locally | No network dependency at inference time; works fully offline |

---

## Data Flow Summary

```
                    ┌─────────┐
                    │ Student │
                    └────┬────┘
                         │ query
                         ▼
              ┌───────────────────────┐
              │   classify_task.py    │
              └──────────┬────────────┘
                         │ task_type
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
    vault_search   web_search     note generation
          │              │         (teach / practice)
          │              │              │
          └──────────────┴──────────────┘
                         │ content
                         │
          ┌──────────────┼────────────────────┐
          │   read-only? │ vault write?        │
          ▼              ▼                     │
      respond        fact_checker              │
      directly       (Gate 1)                  │
                         │ pass                │
                         ▼                     │
                    compliance                 │
                    (Gate 2)                   │
                         │ PASS               │
                         ▼                     │
                    note_writer ◄──────────────┘
                         │
                         ▼
                  ┌─────────────┐
                  │  Vault .md  │
                  │  FAISS idx  │
                  └─────────────┘
```

---

*Generated by Copilot — Study Agent System, 2026-03-21*
