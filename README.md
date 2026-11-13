# Faculty Workload Intelligence Assistant

A terminal-based (CLI) academic intelligence assistant designed for university faculty members, Heads of Departments (HODs), and institutional administrators.

The application combines:
- **Deterministic Workload Calculation Engines** (100% verified arithmetic; no hallucinated numbers)
- **Policy Validation & Exception Tracking** (approved caps, pending/rejected exception isolation, relief exemptions)
- **Role-Based Access Control (RBAC)** (scoped backend queries for FACULTY, HOD, and ADMIN)
- **Timetable Intelligence & Interval Conflict Detection** (faculty double-booking, room overlap, and section clash identification)
- **Retrieval-Augmented Generation (RAG)** (semantic search and source-grounded institutional policy citations)
- **Pluggable LLM Layer** (Ollama integration with high-speed deterministic offline fallback)
- **Rich Terminal User Interface** (interactive tables, status badges, and formatted reports)

---

## 1. System Architecture

```
                    +------------------------------------------+
                    |        Interactive Terminal CLI          |
                    |     (Rich Tables, Panels, Prompts)       |
                    +--------------------+---------------------+
                                         |
                         +---------------+---------------+
                         |                               |
                 Slash Commands              Natural Language Queries
           (/whoami, /workload, etc.)                    |
                         |                   Intent Classifier (21 Intents)
                         |                   & Entity Extractor (IDs, Days)
                         |                               |
                         +---------------+---------------+
                                         |
                            +------------v------------+
                            |      Query Router       |
                            |   (Backend RBAC Scope)  |
                            +------------+------------+
                                         |
     +-------------------+---------------+-------------------+-------------------+
     |                   |                                   |                   |
+----v-----+     +-------v--------+                  +-------v--------+  +-------v--------+
| Workload |     | Timetable &    |                  |  Assignments,  |  | RAG Policy     |
| Engine   |     | Conflict Engine|                  |  Leave, Exempt |  | Vector Store   |
+----+-----+     +-------+--------+                  +-------+--------+  +-------+--------+
     |                   |                                   |                   |
     +-------------------+---------------+-------------------+-------------------+
                                         |
                         +---------------v---------------+
                         |    Relational Database        |
                         |   (SQLite / SQLAlchemy ORM)   |
                         +---------------+---------------+
                                         |
                         +---------------v---------------+
                         | Cleaned Dataset & Ingestion   |
                         |   (Repeatable & Idempotent)   |
                         +-------------------------------+
```

### Core Design Principles
1. **Deterministic Business Logic:** The LLM is never permitted to calculate teaching hours or determine policy violations independently. All calculations are executed via typed Python engines and SQL queries.
2. **Backend-Enforced Authorization:** Security scopes are enforced in the backend service layer, not via prompt instructions. Unauthorized records are never passed to the LLM.
3. **Traceability & Grounding:** Numerical responses state their calculation basis, policy explanations cite document ID, policy ID, and page number, and data points reference source worksheets.

---

## 2. Technology Stack

- **Language:** Python 3.11 / 3.12 / 3.14
- **Database:** SQLite via SQLAlchemy ORM (portable to PostgreSQL)
- **Embeddings & Vector Store:** SentenceTransformers (`all-MiniLM-L6-v2`) / scikit-learn TF-IDF with persistent local JSON and NumPy array storage
- **LLM Layer:** Pluggable interface supporting Ollama with an automatic deterministic offline mode
- **Terminal UI:** Rich (tables, panels, status indicators, markdown formatting)
- **Testing & QA:** pytest, automated scenario runner generating JSON, CSV, and Markdown audit reports

---

## 3. Directory Structure

