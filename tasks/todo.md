# Hybrid Read Tool Implementation Plan

## Overview
Build a Claude Code CLI-like Read tool with multiple OCR engines and vision capabilities - **NO API KEYS REQUIRED**.

**Supported Languages:** English (en) and Arabic (ar) only (initially)

**Full Plan Document:** [docs/HYBRID_READ_TOOL_IMPLEMENTATION_PLAN.md](../docs/HYBRID_READ_TOOL_IMPLEMENTATION_PLAN.md)

## Status: PLANNING PHASE - AWAITING APPROVAL

---

## Hybrid Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    HYBRID READ TOOL                             │
├─────────────────────────────────────────────────────────────────┤
│  PaddleOCR (Primary)  │  Tesseract (Fallback)  │  Ollama (Vision) │
│  • English + Arabic   │  • English + Arabic     │  • LLaVA/Gemma3  │
│  • High accuracy      │  • Lightweight          │  • Context-aware │
│  • GPU support        │  • Fast                 │  • Analysis      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation & Refactoring (Claude Code CLI Parity)
- [ ] Create `src/` package structure
- [ ] Implement `ReadOptions` dataclass (CLI-compatible params)
- [ ] Implement `ReadResult` dataclass
- [ ] Implement `BaseEngine` abstract class
- [ ] Implement `ReadToolConfig` dataclass
- [ ] Create `EngineManager` class
- [ ] Implement `HybridReadTool` main class with:
  - [ ] Text file reading with line numbers (cat -n format)
  - [ ] Offset/limit parameter support
  - [ ] Line truncation (2000 chars)
  - [ ] Directory validation (reject directories)
  - [ ] Absolute path validation
- [ ] Implement Jupyter notebook (.ipynb) reader
- [ ] Refactor `ocr_tool.py` into `PaddleEngine`
- [ ] Implement file type detection utilities
- [ ] Write unit tests for base classes

### Phase 1.5: Structured Arabic Output (Claude Code Parity)
- [ ] Create `src/formatters/` package structure
- [ ] Implement `field_dictionary.py` with Arabic-English mappings
  - [ ] Invoice fields (فاتورة, التاريخ, الاجمالي, etc.)
  - [ ] Company fields (شركة, هاتف, العنوان, etc.)
  - [ ] Payment fields (البائع, المستلم, نقدي, آجل)
  - [ ] Reverse mapping (English → Arabic)
- [ ] Implement `DocumentAnalyzer` class:
  - [ ] Document type detection (invoice, form, receipt, generic)
  - [ ] Language detection (Arabic/English/bilingual)
  - [ ] Key-value pair extraction
  - [ ] Layout region identification
- [ ] Implement `StructuredOutputFormatter` class:
  - [ ] Markdown output with bilingual tables
  - [ ] Invoice template (Claude Code style)
  - [ ] Generic document template
  - [ ] JSON structured output
- [ ] Integrate PP-StructureV3 for layout analysis:
  - [ ] Table detection and extraction
  - [ ] Text region detection
  - [ ] Reading order detection
- [ ] Add Arabic RTL text handling
- [ ] Write unit tests for formatters

### Phase 2: Tesseract Integration
- [ ] Install Tesseract OCR system package
- [ ] Implement `TesseractEngine` class
- [ ] Add language pack installation script
- [ ] Implement language code translation
- [ ] Add fallback logic to `EngineManager`
- [ ] Write unit tests for Tesseract engine

### Phase 3: Ollama Vision Integration
- [ ] Document Ollama installation process
- [ ] Implement `OllamaEngine` class
- [ ] Add base64 image encoding utilities
- [ ] Implement prompt templates for OCR
- [ ] Add vision analysis capabilities
- [ ] Write unit and integration tests

### Phase 4: API & Frontend Updates
- [ ] Refactor Flask app with blueprints
- [ ] Add new API endpoints
- [ ] Implement OpenAPI documentation
- [ ] Update React components for engine selection
- [ ] Add vision analysis UI component
- [ ] Write API integration tests

### Phase 5: Polish & Documentation
- [ ] Complete unit test coverage (>80%)
- [ ] End-to-end integration testing
- [ ] Performance optimization
- [ ] Update README with full documentation
- [ ] Create user and developer guides
- [ ] Final security review

---

## Key Deliverables

| Deliverable | Location | Status |
|-------------|----------|--------|
| Implementation Plan | `docs/HYBRID_READ_TOOL_IMPLEMENTATION_PLAN.md` | Done |
| ReadOptions/ReadResult | `src/models.py` | Pending |
| Base Engine Class | `src/engines/base_engine.py` | Pending |
| PaddleOCR Engine | `src/engines/paddle_engine.py` | Pending |
| Tesseract Engine | `src/engines/tesseract_engine.py` | Pending |
| Ollama Engine | `src/engines/ollama_engine.py` | Pending |
| **HybridReadTool (CLI-like)** | `src/read_tool.py` | Pending |
| Text File Reader | `src/readers/text_reader.py` | Pending |
| Jupyter Notebook Reader | `src/readers/notebook_reader.py` | Pending |
| Engine Manager | `src/engine_manager.py` | Pending |
| **Arabic-English Field Dictionary** | `src/formatters/field_dictionary.py` | Pending |
| **Document Structure Analyzer** | `src/formatters/document_analyzer.py` | Pending |
| **Structured Output Formatter** | `src/formatters/output_formatter.py` | Pending |
| **PP-StructureV3 Engine** | `src/engines/structure_engine.py` | Pending |
| Updated API | `api/routes/*.py` | Pending |
| Updated Frontend | `frontend/src/` | Pending |
| Test Suite | `tests/` | Pending |

---

## Success Criteria

- [ ] All three OCR engines integrated and functional
- [ ] **Claude Code CLI Feature Parity:**
  - [ ] Text files with line numbers (cat -n format)
  - [ ] Offset/limit parameters working
  - [ ] Line truncation at 2000 chars
  - [ ] Jupyter notebook (.ipynb) support
  - [ ] Directory rejection validation
  - [ ] Absolute path requirement
- [ ] **Structured Arabic Output Parity (Claude Code style):**
  - [ ] Bilingual markdown tables (English | Arabic)
  - [ ] Invoice template with semantic sections
  - [ ] Document structure analysis via PP-StructureV3
  - [ ] Table detection and extraction
  - [ ] Arabic-English field dictionary working
  - [ ] RTL Arabic text handling
- [ ] English and Arabic language support working
- [ ] Automatic engine selection based on use case
- [ ] REST API with all endpoints documented
- [ ] React frontend with engine selection UI
- [ ] Unit and integration tests passing (>80% coverage)
- [ ] Performance benchmarks meeting targets
- [ ] Documentation complete and reviewed

---

## Previous Completed Work

### PaddleOCR Setup (Completed)
- [x] Python 3.13.1 environment setup
- [x] PaddlePaddle and PaddleOCR installed
- [x] Basic OCR tool (`ocr_tool.py`) working
- [x] Flask API (`api.py`) running
- [x] React frontend scaffolded
- [x] PDF support via PyMuPDF
- [x] Test verified with 98-99% accuracy

---

## Next Steps

1. **Review and approve** the implementation plan
2. **Start Phase 1** - Create modular architecture
3. **Track progress** in this file

---

*Last Updated: January 5, 2026*
