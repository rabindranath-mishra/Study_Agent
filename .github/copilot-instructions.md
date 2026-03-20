# GitHub Copilot Instructions - Study Agent System

> Comprehensive context and guidelines for AI-assisted development of the Study Agent System

## 🎯 System Overview

### Mission Statement

The Study Agent System is **NOT** a general-purpose chatbot or homework solver. It is a **pedagogically-rigorous learning infrastructure** designed to support:

- **Mastery over completion** - Deep understanding, not quick answers
- **Understanding over memorization** - Conceptual grasp, not rote learning
- **Durable artifacts over ephemeral chat** - Persistent notes in Obsidian vault
- **Structured workflows over ad-hoc queries** - Systematic study processes

**Core Principle:** Build student independence through guided learning, not dependency through instant solutions.

### Project Architecture

```
System Type:        Educational Learning Infrastructure
Primary Platform:   Obsidian (knowledge management)
Backend:            Copilot CLI ACP Service (orchestration)
Language:           Python 3.14+
AI Framework:       Multi-agent orchestration (9 specialists)
Search Engine:      FAISS vector index (semantic search)
Embedding Model:    sentence-transformers/all-MiniLM-L6-v2
Web Research:       Tavily API
System of Record:   Obsidian vault (markdown + YAML frontmatter)
```

## 🏗️ Multi-Agent Architecture

### Agent System Design

The system uses **governed orchestration**, not free-form agent swarms. Each agent has specific, bounded responsibilities:

| Agent | Role | Primary Functions | Key Constraints |
|-------|------|-------------------|-----------------|
| **Orchestrator** | Router & Composer | Intent interpretation, agent selection, response composition | Must route to appropriate specialist, never does specialized work directly |
| **Curriculum** | Structure & Sequencing | Subject maps, topic trees, prerequisite chains, exam alignment | Must maintain topological ordering of prerequisites |
| **Knowledge** | Retrieval & Grounding | Semantic search, source retrieval, fact extraction | Must preserve provenance, never fabricate |
| **Teaching** | Explanation & Pedagogy | Concept explanation, simplification, analogy generation | Must adapt to student level, never pretend certainty |
| **Practice** | Assessment Generation | Quiz creation, flashcard generation, drill exercises | Must align difficulty to mastery level |
| **Diagnostic** | Error Analysis | Misconception detection, gap identification, feedback generation | Distinguish conceptual vs careless errors |
| **Revision Planner** | Schedule Optimization | Study plans, spaced repetition, exam countdown schedules | Prioritize weak areas, respect time constraints |
| **Memory** | State Management | Mastery tracking, learning history, revision queues | Maintain consistency across sessions |
| **Output** | Artifact Formatting | Note templates, revision sheets, summary generation | Follow metadata standards, vault structure |

### Agent Interaction Patterns

**Request Flow:**
```
User Query → Orchestrator → [classify intent]
                ↓
    [select relevant specialists]
                ↓
    Specialist Agent(s) → [execute specialized task]
                ↓
    Results → Orchestrator → [compose response]
                ↓
    User + Vault Persistence
```

**Key Rules:**
- Agents never call each other directly (only through Orchestrator)
- Agents are stateless (state managed by Memory Agent in vault)
- Agents propose changes, never force writes (approval gates)
- Agents must document reasoning in logs

## 📁 Vault Structure & Organization

### Canonical Directory Structure

```
Study_Agent/
├── 00 - System/              # Governance & Infrastructure (SACRED)
│   ├── .agent/               # Python agent tools & runtime
│   │   ├── tools/            # Agent utilities (Python scripts)
│   │   ├── index/            # FAISS semantic search index
│   │   ├── logs/             # Session logs (JSONL format)
│   │   ├── state/            # Learner state (JSON format)
│   │   ├── venv/             # Python virtual environment
│   │   └── requirements.txt  # Python dependencies
│   ├── Vault Constitution.md          # 21 binding governance sections
│   └── Study Agent Architecture.md    # System design documentation
│
├── 01 - Inbox/               # Capture zone (unsorted queries)
├── 02 - Sources/             # Primary learning materials
├── 03 - Subjects/            # Curriculum maps & topic organization
├── 04 - Concepts/            # Deep-dive conceptual notes
├── 05 - Practice/            # Quizzes, flashcards, drills
├── 06 - Plans/               # Revision schedars, exam prep
├── 07 - Outputs/             # Generated summaries, reports
├── 08 - Templates/           # Reusable note structures
└── 99 - Archive/             # Superseded/completed materials
```

