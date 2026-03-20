# Student Study Agent System

> A sophisticated AI-powered learning infrastructure built on Obsidian for exam preparation and subject mastery

[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎯 Mission

This is **NOT** a general-purpose chatbot or answer vending machine. It's a **coherent learning system** centered on durable student outcomes:

- ✅ **Mastery** over completion
- ✅ **Understanding** over memorized output
- ✅ **Durable learning artifacts** over ephemeral chat
- ✅ **Structured study workflows** inside an Obsidian vault

## 🏗️ Architecture

### Multi-Agent System

A **governed orchestrator system** with 9 specialist agents:

| Agent | Responsibility |
|-------|---------------|
| 🎯 **Orchestrator** | Interprets intent, routes to specialists, composes responses |
| 📚 **Curriculum** | Subject structure, topic sequencing, prerequisites, exam alignment |
| 🧠 **Knowledge** | Retrieves grounded content, facts, definitions, formulas |
| 👨‍🏫 **Teaching** | Explains at appropriate depth, simplifies without distortion |
| ✍️ **Practice** | Generates drills, quizzes, flashcards, adjusts difficulty |
| 🔍 **Diagnostic** | Analyzes student errors, identifies misconceptions |
| 📅 **Revision Planner** | Creates daily/countdown plans, prioritizes by weakness |
| 💾 **Memory** | Tracks mastery, learning history, study state, revision queues |
| 📄 **Output** | Formats notes, revision sheets, reports, study deliverables |

### Technology Stack

```
Frontend:    Obsidian Plugin (chat interface, context-aware actions)
Backend:     Copilot CLI ACP Service (orchestration, tool use, workflow routing)
System of Record: Obsidian Vault (all durable learning artifacts)
Search:      FAISS Vector Index (semantic search)
Embeddings:  sentence-transformers (all-MiniLM-L6-v2)
Research:    Tavily API (web research when needed)
Language:    Python 3.14+
```

## 📁 Vault Structure

The workspace is organized into 10 canonical directories following a learning workflow.

See the full vault structure in the repository folders.

## 🚀 Quick Start

### Prerequisites

- **Python 3.14+** installed
- **Obsidian** application installed
- **Tavily API Key** (for web research)

### Installation

**For detailed setup instructions, see [SETUP.md](SETUP.md)**

## 🔄 Learning Flow

The default learning loop involves 9 agents working together to support mastery-focused learning.

## 🛡️ Governance & Control

This system follows strict governance policies:
- Vault containment (all artifacts in vault)
- File write governance (student approval for changes)
- Source grounding (trustworthy educational sources)

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📚 Documentation

- **[SETUP.md](SETUP.md)** - Detailed installation and configuration guide
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and updates

---

**Remember:** This is a learning system focused on mastery, not a homework solver. Use it to build understanding, not to bypass learning.