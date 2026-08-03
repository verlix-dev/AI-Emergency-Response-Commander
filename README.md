<div align="center">

# 🚨 ARES
## AI-Assisted Response & Emergency System

### **From Detection to Decision**

An AI-powered emergency response platform that transforms aerial imagery into structured operational intelligence through computer vision, deterministic decision engines, intelligent resource allocation, and AI-assisted commander briefing.

---

![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi)
![YOLO](https://img.shields.io/badge/YOLO26m-Custom%20Trained-red?style=for-the-badge)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite)
![Groq](https://img.shields.io/badge/Groq-LLM-orange?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-success?style=for-the-badge)

</div>

---

# 📖 Overview

ARES (AI-Assisted Response & Emergency System) is an intelligent emergency management platform designed to assist emergency coordinators in making faster, more informed operational decisions.

Unlike traditional disaster detection systems that stop after identifying objects, ARES continues the decision-making pipeline by analyzing incidents, evaluating severity, prioritizing emergency response, recommending operational resources, generating commander-ready briefings, and maintaining incident history.

The system combines computer vision, deterministic decision intelligence, operational planning, and AI-assisted narration into a single workflow.

---

# 🚨 The Problem

Emergency responders often receive aerial images from drones, CCTV systems, helicopters, or satellites.

Although object detection models can identify hazards, responders still need to answer operational questions:

- What type of incident is this?
- How severe is it?
- How urgent is the response?
- Which emergency resources should be deployed?
- How should commanders be briefed?
- How should the incident be documented?

Traditional vision systems stop after detection.

ARES continues until actionable decisions are produced.

---

# ✨ Features

## 🛰️ Vision Intelligence

- Custom-trained YOLO26m disaster detection model
- Multi-disaster aerial scene understanding
- Bounding box visualization
- Structured object extraction

---

## 🧠 Incident Analysis

- Incident classification
- Hazard identification
- Situation assessment
- Operational evidence generation

---

## 🚨 Decision Intelligence

- Severity Assessment Engine
- Priority Assessment Engine
- Confidence Engine
- Explanation Engine

All operational decisions are deterministic and fully explainable.

---

## 🚒 Resource Allocation

ARES recommends emergency resources based on:

- Incident type
- Severity
- Operational rules
- Resource availability

Examples:

- Fire Trucks
- Ambulances
- Police Units
- Rescue Teams
- Boats
- Heavy Machinery
- Hazmat Teams

---

## 🤖 Commander Intelligence

Powered by Groq LLM.

ARES generates natural-language commander briefings while keeping all operational decisions deterministic.

The LLM never determines:

- Severity
- Priority
- Resource Allocation

It only converts structured facts into professional operational briefings.

---

## 💾 Incident Management

- Incident database
- Vision result storage
- Incident history
- Action plans
- Commander briefs
- Resource persistence

---

# 🏗️ System Architecture

```text
                    ARES

        Upload Drone / Aerial Image
                     │
                     ▼
      Vision Intelligence Engine
                     │
                     ▼
     Disaster Detection & Parsing
                     │
                     ▼
     Incident Analysis Engine
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
 Severity Engine          Priority Engine
        │                         │
        └────────────┬────────────┘
                     ▼
      Resource Allocation Engine
                     │
                     ▼
     Commander Intelligence Layer
                     │
                     ▼
 Incident Database & Operations Dashboard
```

---

# ⚙️ Workflow

```
Drone Image

↓

Vision Intelligence

↓

Incident Understanding

↓

Severity Analysis

↓

Priority Assessment

↓

Resource Recommendation

↓

Commander Brief

↓

Database Storage

↓

Operations Dashboard
```

---

# 🧠 Core Components

## Vision Intelligence Engine

Uses a custom-trained YOLO26m model to detect disaster-related objects from aerial imagery.

The model serves as the evidence collection stage rather than the final output.

---

## Incident Analysis Engine

Transforms raw detections into structured incident information.

Examples:

- Building Fire
- Flood
- Road Accident
- Building Collapse

---

## Severity Assessment Engine

Calculates operational severity using deterministic rules.

---

## Priority Assessment Engine

Determines response urgency.

---

## Resource Allocation Engine

Determines required emergency resources.

---

## Commander Intelligence Engine

Uses Groq to generate professional operational briefings while preserving deterministic decisions.

---

# 🛠️ Tech Stack

| Category | Technologies |
|-----------|-------------|
| Backend | FastAPI |
| Frontend | React + Vite |
| AI | YOLO26m |
| Computer Vision | OpenCV |
| LLM | Groq |
| Database | SQLite |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Validation | Pydantic |
| Testing | Pytest |

---

# 📂 Project Structure

```text
ARES/
│
├── backend/
│
├── frontend/
│
├── app/
│
├── vision/
│
├── database/
│
├── api/
│
├── services/
│
├── engines/
│
├── tests/
│
└── README.md
```

---

# 🚀 Installation

```bash
git clone https://github.com/yourusername/ARES.git

cd ARES
```

Backend

```bash
cd backend

python -m venv venv

source venv/bin/activate

pip install -r requirements.txt
```

Run

```bash
uvicorn app.main:app --reload
```

---

# 🔥 Example Pipeline

```
Input

↓

Flood Image

↓

Flood Detected

↓

Severity: Moderate

↓

Priority: High

↓

Resources:

• Rescue Boat

• Police

• Medical Team

↓

Commander Brief Generated

↓

Incident Stored
```

---

# 📊 Database

ARES stores:

- Incidents
- Vision Results
- Resources
- Incident Analysis
- Action Plans
- Commander Briefs
- Upload History

---

# 📈 Future Roadmap

- Live Drone Integration
- CCTV Support
- Video Analysis
- GIS Mapping
- Weather Integration
- Live Resource Dispatch
- Multi-Agent Coordination
- Predictive Incident Analytics

---

# 🤝 Contributing

Contributions are welcome.

Please open an issue before submitting major changes.

---



<div align="center">

## 🚨 ARES

### AI-Assisted Response & Emergency System

**Detect. Analyze. Dispatch. Respond.**

</div>
