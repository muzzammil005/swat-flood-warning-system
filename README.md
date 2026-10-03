# Swat Flood Early-Warning System

University Final-Year Project (FYP). An industrial-quality, production-ready system for flood early warning across a river-basin zone network using AI prediction models, a Next.js web dashboard, and a Flutter mobile app.

## 🚀 Quick Start (How to Run)

To run this project, you do NOT need to install Python, Node.js, or configure any databases locally. The entire infrastructure is containerized and will set itself up automatically.

### Prerequisites
- [Git](https://git-scm.com/downloads)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Make sure it is running)

### Step-by-Step Instructions

1. **Clone the repository**
   Open your terminal or command prompt and run:
   ```bash
   git clone https://github.com/muzzammil005/swat-flood-warning-system.git
   cd swat-flood-warning-system
   ```

2. **Start the System**
   In the project folder, simply run:
   ```bash
   docker compose up --build -d
   ```
   *Note: On the first run, this command will download the necessary AI libraries (like scikit-learn, numpy) and build the containers. It may take a few minutes depending on your internet connection.*

3. **Access the Applications**
   Once the containers are running, the system is fully operational. The database will automatically migrate and seed itself with demo data and AI terrain features.
   - **Web Dashboard (Frontend):** Open your browser and go to `http://localhost:3000`
   - **API (Backend):** The FastAPI server runs on `http://localhost:8000` (You can view the API documentation at `http://localhost:8000/docs`)

## 📱 Mobile Application

The Flutter mobile application APK has been pre-built for your convenience.
You can find the production-ready Android APK in the repository at:
`mobile/build/app/outputs/flutter-apk/app-release.apk`

Transfer this file to any Android device and install it to view the mobile client.

## 🏗️ Architecture & Tech Stack

This project follows a Clean Architecture (Onion) pattern ensuring domain purity and industrial-grade quality.

- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL + PostGIS, Alembic
- **Machine Learning:** LightGBM, Scikit-learn, Numpy, Pandas (Risk Prediction Engine)
- **Frontend (Web):** Next.js 15, React, Tailwind CSS, Leaflet Maps
- **Mobile App:** Flutter, Dart
- **Infrastructure:** Docker, Docker Compose

---
*Created by Muhammad Muzzammil for the Final Year Project.*