### Directory Rules

**Immutable Rules:**
1. **System Folder Sanctity**: `00 - System/` contains governance documents that define system behavior. Changes require explicit review.
2. **Inbox as Buffer**: `01 - Inbox/` is temporary capture zone. Notes should migrate to proper folders.
3. **Source Fidelity**: `02 - Sources/` preserves original materials. Never modify source content, only annotate.
4. **Archive Discipline**: `99 - Archive/` is one-way. Archived materials should not return to active folders without explicit decision.

### File Naming Conventions

```
Pattern: <date>-<descriptive-slug>.md

Examples:
✅ 2026-03-20-photosynthesis-deep-dive.md
✅ 2026-03-20-algebra-quadratic-equations.md
✅ mock-exam-biology-2024-paper-1.md

❌ note1.md (not descriptive)
❌ Photo.md (too brief)
❌ My Notes on Photosynthesis from Class Today.md (too verbose)
```

## 📝 Metadata Standards & Note Types

### Required YAML Frontmatter

**Every note MUST include:**

```yaml
---
type: <note-type>              # REQUIRED: See note type taxonomy
subject: <subject-name>        # REQUIRED: Subject area
topic: <topic-name>            # REQUIRED: Specific topic
level: <complexity>            # REQUIRED: beginner|intermediate|advanced|expert
status: <state>                # REQUIRED: draft|in_progress|complete|archived
prerequisites: []              # REQUIRED: List of prerequisite topics (empty if none)
mastery: 0.0                   # REQUIRED: 0.0-1.0 mastery score
practice_status: <state>       # REQUIRED: not_started|in_progress|complete
exam_relevance: <priority>     # REQUIRED: critical|high|medium|low|none
review_status: <state>         # REQUIRED: pending|scheduled|complete
generated_by: <agent>          # REQUIRED: Agent that created note
created: YYYY-MM-DD            # REQUIRED: Creation date
last_updated: YYYY-MM-DD       # AUTO: Last modification date
tags: []                       # OPTIONAL: Additional classification tags
source: <source-ref>           # OPTIONAL: Source material reference
exam_board: <board>            # OPTIONAL: AQA, OCR, Edexcel, etc.
year: YYYY                     # OPTIONAL: Academic year
---
```

### Note Type Taxonomy

| Type | Purpose | Location | Metadata Requirements |
|------|---------|----------|----------------------|
| `source` | Original learning materials | `02 - Sources/` | Must include `source`, `source_type` (textbook, paper, lecture, video) |
| `subject-map` | Curriculum overview | `03 - Subjects/` | Must include `topics: []` list, `exam_board` |
| `topic` | Subject topic notes | `03 - Subjects/` | Must include `prerequisites: []`, `subtopics: []` |
| `concept` | Deep conceptual explanation | `04 - Concepts/` | Must include `key_ideas: []`, `misconceptions: []` |
| `practice` | Quiz/drill/flashcard | `05 - Practice/` | Must include `difficulty`, `question_count`, `topic` |
| `review` | Review summary | `07 - Outputs/` | Must include `topics_covered: []`, `review_date` |
| `revision-plan` | Study schedule | `06 - Plans/` | Must include `start_date`, `end_date`, `daily_topics: {}` |
| `exam` | Exam preparation pack | `06 - Plans/` | Must include `exam_date`, `exam_board`, `topics: []` |
| `dashboard` | Navigation hub | `03 - Subjects/` | Must include `links: []`, `subjects: []` |
| `output` | Generated report | `07 - Outputs/` | Must include `generated_date`, `output_type` |
| `system` | Governance document | `00 - System/` | Must include `version`, `binding: true/false` |

### Content Structure Standards

**Concept Notes Template:**
```markdown
---
type: concept
subject: Biology
topic: Photosynthesis
# ... other metadata
---

# {{Concept Name}}

## Overview
Brief 2-3 sentence summary

## Key Ideas
- Idea 1
- Idea 2
- Idea 3

## Detailed Explanation
### Subsection 1
...

### Subsection 2
...

## Common Misconceptions
- Misconception 1 → Correction
- Misconception 2 → Correction

## Prerequisites
- [[Prerequisite Concept 1]]
- [[Prerequisite Concept 2]]

## Practice Questions
1. Question 1
2. Question 2

## Related Concepts
- [[Related Concept 1]]
- [[Related Concept 2]]

## Sources
- [Source 1](link)
- [Source 2](link)
```

