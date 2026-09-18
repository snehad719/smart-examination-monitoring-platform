# Development of Smart Examination Monitoring Platform with Integrity Analysis & Reporting System

## 1. Project Overview

This project is a Python-based online examination monitoring platform designed to support secure and evidence-based exam monitoring.

The system uses Flask and OpenCV for examination monitoring, records browser and face-monitoring events, calculates an integrity score using rule-based logic, generates integrity reports, and provides data analytics through a Streamlit dashboard.

The platform is designed to assist invigilators by providing monitoring evidence, integrity scores, alerts, AI-assisted summaries, and analytics rather than making automated disciplinary decisions.

## 2. Objectives

- Secure candidate registration and authentication
- Capture and monitor candidate face presence using a webcam
- Detect and record browser activity such as tab switching and focus loss
- Detect suspicious examination events
- Calculate examination integrity scores
- Generate natural-language integrity reports
- Analyse examination-session data using Data Science techniques
- Provide alerts and evidence for examiner review
- Provide a unified monitoring dashboard
- Support JSON/CSV data export

## 3. Project Modules

1. Candidate Authentication & Session Management
2. Face Presence Monitoring
3. Browser Activity & Event Logging
4. Suspicious Event Detection Engine
5. Integrity Scoring Module
6. AI Integrity Report Agent
7. Data Science & Analytics Module
8. Alert & Evidence Management
9. Examination Monitoring Dashboard
10. Reporting & Export Module

## 4. Technology Stack

- Python
- Flask
- OpenCV
- SQLite
- LangChain
- Pandas
- Matplotlib
- Seaborn
- Scikit-learn
- Streamlit
- Faker

## 5. System Workflow

Candidate Registration → Login & Authentication → Exam Instructions → Start Examination → Webcam Face Monitoring + Browser Activity Monitoring → Event Logging → Suspicious Event Detection → Integrity Score Calculation → AI / Rule-Based Integrity Report → Alerts & Evidence → Data Science Analytics → Streamlit Monitoring Dashboard → Reports / Data Export

## 6. Integrity Scoring

| Event Type | Weight |
|---|---:|
| FACE_ABSENT | 10 |
| TAB_SWITCH | 20 |
| FOCUS_LOST | 10 |
| MULTIPLE_FACES | 30 |
| LOOKING_AWAY | 15 |
| KEYBOARD_ACTIVITY | 10 |

The event penalties are used to calculate the integrity score and corresponding risk level.

## 7. Monitoring Thresholds

- Face absent threshold: 10 seconds
- Focus loss threshold: 5 events
- Tab switch threshold: 3 events

When configured thresholds are exceeded, the system can create high-severity alerts and store supporting evidence.

## 8. Project Structure

```text
ExamGuard/
├── app.py
├── ai_report_agent.py
├── database.py
├── create_session.py
├── close_session.py
├── requirements.txt
├── .gitignore
├── app/
│   ├── __init__.py
│   ├── ai_integrity_report.py
│   ├── ai_report_agent.py
│   ├── alert_evidence.py
│   ├── analytics.py
│   ├── camera.py
│   ├── dashboard.py
│   ├── evidence_manager.py
│   ├── integrity_scoring.py
│   └── test_risk_profiles.py
├── templates/
│   ├── dashboard.html
│   ├── exam.html
│   ├── exam_details.html
│   ├── login.html
│   ├── monitoring_report.html
│   └── register.html
├── data/
│   └── generated runtime / analytics data
└── uploads/
    └── candidate upload data (ignored by Git)
```

## 9. Database

The application uses SQLite.

Database location:

```text
data/examguard.db
```

The database stores information related to candidates, examination sessions, face-monitoring events, browser events, alerts, evidence, and integrity reports.

Runtime database files are excluded from GitHub through `.gitignore`.

## 10. Installation

Create and activate a virtual environment:

```powershell
python -m venv venv
venv\Scripts\activate
```

Install the required packages:

```powershell
pip install -r requirements.txt
```

Initialize the database:

```powershell
python database.py
```

## 11. Running the Flask Application

```powershell
python app.py
```

The Flask application runs locally at `http://127.0.0.1:5000`.

## 12. Running the AI Integrity Report Agent

```powershell
python ai_report_agent.py
```

The program requests an examination session ID and generates an integrity report. The implementation supports a rule-based fallback when an external LLM API key is not configured.

## 13. Streamlit Analytics Dashboard

```powershell
streamlit run app/dashboard.py
```

The dashboard includes:

- Overview
- Session Analysis
- K-Means Clustering
- Alerts & Evidence
- Event Analysis
- AI Reports
- Data Export

## 14. Data Science Analytics

The analytics module provides:

- Integrity score distribution
- Risk-level distribution
- Event frequency analysis
- Event frequency heatmaps
- K-Means clustering
- Cohort risk profiling
- Session-level analysis

Synthetic data can be generated for testing and analytics using the project data generator.

## 15. Alerts and Evidence

The system records suspicious monitoring events and creates alerts when configured thresholds are exceeded.

Examples include face absence for a configured duration, excessive tab switching, and excessive focus loss. Evidence can include stored monitoring frames and event information associated with examination sessions.

## 16. Testing

Testing covered candidate registration, login, exam session creation, exam start and submission, face monitoring, browser event logging, tab-switch detection, focus-loss detection, integrity scoring, integrity report generation, alerts and evidence, and the analytics dashboard.

## 17. AI Reporting

The AI Integrity Report Agent is designed to convert monitoring and scoring information into a readable integrity summary. A rule-based fallback is available when an external LLM API key is unavailable.

No external model training is required for the core monitoring system.

## 18. Security and Privacy Notes

- Runtime database files are not committed to GitHub.
- Candidate uploads are excluded from Git using `.gitignore`.
- Evidence generated during local execution is excluded from Git.
- Credentials and API keys should not be stored directly in source code.
- The system is intended to support examiner review and evidence-based decision making.

## 19. Future Enhancements

- More advanced face and gaze analysis
- Improved real-time anomaly detection
- Additional browser-security controls
- Better AI-generated reporting
- Cloud deployment
- Role-based access control
- Advanced analytics and visualization
- More comprehensive automated testing

## 20. Project Outcome

The completed platform integrates examination monitoring, event logging, rule-based integrity scoring, AI-assisted reporting, evidence management, and Data Science analytics into a single examination monitoring workflow.

It provides structured information and evidence that can help invigilators review examination sessions efficiently.

## License

This project is intended to be released under the MIT License.
