# MedAI Nexus — Professional Full Working Prototype

Hospital-style Flask prototype for the seminar project **From Data to Diagnosis: The Power of Artificial Intelligence in Healthcare**.

### Modules
- Clinical Command Center
- Patient Registry
- Live Patient Monitoring + demo vital assessment
- Appointments
- Medical Imaging review workflow + image upload
- AI Drug Discovery virtual screening demo
- Virtual Care
- Trust & Safety interactive controls

### Run on Windows
Open PowerShell in this folder:

```powershell
py -m pip install -r requirements.txt
py app.py
```

Open **http://127.0.0.1:5000**

The app creates its SQLite database automatically at `data/medai_nexus.db`.

### Important
This is an academic/prototype system. The AI results in the drug-discovery module are simulated for demonstration. The imaging workflow is an AI-assisted review workflow, not an autonomous diagnostic system. Do not use this prototype for real clinical diagnosis or treatment.


## Dataset integration
The project bundles `data/MedAI_Nexus_Healthcare_Dataset_10000.csv` and automatically imports its 10,000 synthetic records into the local database on first run. The dataset contains 22 fields: the original 15-field Healthcare Dataset structure plus project-specific monitoring fields. The project uses the Kaggle dataset schema as a reference; this bundled CSV is a customized synthetic dataset, not the original Kaggle download.
