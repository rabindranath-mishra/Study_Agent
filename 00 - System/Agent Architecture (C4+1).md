---
title: "Agent Architecture (C4+1)"
date: 2026-03-22
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
> **Last updated:** 2026-03-22

---

## Introduction

The Study Agent System is a multi-agent AI learning infrastructure built on Obsidian. It is designed as pedagogically-rigorous learning infrastructure — not a general-purpose chatbot — to help students achieve mastery through structured, repeatable study workflows.

The system orchestrates specialist agents (teaching, practice, fact-checking, compliance, profile, vault search, web search, indexing, and note writing) via a Copilot CLI specification (`study.agent.md`). The **Copilot CLI agent is the LLM** — Python tools are pure data fetchers and gate keepers. The LLM acts as the **Master Elaborator**, transforming raw tool output into rich, structured Learning Modules, and as the **Socratic Tutor**, guiding students to understanding through probing questions rather than direct answers. Every persistent learning artifact is written to an Obsidian vault as a Markdown note with YAML frontmatter, making all outputs human-readable, inspectable, and linkable inside the student's knowledge graph.

Four binding constraints govern the architecture:

- **Vault Constitution v1.2** — governing rules defining note standards, metadata doctrine, write governance, educational behaviour, and Obsidian-native linking
- **Sequential write-gate pipeline** — fact-check (Gate 1) then compliance (Gate 2) then write; fail-fast, no skipping
- **Single write endpoint** — `note_writer_agent.py` enforces both gates at code level; no agent or developer may bypass it
- **Obsidian wikilink standard** — all internal vault references use `[[wikilink]]` syntax (§V rule 8); source traceability requires `[Title](URL)` for web and `[[note]]` for vault references (§X rule 6)

---

## Contents

