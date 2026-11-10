# Inkloom AI — Brand Governance AI Platform 🚀

Inkloom AI is an automated brand governance and compliance platform designed to evaluate marketing assets and content drafts against codified brand guidelines in real time.

---

## 🔗 Project Links

- **Live Production App:** [Your Vercel Live URL Here]
- **GitHub Repository:** [https://github.com/gmraarush210-blip/brand-governance-ai](https://github.com/gmraarush210-blip/brand-governance-ai.git)

---

## 🛠️ Tech Stack

- **Backend:** FastAPI (Python 3.x), SQLite, Uvicorn
- **Frontend:** React, Vite
- **Rule Engine:** Custom `inkloom_engine` validation pipeline
- **Deployment:** Vercel (Serverless Functions + Static Hosting)

---

## 📁 Repository Structure

```text
brand-governance-ai/
├── engine/              # Engine utility modules
├── inkloom_engine/      # Core brand compliance & rule extraction logic
├── routes/              # FastAPI API routing endpoints
├── frontend/            # React / Vite web interface
├── data/                # Data storage and reference guidelines
├── docs/                # Project documentation & specs
├── tests/               # Test suites
├── database.py          # SQLite database setup & connection
├── main.py              # Main FastAPI application entry point
├── requirements.txt     # Python backend dependencies
└── vercel.json          # Serverless deployment configuration