**Practice Notes Template:**
```markdown
---
type: practice
subject: Mathematics
topic: Algebra
difficulty: intermediate
question_count: 10
# ... other metadata
---

# {{Practice Set Name}}

## Instructions
- Time limit: 30 minutes
- No calculator
- Show all working

## Questions

### Question 1
**Topic:** Quadratic equations
**Difficulty:** ⭐⭐⭐

Solve for x: 2x² + 5x - 3 = 0

<details>
<summary>Solution</summary>

Using the quadratic formula...
Answer: x = 0.5 or x = -3

</details>

### Question 2
...
```

## 🔧 Python Code Standards

### File Organization

```
00 - System/.agent/tools/
├── __init__.py              # Package initialization
├── index_vault.py           # FAISS index builder
├── query_vault.py           # Semantic search
├── create_note.py           # Note creation utility
├── vault_search_agent.py    # Vault reading with validation
├── fact_checker_agent.py    # Claim verification gate
├── compliance_agent.py      # Constitution validation
├── note_writer_agent.py     # Artifact generation
├── web_search_agent.py      # Tavily integration
├── archive_and_reset.py     # Vault maintenance
├── classify_task.py         # Query routing
├── config.py                # Configuration management
└── utils.py                 # Shared utilities
```

### Code Style Guidelines

**Language Version:** Python 3.14+

**Style Guide:** PEP 8 with modifications:
- Line length: 100 characters (not 79)
- Docstrings: Google style (not NumPy or reStructuredText)
- Type hints: Required for all public functions
- F-strings preferred over .format() or % formatting

**Example Function:**
```python
"""
Module for semantic search against vault FAISS index.
"""
from typing import List, Dict, Optional
from pathlib import Path
import json
import frontmatter
from sentence_transformers import SentenceTransformer
import faiss

def search_vault(
    query: str,
    top_k: int = 5,
    filter_type: Optional[str] = None,
    min_score: float = 0.0
) -> List[Dict[str, any]]:
    """
    Search vault content using semantic similarity.
    
    Args:
        query: Natural language search query
        top_k: Number of results to return
        filter_type: Optional note type filter (e.g., 'concept', 'practice')
        min_score: Minimum similarity score threshold (0.0-1.0)
        
    Returns:
        List of dictionaries with keys:
            - passage: The matched text passage
            - source: Path to source file
            - score: Similarity score (0.0-1.0)
            - metadata: Note frontmatter metadata
            
    Raises:
        FileNotFoundError: If FAISS index not found
        ValueError: If query is empty or top_k is invalid
        
    Example:
        >>> results = search_vault("photosynthesis process", top_k=3)
        >>> for result in results:
        ...     print(f"{result['source']}: {result['score']:.2f}")
    """
    if not query.strip():
        raise ValueError("Query cannot be empty")
    
    if top_k < 1:
        raise ValueError(f"top_k must be >= 1, got {top_k}")
    
    # Implementation...
    pass
```

### Error Handling Patterns

**Do:**
```python
# Specific exceptions
try:
    index = load_faiss_index(index_path)
except FileNotFoundError:
    logger.error(f"FAISS index not found at {index_path}")
    raise
except Exception as e:
    logger.error(f"Failed to load FAISS index: {e}")
    raise RuntimeError(f"Index loading failed: {e}") from e
```

**Don't:**
```python
# Bare except (hides errors)
try:
    index = load_faiss_index(index_path)
except:
    print("Error loading index")  # No context, loses stack trace
```

### Logging Standards

```python
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Usage
logger.debug("Loading FAISS index from {path}")
logger.info(f"Found {len(results)} results for query: {query}")
logger.warning(f"Low confidence result (score={score:.2f})")
logger.error(f"Fact check failed: {reason}")
```

### Testing Requirements

**Test Structure:**
```
00 - System/.agent/tests/
├── __init__.py
├── test_index_vault.py
├── test_query_vault.py
├── test_fact_checker.py
├── test_compliance.py
└── fixtures/
    ├── sample_notes/
    └── test_index/
```

**Test Example:**
```python
import pytest
from pathlib import Path
from tools.query_vault import search_vault

def test_search_vault_basic():
    """Test basic semantic search functionality."""
    results = search_vault("photosynthesis", top_k=5)
    
    assert len(results) <= 5
    assert all('passage' in r for r in results)
    assert all('score' in r for r in results)
    assert all(0.0 <= r['score'] <= 1.0 for r in results)

def test_search_vault_with_filter():
    """Test search with note type filtering."""
    results = search_vault(
        "quadratic equations",
        filter_type="concept",
        top_k=3
    )
    
    for result in results:
        metadata = result.get('metadata', {})
        assert metadata.get('type') == 'concept'

def test_search_vault_empty_query():
    """Test that empty query raises ValueError."""
    with pytest.raises(ValueError, match="Query cannot be empty"):
        search_vault("")

@pytest.mark.skip(reason="Requires Tavily API key")
def test_web_search_integration():
    """Test web search fallback when vault has no results."""
    # Test implementation
    pass
```

