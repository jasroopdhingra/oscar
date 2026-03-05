## Oscar Medical Guidelines → PDF Scraper + "Initial Criteria" Tree Explorer

### Setup

**Prerequisites:**
- Python 3.9+
- Node.js 18+ (install via [fnm](https://github.com/Schniz/fnm) or nvm)
- A [Groq API key](https://console.groq.com) (free tier)

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

**Environment:**
```bash
cp .env.example .env
# Edit .env and set your GROQ_API_KEY
```

---

### How to Run

#### Option 1: Full pipeline (one command)
```bash
cd backend
source venv/bin/activate
python run_pipeline.py
```
This runs all three steps sequentially: discover → download → structure.

#### Option 2: Individual steps
```bash
cd backend && source venv/bin/activate

# Step 1: Discover all PDF links from Oscar's clinical guidelines page
python run_pipeline.py discover

# Step 2: Download all discovered PDFs
python run_pipeline.py download

# Step 3: Structure at least 10 guidelines using Groq LLM
python run_pipeline.py structure
```

#### Option 3: Via API (while server is running)
```bash
curl -X POST http://localhost:8000/api/pipeline/discover
curl -X POST http://localhost:8000/api/pipeline/download
curl -X POST http://localhost:8000/api/pipeline/structure
```

#### Start the UI
```bash
# Terminal 1 — Backend API
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

Open **http://localhost:5173/** to browse policies and view criteria trees.

---

### Architecture

```
full-stack-feb/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, startup
│   │   ├── database.py          # SQLAlchemy + SQLite engine
│   │   ├── models.py            # policies, downloads, structured_policies tables
│   │   ├── schemas.py           # Pydantic models (including CriteriaTree validation)
│   │   ├── routers/
│   │   │   ├── policies.py      # GET /api/policies, GET /api/policies/:id
│   │   │   └── pipeline.py      # POST triggers for discover/download/structure
│   │   └── services/
│   │       ├── scraper.py       # PDF discovery via __NEXT_DATA__ parsing
│   │       ├── downloader.py    # PDF download with retry + throttle
│   │       ├── extractor.py     # pdfplumber text extraction + initial-only pre-filter
│   │       └── structurer.py    # Groq LLM structuring + Pydantic validation
│   ├── run_pipeline.py          # CLI runner
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── PoliciesPage.tsx     # Policy list with filter controls
│   │   │   └── PolicyDetailPage.tsx # Detail view + criteria tree
│   │   ├── components/
│   │   │   └── CriteriaTree.tsx     # Recursive expand/collapse tree
│   │   ├── api/client.ts            # API client
│   │   └── types/index.ts           # TypeScript types
│   └── vite.config.ts               # Proxy /api → backend
├── oscar.json                       # Reference schema
└── .env.example                     # GROQ_API_KEY placeholder
```

---

### Which Policies Were Structured

The following 14 guidelines were structured into JSON decision trees:

| # | Policy Title |
|---|-------------|
| 1 | 2026 Q1 (January) P&T Summary of Changes |
| 2 | 2025 Q4 Clinical Advisory Subcommittee (CAS) Summary of Changes |
| 3 | 2025 Q4 (December) P&T Summary of Changes |
| 4 | 2025 Q4 (November) P&T Summary of Changes |
| 5 | Antineoplastic and Immunomodulating Agents - Biologics for Autoimmune and Inflammatory Conditions (CG086, Ver. 9) |
| 6 | (Commercial) Preferred Physician-Administered Specialty Drugs (CG052, Ver. 34) |
| 7 | Erythropoiesis-Stimulating Agent (ESA) (CG084, Ver. 4) |
| 8 | Gonadotropin-Releasing Hormone Agonists for Prostate Cancer (CG085, Ver. 3) |
| 9 | Ilaris (canakinumab) (PG185, Ver. 3) |
| 10 | Intravitreal Corticosteroid Injections or Implants (PG271, Ver. 1) |
| 11 | Syfovre (pegcetacoplan injection) (PG150, Ver. 4) |
| 12 | Tepezza (teprotumumab-trbw) (PG273, Ver. 1) |
| 13 | Anesthesia and Sedation in Endoscopic Procedures (CG041, Ver. 11) |
| 14 | Contact Lenses and Eyeglasses (CG039, Ver. 11) |

---

### Initial-Only Selection Logic

A two-layer approach is used to extract only "initial" (not continuation) criteria:

**Layer 1 — Heuristic text pre-filtering** (`extractor.py`):
Before sending text to the LLM, the extracted PDF text is scanned for section headers that distinguish initial from continuation criteria. Common patterns searched:

- "Initial Authorization Criteria", "Initial Criteria", "Initial Medical Necessity Criteria"
- "Continuation of Therapy Criteria", "Continuation/Renewal Criteria", "Reauthorization Criteria"

If both an initial and a continuation header are found (with initial appearing first), only the text between the two headers is extracted. If only an initial header is found, text from that header onward is used. This pre-filters the text before it reaches the LLM.

**Layer 2 — Explicit LLM instruction** (`structurer.py`):
The system prompt explicitly instructs the LLM to:
- Extract ONLY initial authorization/medical necessity criteria
- Ignore continuation, renewal, and reauthorization criteria
- Ignore exclusion criteria, appendices, and references

**Fallback behavior:**
If no initial/continuation section headers are detected in the text (common for simpler guidelines that only have one criteria section), the full extracted text is sent to the LLM. In this case, the LLM instruction alone handles the distinction. This fallback is documented in the logs.

**Known failure modes:**
- Guidelines where "initial" vs "continuation" distinction uses non-standard headers (e.g., "First Authorization" or indication-specific headings) may not be pre-filtered and rely entirely on the LLM.
- Very long PDFs are truncated to the first 15 pages / 30,000 characters. If initial criteria appear beyond this limit, they would be missed.

---

### Technical Decisions

- **Scraping strategy**: Instead of HTML DOM parsing, the scraper extracts the `__NEXT_DATA__` JSON embedded by Next.js in the page source. This gives structured access to all guideline titles and URLs — more reliable than CSS selector-based scraping.
- **PDF URL resolution**: The URLs on the listing page (e.g., `/medical/cg013v11`) point to Next.js pages, not raw PDFs. The downloader fetches each page and extracts the actual Contentful CDN URL from `__NEXT_DATA__`. This two-step resolution is necessary because Oscar hosts PDFs on `assets.ctfassets.net`.
- **LLM**: Groq (free tier) with Llama 3.3 70B via the OpenAI-compatible API. JSON mode (`response_format: json_object`) is used for reliable output.
- **Validation**: Every LLM response is validated against a recursive Pydantic model (`CriteriaTree` / `RuleNode`). Failures are stored in `validation_error` rather than silently dropped.
- **Idempotency**: Discovery uses `INSERT OR IGNORE` on the unique `pdf_url` constraint. Downloads skip policies that already have a successful download record. Structuring skips policies that already have valid structured output.
- **Rate limiting**: 1.5s delay between PDF downloads, 3s delay between LLM calls. The Groq SDK also handles 429 responses with automatic retry and exponential backoff.

---
