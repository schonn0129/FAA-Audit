# FAA Audit Application - Windows Docker Setup Guide

## Overview

This guide walks you through setting up and running the FAA Audit Application locally on Windows using Docker Desktop.

## Prerequisites

- **Windows 10/11** with WSL 2 (Windows Subsystem for Linux 2)
- **Docker Desktop for Windows** (4.4+)
- Download from: https://www.docker.com/products/docker-desktop
- **At least 4GB RAM** allocated to Docker (application uses machine learning embeddings)
- **At least 5GB free disk space**

## Installation Steps

### 1. Install Docker Desktop

1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop
2. Run the installer and follow the prompts
3. When prompted for WSL 2, select "Yes" (required for smooth Docker performance)
4. Restart your computer if required
5. Verify installation:
   ```powershell
   docker --version
   docker run hello-world
   ```

### 2. Configure Docker for WSL 2 (Recommended)

1. Open Docker Desktop **Settings**
2. Go to **Resources** → **WSL Integration**
3. Enable WSL Integration with your distribution
4. Apply & Restart

This significantly improves performance on Windows.

### 3. Navigate to the Project

```powershell
cd C:\Users\SchonnUnderwood\FAA-Audit
```

## Running the Application

### Quick Start (Recommended)

Use the PowerShell script to manage Docker:

```powershell
# Start the application
.\docker-start.ps1 up

# View logs
.\docker-start.ps1 logs

# Check status
.\docker-start.ps1 status

# Stop the application
.\docker-start.ps1 down

# Rebuild containers (if code changes)
.\docker-start.ps1 rebuild
```

### First Launch

1. **Start the application:**
   ```powershell
   .\docker-start.ps1 up
   ```

2. **Wait for containers to start:**
   - First build takes 5-10 minutes
   - Downloads Python dependencies
   - Downloads Node.js build tools
   - Pre-downloads AI embedding model (~500MB)

3. **View progress:**
   ```powershell
   .\docker-start.ps1 logs
   ```
   
   Wait until you see messages like:
   - `faa-audit-backend: * Running on http://0.0.0.0:5000`
   - `faa-audit-frontend: Creating volume...`

### Access the Application

- **Frontend (Web UI):** http://localhost:8888
- **Backend API:** http://localhost:5000
- **Health Check:** http://localhost:5000/api/health

## Using Docker Commands Directly

If you prefer using docker-compose commands directly:

```powershell
# Start containers in background
docker-compose -f docker-compose.windows.yml up -d

# View logs
docker-compose -f docker-compose.windows.yml logs -f

# View specific service logs
docker-compose -f docker-compose.windows.yml logs -f backend
docker-compose -f docker-compose.windows.yml logs -f frontend

# Stop containers
docker-compose -f docker-compose.windows.yml down

# Remove containers and rebuild from scratch
docker-compose -f docker-compose.windows.yml down
docker-compose -f docker-compose.windows.yml build --no-cache
docker-compose -f docker-compose.windows.yml up -d
```

## Troubleshooting

### Docker daemon not running

**Solution:**
1. Open Docker Desktop application
2. Wait for it to fully start (check system tray)
3. Try again

### Ports Already in Use

If you get "port already in use" error:

**Option 1: Use different ports**
- Edit `docker-compose.windows.yml`
- Change port mappings:
  ```yaml
  backend:
    ports:
      - "5001:5000"  # Change first number
  frontend:
    ports:
      - "8889:80"    # Change first number
  ```

**Option 2: Find and stop process using port**
```powershell
# Find process on port 5000
Get-NetTCPConnection -LocalPort 5000 | Select-Object -Property State, OwningProcess
```

### Containers keep restarting

**Check logs:**
```powershell
.\docker-start.ps1 logs
```

**Common causes:**
- Insufficient memory (increase Docker memory allocation)
- Port conflict
- Missing dependencies

### Out of Memory

The embedding model requires ~2GB RAM during first initialization.

**Solution:**
1. Open Docker Desktop Settings
2. Go to **Resources**
3. Increase **Memory** to at least 4GB
4. Apply & Restart

### Frontend shows but API errors appear

**Check backend is running:**
```powershell
.\docker-start.ps1 status
```

**Restart everything:**
```powershell
.\docker-start.ps1 down
.\docker-start.ps1 up
```

## Persistent Data

Your uploaded PDFs and database are saved in:
```
backend/
  ├── uploads/   <- Uploaded PDF files
  ├── manuals/   <- Parsed manual data
  └── data/      <- SQLite database
```

These directories persist between container restarts, but are deleted if you use `docker-compose down -v`.

## Updating the Application

When code changes are pushed to GitHub:

1. Update your local repository:
   ```powershell
   git pull
   ```

2. Rebuild and restart:
   ```powershell
   .\docker-start.ps1 rebuild
   ```

The database and uploaded files are preserved.

## Development Mode

For development with live code reloading, run without Docker:

**Terminal 1 - Backend:**
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

**Terminal 2 - Frontend:**
```powershell
cd frontend
npm install
npm run dev
```

Access at: http://localhost:3000

## Performance Tips

1. **Enable WSL 2 Integration** for better performance
2. **Allocate sufficient RAM** - at least 4GB to Docker
3. **Use SSD** - faster image builds and data access
4. **Keep Docker updated** - regularly update Docker Desktop

## Support & Documentation

- **API Documentation:** http://localhost:5000/api/docs (if implemented)
- **Project Repository:** https://github.com/schonn0129/FAA-Audit
- **Issue Tracker:** https://github.com/schonn0129/FAA-Audit/issues

## Next Steps

1. Open http://localhost:8888 in your browser
2. Upload a DCT PDF file
3. Wait for parsing to complete
4. Review the extracted data

## Useful Commands

```powershell
# Remove all FAA Audit containers and images
docker-compose -f docker-compose.windows.yml down
docker rmi faa-audit-backend faa-audit-frontend

# Check Docker disk usage
docker system df

# Clean up unused images/containers
docker system prune

# View all containers
docker ps -a

# View all images
docker images

# Stop a specific container
docker stop faa-audit-backend

# Access container shell (debugging)
docker exec -it faa-audit-backend bash
docker exec -it faa-audit-frontend sh
```