## 🛡️ Governance Policies

### Vault Containment Policy (SACRED)

**Rule:** All student learning artifacts MUST reside in vault directories.

**Prohibited:**
- External databases for learner state
- Cloud storage for study notes
- Separate config files outside vault
- External JSON/CSV for mastery data

**Permitted:**
- Copilot CLI executable (system binary)
- Python virtual environment (infrastructure)
- Temporary OS files (cache, logs)
- Build artifacts (FAISS index regenerated on setup)

**Implementation:**
```python
# ✅ Correct: State in vault
STATE_PATH = Path("00 - System/.agent/state/learner_state.json")

# ❌ Wrong: State outside vault
STATE_PATH = Path.home() / ".study_agent" / "state.json"
```

### File Write Governance (CRITICAL)

**Approval Gates:**
- Backend proposes changes → Plugin mediates → Student approves → Vault updated
- Never write directly to vault without approval for non-trivial changes

**Safe Automatic Writes (No Approval Needed):**
- Session logs (`00 - System/.agent/logs/*.jsonl`)
- Learner state updates (`00 - System/.agent/state/*.json`)
- FAISS index rebuilds (`00 - System/.agent/index/`)
- Cache updates

**Approval-Gated Writes (Require Student Review):**
- New study notes (any folder except System)
- Topic updates (modifications to existing notes)
- Quiz generation (`05 - Practice/`)
- Revision plans (`06 - Plans/`)
- Subject maps (`03 - Subjects/`)

**Implementation Pattern:**
```python
def create_note(content: str, path: Path, requires_approval: bool = True) -> Dict:
    """Create new note with optional approval gate."""
    
    if requires_approval:
        # Return proposal for student review
        return {
            "action": "create_note",
            "path": str(path),
            "content": content,
            "status": "pending_approval",
            "preview": content[:500]  # First 500 chars for review
        }
    else:
        # Safe automatic write (logs, state)
        path.write_text(content, encoding='utf-8')
        return {
            "action": "create_note",
            "path": str(path),
            "status": "completed"
        }
```

### Source & Grounding Policy

**Source Hierarchy (Trustworthiness Order):**
1. Official syllabus documents (exam board specifications)
2. Student's own textbooks (prescribed by course)
3. Teacher-provided materials (handouts, slides)
4. Past examination papers (official)
5. Trusted educational references (Khan Academy, OpenStax, university resources)
6. General encyclopedias (Wikipedia, Britannica)
7. Web articles (verify credibility)

**Requirements:**
- **Never fabricate** when uncertain → admit uncertainty
- **Distinguish grounded vs inferred** → "According to [source]" vs "This suggests"
- **Preserve provenance** → maintain source links through transformations
- **Respect source scope** → don't extrapolate beyond source's claims

**Implementation:**
```python
def retrieve_grounded_content(topic: str) -> Dict:
    """Retrieve content with explicit source tracking."""
    
    # Search vault first (most trusted)
    vault_results = search_vault(topic, top_k=3)
    
    if not vault_results:
        # Fallback to web search
        web_results = web_search(topic)
        
        return {
            "content": web_results['content'],
            "source": web_results['url'],
            "source_type": "web",
            "confidence": "low",  # Web sources less trusted
            "verification_needed": True
        }
    
    return {
        "content": vault_results[0]['passage'],
        "source": vault_results[0]['source'],
        "source_type": "vault",
        "confidence": "high",
        "verification_needed": False
    }
```

### Educational Behavior Standards

**Required Behaviors:**
1. **Progressive Disclosure:** Start with hints, not full solutions
2. **Level Adaptation:** Adjust explanation depth to student's demonstrated understanding
3. **Error Diagnosis:** Distinguish conceptual gaps from careless mistakes
4. **State Updates:** Track mastery changes after significant learning events
5. **Weakness Prioritization:** Focus revision on areas with mastery < 0.7
6. **Independence Building:** Encourage self-explanation before providing answers

