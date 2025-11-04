# AEMS - Automated Exam Marking System

A privacy-conscious, multi-language, PDF-native automated exam marking system for math/engineering courses with AI-powered grading, color-coded annotations, and human-in-the-loop calibration.

## Features

- **Multi-language OCR**: Supports 100+ languages with Tesseract, handwriting recognition, and mathematical expression parsing (LaTeX output)
- **Color-coded PDF Annotations**: Green (correct), Amber (review needed), Red (incorrect) with inline comments
- **Rubric Grounding**: Stepwise marking plans with partial credit and micro-checks
- **Human-in-the-Loop**: Review interface with "Improve checking" feedback loop
- **Privacy-First**: GDPR-compliant, on-premise capable, minimal PII exposure
- **Multi-Provider LLM**: Switchable backends (Claude, OpenAI, Gemini, local models)
- **Canvas Integration**: Export gradebook-compatible CSV

## Architecture

```
┌─────────────┐
│ Gold Package│ (exam PDF + solution + rubric)
└──────┬──────┘
       │
       v
┌─────────────────┐
│ Ingestion Agent │ → Layout detection → OCR → Rubric compilation
└──────┬──────────┘
       │
       v
┌──────────────────┐
│ Batch Grader     │ → Segment → OCR → Grade → Annotate → Export
└──────┬───────────┘
       │
       v
┌──────────────┐
│ Reviewer UI  │ → Override → Memory update → Re-grade
└──────────────┘
```

## Installation

### Basic Installation

```bash
pip install -e .
```

### With Advanced OCR (handwriting, math)

```bash
pip install -e ".[advanced-ocr]"
```

### With Layout Detection

```bash
pip install -e ".[layout]"
```

### Development

```bash
pip install -e ".[dev]"
```

## Quick Start

### 1. Create a Rubric

Create a rubric file (JSON or YAML) defining grading criteria:

```yaml
# rubric.yaml
question_id: "Q1"
title: "Integration by Parts"
total_points: 8.0
items:
  - description: "Identify correct u and dv"
    points: 2.0
    hints: ["u", "dv", "LIATE"]
    common_errors: ["Wrong choice of u and dv"]
  - description: "Compute du and v correctly"
    points: 2.0
  # ... more items
```

See `examples/rubric_example_mechanics.yaml` for a complete example.

### 2. Ingest Gold Materials

```bash
aems ingest \
  --exam exam.pdf \
  --solution solution.pdf \
  --rubric rubric.yaml \
  --output gold/
```

This will:
- Parse the rubric
- Extract text from the solution PDF
- Compile micro-checks with partial credit rules
- Save to `gold/checks.yaml`

### 3. Batch Mark Student Submissions

```bash
aems mark \
  --gold gold/checks.yaml \
  --input submissions/ \
  --output marked/ \
  --provider claude \
  --temperature 0.2
```

### 3. Review and Improve

Launch the web-based reviewer interface:

```bash
aems review marked/ \
  --memory memory/ \
  --course "PHYS-101" \
  --exam "Midterm-2024" \
  --port 5000
```

This will:
- Start a local web server at `http://localhost:5000`
- Display all marked submissions with PDF viewer
- Allow overriding grades with rationale
- Enable "Improve checking" feedback submission
- Store learnings in memory layers for future grading
- Support side-by-side comparison of grading results

### 4. Export Grades to Canvas

```bash
aems export \
  --input marked/ \
  --output grades.csv \
  --format canvas \
  --section "PHYS-101-A" \
  --assignment "Midterm"
```

This will:
- Read all `*_results.yaml` files from the marked directory
- Generate Canvas-compatible CSV with student grades
- Include separate columns for each question (Midterm Q1, Midterm Q2, etc.)
- Add a total score column
- Flag submissions that need human review
- Display summary statistics (average score, review count)

## Demo Commands

Test individual features:

### M0 Demo: PDF Annotations

```bash
# Create a test PDF
python examples/create_test_pdf.py

# Add color-coded annotations
aems demo annotate examples/sample_exam_submission.pdf
```

### M1 Demo: OCR

```bash
# Test OCR on a PDF (requires Tesseract)
aems demo ocr examples/sample_exam_submission.pdf --page 0 --lang eng

# Test OCR on an image
aems demo ocr my_image.png --lang eng+swe
```

### M1 Demo: Layout Detection

