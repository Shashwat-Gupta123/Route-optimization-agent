# 🚚 AI-Powered Route Optimization Agent

![Status](https://img.shields.io/badge/Status-Active-success) ![License](https://img.shields.io/badge/License-MIT-blue) ![Render Ready](https://img.shields.io/badge/Deployed_on-Render-purple)

## 📌 Executive Summary
The **AI-Powered Route Optimization Agent** is an enterprise-grade logistics and supply chain solution designed to automate, optimize, and monitor delivery fleets. Built upon a powerful Agentic AI Framework, it leverages modern language models to dynamically generate routing plans that balance delivery speed, operational cost, and carbon emissions. 

By unifying mathematical constraint solving with LLM-driven intelligence and real-time geocoding, this platform ensures maximum fleet utilization, rapid disruption handling, and complete operational visibility.

---

## ✨ Key Features

* **🧠 AI-Driven Route Planning**: Automatically generates optimal delivery routes, comparing the *Fastest*, *Cheapest*, and *Balanced* plans.
* **📍 Real-Time Fleet Monitoring**: A live interactive map (powered by Leaflet) tracks vehicle locations, active speeds, ETA deviations, and completed deliveries.
* **🌦️ Dynamic Weather Integration**: Ingests live weather data per delivery zone to factor conditions into delivery ETAs and routing decisions.
* **🚨 Proactive Alerting System**: Dispatches automated email alerts via SMTP for real-time operational disruptions (e.g., vehicle breakdowns, ETA delays, maintenance requirements).
* **📊 Analytics & KPI Dashboard**: Comprehensive reporting on fleet utilization, fuel costs, distance traveled, and carbon (CO2) emissions.
* **💬 Conversational AI Assistant**: An integrated natural language chat interface allowing dispatch managers to query route plans, ask for justifications, and receive strategic advice.

---

## 🏗️ System Architecture

This solution is divided into two decoupled components: a high-performance Python API and a rich, interactive React frontend.

### Backend (Python / FastAPI)
- **Framework**: FastAPI for high-throughput, async REST APIs.
- **AI/Agents**: Azure OpenAI for agentic decision-making, natural language Q&A, and anomaly detection.
- **Optimization**: Route solving heuristics and matrix distance calculation.
- **Integrations**: OpenRouteService (Routing), Nominatim (Geocoding), Open-Meteo (Weather), SMTP (Alerts).

### Frontend (React / Vite)
- **Framework**: React 19 + Vite for rapid development and optimized builds.
- **Mapping**: React-Leaflet for rich, interactive, real-time vector maps.
- **Visualizations**: Recharts for dynamic KPI charting and analytics.

---

## 🚀 Quick Start Guide

### Prerequisites
- Node.js (v18+)
- Python (v3.10+)
- Valid API Keys (Azure OpenAI, OpenRouteService)

### 1. Backend Setup
```bash
cd backend
python -m venv .venv
# Activate virtual environment
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory based on `.env.example`:
```env
OPEN_ROUTER_API_KEY=your_key_here
AZURE_OPEN_AI_KEY=your_key_here
AZURE_OPEN_AI_ENDPOINT=https://your-endpoint.openai.azure.com/
DEPLOYEMENT_NAME=your_model_deployment
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
```

Start the API:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend/route-optimization
npm install
npm run dev
```
The dashboard will be available at `http://localhost:5173`.

---

## ☁️ Deployment (Render)

This project is fully configured for one-click deployment on [Render](https://render.com) using the provided `render.yaml` Blueprint.

1. Push this repository to GitHub.
2. Log into the Render Dashboard and click **New Blueprint Instance**.
3. Connect your repository. Render will automatically provision:
   - A **Web Service** for the FastAPI backend.
   - A **Static Site** for the React frontend.
4. Add your Environment Variables (from your `.env` file) to the backend service in the Render dashboard.

---

## 📈 Business Impact

By deploying the AI Route Optimization Agent, logistics operations can expect:
- **15-20% reduction** in fuel consumption and vehicle wear-and-tear.
- **Enhanced SLA compliance** through proactive delay management.
- **Reduced manual dispatch time** by automating complex routing calculations.
- **Lower carbon footprint**, directly contributing to corporate ESG (Environmental, Social, and Governance) sustainability goals.
