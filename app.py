import os, sqlite3, json, csv
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "medai_nexus.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "medai-nexus-demo-key")

def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = db()
    c.executescript("""
CREATE TABLE IF NOT EXISTS patients(
      id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT UNIQUE, name TEXT NOT NULL,
      age INTEGER, gender TEXT, blood_type TEXT, condition TEXT, date_of_admission TEXT,
      doctor TEXT, hospital TEXT, insurance_provider TEXT, billing_amount REAL,
      room_number INTEGER, admission_type TEXT, discharge_date TEXT, medication TEXT,
      test_results TEXT, heart_rate REAL, spo2 REAL, temperature REAL,
      systolic REAL, diastolic REAL, patient_status TEXT, phone TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS vitals(
      id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT, heart_rate REAL, spo2 REAL,
      temperature REAL, systolic REAL, diastolic REAL, status TEXT, recorded_at TEXT);
    CREATE TABLE IF NOT EXISTS appointments(
      id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT, clinician TEXT, date TEXT,
      time TEXT, visit_type TEXT, notes TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS imaging(
      id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT, modality TEXT, priority TEXT,
      body_region TEXT, context TEXT, filename TEXT, status TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS consultations(
      id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT, reason TEXT, priority TEXT,
      message TEXT, status TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS care_notes(
      id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT, note TEXT, author TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS drug_runs(
      id INTEGER PRIMARY KEY AUTOINCREMENT, target TEXT, library_size INTEGER, status TEXT,
      candidates TEXT, created_at TEXT);
    """)
    # Upgrade older local databases so the bundled 10,000-record dataset can be imported safely.
    required_columns = {
        "blood_type":"TEXT","date_of_admission":"TEXT","hospital":"TEXT",
        "insurance_provider":"TEXT","billing_amount":"REAL","room_number":"INTEGER",
        "admission_type":"TEXT","discharge_date":"TEXT","medication":"TEXT",
        "test_results":"TEXT","heart_rate":"REAL","spo2":"REAL","temperature":"REAL",
        "systolic":"REAL","diastolic":"REAL","patient_status":"TEXT"
    }
    existing_cols={r["name"] for r in c.execute("PRAGMA table_info(patients)").fetchall()}
    for col,typ in required_columns.items():
        if col not in existing_cols:
            c.execute(f"ALTER TABLE patients ADD COLUMN {col} {typ}")

    c.execute("""CREATE TABLE IF NOT EXISTS app_meta(
      key TEXT PRIMARY KEY, value TEXT, created_at TEXT)""")
    imported=c.execute("SELECT value FROM app_meta WHERE key='healthcare_dataset_imported'").fetchone()
    dataset_path=os.path.join(BASE_DIR,"data","MedAI_Nexus_Healthcare_Dataset_10000.csv")
    if not imported and os.path.exists(dataset_path):
        c.execute("DELETE FROM patients")
        with open(dataset_path,"r",encoding="utf-8-sig",newline="") as f:
            reader=csv.DictReader(f)
            batch=[]
            for r in reader:
                batch.append((
                    r.get("Patient_ID"),r.get("Name"),r.get("Age"),r.get("Gender"),r.get("Blood_Type"),
                    r.get("Medical_Condition"),r.get("Date_of_Admission"),r.get("Doctor"),r.get("Hospital"),
                    r.get("Insurance_Provider"),r.get("Billing_Amount"),r.get("Room_Number"),
                    r.get("Admission_Type"),r.get("Discharge_Date"),r.get("Medication"),r.get("Test_Results"),
                    r.get("Heart_Rate"),r.get("SpO2"),r.get("Temperature_F"),r.get("Systolic_BP"),
                    r.get("Diastolic_BP"),r.get("Patient_Status"),"",datetime.now().isoformat(timespec="seconds")
                ))
                if len(batch)>=500:
                    c.executemany("""INSERT OR IGNORE INTO patients(
                      patient_id,name,age,gender,blood_type,condition,date_of_admission,doctor,hospital,
                      insurance_provider,billing_amount,room_number,admission_type,discharge_date,medication,
                      test_results,heart_rate,spo2,temperature,systolic,diastolic,patient_status,phone,created_at)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",batch)
                    batch=[]
            if batch:
                c.executemany("""INSERT OR IGNORE INTO patients(
                  patient_id,name,age,gender,blood_type,condition,date_of_admission,doctor,hospital,
                  insurance_provider,billing_amount,room_number,admission_type,discharge_date,medication,
                  test_results,heart_rate,spo2,temperature,systolic,diastolic,patient_status,phone,created_at)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",batch)
        c.execute("INSERT OR REPLACE INTO app_meta(key,value,created_at) VALUES('healthcare_dataset_imported','10000',?)",
                  (datetime.now().isoformat(timespec="seconds"),))
    elif not imported:
        # Fallback for a missing dataset file.
        if c.execute("SELECT COUNT(*) AS n FROM patients").fetchone()["n"]==0:
            rows=[("P-1001","Ananya Rao",34,"Female","","Routine follow-up","","Dr. Priya Sharma","","","","","","","","",75,98,98.6,120,80,"Stable","",datetime.now().isoformat(timespec="seconds"))]
            c.executemany("""INSERT INTO patients(
              patient_id,name,age,gender,blood_type,condition,date_of_admission,doctor,hospital,
              insurance_provider,billing_amount,room_number,admission_type,discharge_date,medication,
              test_results,heart_rate,spo2,temperature,systolic,diastolic,patient_status,phone,created_at)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",rows)

    c.commit()
    c.close()

def rows(sql, args=()):
    c = db()
    out = [dict(r) for r in c.execute(sql, args).fetchall()]
    c.close()
    return out

init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.get("/api/patients")
def get_patients():
    q=(request.args.get("q") or "").strip()
    limit=min(max(int(request.args.get("limit",200)),1),500)
    if q:
        like=f"%{q}%"
        data=rows("""SELECT * FROM patients
                     WHERE patient_id LIKE ? OR name LIKE ? OR condition LIKE ?
                     OR doctor LIKE ? OR hospital LIKE ?
                     ORDER BY id DESC LIMIT ?""",(like,like,like,like,like,limit))
    else:
        data=rows("SELECT * FROM patients ORDER BY id DESC LIMIT ?",(limit,))
    c=db()
    total=c.execute("SELECT COUNT(*) AS n FROM patients").fetchone()["n"]
    c.close()
    return jsonify(total=total,patients=data)

@app.get("/api/summary")
def summary():
    c=db()
    total=c.execute("SELECT COUNT(*) AS n FROM patients").fetchone()["n"]
    stable=c.execute("SELECT COUNT(*) AS n FROM patients WHERE patient_status='Stable'").fetchone()["n"]
    attention=c.execute("SELECT COUNT(*) AS n FROM patients WHERE patient_status='Attention'").fetchone()["n"]
    c.close()
    return jsonify(
        total_patients=total, stable_patients=stable, attention_patients=attention,
        notes=rows("SELECT * FROM care_notes ORDER BY id DESC LIMIT 6")
    )

@app.post("/api/patients")
def add_patient():
    x = request.json or {}
    if not x.get("name"):
        return jsonify(ok=False, error="Patient name is required"), 400
    pid = x.get("patient_id") or f"P-{8000 + len(rows('SELECT id FROM patients')) + 1}"
    try:
        c = db()
        c.execute(
            "INSERT INTO patients(patient_id,name,age,gender,condition,doctor,phone,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (pid,x.get("name"),x.get("age"),x.get("gender"),x.get("condition"),
             x.get("doctor"),x.get("phone"),datetime.now().isoformat(timespec="seconds"))
        )
        c.commit(); c.close()
        return jsonify(ok=True, patient_id=pid)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400

@app.post("/api/vitals")
def save_vitals():
    x = request.json or {}
    try:
        hr=float(x.get("heart_rate",0)); spo=float(x.get("spo2",0))
        temp=float(x.get("temperature",0)); syst=float(x.get("systolic",0)); dia=float(x.get("diastolic",0))
        status = "Attention" if (hr < 55 or hr > 100 or spo < 94 or temp >= 100.4 or syst >= 140 or syst < 90 or dia >= 90) else "Stable"
        c=db()
        c.execute(
            "INSERT INTO vitals(patient_id,heart_rate,spo2,temperature,systolic,diastolic,status,recorded_at) VALUES(?,?,?,?,?,?,?,?)",
            (x.get("patient_id"),hr,spo,temp,syst,dia,status,datetime.now().isoformat(timespec="seconds"))
        )
        c.commit(); c.close()
        return jsonify(ok=True,status=status)
    except Exception as e:
        return jsonify(ok=False,error=str(e)),400

@app.post("/api/appointments")
def appointment():
    x=request.json or {}
    c=db()
    c.execute(
        "INSERT INTO appointments(patient_id,clinician,date,time,visit_type,notes,created_at) VALUES(?,?,?,?,?,?,?)",
        (x.get("patient_id"),x.get("clinician"),x.get("date"),x.get("time"),x.get("visit_type"),
         x.get("notes"),datetime.now().isoformat(timespec="seconds"))
    )
    c.commit(); c.close()
    return jsonify(ok=True,message="Appointment scheduled successfully.")

@app.post("/api/imaging")
def imaging():
    x=request.form
    f=request.files.get("image")
    filename=""
    if f and f.filename:
        filename=os.path.basename(f.filename)
        f.save(os.path.join(UPLOAD_DIR, filename))
    c=db()
    c.execute(
        "INSERT INTO imaging(patient_id,modality,priority,body_region,context,filename,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
        (x.get("patient_id"),x.get("modality"),x.get("priority"),x.get("body_region"),x.get("context"),
         filename,"Pending clinician review",datetime.now().isoformat(timespec="seconds"))
    )
    c.commit(); c.close()
    return jsonify(ok=True,message="Imaging review case created.",filename=filename)


@app.post("/api/notes")
def care_note():
    x=request.json or {}
    c=db()
    c.execute(
        "INSERT INTO care_notes(patient_id,note,author,created_at) VALUES(?,?,?,?)",
        (x.get("patient_id"),x.get("note"),x.get("author","Care Team"),
         datetime.now().isoformat(timespec="seconds"))
    )
    c.commit(); c.close()
    return jsonify(ok=True)

@app.post("/api/drug-screen")
def drug_screen():
    x=request.json or {}
    target=x.get("target","EGFR")
    n=int(x.get("library_size",80))
    candidates=[
        {"rank":1,"compound":"MNX-047","score":0.94},
        {"rank":2,"compound":"MNX-112","score":0.89},
        {"rank":3,"compound":"MNX-203","score":0.84}
    ]
    c=db()
    c.execute(
        "INSERT INTO drug_runs(target,library_size,status,candidates,created_at) VALUES(?,?,?,?,?)",
        (target,n,"Completed",json.dumps(candidates),datetime.now().isoformat(timespec="seconds"))
    )
    c.commit(); c.close()
    return jsonify(ok=True,candidates=candidates,
                   message=f"Virtual screening completed for {n} compounds.")

@app.get("/api/health")
def health():
    try:
        c=db(); c.execute("SELECT 1"); c.close()
        return jsonify(ok=True, database="SQLite")
    except Exception as e:
        return jsonify(ok=False,error=str(e)),500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
