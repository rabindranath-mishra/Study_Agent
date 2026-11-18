# Changelog

All notable changes to the Study Agent System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial GitHub repository structure
- Comprehensive README.md with architecture and usage
- Contributing guidelines
- MIT License
- .gitignore for Python, Obsidian, and sensitive files
- `.gitattributes` — binary markers for model archives, FAISS index, and images

### Changed
- `README.md` corrected: replaced the aspirational 9-agent table with the real
  19-tool agent model, added a Mermaid diagram of the classification →
  retrieval → gate pipeline, added a "Run the agent" step, and fixed the
  architecture-doc link
- `setup_windows.ps1` rewritten: 10 idempotent steps, `-SkipIndex` / `-Reindex` /
  `-SkipTests` / `-NonInteractive` switches, Study Agent branding, correct
  `tools/requirements.txt` path, BOM-less `.env` writer, and a verification query
- `SETUP.md` rewritten to match the actual tool CLIs, JSON schemas, and paths
- `index_vault.py` now accepts `--rebuild`, `--vault`, `--persist`, `--model`,
  `--chunk-size`, `--chunk-overlap` (zero-argument invocation still works)
- `query_vault.py` now accepts `question [k]`, `--k`, `--persist`, `--model`;
  fixes a crash when extra positional arguments were supplied
- `generate_presentation.py` default output directory is now
  `07 - Outputs/presentations` (was `07 - Writing/presentations`)
- `create_note.py` `--folder` help example now references `04 - Concepts`
- `CONTRIBUTING.md` and `.github/copilot-instructions.md` corrected: real tool
  inventory, `faiss_store/` index location, `Agent Architecture (C4+1).md`

## [1.0.0] - 2026-03-20

### Added
- Multi-agent orchestration system (9 specialist agents)
- FAISS semantic search with sentence-transformers embeddings
- Vault Constitution with 21 governance sections
- Study Agent Architecture documentation
- Python agent tools suite:
  - `index_vault.py` - Semantic index builder
  - `query_vault.py` - Semantic search
  - `create_note.py` - Note creation with frontmatter
  - `vault_search_agent.py` - Vault reading with contradiction checking
  - `fact_checker_agent.py` - Claim verification gate
  - `compliance_agent.py` - Constitution validation
  - `note_writer_agent.py` - Study artifact generation
  - `web_search_agent.py` - Tavily API integration
  - `archive_and_reset.py` - Vault cleanup
  - `classify_task.py` - Query routing
- Setup automation via `setup_windows.ps1`
- Session logging (JSONL format)
- Learner state tracking (JSON format)
- 10-folder vault structure (System, Inbox, Sources, Subjects, Concepts, Practice, Plans, Outputs, Templates, Archive)
- Note type taxonomy (11 standardized types)
- Metadata standards with required frontmatter fields
- File write governance with approval gates
- Source and grounding policy
- Educational behavior standards

### Features
- **Semantic Search**: FAISS-powered contextual retrieval
- **Fact Checking**: Hard gate before vault writes
- **Compliance Validation**: Automatic Constitution enforcement
- **Adaptive Learning**: Mastery tracking and spaced repetition
- **Web Research**: Tavily API integration for external sources
- **Multi-modal Generation**: Notes, quizzes, flashcards, revision plans
- **Session Logging**: Complete audit trail of agent activities
- **Portable Setup**: Relative paths, platform-independent

### Architecture
- Frontend: Obsidian plugin with chat interface
- Backend: Copilot CLI ACP service
- System of Record: Obsidian vault
- Tech Stack: Python 3.14+, PyTorch 2.10, FAISS, Transformers

## Implementation Notes

### Version 1.0.0 Design Decisions

1. **Multi-Agent vs Monolithic**: Chose specialist agents for clear separation of concerns and composable workflows

2. **FAISS vs Alternative Search**: Selected FAISS for local, privacy-preserving semantic search without cloud dependencies

3. **Obsidian as Platform**: Leveraged existing note-taking tool familiar to students, avoiding custom UI development

4. **Governance-First**: Established Vault Constitution before implementation to ensure consistent behavior

5. **Approval Gates**: Required student review for significant changes to maintain agency and prevent blind acceptance

6. **Source Grounding**: Prioritized provenance tracking to combat misinformation and support critical evaluation

7. **Durable Artifacts**: Insisted on vault persistence over ephemeral chat to support long-term learning

### Known Limitations

- Requires Python 3.14+ (uses modern type hints and features)
- FAISS index must be rebuilt when vault structure changes significantly
- Web research requires Tavily API key (paid service)
- Obsidian plugin not yet publicly available
- Single-user system (no multi-user collaboration features)

### Future Roadmap

- [ ] Multi-language support (currently English-centric)
- [ ] Mobile app integration
- [ ] Collaborative study groups
- [ ] Integration with popular LMS platforms
- [ ] Advanced analytics dashboard
- [ ] Voice interface for hands-free study
- [ ] Automatic past paper analysis
- [ ] Peer study matching based on learning patterns

---

**How to Use This Changelog**

- Check `[Unreleased]` for upcoming features
- Reference version numbers when reporting issues
- Use as migration guide when upgrading

**Contributing to Changelog**

When submitting PRs, add entries to `[Unreleased]` section:
- `Added` for new features
- `Changed` for changes in existing functionality
- `Deprecated` for soon-to-be removed features
- `Removed` for removed features
- `Fixed` for bug fixes
- `Security` for vulnerability fixes