```bash
# Analyze PDF layout and detect questions
aems demo layout examples/sample_exam_submission.pdf --page 0

# Show only questions (hide blocks)
aems demo layout exam.pdf --page 0 --no-blocks
```

## Tool Schemas (Claude Messages API)

AEMS is built around the Claude Messages API tool-use pattern. Available tools:

- `pdf_layout_detect` - Detect pages, blocks, questions, figures with bounding boxes
- `region_ocr` - OCR regions using best engine for type (printed, handwriting, math)
- `rubric_compile` - Build micro-check list from gold solution and rubric
- `grade_stepwise` - Compare student work vs micro-checks with RAG grounding
- `pdf_annotate` - Insert color-coded annotations (green/amber/red)
- `export_canvas_csv` - Generate Canvas-compatible gradebook CSV
- `memory_update` - Persist learnings at course/exam/question/user layers

## Configuration

Create `.env` file:

```env
# LLM Provider (claude, openai, gemini, local)
AEMS_PROVIDER=claude
AEMS_ANTHROPIC_API_KEY=sk-ant-...
AEMS_OPENAI_API_KEY=sk-...
AEMS_GEMINI_API_KEY=...

# Model settings
AEMS_MODEL=claude-3-5-sonnet-20241022
AEMS_TEMPERATURE=0.2
AEMS_MAX_TOKENS=4096

# OCR
AEMS_OCR_ENGINE=tesseract
AEMS_TESSERACT_LANG=eng+swe

# Privacy
AEMS_PSEUDONYMIZE=true
AEMS_LOCAL_ONLY=false
```

## Privacy & GDPR Compliance

AEMS is designed with privacy-first principles:

- **Lawful Basis**: Public interest processing (GDPR Art.6(1)(e)) for educational institutions
- **Data Minimisation**: Pseudonymize student identifiers, minimal PII in API calls
- **On-Premise**: Support for fully local OCR and LLM processing
- **Retention Controls**: Configurable data retention and deletion
- **DPIA Ready**: Documentation and controls for Data Protection Impact Assessments

## Evaluation

Before production use, evaluate on gold standard datasets:

```bash
aems evaluate \
  --gold-set evaluation/gold_100/ \
  --metrics agreement,mae,cohen_kappa \
  --output eval_report.html
```

## Project Structure

```
aems/
├── src/aems/
│   ├── models/        # Pydantic data models
│   ├── tools/         # Claude tool implementations
│   ├── pdf/           # PDF handling (PyMuPDF)
│   ├── ocr/           # OCR engines (Tesseract, docTR, pix2tex)
│   ├── grading/       # Grading logic and RAG
│   ├── memory/        # Memory store (course/exam/question/user)
│   ├── providers/     # LLM provider adapters
│   └── cli.py         # CLI entry point
├── tests/
├── examples/
└── docs/
```

## Memory Layers

AEMS implements a four-tier memory system for continuous improvement:

### Course Level
- General grading policies and standards
- Cross-exam patterns and equivalences
- Common misconceptions across topics

### Exam Level
- Exam-specific grading guidelines
- Typical solution approaches
- Frequent error patterns

### Question Level
- Question-specific equivalences (e.g., "F=ma" ≡ "Force equals mass times acceleration")
- Common alternative solutions
- Partial credit rules refined through feedback

### User Level
- Individual grader preferences
- Calibration data
- Review history

Memories are stored in human-readable YAML files and automatically integrated into grading prompts to improve accuracy and consistency over time.

## Milestones

- [x] M0: PDF annotation spike (color-coded annotations) **✅ COMPLETE**
- [x] M1: Gold understanding pipeline (OCR, Layout Detection, Rubric Compilation) **✅ COMPLETE**
- [x] M2: Grader agent with stepwise RAG (Providers, GradingEngine, BatchGrader) **✅ COMPLETE**
- [x] M3: Canvas CSV export (CanvasExporter, export command) **✅ COMPLETE**
- [x] M4: Reviewer UI + memory layers **✅ COMPLETE**

## License

MIT License - See LICENSE file

## Contributing

This is a research/educational project. Contributions welcome!

## References

- PyMuPDF: https://pymupdf.readthedocs.io/
- Tesseract OCR: https://github.com/tesseract-ocr/tesseract
- LayoutParser: https://layout-parser.github.io/
- Anthropic Claude: https://docs.anthropic.com/
- Canvas Gradebook: https://community.canvaslms.com/docs/DOC-26549