1. [Level 1 — System Context](#level-1--system-context)
2. [Level 2 — Container Diagram](#level-2--container-diagram)
3. [Level 3 — Component Diagram](#level-3--component-diagram)
4. [Level 4 — Code / Module Map](#level-4--code--module-map)
5. [+1 — Key Scenarios](#1--key-scenarios)
6. [Architecture Decisions](#architecture-decisions)
7. [Data Flow Summary](#data-flow-summary)

---

## Level 1 — System Context

> *Who uses the system and what external systems does it depend on?*

```mermaid
graph LR
    Student["👨‍🎓 Student<br/>Grade 9-12<br/>CBSE / ICSE / IB / Cambridge"]
    Admin["⚙️ System Admin<br/>setup and config"]

    subgraph SAS["Study Agent System"]
        CLI["GitHub Copilot CLI<br/>study.agent.md"]
        PY["Python Runtime<br/>.agent/venv/"]
        VAULT["Obsidian Vault<br/>markdown + YAML frontmatter"]
    end

    subgraph EXT["External Systems"]
        Tavily["Tavily API<br/>web search"]
        ST["Sentence Transformers<br/>all-MiniLM-L6-v2<br/>384-dim embeddings"]
        FAISS_LIB["FAISS<br/>local flat index"]
        PS["PowerShell<br/>create_note_stdin.ps1"]
    end

    Student -- "queries / studies" --> CLI
    Admin -- "configures vault" --> VAULT
    CLI -- "invokes tools" --> PY
    PY -- "reads / writes" --> VAULT
    PY -- "web search" --> Tavily
    PY -- "embed queries" --> ST
    PY -- "vector search" --> FAISS_LIB
    PY -- "vault writes" --> PS
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

```mermaid
graph TB
    subgraph SAS["Study Agent System"]
        subgraph ORCH["Orchestration Layer"]
            SAMD["study.agent.md<br/>17+ tools · routing rules<br/>Master Elaborator · Socratic Tutor<br/>write gates · pedagogy rules"]
        end

        subgraph PY["Python Runtime (.agent/venv/)"]
            Agents["Agents<br/>teaching · practice · fact-check<br/>compliance · profile · search"]
            Stores["State Stores<br/>profile · exam-calendar · activity-log"]
        end

        subgraph DATA["Data Layer"]
            FAISS_IDX["FAISS Index<br/>.agent/faiss_store/<br/>500+ passages"]
            STATE_F["State Files<br/>.agent/state/<br/>*.json / *.jsonl"]
            VAULT_MD["Vault Markdown<br/>01-07 · 99<br/>*.md + YAML frontmatter"]
            LOGS_F["Logs<br/>.agent/logs/<br/>*.jsonl"]
        end
    end

    SAMD -- "tool invocations" --> Agents
    SAMD -- "state queries" --> Stores
    Agents -- "semantic search" --> FAISS_IDX
    Agents -- "read / write state" --> STATE_F
    Stores -- "read / write state" --> STATE_F
    Agents -- "write notes (via gates)" --> VAULT_MD
    Agents -- "append events" --> LOGS_F
```

### Containers

| Container | Technology | Responsibility |
|-----------|-----------|----------------|
| **Orchestration Layer** | `study.agent.md` (Copilot CLI spec) | Routes student intent to tools; the CLI agent IS the LLM — acts as Master Elaborator (transforms raw tool JSON into Learning Modules) and Socratic Tutor; enforces pedagogy and gate rules |
| **Python Runtime** | Python 3.9+, venv at `.agent/venv/` | Executes all agents and stores |
| **FAISS Index** | FAISS flat index + `metadata.jsonl` | Semantic search over 500+ vault passages |
| **State Files** | JSON / JSONL in `.agent/state/` | Learner profile, mastery, revision queue, exam calendar |
| **Vault Markdown** | Markdown + YAML frontmatter | Persistent knowledge base (Obsidian-compatible) |
| **Logs** | JSONL in `.agent/logs/` | Session and activity audit trail |

---

## Level 3 — Component Diagram

> *What are the components inside the Python Runtime container?*

```mermaid
flowchart TD
    Q(["Student Query"])
    CT["classify_task.py<br/>5 task types · confidence scoring<br/>auto-escalate if confidence below 0.7"]

    Q --> CT
    CT -- "simple_lookup" --> VS1["vault_search_agent.py"]
    CT -- "research" --> VS2["vault_search_agent.py<br/>+ web_search_agent.py"]
    CT -- "note_creation" --> GEN["teach_concept<br/>OR practice_agent.py<br/>→ raw JSON + raw_content[]"]

    VS1 --> R1(["Respond to student<br/>read-only flow"])
    VS2 --> R2(["Respond to student<br/>read-only flow"])

    GEN --> ELAB["LLM Master Elaborator<br/>raw_content[] → Learning Module<br/>Hook · Concept Map · Layered Explanation<br/>Examples · Analogy · Exam Corner · Self-Check"]
    ELAB --> G1{"GATE 1<br/>fact_checker_agent.py<br/>contradiction_check.py"}
    G1 -- "FAIL" --> REJ1(["Reject<br/>report conflict to student"])
    G1 -- "PASS" --> G2{"GATE 2<br/>compliance_agent.py<br/>10 Constitution checks"}
    G2 -- "FAIL" --> REJ2(["Return violations<br/>fix and re-run"])
    G2 -- "PASS" --> NW["note_writer_agent.py<br/>ONLY write endpoint<br/>create_note_stdin.ps1<br/>index_vault.py"]
    NW --> VAULT(["Written to vault<br/>FAISS index updated"])
```

### Component Catalogue

#### Routing

| Component | File | Responsibility |
|-----------|------|----------------|
| **Task Classifier** | `classify_task.py` | Parses query to task type + confidence; auto-escalates if confidence < 0.7 |

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
| **Teaching Agent** | `teaching_agent.py` | Level-adapted concept explanation; adapts to grade + learning_style; vault-first with web fallback at threshold 0.6; returns `raw_content[]` (full unprocessed vault/web chunks) for LLM elaboration alongside `explanation`, `examples`, `key_points`, `exam_tips` |
| **Practice Agent** | `practice_agent.py` | Generates 5 question types (MCQ, short_answer, long_answer, fill_blank, true_false); board-aware marking scheme |
| **Marking Scheme Store** | `marking_scheme_store.py` | Single source of truth for marking rules across CBSE, ICSE, IB, Cambridge, Generic |

#### Write Gates

| Component | File | Gate | Pass Condition |
|-----------|------|------|----------------|
| **Fact Checker** | `fact_checker_agent.py` | Gate 1 | `pass: true` — no vault contradictions (negation, numeric mismatch) |
| **Contradiction Check** | `contradiction_check.py` | Gate 1 (sub) | CLEAR or REVIEW verdict; CONFLICT fails Gate 1 |
| **Compliance Agent** | `compliance_agent.py` | Gate 2 | `status: PASS` — all 10 Constitution checks pass; valid types include `learning-module` (added 2026-03-22) |

#### Vault Write

| Component | File | Responsibility |
|-----------|------|----------------|
| **Note Writer Agent** | `note_writer_agent.py` | Only vault write endpoint; validates both gates internally; routes by note_type — `concept` + `learning-module` → `04 - Concepts`, `practice` → `05 - Practice`, `revision-plan` + `exam` → `06 - Plans` |
| **Create Note** | `create_note.py` + `create_note_stdin.ps1` | Atomic file creation via PowerShell |
| **Vault Indexer** | `index_vault.py` | Rebuilds FAISS index from all vault markdown; runs post-write |

#### Profile and State

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
| **Archive and Reset** | `archive_and_reset.py` | Batch-archives content folders to `99 - Archive/`; re-indexes |

---

## Level 4 — Code / Module Map

> *Key internal structures for the most complex modules.*

### `classify_task.py` — Signal Routing

```mermaid
flowchart TD
    IN(["Input: query string"])

    subgraph SIGNALS["Signal Matching"]
        NS["NOTE_SIGNALS<br/>weight 0.9-1.0<br/>→ note_creation"]
        VS["VAULT_SIGNALS<br/>weight 0.7-0.9<br/>→ vault_only"]
        RS["RESEARCH_SIGNALS<br/>weight 0.6-0.8<br/>→ research"]
        LS["LOOKUP_SIGNALS<br/>weight 0.5-0.7<br/>→ simple_lookup"]
    end

    IN --> SIGNALS
    SIGNALS --> CONF["Confidence = sum of matched weights / max_possible"]
    CONF --> ESC{"confidence below 0.7?"}
    ESC -- "yes" --> ESCL["escalate one tier"]
    ESC -- "no" --> OUT
    ESCL --> OUT(["Output: task_type<br/>confidence · escalated · signals_matched"])
```

### `note_writer_agent.py` — Gate Enforcement

```mermaid
flowchart TD
    IN(["Inputs: title · content<br/>note_type · fact_check_result · compliance_result"])

    IN --> VFC["validate_fact_check<br/>pass must be True"]
    VFC -- "fail" --> E2(["exit 2 — Gate 1 not passed"])
    VFC -- "ok" --> VCC["validate_compliance<br/>status must be PASS"]
    VCC -- "fail" --> E3(["exit 3 — Gate 2 not passed"])
    VCC -- "ok" --> RF["resolve_folder<br/>concept + learning-module→04<br/>practice→05 · revision-plan→06"]
    RF --> WN["write_note<br/>create_note_stdin.ps1"]
    WN -- "fail" --> E4(["exit 4 — note write failed"])
    WN -- "ok" --> IDX["index_vault.py<br/>rebuild FAISS index"]
    IDX --> OUT(["Output: path · indexed<br/>index_time_ms · gate_state"])
```

### `practice_agent.py` — Question Generation

```mermaid
flowchart TD
    PROF(["Student Profile"])
    PROF --> CTX["_resolve_context<br/>difficulty · grade · board"]
    CTX --> MSS["marking_scheme_store.get_scheme<br/>q_scheme · mcq · fill_blank · true_false"]
    CTX --> VS["Vault search<br/>sentences · key_terms · list_items"]
    VS --> DQ["_distribute_questions<br/>total across types"]
    MSS --> GEN
    DQ --> GEN["Question Generators"]

    GEN --> MCQ["_make_mcq<br/>definition · list-item · key-term strategies"]
    GEN --> SA["_make_short_answer<br/>SAQ + value points"]
    GEN --> LA["_make_long_answer<br/>LAQ + value points"]
    GEN --> FB["_make_fill_blank<br/>blank key terms in sentences"]
    GEN --> TF["_make_true_false<br/>true statements + false negations"]

    MCQ & SA & LA & FB & TF --> AK["_build_answer_key<br/>per-question marking scheme attached"]
    AK --> NC["_build_note_content<br/>Obsidian markdown + frontmatter"]
    NC --> OUT(["Output: questions · answer_key<br/>note_content · board · difficulty"])
```

### `teaching_agent.py` — Level Adaptation

```mermaid
flowchart TD
    PROF(["Student Profile"])
    PROF --> GRADE["grade → _GRADE_LEVEL_MAP<br/>junior / senior / advanced"]
    GRADE --> INST["_LEVEL_INSTRUCTIONS<br/>system_prompt suffix"]

    PROF --> VS["Vault search<br/>threshold 0.6"]
    VS -- "score >= 0.6" --> VC["vault_content used"]
    VS -- "score below 0.6" --> WS["web_search fallback"]

    VC --> COMP["Compose Response"]
    WS --> COMP
    INST --> COMP

    COMP --> EXP["explanation — adapted to level"]
    COMP --> EX["examples — concrete and age-appropriate"]
    COMP --> KP["key_points — exam-focused"]
    COMP --> ET["exam_tips — board-specific"]
    COMP --> PED["pedagogy — next steps suggested"]
    COMP --> SRC["sources — vault refs + web URLs"]
    COMP --> RC["raw_content[] — full unprocessed vault/web chunks<br/>primary material for LLM Master Elaborator"]
```

---

## +1 — Key Scenarios

> *End-to-end walkthroughs of the most important use cases.*

---

### Scenario 1: Student asks "Explain photosynthesis"

```mermaid
sequenceDiagram
    actor Student
    participant CT as classify_task.py
    participant VS as vault_search_agent.py
    participant TA as teaching_agent.py
    participant LLM as LLM Master Elaborator<br/>(Copilot CLI agent)

    Student->>CT: "Explain photosynthesis"
    CT-->>CT: signals: explain → simple_lookup confidence 0.65
    CT-->>CT: escalate to vault_only (confidence below 0.7)
    CT->>VS: query: photosynthesis
    VS-->>VS: FAISS top score 0.72 (above 0.6 threshold)
    VS->>CT: 5 vault findings from 04 - Concepts/
    CT->>TA: vault_content + student profile
    TA-->>TA: Grade 11 → senior level, CBSE board
    TA->>LLM: explanation + examples + key_points + raw_content[]
    LLM-->>LLM: Master Elaborator activates on raw_content[]
    LLM-->>LLM: Produces Learning Module:<br/>Hook · Concept Map · Layered Explanation<br/>Examples · Analogy · Key Points · Exam Corner<br/>Self-Check · Further Questions
    LLM->>Student: rich Learning Module with [[wikilinks]]
    Note over Student,LLM: Read-only flow — no vault write
```

---

### Scenario 2: Student asks "Create a concept note on osmosis"

```mermaid
sequenceDiagram
    actor Student
    participant CT as classify_task.py
    participant VS as vault_search_agent.py
    participant WS as web_search_agent.py
    participant TA as teaching_agent.py
    participant LLM as LLM Master Elaborator<br/>(Copilot CLI agent)
    participant FC as fact_checker_agent.py
    participant CA as compliance_agent.py
    participant NW as note_writer_agent.py

    Student->>CT: "Create a concept note on osmosis"
    CT-->>CT: note_creation confidence 0.95
    CT->>VS: query: osmosis
    VS-->>VS: FAISS top score 0.58 (below 0.6 threshold)
    VS->>WS: vault insufficient — web fallback triggered
    WS-->>WS: Tavily: osmosis CBSE class 11
    WS->>TA: 3 educational sources
    TA-->>TA: compose raw_content[] + explanation + key_points
    TA->>LLM: raw_content[] + extracted fields
    LLM-->>LLM: Master Elaborator produces Learning Module<br/>type: learning-module · [[wikilinks]] · [Title](URL) sources
    LLM->>FC: Learning Module content + claims
    Note over FC: GATE 1
    FC-->>FC: contradiction_check k=8 chunks
    FC-->>FC: verdict CLEAR — pass true
    FC->>CA: fact_check_result
    Note over CA: GATE 2
    CA-->>CA: 10 checks: frontmatter type H1 generated_by all pass
    CA-->>CA: learning-module is valid type (§XI) — status PASS
    CA->>NW: compliance_result
    NW-->>NW: both gates verified internally
    NW-->>NW: learning-module → 04 - Concepts/Osmosis.md
    NW-->>NW: index_vault.py re-indexes
    NW->>Student: path 04 - Concepts/Osmosis.md indexed true
```

---

### Scenario 3: Student adds a new subject

```mermaid
sequenceDiagram
    actor Student
    participant OR as Orchestrator
    participant CP as profile_agent.py
    participant LPS as learner_profile_store.py
    participant ALS as activity_log_store.py
    participant SC as write_student_card

    Student->>OR: "Add Physics to my subjects"
    OR->>CP: check_profile_exists
    CP-->>OR: exists true — Shaatvik Mishra Grade 11
    OR->>CP: add_subject Physics difficulty intermediate
    CP->>LPS: add_subject()
    LPS-->>LPS: create Physics-mastery.json
    LPS-->>LPS: create Physics-revision-queue.json
    LPS->>ALS: log_event subject_added Physics
    CP->>SC: auto-trigger write_student_card
    Note over SC: AUTO-TRIGGERED on every profile mutation
    SC-->>SC: _build_student_card_content updated profile
    SC-->>SC: PowerShell writes Student Card md to 01 - Inbox/
    SC->>Student: status success — 6 subjects including Physics
```

---

### Scenario 4: Practice question generation (board-aware)

```mermaid
sequenceDiagram
    actor Student
    participant PRA as practice_agent.py
    participant MSS as marking_scheme_store.py
    participant VS as vault_search_agent.py
    participant WS as web_search_agent.py
    participant FC as fact_checker_agent.py
    participant CA as compliance_agent.py
    participant NW as note_writer_agent.py

    Student->>PRA: "Generate practice on the French Revolution"
    PRA-->>PRA: _resolve_context → intermediate grade 11 CBSE
    PRA->>MSS: get_scheme CBSE
    MSS-->>PRA: q_scheme bands 1/2/3/5/8 — mcq true_false schemes
    PRA->>VS: query: French Revolution History
    VS-->>VS: score 0.41 (below 0.6) — web fallback
    VS->>WS: French Revolution History CBSE class 11
    WS-->>PRA: sentences · key_terms · list_items
    PRA-->>PRA: generate 14 questions across 5 types
    PRA-->>PRA: _build_answer_key CBSE value-point format
    PRA-->>PRA: _build_note_content Obsidian markdown
    PRA->>FC: claims from note content
    Note over FC: GATE 1
    FC-->>FC: pass true
    FC->>CA: fact_check_result
    Note over CA: GATE 2
    CA-->>CA: status PASS
    CA->>NW: compliance_result
    NW-->>NW: write to 05 - Practice/
    NW->>Student: French Revolution Practice Questions.md indexed true
```

---

## Architecture Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| **AD-1** | `paths.py` as single source of truth for all paths | Vault-portable: moving the vault to any directory requires zero code changes |
| **AD-2** | Sequential fail-fast gates (Fact then Compliance then Write) | Prevents bad data from entering vault; Gate 2 never runs if Gate 1 fails |
| **AD-3** | `note_writer_agent.py` as the only vault write endpoint | Single point of enforcement; no agent can bypass gates |
| **AD-4** | Vault score threshold 0.6 for web fallback | Below 0.6 the vault content is not reliably relevant; web search adds marginal value above it |
| **AD-5** | Task auto-escalation at confidence < 0.7 | Low-confidence classification should err toward more thorough processing |
| **AD-6** | Board-aware marking via `marking_scheme_store.py` | Supporting multiple boards (CBSE, ICSE, IB, Cambridge) requires centralised scheme data |
| **AD-7** | Student card auto-refreshed on every profile mutation | Obsidian vault always reflects current profile without a separate sync step |
| **AD-8** | State in JSON/JSONL, not a database | Obsidian-first philosophy: all learner state lives inside the vault and is human-readable |
| **AD-9** | FAISS flat index (no IVF/HNSW) | Vault size below 10,000 passages makes exact search faster than approximate; no training step |
| **AD-10** | all-MiniLM-L6-v2 cached locally | No network dependency at inference time; works fully offline |
| **AD-11** | Copilot CLI agent IS the LLM elaboration layer | Python tools are pure data fetchers; the LLM (Copilot CLI) does all generative work; no new Python LLM API services needed — just prompt engineering in `study.agent.md` |
| **AD-12** | `[[wikilinks]]` required for all internal vault references (§V rule 8) | Obsidian builds its knowledge graph from wikilinks; without them, notes are isolated islands rather than a connected second brain |
| **AD-13** | `[Title](URL)` required for web sources; `[[note]]` for vault (§X rule 6) | Full source traceability — every claim traceable to its origin; `<br/>` required in Mermaid node labels (Obsidian does not support `\n` escape in diagram labels) |

---

## Data Flow Summary

```mermaid
flowchart TD
    S(["Student"])
    CT["classify_task.py"]

    S -- "query" --> CT
    CT -- "simple_lookup / vault_only" --> VS["vault_search_agent.py"]
    CT -- "research" --> WS["vault_search_agent.py<br/>+ web_search_agent.py"]
    CT -- "note_creation" --> NG["teach_concept<br/>OR practice_agent.py"]

    VS & WS --> RO{"read-only<br/>response?"}
    RO -- "yes" --> ELAB1["LLM Master Elaborator<br/>raw_content[] → Learning Module"]
    ELAB1 --> RESP(["Respond directly to student"])

    NG --> ELAB2["LLM Master Elaborator<br/>raw_content[] → Learning Module<br/>type: learning-module · [[wikilinks]]"]
    ELAB2 --> G1["fact_checker_agent.py<br/>Gate 1"]
    G1 -- "FAIL" --> STOP(["Stop — report conflict to student"])
    G1 -- "PASS" --> G2["compliance_agent.py<br/>Gate 2"]
    G2 -- "FAIL" --> FIX(["Fix violations — re-run Gate 2"])
    G2 -- "PASS" --> NW["note_writer_agent.py"]
    NW --> VAULT(["Vault .md written<br/>FAISS index updated"])
```

---

*Generated by Copilot — Study Agent System, 2026-03-22*
