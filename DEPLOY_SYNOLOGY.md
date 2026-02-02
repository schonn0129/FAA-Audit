# Deploying FAA Audit App on Synology NAS

This guide walks you through deploying the FAA Audit application on a Synology NAS (DS220+ or similar) using Container Manager. No command line required.

## Prerequisites

- Synology NAS running DSM 7.x
- Container Manager installed from Package Center
- At least 4GB free RAM (the app uses machine learning for embeddings)
- At least 5GB free disk space

---

## Step 1: Download the App from GitHub

1. Open your web browser and go to:
   ```
   https://github.com/schonn0129/FAA-Audit
   ```

2. Click the green **Code** button

3. Click **Download ZIP**

4. Save the file (it will be named `FAA-Audit-main.zip`)

---

## Step 2: Prepare the Folder Structure on Your NAS

1. Open **DSM** in your browser

2. Open **File Station**

3. Navigate to your shared folder (or create one). For this guide, we'll use:
   ```
   /volume1/audit-app/
   ```

4. Inside `audit-app`, you should have this structure:
   ```
   /volume1/audit-app/
       compose.yaml      <-- you'll copy this here
       app/              <-- create this folder
       data/             <-- create this folder (for persistent data)
   ```

5. To create folders: Right-click in File Station → Create → Create Folder

---

## Step 3: Upload and Extract the ZIP File

1. In File Station, navigate to `/volume1/audit-app/`

2. Click **Upload** → **Upload - Skip** (or Overwrite if updating)

3. Select the `FAA-Audit-main.zip` file you downloaded

4. Wait for the upload to complete

5. Right-click on `FAA-Audit-main.zip` → **Extract** → **Extract Here**

6. This creates a folder called `FAA-Audit-main`

7. **Rename** the folder: Right-click `FAA-Audit-main` → **Rename** → change it to `app`

   **Important:** The folder must be named exactly `app` (lowercase)

---

## Step 4: Move compose.yaml to the Right Location

1. In File Station, navigate into `/volume1/audit-app/app/`

2. You should see a file called `compose.yaml` inside the app folder

3. **Move it up one level:**
   - Right-click on `compose.yaml`
   - Click **Cut**
   - Navigate up to `/volume1/audit-app/`
   - Right-click in empty space → **Paste**

4. Your final folder structure should look like:
   ```
   /volume1/audit-app/
       compose.yaml         <-- the compose file
       data/                <-- empty folder for persistent data
       app/                 <-- the extracted repo contents
           backend/
           frontend/
           README.md
           ... other files
   ```

---

## Step 5: Create the Project in Container Manager

1. Open **Container Manager** from DSM main menu

2. Click **Project** in the left sidebar

3. Click **Create**

4. Fill in the form:
   - **Project name:** `faa-audit`
   - **Path:** Click **Set Path** and select `/volume1/audit-app`
   - **Source:** Select **Use existing docker-compose.yml**

5. Container Manager should automatically detect `compose.yaml`

6. Click **Next**

7. Review the settings and click **Done** or **Create**

---

## Step 6: Build and Start the Containers

1. Container Manager will now build the containers. This happens automatically.

2. **First build takes 5-10 minutes** because it downloads:
   - Python and dependencies
   - Node.js and React build tools
   - PyTorch (for the AI embedding feature) - this is large (~1-2GB)

3. You can watch the progress in Container Manager:
   - Click on your project (`faa-audit`)
   - Click the **Logs** tab to see build progress

4. When complete, both containers will show as **Running**:
   - `faa-audit-backend`
   - `faa-audit-frontend`

---

## Step 7: Access the Application

1. Open your web browser

2. Go to:
   ```
   http://YOUR-NAS-IP:8888
   ```

   Replace `YOUR-NAS-IP` with your NAS's IP address (e.g., `http://192.168.1.100:8888`)

3. You should see the FAA Audit application interface

4. Try uploading a PDF to test that everything works

---

## Troubleshooting

### Container won't start

1. In Container Manager, click on the project
2. Go to **Logs** tab
3. Look for error messages
4. Common issues:
   - Port 8888 already in use → Edit compose.yaml and change `8888:80` to another port like `8889:80`
   - Out of memory → The embedding model needs ~2GB RAM. Try restarting the NAS.

### Can't connect to the app

1. Make sure both containers show as **Running**
2. Check that port 8888 is not blocked by your NAS firewall:
   - DSM → Control Panel → Security → Firewall
3. Try accessing from the NAS itself: `http://localhost:8888`

### Build fails

1. Check the build logs in Container Manager
2. Make sure you have enough disk space (5GB+)
3. Make sure you have internet connectivity on the NAS

### App loads but API errors appear

1. Check that the backend container is running
2. Look at backend logs in Container Manager
3. The backend and frontend must be on the same Docker network (the compose.yaml handles this)

---

## Updating the App

When a new version is released:

1. Download the new ZIP from GitHub
2. In File Station, delete the old `/volume1/audit-app/app/` folder
3. Upload and extract the new ZIP
4. Rename to `app` as before
5. In Container Manager, select the project and click **Build**
6. This rebuilds with the new code

Your data in `/volume1/audit-app/data/` is preserved during updates.

---

## Data Storage

Your uploaded PDFs and database are stored in:

```
/volume1/audit-app/data/
    uploads/    <-- uploaded PDF files
    manuals/    <-- parsed manual data
    db/         <-- SQLite database
```

**Backup this folder** to preserve your data.
