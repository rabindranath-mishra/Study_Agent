---
type: system
status: architecture
created: 2026-03-08
updated: 2026-03-08
version: 1.0
---

---
# VII. Runtime Architecture Standard

The Student Study Agent shall use the following runtime architecture:

## 1. Frontend
An **Obsidian plugin** provides the student-facing frontend.

The plugin must provide:

- Chat interface
- Context-aware actions
- Artifact previews
- Approval-controlled writes
- Access to current note context
- Rendering of suggested next actions

## 2. Backend
A **Copilot CLI ACP service** provides the agent backend.

The ACP service is responsible for:

- Request interpretation
- Multi-agent orchestration
- Tool use
- Workflow routing
- Structured response generation
- Proposed artifact generation
- State updates

## 4. System of Record
The **Obsidian vault** is the durable workspace and source of truth for student-facing outputs.

---
# VIII. Multi-Agent Architecture

The Student Study Agent shall be implemented as an **orchestrated multi-agent system**, not a free-form swarm.

## Governance Rule

A single orchestrator controls specialist agents.
Specialist agents do not independently modify system goals or invent uncontrolled workflows.

## Required Agents

### 1. Orchestrator Agent
Responsible for:
- Interpreting user intent
- Choosing the workflow
- Invoking specialist agents
- Composing coherent responses
- Managing task boundaries

### 2. Curriculum Agent
Responsible for:
- Subject structure
- Topic sequencing
- Prerequisites
- Syllabus alignment
- Exam relevance mapping

### 3. Knowledge Agent
Responsible for:
- Retrieving study content
- Querying Tavily API when needed
- Collecting definitions, examples, formulas, and source-backed facts
- Building knowledge bundles for downstream agents

### 4. Teaching Agent
Responsible for:
- Explaining at the right level
- Simplifying without distortion
- Creating guided explanations
- Producing stepwise teaching content
- Using diagrams where useful

### 5. Practice Agent
Responsible for:
- Generating drills, quizzes, flashcards, and mock tests
- Adjusting difficulty
- Producing answer structures and practice materials

### 6. Diagnostic Agent
Responsible for:
- Analyzing student answers
- Classifying mistake types
- Identifying misconceptions and prerequisite gaps
- Suggesting corrective follow-up

### 7. Revision Planner Agent
Responsible for:
- Creating daily and exam-countdown plans
- Scheduling revision
- Prioritizing by weakness and importance
- Sequencing next-best study actions

### 8. Memory Agent
Responsible for:
- Maintaining learner state
- Tracking mastery
- Recording study history
- Updating revision queues
- Preserving continuity across sessions

### 9. Output Agent
Responsible for:
- Formatting notes and study artifacts
- Preparing revision sheets
- Preparing reports and summaries
- Producing student-friendly deliverables

---
# IX. Interaction Doctrine

The student interacts with the system through **plugin chat**.

## Binding Interaction Model

1. The student communicates primarily through chat.
2. The plugin includes contextual note awareness.
3. The backend receives structured context, not just raw text.
4. The backend may return both conversational responses and artifact proposals.
5. Durable learning outputs must be persisted to the vault when appropriate.

## Chat Policy

Chat may be used for:

- Concept explanation
- Follow-up questions
- Hints
- Clarification
- Error explanation
- Coaching
- Navigation to generated artifacts

Chat alone must not be the sole storage location for important learning outcomes.

---