**Prohibited Behaviors:**
1. **Faux Certainty:** Never pretend certainty when uncertain
2. **Passive Learning:** Don't enable copying without understanding
3. **Opaque Changes:** Never overwrite notes without showing changes
4. **One-Size-Fits-All:** Don't use same explanation for all students
5. **Chat Dependency:** Don't rely solely on ephemeral conversation

**Implementation Example:**
```python
def explain_concept(
    concept: str,
    student_level: str,
    prior_mastery: float,
    provide_full_solution: bool = False
) -> str:
    """Generate adaptive explanation based on student level."""
    
    if provide_full_solution and prior_mastery < 0.5:
        # Student struggling - provide hint first, not full solution
        return generate_hint(concept, student_level)
    
    if student_level == "beginner":
        # Simple language, concrete examples, minimal jargon
        explanation = generate_beginner_explanation(concept)
    elif student_level == "intermediate":
        # More technical, introduce formal terminology
        explanation = generate_intermediate_explanation(concept)
    else:
        # Advanced: formal definitions, proofs, edge cases
        explanation = generate_advanced_explanation(concept)
    
    # Always include "Why does this matter?" context
    explanation += "\n\n" + generate_relevance_context(concept)
    
    return explanation
```

## 🔍 Common Workflows & Patterns

### Workflow 1: Student Asks Question

```
1. Query arrives → classify_task.py
   ├─ Type: knowledge_retrieval
   ├─ Subject: detected from query
   └─ Complexity: estimated from language

2. Orchestrator routes to specialists:
   ├─ Curriculum Agent → identify prerequisites
   ├─ Knowledge Agent → retrieve relevant passages from vault
   └─ Teaching Agent → generate explanation

3. Teaching Agent adapts response:
   ├─ Check learner_state.json for mastery level
   ├─ Select appropriate depth
   └─ Include guided questions, not just answers

4. Output Agent formats response:
   ├─ Create note in 04 - Concepts/ (if new concept)
   ├─ Update subject map in 03 - Subjects/
   └─ Link to prerequisites

5. Memory Agent updates state:
   ├─ Log query in session_log.jsonl
   ├─ Update mastery_map.json
   └─ Add to revision_queue.json if needed

6. Return to student with approval prompt
```

### Workflow 2: Generate Practice Quiz

```
1. Student requests: "Create quiz on photosynthesis"

2. Curriculum Agent:
   ├─ Identify topic: "Photosynthesis"
   ├─ Check prerequisites: Cell Structure, Chemical Reactions
   └─ Get subtopics: Light-dependent reactions, Calvin cycle, etc.

3. Memory Agent:
   ├─ Check mastery levels for each subtopic
   ├─ Prioritize weak areas (mastery < 0.7)
   └─ Determine appropriate difficulty

4. Practice Agent:
   ├─ Generate 10 questions
   ├─ Weight toward weak subtopics
   ├─ Include variety: multiple choice, short answer, calculation
   └─ Create solutions with explanations

5. Compliance Agent:
   ├─ Validate YAML frontmatter
   ├─ Check directory placement (05 - Practice/)
   └─ Verify question quality

6. Output Agent:
   ├─ Format as markdown
   ├─ Add metadata (difficulty, topics, time limit)
   └─ Present for approval

7. On approval:
   ├─ Write to 05 - Practice/YYYY-MM-DD-photosynthesis-quiz.md
   ├─ Log in session_log.jsonl
   └─ Update practice_status in learner state
```

### Workflow 3: Create Revision Plan

```
1. Student: "Help me prepare for Biology exam in 4 weeks"

2. Curriculum Agent:
   ├─ Get subject map for Biology
   ├─ Extract all topics from 03 - Subjects/Biology/
   └─ Identify exam-relevant topics (exam_relevance: high/critical)

3. Memory Agent:
   ├─ Load mastery_map.json
   ├─ Calculate weak areas (mastery < 0.7)
   └─ Get revision history (review_status)

4. Revision Planner Agent:
   ├─ Calculate days available (28 days)
   ├─ Allocate more time to weak topics
   ├─ Apply spaced repetition (review 3, 7, 14, 21 days after)
   ├─ Build daily schedule
   └─ Include practice time (20% of study time)

5. Output Agent:
   ├─ Format as revision plan note
   ├─ Add YAML frontmatter (start_date, end_date, exam_date)
   ├─ Create daily checklist
   └─ Link to relevant concept/practice notes

6. Present for approval:
   ├─ Show weekly breakdown
   ├─ Highlight prioritization logic
   └─ Allow adjustments

7. On approval:
   ├─ Write to 06 - Plans/YYYY-MM-DD-biology-exam-prep.md
   ├─ Update revision_queue.json
   └─ Schedule reminders (if integration available)
```

