import qrcode
from flask_cors import CORS
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
import os
import hashlib
import sqlite3

# ✅ IMPORT VERIFY LOGIC
from verify import verify_qr as verify_qr_logic

# ---------------- INIT APP ----------------
app = Flask(__name__)
CORS(app)
app.secret_key = "secret123"

UPLOAD_FOLDER = "uploads"
DB_FILE = "database.db"
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DATABASE SETUP ----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT,
        password TEXT,
        role TEXT,
        status INTEGER DEFAULT 1
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        file_hash TEXT,
        student_name TEXT,
        roll_number TEXT,
        course TEXT,
        issue_date TEXT,
        institute TEXT,
        uploaded_by TEXT,
        qr_path TEXT,
        scan_count INTEGER DEFAULT 0,
        failed_attempts INTEGER DEFAULT 0,
        status TEXT DEFAULT 'VALID'
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id INTEGER,
        verified_by TEXT,
        status TEXT,
        file_hash TEXT,
        verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()

# ---------------- PASSWORD ----------------
def generate_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(stored_hash, input_password):
    return stored_hash == hashlib.sha256(input_password.encode()).hexdigest()

# ---------------- USER ----------------
def register_user(username, email, password, role):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        hashed = generate_hash(password)
        c.execute("INSERT INTO users (username,email,password,role) VALUES (?,?,?,?)",
                  (username, email, hashed, role))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_user(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, username, password, role FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "username": row[1], "password": row[2], "role": row[3]}
    return None

# ---------------- DOCUMENT ----------------
def save_document(data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute('''INSERT INTO documents 
    (filename,file_hash,student_name,roll_number,course,issue_date,institute,uploaded_by,qr_path)
    VALUES (?,?,?,?,?,?,?,?,?)''', data)

    doc_id = c.lastrowid

    conn.commit()
    conn.close()

    return doc_id

def update_document(doc_id, scan_count, failed_attempts, status):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''UPDATE documents 
                 SET scan_count=?, failed_attempts=?, status=? 
                 WHERE id=?''',
                 (scan_count, failed_attempts, status, doc_id))
    conn.commit()
    conn.close()

# ---------------- INIT DB ----------------
init_db()

# ---------------- ROUTES ----------------

@app.route('/')
def home():
    return render_template('home.html')

# ---------------- SERVE UPLOADED FILES ----------------
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ---------------- REGISTER DOCUMENT + QR ----------------
@app.route('/register', methods=['POST'])
def register_document():
    file = request.files.get('document')

    if not file or file.filename == '':
        return {"error": "No file uploaded"}, 400

    if not allowed_file(file.filename):
        return {"error": "File type not allowed"}, 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    file_hash = hashlib.sha256(open(file_path, 'rb').read()).hexdigest()

    # ✅ Save document (without QR first)
    metadata = (
        filename,
        file_hash,
        request.form.get('student_name'),
        request.form.get('roll_number'),
        request.form.get('course'),
        request.form.get('issue_date'),
        request.form.get('institute'),
        session.get('user'),
        ""
    )

    doc_id = save_document(metadata)

    # ✅ Generate QR
    verify_url = f"http://192.168.1.2:5000/verify/{doc_id}"   # ⚠️ CHANGE IP

    qr = qrcode.make(verify_url)
    qr_filename = f"{doc_id}_qr.png"
    qr_path = os.path.join(UPLOAD_FOLDER, qr_filename)
    qr.save(qr_path)

    # ✅ Update DB with QR path
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE documents SET qr_path=? WHERE id=?", (qr_filename, doc_id))
    conn.commit()
    conn.close()

    # ✅ RETURN JSON (React will use this)
    return {
        "message": "Document registered successfully",
        "qr": f"http://192.168.1.2:5000/uploads/{qr_filename}",
        "verify_url": verify_url,
        "doc_id": doc_id
    }

# ---------------- VERIFY ROUTE (FIXED) ----------------
@app.route('/verify/<doc_id>')
def verify(doc_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT status, scan_count FROM documents WHERE id=?", (doc_id,))
    doc = c.fetchone()

    if not doc:
        return "<h2>❌ Document Not Found</h2>"

    status, scan_count = doc
    scan_count += 1

    c.execute("UPDATE documents SET scan_count=? WHERE id=?", (scan_count, doc_id))
    conn.commit()
    conn.close()

    return f"""
    <h2>✅ Document Verified</h2>
    <p>Status: {status}</p>
    <p>Total Scans: {scan_count}</p>
    """

# ---------------- VERIFY FILE ----------------
@app.route('/verify_document', methods=['POST'])
def verify_document():
    if 'document' not in request.files:
        return "No file uploaded"

    file = request.files['document']
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    file_hash = hashlib.sha256(open(filepath, "rb").read()).hexdigest()

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT id FROM documents WHERE file_hash=?", (file_hash,))
    doc = c.fetchone()

    if doc:
        status = 'VERIFIED'
    else:
        status = 'TAMPERED'

    c.execute("INSERT INTO logs (doc_id, verified_by, status, file_hash) VALUES (?, ?, ?, ?)",
              (doc[0] if doc else None, session.get('user'), status, file_hash))

    conn.commit()
    conn.close()

    return "✅ Verified" if status == 'VERIFIED' else "❌ Tampered"

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)