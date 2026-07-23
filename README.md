# 🛡️ Vigil AI

### Distributed Edge-to-Core Intrusion Detection System

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-20+-339933?logo=nodedotjs&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-24+-2496ED?logo=docker&logoColor=white)
![React](https://img.shields.io/badge/React-19+-61DAFB?logo=react&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?logo=postgresql&logoColor=white)
![Kafka](https://img.shields.io/badge/Apache_Kafka-3.9+-231F20?logo=apachekafka&logoColor=white)
![License](https://img.shields.io/badge/License-Proprietary-red)

An air-gapped, high-performance monitoring solution for real-time zone intrusion detection and object tracking across distributed camera networks.

**Vigil AI** runs a two-layer distributed pipeline. **Edge nodes** (Raspberry Pi 4 / Jetson) perform all AI inference, object tracking, and zone evaluation locally on each camera. The **Central Core** acts purely as an orchestration layer — ingesting Kafka events, persisting incidents to PostgreSQL, broadcasting real-time updates via WebSocket, and serving the React dashboard to operators.

---

## 📑 Table of Contents

- [Tech Stack](#tech-stack)
- [How It Works](#how-it-works)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Verify Prerequisites](#verify-prerequisites)
- [Clone the Repository](#clone-the-repository)
- [Deploy the Central Server](#deploy-the-central-server)
- [Connect an Edge Device](#connect-an-edge-device)
- [Access the Dashboard](#access-the-dashboard)
- [Operations & Troubleshooting](#operations--troubleshooting)
- [Environment Variable Reference](#environment-variable-reference)
- [Contributing](#contributing)
- [License](#license)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Edge Inference | YOLOv26 ONNX Runtime (CPU), OpenCV |
| Edge Tracking | DeepSORT (Kalman filter + appearance re-ID) |
| Edge → Core Transport | Apache Kafka (KRaft mode, single broker) |
| Core Backend | FastAPI, Uvicorn, Python 3.11 |
| Core Database | PostgreSQL 15 (SQLAlchemy + asyncpg) |
| Core Frontend | React 19, Vite, Tailwind CSS, Nginx |
| Real-Time Sync | WebSocket broadcaster |
| Containerization | Docker + Docker Compose |

---

## How It Works

```
[ EDGE NODE — near each CCTV camera ]
  RTSP Stream → YOLO ONNX Inference → DeepSORT Tracker
      → Zone / Tripwire Engine → Per-Track State Machine
          → Kafka Producer (intrusion_confirmed / heartbeat / track_resolved)

                    [ AIRGAPPED NETWORK ]

[ CENTRAL SERVER ]
  Kafka Consumer → Incident Manager → PostgreSQL
                                    → WebSocket Broadcaster → React Dashboard
```

- **Edge devices never stream continuous video** to the core. Only a single Base64-encoded annotated frame is sent after a confirmed intrusion, keeping bandwidth extremely low.
- **Config flows Core → Edge over REST** (`GET /edge/{camera_id}/config`). Each edge polls this endpoint every 30 seconds and caches the last-known-good config to disk for offline resilience.
- **Kafka is unidirectional** (edge → core telemetry only) on a single topic `edge_events`.
- **Per-track state machine** confirms intrusions based on dwell time inside a zone (not single-frame confidence), suppressing transient false positives.

> 📖 **Detailed documentation** is available in the [`docs/`](docs/) folder:
> - [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — full system design, data flow, state machine, DB schema, and API surface
> - [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) — normalized coordinate system and tripwire direction conventions
> - [`docs/INFERENCE_EXP.md`](docs/INFERENCE_EXP.md) - experiment result statistics when deployed to edge devices
> - [`docs/TRAINING_EMP.md`](docs/TRAINING_EXP.md) - training configurations and results observed

---

## Repository Structure

```
vigilai/
│
├── central/
│   ├── backend/               # FastAPI app — routes, services, Kafka consumer
│   │   ├── app.py             # Entry point; starts background workers on lifespan
│   │   ├── requirements.txt   # Python dependencies
│   │   ├── Dockerfile
│   │   ├── core/              # DB session, security, logging, websocket manager
│   │   ├── db/                # SQLAlchemy models, schema.sql
│   │   ├── routes/            # incidents, cameras, zones, edge, settings, websockets
│   │   ├── services/          # Kafka consumer, escalation worker, camera health worker
│   │   └── schemas/           # Pydantic request/response schemas
│   │
│   ├── frontend/              # React + Vite dashboard
│   │   └── src/
│   │       ├── pages/         # Dashboard, Camera, Settings pages
│   │       ├── components/    # IncidentGrid, ZoneEditor, UI primitives
│   │       └── hooks/         # useWebSocket
│   │
│   ├── .env.example           # Central environment template
│   └── docker-compose.yaml    # Spins up PostgreSQL + Kafka + Backend + Frontend
│
├── edge/
│   ├── app/
│   │   ├── main.py            # Edge pipeline entry point (headless)
│   │   ├── core/config.py     # Pydantic settings — reads from .env
│   │   ├── models/            # YOLO ONNX weights (included in repo)
│   │   └── services/
│   │       ├── capture.py     # RTSP video capture manager
│   │       ├── inference.py   # YOLOv26 ONNX detection wrapper
│   │       ├── tracker.py     # DeepSORT tracker
│   │       ├── zone_engine.py # Point-in-polygon & line-crossing logic
│   │       ├── state_machine.py # Per-track lifecycle (NEW → CANDIDATE → CONFIRMED → RESOLVED)
│   │       ├── kafka_producer.py # Sends intrusion/heartbeat/resolved events
│   │       └── config_sync.py   # Polls central API for zone config updates
│   │
│   ├── .env.example           # Edge environment template
│   └── docker-compose.yaml    # Edge deployment
│
├── contracts/                 # Shared Pydantic (schemas.py) & TypeScript (types.ts) contracts
└── docs/                      # Architecture, conventions, tasks, folder structure
```

---

## Prerequisites

### Central Server

| Requirement | Version | Required For |
|---|---|---|
| Git | 2.40+ | Cloning the repository |
| Docker | 24.0+ | Running all central containers |
| Docker Compose | v2.20+ (plugin) | Orchestration of multi-container stack |
| Python | 3.11+ | Local development / debugging outside Docker |
| Node.js | 20+ | Local frontend development outside Docker |

> **Note:** Docker is the only hard requirement for deployment. Python and Node.js are needed only if you want to run the backend or frontend locally without containers.

### Edge Device

| Requirement | Version | Required For |
|---|---|---|
| Git | 2.40+ | Cloning the repository |
| Docker | 24.0+ | Running the edge container |
| Docker Compose | v2.20+ (plugin) | Edge orchestration |
| Python | 3.11+ | Local development / debugging outside Docker |
| RTSP camera stream | — | Any IP camera with an accessible RTSP URL |
| Network access to Central Server | — | Must reach Kafka (port 9095) and Backend API (port 8080) |

> **Supported hardware:** Raspberry Pi 4 (4GB+) or any Jetson-class device. The ONNX runtime is CPU-only by default; no GPU required. YOLO ONNX model weights are included in the repository under `edge/app/models/`.

---

## Verify Prerequisites

Run these commands on your machine **before** proceeding to deployment.

### Check Git

```bash
git --version
# Expected: git version 2.40.x or higher
```

### Check Docker and Docker Compose

```bash
docker --version
# Expected: Docker version 24.x.x or higher

docker compose version
# Expected: Docker Compose version v2.x.x
```

### Check Docker daemon is running

```bash
docker info
# Should return system info without errors. If it fails, start the Docker daemon:
# Linux:  sudo systemctl start docker
# Mac:    open Docker Desktop
# Windows: open Docker Desktop
```

### Check Python (for local development)

```bash
python --version
# Expected: Python 3.11.x or higher
```

### Check Node.js (for local frontend development)

```bash
node --version
# Expected: v20.x.x or higher
```
---

## 🏢 Organization Setup

Before cloning the repository, configure Git access according to organizational standards.

See:

**[AADF Gitea – Team Setup & Usage Guide](http://10.10.30.65:3000/AADF/rip-platform/wiki/AADF-Gitea-%E2%80%94-Team-Setup-%26-Usage-Guide)**

---

## Clone the Repository

Clone this repository on **both** the central server and each edge device.

```bash
git clone https://github.com/sultan-rrcat/vigilai.git
cd vigilai
```

---

## Deploy the Central Server

The central stack runs four containers: **PostgreSQL**, **Kafka** (KRaft mode), **FastAPI backend**, and the **React frontend**.

### Step 1 — Configure the environment

```bash
cd central
cp .env.example .env
cp frontend/.env.example .env
```

Open `.env` and fill in all required values:

```env
# Database
DB_USER=trainee
DB_PASSWORD=your_secure_password_here
DB_NAME=vigil-ai
DB_HOST_PORT=5435          # Host port mapped to Postgres (internal is always 5432)

# Kafka — KAFKA_ADVERTISED_HOST must be the IP address other machines use to reach THIS server
KAFKA_ADVERTISED_HOST=10.31.2.94    # ← Replace with your central server's LAN IP
KAFKA_HOST_PORT=9095                # External port edge devices connect to

# Proxy — leave blank if you are not behind a corporate proxy
HTTP_PROXY=
HTTPS_PROXY=
NO_PROXY=localhost,127.0.0.1,kafka,postgres,backend
```

> ⚠️ **`KAFKA_ADVERTISED_HOST` is critical.** Edge devices use this IP to connect to Kafka. It must be the LAN IP of the central server, reachable from the edge device's network. If this is set incorrectly, edge devices will fail with `NoBrokersAvailable`.

### Step 2 — Build and start the stack

```bash
# From the central/ directory
docker compose up -d --build
```

This will pull base images, build the backend and frontend, and start all four services. The first build takes 3–5 minutes.

### Step 3 — Verify all containers are running

```bash
docker compose ps
```

All four services should show status `running`:

| Container | Name | Port |
|---|---|---|
| PostgreSQL | `vigil-ai-postgres` | 5435 |
| Kafka | `vigil-ai-kafka` | 9095, 9096 |
| FastAPI Backend | `vigil-ai-backend` | 8080 |
| React Frontend | `vigil-ai-frontend` | 3001 |

The backend container waits for both PostgreSQL and Kafka to report healthy before it starts. Kafka needs approximately 20 seconds to initialize.

### Step 4 — Create the Kafka topic

This step is required on every fresh deployment (new volume). Run it after all containers are running:

**Linux / macOS:**
```bash
docker exec -it vigil-ai-kafka /opt/kafka/bin/kafka-topics.sh --create --topic edge_events --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
```

**Windows (PowerShell):**
```powershell
docker exec -it vigil-ai-kafka /opt/kafka/bin/kafka-topics.sh --create --topic edge_events --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
```

> **Note:** The command is identical on both platforms — Docker handles the path translation. Just copy and paste the single-line version.

### Step 5 — Verify the backend is healthy

```bash
curl http://localhost:8080/health
# Expected: {"status":"healthy"}
```

If this does not return `healthy`, check the backend logs:

```bash
docker logs vigil-ai-backend
```

### Step 6 — Verify the dashboard is accessible

Open your browser and navigate to:

```
http://localhost:3001
```

You should see the Vigil AI dashboard with an empty camera list.

---

## Connect an Edge Device

Each edge device represents one camera. Follow these steps **in order** — do not skip steps.

### Step 1 — Verify network connectivity to the central server

Run these from the edge device's terminal:

```bash
# Replace 10.31.2.94 with your central server's IP address
ping 10.31.2.94

# Check that the Kafka external port is reachable
nc -zv 10.31.2.94 9095
# Expected: Connection succeeded!

# Check that the backend API is reachable
curl http://10.31.2.94:8080/health
# Expected: {"status":"healthy"}
```

If any of these fail, resolve the network issue before proceeding. Check firewall rules, IP addressing, and ensure the central server is running.

### Step 2 — Verify prerequisites are met

```bash
git --version
docker --version
docker compose version
```

All three must return valid version numbers. If any fail, refer to the [Prerequisites](#prerequisites) section.

### Step 3 — Clone the repository

```bash
git clone https://github.com/sultan-rrcat/vigilai.git
cd vigilai/edge
```

### Step 4 — Register the camera in the dashboard

1. On a browser, open the dashboard at `http://<CENTRAL_SERVER_IP>:3001`
2. Navigate to **Cameras** → **Add Camera**
3. Fill in the camera name and location
4. Copy the generated **Camera ID** (UUID format, e.g. `b6f2b6b0-1234-4d3a-9f1a-000000000001`)

### Step 5 — Configure the edge environment

```bash
cp .env.example .env
```

Edit `edge/.env` with the following values:

```env
# Camera identity — paste the UUID from Step 4
CAMERA_ID=b6f2b6b0-1234-4d3a-9f1a-000000000001

# Your camera's RTSP stream URL
RTSP_URL=rtsp://admin:password@192.168.1.100:554/stream1

# Central server addresses (from the edge device's network perspective)
KAFKA_BROKER=10.31.2.94:9095
CENTRAL_API_URL=http://10.31.2.94:8080

# Inference tuning (optional — defaults shown)
FRAME_STRIDE=3
MODEL_PATH=models/yolo26n_coco_local.onnx

# State machine thresholds (optional — defaults shown)
MIN_DWELL_SECONDS=2.0
TRACK_TTL_SECONDS=5.0
```

> ⚠️ **Double-check all four required values** before proceeding: `CAMERA_ID`, `RTSP_URL`, `KAFKA_BROKER`, and `CENTRAL_API_URL`. A wrong value in any of these will cause the edge pipeline to fail silently or hang.

### Step 6 — Start the edge pipeline

```bash
docker compose up -d --build
```

### Step 7 — Verify the edge is connected

```bash
docker logs -f vigil-ai-edge
```

You should see the following log sequence:

```
[INFO] Initializing Autonomous Edge Pipeline (Headless Mode)...
[INFO] Capturing baseline reference frame for Central Dashboard...
[INFO] Successfully uploaded reference frame to Central Core.
[INFO] [heartbeats every 3 seconds]
```

On the dashboard, the camera card should change from **Offline** to **Online** within a few seconds of the first heartbeat.

### Step 8 — Draw detection zones

1. In the dashboard, click on your camera card → **Edit Zones**
2. The camera's reference frame (captured automatically on startup) is displayed as a background
3. Draw one or more **restricted zone polygons** over the areas you want to monitor
4. Set a **dwell threshold** per zone (e.g. 2 seconds — an object must remain inside this long to trigger an alarm)
5. Save — the edge device polls for config updates every 30 seconds and will reload automatically

---

## Access the Dashboard

| Service | URL |
|---|---|
| React Dashboard | `http://<server-ip>:3001` |
| Backend API (Swagger docs) | `http://<server-ip>:8080/docs` |
| Health endpoint | `http://<server-ip>:8080/health` |

The dashboard provides:

- **Incident Grid** — live list of intrusion events with snapshots, track info, and acknowledge/escalate controls
- **Camera Management** — register, view, and configure edge nodes
- **Zone Editor** — draw detection polygons and tripwires over camera reference frames
- **Settings** — configure dwell thresholds, escalation timeout, and retention policies

---

## Operations & Troubleshooting

### View logs

```bash
# Central backend
docker logs -f vigil-ai-backend

# Kafka broker
docker logs -f vigil-ai-kafka

# PostgreSQL
docker logs -f vigil-ai-postgres

# Frontend
docker logs -f vigil-ai-frontend

# Edge pipeline
docker logs -f vigil-ai-edge
```

### Restart a specific service

```bash
# From central/
docker compose restart backend

# From edge/
docker compose restart app
```

### Stop all services

```bash
# Central (from central/)
docker compose down

# Edge (from edge/)
docker compose down
```

### Full reset (deletes all data)

```bash
# ⚠️ This deletes all volumes — incidents, snapshots, DB data, Kafka data
docker compose down -v
```

### Common issues

| Symptom | Likely Cause | Fix |
|---|---|---|
| Backend container keeps restarting | Kafka or Postgres not healthy yet | Wait 30s and re-check `docker compose ps`. Kafka needs ~20s to initialize. |
| Edge logs show `Failed to upload reference frame` | Central API not reachable from edge | Verify `CENTRAL_API_URL` in edge `.env` and check firewall rules on port 8080. |
| Edge logs show `NoBrokersAvailable` | Kafka broker unreachable | Verify `KAFKA_BROKER` IP/port in edge `.env` and that port 9095 is open. Ensure `KAFKA_ADVERTISED_HOST` in central `.env` is the correct LAN IP. |
| Camera stuck on `Offline` in dashboard | No heartbeat received | Check edge logs. Confirm `CAMERA_ID` in edge `.env` matches the UUID from the dashboard. |
| Kafka topic not found error | Topic not created yet | Run the `kafka-topics.sh --create` command from the central deployment Step 4. |
| Zone changes not applied on edge | Config poll delay | Wait up to 60 seconds. Edge polls `GET /edge/{camera_id}/config` on a 30s timer. Check edge logs for `New config version detected` message. |
| Dashboard loads but shows no data | Backend not fully started | Check `docker logs vigil-ai-backend` for errors. Verify `curl http://localhost:8080/health` returns `healthy`. |
| Docker build fails with proxy error | Corporate proxy blocking image pulls | Set `HTTP_PROXY` and `HTTPS_PROXY` in central `.env` to your corporate proxy URL. |

---

## Environment Variable Reference

### Central (`central/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `DB_USER` | ✅ | — | PostgreSQL username |
| `DB_PASSWORD` | ✅ | — | PostgreSQL password |
| `DB_NAME` | ✅ | — | PostgreSQL database name |
| `DB_HOST_PORT` | ✅ | `5435` | Host port for Postgres (mapped from internal 5432) |
| `KAFKA_ADVERTISED_HOST` | ✅ | `10.31.2.94` | LAN IP of the central server (used by edge devices to connect to Kafka) |
| `KAFKA_HOST_PORT` | ✅ | `9095` | External Kafka port for edge device connections |
| `HTTP_PROXY` | ❌ | — | HTTP proxy for Docker builds (corporate network only) |
| `HTTPS_PROXY` | ❌ | — | HTTPS proxy for Docker builds (corporate network only) |
| `NO_PROXY` | ❌ | — | Comma-separated list of hosts to bypass proxy |

### Edge (`edge/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `CAMERA_ID` | ✅ | — | UUID of this camera, generated from the central dashboard |
| `RTSP_URL` | ✅ | — | Full RTSP URL of the camera stream |
| `KAFKA_BROKER` | ✅ | — | `<central-ip>:<KAFKA_HOST_PORT>` |
| `CENTRAL_API_URL` | ✅ | — | `http://<central-ip>:8080` |
| `FRAME_STRIDE` | ❌ | `3` | Process every Nth frame. Lower = more CPU usage. |
| `MODEL_PATH` | ❌ | `models/yolo26n_coco_local.onnx` | Path to YOLO ONNX model inside the container |
| `MIN_DWELL_SECONDS` | ❌ | `2.0` | Minimum dwell time inside a zone before intrusion is confirmed |
| `TRACK_TTL_SECONDS` | ❌ | `5.0` | Time before a lost track is discarded |

---

## Contributing

This is a proprietary project developed for RRCAT. Internal contributors should follow these guidelines:

1. Create a feature branch from `main` (`git checkout -b feature/your-feature`)
2. Follow the conventions in [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) for any geometry or coordinate changes
3. Keep the shared contracts in sync — if you change `contracts/schemas.py`, update `contracts/types.ts` in the same commit
4. Test edge changes with both a live RTSP stream and the mock test files in `edge/app/test/`
5. Use conventional commit messages (`feat:`, `fix:`, `docs:`, `refactor:`)

---

## License

Copyright © 2026 Raja Ramanna Centre for Advanced Technology (RRCAT).  
All rights reserved. This software and its associated documentation are proprietary and confidential property of RRCAT.

**Developed by:** Sultan Mamud, CAT1 Trainee, Computer Division, Raja Ramanna Centre for Advanced Technology (RRCAT)