## 🧪 Testing & Validation

### FAISS Index Validation

```python
def validate_faiss_index(index_path: Path, metadata_path: Path) -> Dict:
    """Validate FAISS index integrity and coverage."""
    
    checks = {
        "index_exists": index_path.exists(),
        "metadata_exists": metadata_path.exists(),
        "index_size": 0,
        "metadata_count": 0,
        "coverage_percentage": 0.0,
        "missing_files": []
    }
    
    if checks["index_exists"]:
        index = faiss.read_index(str(index_path))
        checks["index_size"] = index.ntotal
    
    if checks["metadata_exists"]:
        with open(metadata_path) as f:
            metadata = json.load(f)
        checks["metadata_count"] = len(metadata)
    
    # Check all notes are indexed
    vault_notes = list(Path(".").rglob("*.md"))
    indexed_files = {m['source'] for m in metadata}
    checks["missing_files"] = [
        str(n) for n in vault_notes 
        if str(n) not in indexed_files
    ]
    
    checks["coverage_percentage"] = (
        len(indexed_files) / len(vault_notes) * 100
        if vault_notes else 0
    )
    
    return checks
```

### Fact Checker Validation

```python
def validate_claim(
    claim: str,
    vault_context: Optional[List[str]] = None,
    web_verification: bool = True
) -> Dict:
    """
    Validate factual claim against trusted sources.
    
    Returns:
        {
            "status": "PASS" | "FAIL" | "UNCERTAIN",
            "confidence": 0.0-1.0,
            "contradictions": [],
            "supporting_sources": [],
            "recommendation": "approve" | "reject" | "review"
        }
    """
    result = {
        "status": "UNCERTAIN",
        "confidence": 0.0,
        "contradictions": [],
        "supporting_sources": [],
        "recommendation": "review"
    }
    
    # Check vault first (most trusted)
    if vault_context:
        vault_check = check_against_vault(claim, vault_context)
        if vault_check['contradictions']:
            result["status"] = "FAIL"
            result["contradictions"].extend(vault_check['contradictions'])
            result["recommendation"] = "reject"
            return result
    
    # Verify against web if enabled
    if web_verification:
        web_check = verify_claim_web(claim)
        result["supporting_sources"].extend(web_check['sources'])
        result["confidence"] = web_check['confidence']
        
        if web_check['confidence'] > 0.8:
            result["status"] = "PASS"
            result["recommendation"] = "approve"
        elif web_check['confidence'] < 0.3:
            result["status"] = "FAIL"
            result["recommendation"] = "reject"
    
    return result
```

### Compliance Validation

```python
def validate_note_compliance(note_path: Path) -> Dict:
    """
    Validate note against Vault Constitution standards.
    
    Checks:
    - YAML frontmatter present and complete
    - Required fields populated
    - Note type valid
    - Directory placement correct
    - Metadata format valid
    """
    issues = []
    
    with open(note_path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)
    
    # Check required fields
    required_fields = [
        'type', 'subject', 'topic', 'level', 'status',
        'prerequisites', 'mastery', 'practice_status',
        'exam_relevance', 'review_status', 'generated_by', 'created'
    ]
    
    for field in required_fields:
        if field not in post.metadata:
            issues.append(f"Missing required field: {field}")
    
    # Validate note type
    valid_types = [
        'source', 'subject-map', 'topic', 'concept', 'practice',
        'review', 'revision-plan', 'exam', 'dashboard', 'output', 'system'
    ]
    if post.get('type') not in valid_types:
        issues.append(f"Invalid note type: {post.get('type')}")
    
    # Validate directory placement
    note_type = post.get('type')
    expected_dir = get_expected_directory(note_type)
    actual_dir = note_path.parent.name
    
    if actual_dir != expected_dir:
        issues.append(
            f"Wrong directory: {note_type} should be in {expected_dir}, "
            f"found in {actual_dir}"
        )
    
    # Validate mastery range
    mastery = post.get('mastery', -1)
    if not (0.0 <= mastery <= 1.0):
        issues.append(f"Mastery must be 0.0-1.0, got {mastery}")
    
    return {
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "path": str(note_path)
    }
```

## 📊 State Management

### Learner State Schema

File: `00 - System/.agent/state/learner_state.json`