```
faculty-workload-assistant/
├── app/
│   ├── config/            # Settings (Pydantic) & logging configuration
│   ├── database/          # SQLAlchemy models, connection, lifecycle
│   ├── security/          # RBAC scopes, user context, demo authentication
│   ├── engines/           # Workload calculation, policy validation, conflict detector
│   ├── services/          # Faculty, timetable, assignment, leave, calendar, analytics services
│   ├── rag/               # Document loader, chunker, embeddings, vector store, retriever
│   ├── llm/               # LLM provider abstraction, Ollama provider, offline provider
│   ├── nlp/               # Intent classifier (21 intents), entity extractor, query router
│   ├── tools/             # Typed, authorized backend tools
│   ├── response/          # Response generator & citation builder
│   ├── audit/             # Audit logging into audit_logs table
│   ├── cli/               # Terminal UI, main interactive loop, slash commands
│   └── evaluation/       # Benchmark test runner & evaluation report generators
├── data/
│   └── faculty_workload_dummy_dataset.xlsx  # Untouched source dataset
├── reports/
│   ├── data_quality/      # JSON and Markdown data quality reports
│   └── evaluation/        # Automated test evaluation results (JSON, CSV, MD)
├── storage/
│   ├── database/          # SQLite database storage (faculty_workload.db)
│   ├── documents/         # Generated institutional policy documents
│   └── vector_store/      # Persistent vector chunks and embeddings
├── tests/                 # Comprehensive pytest test suite (13 test modules)
├── .env.example
├── .gitignore
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 4. Setup and Installation

### Step 1: Clone and Prepare Environment
```bash
cd d:/faculty-workload-assistant
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### Step 2: Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### Step 3: Configure Environment
Copy the example environment configuration:
```bash
cp .env.example .env
```

---

## 5. Data Ingestion & Quality Audit

Run the automated ingestion pipeline to audit the source Excel workbook, resolve reported synthetic anomalies in memory, and load the 19 relational tables idempotently:

```bash
python -m app.ingestion.ingestion_service
```

### Ingestion Output:
- **Preserved Source Data:** The source Excel workbook (`data/faculty_workload_dummy_dataset.xlsx`) is strictly read-only and never modified.
- **Reported Dataset Inconsistencies:**
  1. `Faculty_Availability`: Column shift anomaly in header resolved in memory by deriving `faculty_id` from `availability_id` (`AV-FAC001` -> `FAC001`).
  2. `Timetable` Rooms: Discrepancies (`IML-` -> `AIML-` and `-DS-` -> `DS-`) normalized for conflict checking while preserving original raw strings.
  3. `Workload_Summary`: 18/18 faculty teaching hours and violations recomputed from `Timetable` and verified with 100% agreement.
- Audit reports saved in `reports/data_quality/data_quality_report.json` and `.md`.

---

## 6. Running the Application

### A. Interactive Terminal Mode
Start the interactive assistant:
```bash
python -m app.cli.main
```

Upon launch, select a demo identity:
1. `1` - **FAC001** (Dr. Meera Nair, Professor & HOD - Computer Science and Engineering)
2. `2` - **FAC002** (Arjun Menon, Associate Professor - Computer Science and Engineering)
3. `3` - **FAC003** (Kavya Sharma, Assistant Professor - Computer Science and Engineering)
4. `4` - **FAC007** (Dr. Vikram Rao, Professor & HOD - Artificial Intelligence and Machine Learning)
5. `5` - **FAC013** (Dr. Ananya Iyer, Professor & HOD - Data Science)
6. `6` - **ADMIN** (System Administrator - Institution-wide access)

### B. Direct Login
```bash
python -m app.cli.main --user FAC002
```

### C. Single Query Execution
```bash
python -m app.cli.main --user FAC002 --query "How many hours am I teaching this week?"
```

### D. System Diagnostics
```bash
python -m app.cli.main --check-system
```

### E. Rebuild Policy Vector Index
```bash
python -m app.cli.main --rebuild-index
```

---

## 7. Available Slash Commands

| Command | Description |
|---|---|
| `/whoami` | View current authenticated identity, role, and department scope |
| `/workload` | View total weekly teaching hours and session breakdown |
| `/violations` | Check policy compliance (individual or department-wide) |
| `/timetable` | Display scheduled classes, room numbers, and session types |
| `/assignments` | List pending, completed, or overdue academic duties |
| `/policy` | Retrieve workload regulations and maximum limits for your designation |
| `/history` | View multi-semester historical workload trends and averages |
| `/analytics` | View department workload distribution or institution-wide comparison |
| `/data-quality`| Inspect dataset integrity, record counts, and anomaly reports |
| `/help` | Display command reference and sample questions |
| `/logout` | Log out and switch to another seeded user identity |
| `/exit` | Exit the CLI application |

