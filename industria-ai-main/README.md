# INDUSTRIA AI — Intelligent Industrial Manual & Maintenance Assistant

An evidence-grounded, production-minded industrial knowledge application built with Django REST Framework, persistent ChromaDB vector storage, PyMuPDF extraction, and official Groq API LLM integration.

---

## 1. System Architecture

```
                       [ Engineer / Supervisor / Admin ]
                                      |
                     [ Bootstrap 5 Industrial UI ]
                                      |
                         [ Django REST Backend ]
                       /           |           \
         [ User Auth & RBAC ]  [ Machines API ]  [ Assistant RAG API ]
                                                       |
                                            [ VectorStoreService ]
                                            (ChromaDB Persistent)
                                           / strict machine_id \\
                                          /      filter         \\
                     [ M-HP200 Collection ]               [ M-AC90 Collection ]
                     - HP-OPS-01 (Rev 1.0)                 - AC-OM-01 (Rev 1.0)
                     - HP-MNT-01 (Rev 1.0)                         |
                              \                                    /
                               \                                  /
                                [ Retrieved Manual Evidence ]
                                              |
                                   [ Official Groq API ]
                               (llama-3.3-70b-versatile)
                               (Offline Synthesizer Fallback)
                                              |
                                 [ Grounded Answer JSON ]
                                 - Direct Answer
                                 - 1-Based Page Citations
                                 - Verifiable Passages
```

---

## 2. Machine & Manual Registration Inventory

The dataset consists of **2 distinct industrial machines** and **3 technical manuals** registered via `machine_manual_index.csv`:

| Machine Identifier | Model | Machine Name | Document ID | Revision | Pages | Chunks |
|---|---|---|---|---|---|---|
| **M-HP200** | HP-200 | Hydraulic forming press | **HP-OPS-01** | 1.0 | 3 | 17 |
| **M-HP200** | HP-200 | Hydraulic forming press | **HP-MNT-01** | 1.0 | 3 | 16 |
| **M-AC90** | AC-90 | Air compressor | **AC-OM-01** | 1.0 | 3 | 15 |

*Note: Both HP-200 operations and maintenance manuals belong to the single `M-HP200` machine record. When querying HP-200, evidence is retrieved from both manuals.*

---

## 3. Groq API Setup & Environment Configuration

### Exact `.env` File Location:
```
c:\Users\Bhagyashree\INDUSTRIA AI\.env
```

### Setup Instructions:
1. Open `.env` in your text editor (or copy from `.env.example`):
   ```bash
   copy .env.example .env
   ```
2. Insert your official Groq API key:
   ```ini
   GROQ_API_KEY=gsk_your_actual_groq_api_key_here
   GROQ_MODEL=llama-3.3-70b-versatile
   ```
3. Get a free Groq API key from: [https://console.groq.com/keys](https://console.groq.com/keys)

> **Resilience Guarantee:** If `GROQ_API_KEY` is not provided, the application runs seamlessly using the built-in **Deterministic Grounded Synthesizer**, allowing 100% offline development, testing, and evaluation.

---

## 4. Default User Credentials

| Username | Password | Role | Permissions |
|---|---|---|---|
| `admin` | `Admin@123456` | **Administrator** | Register machines, upload manuals, run ingestion, full access |
| `engineer` | `Engineer@123456` | **Engineer** | Select machines, query manuals, inspect citations, view own history |
| `supervisor` | `Supervisor@123456` | **Supervisor** | Query manuals, audit all engineer queries, mark reviewed, view knowledge gaps |

---

## 5. Execution & Ingestion Commands

Run all commands using the project's virtual environment:

### Step 1: Database Migrations
```powershell
& ".\venv\Scripts\python.exe" backend/manage.py migrate
```

### Step 2: Seed Users and Initial Data
```powershell
& ".\venv\Scripts\python.exe" backend/manage.py seed_industria
```

### Step 3: Run PDF Manual Ingestion
```powershell
& ".\venv\Scripts\python.exe" backend/manage.py ingest_manuals
```

### Step 4: Run Automated Test Suite
```powershell
$env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'; & ".\venv\Scripts\python.exe" backend/manage.py test tests.test_industria --verbosity=2
```

### Step 5: Start the Web Application
```powershell
& ".\venv\Scripts\python.exe" backend/manage.py runserver 0.0.0.0:8000
```
Open your browser at: `http://localhost:8000/`

---

## 6. Key Demonstration Scenarios

1. **HP-200 Alarm E17:**
   - Select: `HP-200`
   - Question: *"What does E17 mean?"*
   - Grounded Answer: Low hydraulic pressure. Place on HOLD; request checks in HP-MNT-01 page 3.
   - Citation: `HP-OPS-01` Page 2.

2. **AC-90 Alarm E17 (Machine Isolation):**
   - Select: `AC-90`
   - Question: *"What does E17 mean?"*
   - Grounded Answer: High discharge temperature. Record temperature; above 95°C request cooling-path review.
   - Citation: `AC-OM-01` Page 2.
   - *Strict isolation: Never returns HP-200 low hydraulic pressure.*

3. **Multi-Manual Integration (HP-200 Trigger + Observations):**
   - Select: `HP-200`
   - Question: *"What triggers E17, and what observations should be collected?"*
   - Grounded Answer: Triggers when pressure stays below 110 bar for >5s (normal: 120–140 bar). Observations to collect: reservoir level, external leakage, RF-20 restriction indicator, oil temperature/pressure.
   - Citations: `HP-OPS-01` Page 2 AND `HP-MNT-01` Page 3.

4. **Inspection Interval (AC-90 AF-10 Filter):**
   - Select: `AC-90`
   - Question: *"How often should the AF-10 filter indicator be checked, and when is planned replacement due?"*
   - Grounded Answer: Check indicator every 100 operating hours; planned replacement due every 600 operating hours.
   - Citation: `AC-OM-01` Page 3.

5. **Missing Evidence Boundary Guard:**
   - Select: `HP-200`
   - Question: *"What is the pump replacement price?"*
   - Grounded Status: `insufficient_evidence`.
   - Answer: *"The available manuals do not contain enough information to answer this question."*

6. **Cross-Machine Leakage Prevention:**
   - Select: `AC-90`
   - Question: *"What is the HP-200 return-filter replacement interval?"*
   - Grounded Status: `insufficient_evidence` (AC-90 manual does not contain HP-200 component data).