```json
{
  "student_id": "default",
  "created": "2026-03-20T14:20:55Z",
  "last_updated": "2026-03-20T14:20:55Z",
  "subjects": {
    "Biology": {
      "started": "2026-01-15",
      "overall_mastery": 0.72,
      "topics": {
        "Photosynthesis": {
          "mastery": 0.85,
          "last_reviewed": "2026-03-18",
          "review_count": 5,
          "practice_completed": 3,
          "weak_subtopics": ["Calvin cycle regulation"]
        },
        "Cell Structure": {
          "mastery": 0.60,
          "last_reviewed": "2026-03-10",
          "review_count": 2,
          "practice_completed": 1,
          "weak_subtopics": ["Mitochondrial structure", "Endoplasmic reticulum"]
        }
      }
    }
  },
  "learning_preferences": {
    "explanation_style": "visual",
    "difficulty_preference": "challenging",
    "study_time_available": "2_hours_daily"
  },
  "exam_targets": [
    {
      "subject": "Biology",
      "exam_board": "AQA",
      "exam_date": "2026-05-15",
      "target_grade": "A*"
    }
  ]
}
```

### Mastery Map Schema

File: `00 - System/.agent/state/mastery_map.json`

```json
{
  "Biology": {
    "Photosynthesis": 0.85,
    "Cell Structure": 0.60,
    "Respiration": 0.75,
    "DNA and RNA": 0.90
  },
  "Mathematics": {
    "Algebra": 0.70,
    "Calculus": 0.55,
    "Trigonometry": 0.80
  },
  "last_updated": "2026-03-20T14:20:55Z"
}
```

### Revision Queue Schema

File: `00 - System/.agent/state/revision_queue.json`

```json
{
  "queue": [
    {
      "topic": "Cell Structure",
      "subject": "Biology",
      "scheduled_date": "2026-03-22",
      "priority": "high",
      "reason": "Low mastery (0.60)",
      "estimated_time": 45,
      "materials": [
        "04 - Concepts/2026-01-20-cell-structure.md",
        "05 - Practice/2026-02-01-cell-structure-quiz.md"
      ]
    },
    {
      "topic": "Calculus",
      "subject": "Mathematics",
      "scheduled_date": "2026-03-23",
      "priority": "high",
      "reason": "Low mastery (0.55)",
      "estimated_time": 60,
      "materials": [
        "04 - Concepts/2026-02-10-calculus-derivatives.md"
      ]
    }
  ],
  "completed": [
    {
      "topic": "Photosynthesis",
      "subject": "Biology",
      "completed_date": "2026-03-18",
      "mastery_before": 0.80,
      "mastery_after": 0.85
    }
  ]
}
```

## 🚀 Development Workflows

### Adding a New Agent Tool

1. **Create tool file:**
   ```bash
   touch "00 - System/.agent/tools/new_agent_tool.py"
   ```

2. **Implement with standards:**
   ```python
   """
   Brief description of new tool.
   """
   from typing import List, Dict
   import logging
   
   logger = logging.getLogger(__name__)
   
   def main_function(param: str) -> Dict:
       """Docstring with Google style."""
       pass
   ```

3. **Add tests:**
   ```bash
   touch "00 - System/.agent/tests/test_new_agent_tool.py"
   ```

4. **Update documentation:**
   - Add to README.md agent tools table
   - Document in Study Agent Architecture.md
   - Update this file if adding new patterns

### Adding a New Note Type

1. **Update taxonomy** in Vault Constitution.md Section XI
2. **Add directory** if needed (rare - use existing 10 folders)
3. **Create template** in `08 - Templates/`
4. **Update compliance validator** in `compliance_agent.py`
5. **Document** in this file under "Note Type Taxonomy"

### Extending FAISS Index

1. **Modify** `index_vault.py` to include new content types
2. **Update metadata schema** to track new fields
3. **Rebuild index:** `python tools/index_vault.py --rebuild`
4. **Test:** `python tools/query_vault.py "test query"`
5. **Validate:** Check coverage percentage

## 🎓 Educational Philosophy Integration

### Bloom's Taxonomy Mapping

When generating content, consider cognitive levels:

```python
BLOOMS_LEVELS = {
    "remember": {
        "verbs": ["list", "define", "name", "recall"],
        "assessment": "multiple_choice",
        "difficulty": "beginner"
    },
    "understand": {
        "verbs": ["explain", "describe", "summarize", "interpret"],
        "assessment": "short_answer",
        "difficulty": "beginner"
    },
    "apply": {
        "verbs": ["calculate", "solve", "demonstrate", "use"],
        "assessment": "problem_solving",
        "difficulty": "intermediate"
    },
    "analyze": {
        "verbs": ["compare", "contrast", "examine", "distinguish"],
        "assessment": "essay",
        "difficulty": "intermediate"
    },
    "evaluate": {
        "verbs": ["judge", "critique", "assess", "defend"],
        "assessment": "case_study",
        "difficulty": "advanced"
    },
    "create": {
        "verbs": ["design", "construct", "develop", "formulate"],
        "assessment": "project",
        "difficulty": "advanced"
    }
}
```