---

## 8. Sample Natural Language Queries

### Faculty Questions:
- "How many hours am I teaching this week?"
- "Am I exceeding my weekly teaching-hour limit?"
- "What classes do I have on Wednesday?"
- "Which assignments are pending for me?"
- "How many project supervision and exam duties are assigned to me?"
- "Who is substituting my cancelled class?"
- "What is the maximum teaching workload for my designation?"
- "Show my historical workload trends."

### HOD Questions:
- "Which faculty members in DEP-CSE exceed their policy limit?"
- "Show department workload distribution for DEP-CSE."
- "Who is on approved leave in my department this week?"
- "Which workload exemptions are approved in my department?"
- "Are there any timetable conflicts in my department?"

### Administrator Questions:
- "Which department has the highest total scheduled teaching hours?"
- "Show institution-wide workload comparison."
- "Which policy exceptions are approved, pending, and rejected?"
- "How many working and examination days are in the academic calendar?"
- "Show data quality and integrity report."

---

## 9. Automated Testing & Evaluation

### Run Comprehensive Automated Benchmark Suite (35 Scenarios)
Executes all 15 queries from `Test_Queries` worksheet + 20 required real-world scenarios:
```bash
python -m app.evaluation.test_runner
```
*Current benchmark score:* **35/35 Passed (100.0%)**.
Reports generated:
- `reports/evaluation/evaluation_report.json`
- `reports/evaluation/evaluation_report.csv`
- `reports/evaluation/evaluation_report.md`

### Run pytest Test Suite (Unit & Integration Tests)
```bash
python -m pytest -v
```
*Result:* **33 unit/integration tests passing (100%)**.

---

## 10. Role-Based Access Control (RBAC) Matrix

| Capability | FACULTY | HOD | ADMIN |
|---|:---:|:---:|:---:|
| View own timetable & teaching hours | ✅ | ✅ | ✅ |
| View own assignments & pending duties | ✅ | ✅ | ✅ |
| Check own workload policy compliance | ✅ | ✅ | ✅ |
| Access other faculty members' records | ❌ | ❌ | ✅ |
| View department-wide timetable & workload | ❌ | ✅ (Own Dept) | ✅ (All Depts) |
| Identify faculty exceeding policy limits | ❌ (Own only) | ✅ (Own Dept) | ✅ (Institution) |
| Detect timetable scheduling conflicts | ❌ | ✅ (Own Dept) | ✅ (Institution) |
| Institution-wide comparisons & audit logs | ❌ | ❌ | ✅ |

---

## 11. Known Data Inconsistencies & Explicit Handling

| Inconsistency ID | Worksheet | Issue Description | Handling Strategy |
|---|---|---|---|
| **INC-001** | `Faculty_Availability` | Column headers shifted by 1 column (`faculty_id` has date, dates in status, etc.). | Ingestion cleaner parses `faculty_id` from `availability_id` (`AV-FAC001` -> `FAC001`) and re-aligns shifted columns in memory. Source Excel is untouched. |
| **INC-002** | `Timetable` | Room names missing `A` prefix in AIML (`IML-202`) and leading hyphen in DS (`-DS-203`). | Cleaner stores raw room name and generates `normalized_room` (`AIML-202`, `DS-203`) for referential checks and conflict detection. |
| **INC-003** | `Users_Roles` | Admin user `USR999` has null `faculty_id`. | Supported by schema design; administrators operate at institution level without personal teaching allocations. |

---

## 12. Future Deployment Considerations

1. **PostgreSQL Migration:** The SQLAlchemy models and connection manager are designed for database independence; changing `DATABASE_URL` in `.env` to a PostgreSQL connection string enables enterprise multi-tenant deployment.
2. **Production Authentication:** Replace demo identity selection with OAuth2 / SAML / LDAP integration using JWT session tokens.
3. **External LLM Gateways:** The `LLMProvider` abstraction allows plugging in Gemini, Anthropic, or OpenAI API gateways while preserving deterministic tool execution.

