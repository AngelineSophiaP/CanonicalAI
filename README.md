# Multi-Source Candidate Data Transformer

A high-fidelity, end-to-end data integration pipeline and interactive dashboard that ingests recruiter CSVs, candidate resumes (PDF/TXT), and live GitHub profiles, merges them into unified canonical profiles, resolves duplicates with a self-healing algorithm, and supports dynamic, spec-based field projections.

---

## Technical Stack
* **Backend**: Python 3.12, Starlette (ASGI Server), SQLite3, Pydantic V2, Uvicorn, and TheFuzz (Fuzzy Name Matching).
* **Frontend**: HTML5, Vanilla CSS (Premium Sky Blue Theme, Glassmorphism, Responsive Grid), and Vanilla JavaScript (SPA AJAX Client).
* **Testing**: PyTest.

---

## Project Structure
```text
candidate_transformer/
├── app.py                  # ASGI Starlette Web Application Entrypoint
├── main.py                 # Command-Line Pipeline Entrypoint
├── db.py                   # SQLite Database Management
├── config/                 # Configuration Schemas & Templates
├── inputs/                 # Recruiter CSV, Resume, and GitHub Source Adapters
├── merger/                 # Matching & Merge Engines (Duplicate Resolution)
├── models/                 # Canonical Pydantic schemas (Candidate, Profile, etc.)
├── normalizers/            # Phone, Date, and Name normalizers
├── projection/             # Dynamic Field Spec Projector engine
├── validators/             # Canonical schema validation rules
├── static/                 # Frontend Web Assets (index.html, style.css, app.js)
├── tests/                  # Automated Test Suite (PyTest cases)
└── requirements.txt        # Backend dependencies
```

---

## Installation & Setup

Follow these steps to initialize the environment and run the application locally.

### 1. Prerequisites
Ensure you have **Python 3.12** installed on your system. You can verify your version by running:
```bash
python --version
```

### 2. Create a Virtual Environment
Navigate to the project root directory and initialize a clean virtual environment:
```bash
# Create the venv
python -m venv venv

# Activate the venv (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate the venv (Windows CMD)
.\venv\Scripts\activate.bat

# Activate the venv (macOS/Linux)
source venv/bin/activate
```

### 3. Install Dependencies
Install all required package dependencies:
```bash
pip install -r requirements.txt
```

### 4. Configure GitHub Token (Optional)
To fetch live profiles without encountering GitHub API rate limits, set a `GITHUB_TOKEN` environment variable.
* **Windows (PowerShell)**:
  ```powershell
  $env:GITHUB_TOKEN="your_personal_access_token"
  ```
* **Windows (CMD)**:
  ```cmd
  set GITHUB_TOKEN=your_personal_access_token
  ```
* **macOS/Linux**:
  ```bash
  export GITHUB_TOKEN="your_personal_access_token"
  ```

---

## Running the Web Dashboard

The web application serves both the backend API and the rich glassmorphic SPA frontend.

### 1. Start the Server
With your virtual environment active, start the server:
```bash
python app.py
```
This starts the Uvicorn engine listening on **http://localhost:8501**.

### 2. Access the Application
Open your web browser and navigate to:
**[http://localhost:8501](http://localhost:8501)**

---

## How to Use the Dashboard
1. **Upload Recruiter CSV**: Select a recruiter candidate listing CSV file.
2. **Upload Resumes**: Choose multiple candidate resume files (`.pdf` or `.txt`).
3. **GitHub Handles**: Input a comma-separated list of candidate GitHub handles (optional).
4. **Ingest Data**: Click **Ingest Data**. The backend processes, parses, normalizes, and merges matches. The list in the sidebar will refresh, and the first candidate's profile is loaded immediately.
5. **Interactive Controls**:
   * **Field Toggles**: Toggle fields at the top of the Projected JSON panel to dynamically construct client projections.
   * **Copy / Download JSON**: Instantly copy or download the projected profiles.
   * **Timeline & Traceability**: Explore the employment history timeline and inspect the provenance logs mapping target values back to their source files and extraction techniques.

---

## Command Line Usage
You can also run the transformation pipeline via the command line interface:
```bash
python main.py --csv sample_data/recruiter.csv --resume sample_data/resume.txt --config config/default_config.json --output final_profile.json
```

---

## Running the Automated Tests
The repository includes a comprehensive suite of unit tests validating adapters, normalizers, mergers, validators, and projections.

To execute the tests, run:
```bash
pytest
```
