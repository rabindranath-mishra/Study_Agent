# Contributing to Study Agent System

Thank you for your interest in contributing to the Study Agent System! This document provides guidelines for contributing to this educational learning infrastructure.

## 🎯 Core Principles

Before contributing, please understand the mission:

- **Mastery over completion** - Focus on deep understanding, not quick answers
- **Durable artifacts** - All learning outputs must persist in the vault
- **Source fidelity** - Maintain provenance and grounding in trustworthy sources
- **Student agency** - Students review and approve all significant changes
- **Pedagogical rigor** - Follow educational best practices

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/Study_Agent.git
   cd Study_Agent
   ```
3. **Set up the development environment**:
   ```powershell
   cd "00 - System/.agent"
   .\setup_windows.ps1
   ```
4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 📋 Contribution Areas

### 1. Agent Tools & Utilities

Located in `00 - System/.agent/tools/`

**Guidelines:**
- Follow existing code patterns and naming conventions
- Add type hints for all function parameters and returns
- Include docstrings with examples
- Write unit tests for new functionality
- Update `requirements.txt` if adding dependencies

**Example structure:**
```python
"""
Brief description of what this tool does.
"""
from typing import List, Dict, Optional
import frontmatter
from pydantic import BaseModel

def your_tool_function(param: str, optional_param: Optional[int] = None) -> Dict:
    """
    Detailed description of function behavior.
    
    Args:
        param: Description of parameter
        optional_param: Description of optional parameter
        
    Returns:
        Dictionary containing results
        
    Example:
        >>> result = your_tool_function("test")
        >>> print(result)
    """
    # Implementation
    pass
```

### 2. Vault Constitution & Governance

Located in `00 - System/Vault Constitution.md`

**Guidelines:**
- Propose changes via issue discussion first
- Maintain the 21-section structure
- Keep rules clear, specific, and enforceable
- Provide rationale for new rules
- Update compliance_agent.py to enforce new rules

### 3. Note Templates

Located in `08 - Templates/`

**Guidelines:**
- Include complete YAML frontmatter with all required fields
- Provide clear placeholders and instructions
- Follow metadata standards (Section XII of Vault Constitution)
- Include example content showing proper structure

### 4. Agent Architecture

Located in `00 - System/Agent Architecture (C4+1).md`

**Guidelines:**
- Document changes to agent responsibilities
- Update interaction flows and diagrams
- Maintain consistency with implementation
- Explain rationale for architectural decisions

### 5. Documentation

**Guidelines:**
- Keep README.md synchronized with actual implementation
- Update setup instructions if dependencies change
- Add examples for new features
- Fix typos and improve clarity

## 🔍 Code Quality Standards

### Python Code

- **Style**: Follow PEP 8
- **Type hints**: Required for all public functions
- **Docstrings**: Use Google-style docstrings
- **Error handling**: Use specific exceptions, not bare `except:`
- **Logging**: Use Python's `logging` module, not `print()`

### Markdown

- **Headers**: Use ATX-style (`#`, `##`, etc.)
- **Links**: Use reference-style links for readability
- **Code blocks**: Always specify language for syntax highlighting
- **Frontmatter**: YAML format with proper indentation

## 🧪 Testing

### Before Submitting

1. **Run existing tests** (if available):
   ```bash
   pytest
   ```

2. **Test vault indexing**:
   ```powershell
   python tools/index_vault.py
   ```

3. **Test semantic search**:
   ```powershell
   python tools/query_vault.py "test query"
   ```

4. **Verify compliance**:
   ```powershell
   python tools/compliance_agent.py
   ```

### Adding Tests

- Place tests in `00 - System/.agent/tests/`
- Use pytest framework
- Mock external API calls (Tavily, etc.)
- Test both success and failure cases

## 📝 Commit Guidelines

### Commit Messages

Follow conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style/formatting (no functional change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(agent): add diagnostic agent for error analysis

Implements misconception detection and targeted feedback
generation based on student practice errors.

Closes #42
```

```
fix(indexing): handle missing frontmatter gracefully

Previously crashed when encountering notes without YAML.
Now logs warning and continues indexing.
```

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring

Examples:
- `feature/practice-generator`
- `fix/faiss-index-corruption`
- `docs/setup-guide`

## 🔄 Pull Request Process

1. **Update documentation** - Reflect your changes in README.md and relevant docs

2. **Add tests** - Include tests for new functionality

3. **Check code quality**:
   ```bash
   # Format code
   black .
   
   # Check linting
   flake8 .
   
   # Type checking
   mypy .
   ```

4. **Update CHANGELOG** (if applicable)

5. **Create Pull Request** with:
   - Clear title describing the change
   - Detailed description of what and why
   - Reference to related issues
   - Screenshots/examples if applicable

6. **Request review** from maintainers

7. **Address feedback** - Be responsive to review comments

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change (fix or feature requiring existing functionality to change)
- [ ] Documentation update

## Testing
How has this been tested?

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added/updated
- [ ] All tests pass
```

## 🛡️ Governance Compliance

All contributions must adhere to:

### Vault Containment (Section VI)
- All learning artifacts in vault directories
- No external state storage
- Paths relative, not absolute

### File Write Governance (Section XIII)
- Propose changes, don't force writes
- Maintain approval gates for student-facing content
- Safe automatic writes only for logs/cache

### Source & Grounding (Section X)
- Prefer trustworthy educational sources
- Preserve provenance
- Don't fabricate when uncertain

### Educational Behavior (Section XVI)
- Guide, don't solve
- Adapt to student level
- Build mastery, not dependency

## 🚫 What NOT to Contribute

- **Homework solvers** - This is a learning system, not a cheating tool
- **Fabricated content** - All material must be grounded in sources
- **Privacy violations** - No personal student data in commits
- **Copyrighted material** - Respect intellectual property
- **External dependencies** - Avoid unnecessary external services

## 📞 Getting Help

- **Questions?** Open a GitHub discussion
- **Bug found?** Open an issue with reproduction steps
- **Feature idea?** Open an issue for discussion first
- **Stuck?** Check existing issues and documentation

## 🏆 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Credited in release notes
- Mentioned in relevant documentation

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for helping make learning more effective for students everywhere!** 🎓