### Spaced Repetition Algorithm

```python
def calculate_next_review(
    mastery: float,
    review_count: int,
    last_review_date: str
) -> str:
    """
    Calculate optimal next review date using spaced repetition.
    
    Intervals based on mastery level:
    - mastery < 0.5: Review in 1 day
    - mastery 0.5-0.7: Review in 3 days
    - mastery 0.7-0.85: Review in 7 days
    - mastery > 0.85: Review in 14 days
    
    Adjusted by review count (more reviews = longer intervals)
    """
    from datetime import datetime, timedelta
    
    base_intervals = {
        (0.0, 0.5): 1,
        (0.5, 0.7): 3,
        (0.7, 0.85): 7,
        (0.85, 1.0): 14
    }
    
    # Find appropriate interval
    for (low, high), days in base_intervals.items():
        if low <= mastery < high:
            base_interval = days
            break
    else:
        base_interval = 14  # Default for mastery >= 1.0
    
    # Increase interval with each review (up to 2x)
    multiplier = min(1 + (review_count * 0.2), 2.0)
    final_interval = int(base_interval * multiplier)
    
    last_review = datetime.fromisoformat(last_review_date)
    next_review = last_review + timedelta(days=final_interval)
    
    return next_review.isoformat()
```

## ⚠️ Critical Warnings

### DO NOT

1. **Never commit secrets** - API keys, tokens, personal data
2. **Never modify System folder** without explicit governance review
3. **Never fabricate sources** - admit uncertainty instead
4. **Never bypass approval gates** - respect file write governance
5. **Never break vault containment** - all artifacts must stay in vault
6. **Never mix learning styles** - maintain pedagogical consistency
7. **Never assume mastery** - always check learner state

### ALWAYS

1. **Always preserve provenance** - track source of all information
2. **Always validate frontmatter** - use compliance agent before writes
3. **Always log activities** - maintain complete audit trail
4. **Always update state** - keep learner_state.json current
5. **Always test changes** - run pytest before committing
6. **Always document reasoning** - explain "why" not just "what"
7. **Always prioritize learning** - mastery over completion

## 📚 Key Resources

### Internal Documentation
- `00 - System/Vault Constitution.md` - 21 binding governance sections
- `00 - System/Study Agent Architecture.md` - System design
- `.github/CONTRIBUTING.md` - Contribution guidelines
- `.github/CHANGELOG.md` - Version history

### External References
- FAISS documentation: https://github.com/facebookresearch/faiss/wiki
- Sentence Transformers: https://www.sbert.net/
- Tavily API: https://docs.tavily.com/
- Obsidian: https://help.obsidian.md/

### Educational Theory
- Bloom's Taxonomy (cognitive levels)
- Spaced Repetition (Ebbinghaus forgetting curve)
- Constructivist Learning Theory
- Zone of Proximal Development (Vygotsky)

---

## 🤖 For GitHub Copilot

When assisting with this codebase:

1. **Context First:** Read Vault Constitution and Study Agent Architecture before suggesting changes
2. **Standards Compliance:** Follow PEP 8, type hints, Google docstrings
3. **Educational Focus:** Prioritize learning outcomes over convenience
4. **Governance Respect:** Never suggest bypassing approval gates or vault containment
5. **Source Grounding:** Always track provenance of information
6. **State Awareness:** Check learner_state.json before suggesting content
7. **Testing:** Include pytest tests for new functionality
8. **Documentation:** Update README, CHANGELOG, and this file when adding features

### Quick Reference Commands

```bash
# Rebuild FAISS index
python "00 - System/.agent/tools/index_vault.py" --rebuild

# Search vault
python "00 - System/.agent/tools/query_vault.py" "your query"

# Validate note
python "00 - System/.agent/tools/compliance_agent.py" "path/to/note.md"

# Run tests
pytest "00 - System/.agent/tests/" -v

# Check code quality
black "00 - System/.agent/tools/"
flake8 "00 - System/.agent/tools/"
mypy "00 - System/.agent/tools/"
```

---

**Last Updated:** 2026-03-20  
**Version:** 1.0.0  
**Binding Status:** Advisory (not governance)
