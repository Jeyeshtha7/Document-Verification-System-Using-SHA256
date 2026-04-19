import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

DB_NAME = "database.db"

# ---------------- INIT DB ----------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # USERS
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin','verifier')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1
    )
    ''')

    # ✅ UPDATED DOCUMENTS TABLE (QR + FRAUD)
    c.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id TEXT UNIQUE,
        filename TEXT NOT NULL,
        hash TEXT NOT NULL,
        student_name TEXT,
        roll_number TEXT,
        course TEXT,
        issue_date TEXT,
        institute TEXT,
        uploaded_by TEXT,
        qr_path TEXT,
        scan_count INTEGER DEFAULT 0,
        failed_attempts INTEGER DEFAULT 0,
        status TEXT DEFAULT 'VALID',
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # LOGS
    c.execute('''
    CREATE TABLE IF NOT EXISTS verification_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        result TEXT NOT NULL,
        verified_by TEXT,
        verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()


# ---------------- USER ----------------
def register_user(username, email, password, role):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        hashed = generate_password_hash(password)
        c.execute("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                  (username, email, hashed, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user(username):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND is_active=1", (username,))
    user = c.fetchone()
    conn.close()
    return user

def check_password(hashed_password, plain_password):
    return check_password_hash(hashed_password, plain_password)

def get_all_verifiers():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE role='verifier'")
    result = c.fetchall()
    conn.close()
    return result

def toggle_verifier(user_id, status):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET is_active=? WHERE id=?", (status, user_id))
    conn.commit()
    conn.close()


# ---------------- DOCUMENT ----------------

# ✅ SAVE DOCUMENT WITH QR + FRAUD
def save_document(doc_id, filename, hash_value, metadata, uploaded_by, qr_path):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute('''
        INSERT INTO documents 
        (doc_id, filename, hash, student_name, roll_number, course, issue_date, institute, uploaded_by, qr_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        doc_id,
        filename,
        hash_value,
        metadata.get('student_name'),
        metadata.get('roll_number'),
        metadata.get('course'),
        metadata.get('issue_date'),
        metadata.get('institute'),
        uploaded_by,
        qr_path
    ))

    conn.commit()
    conn.close()


# ✅ GET DOCUMENT BY QR ID
def get_document_by_doc_id(doc_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM documents WHERE doc_id=?", (doc_id,))
    doc = c.fetchone()
    conn.close()
    return doc


# ✅ UPDATE FRAUD DATA
def update_document_status(doc_id, scan_count, failed_attempts, status):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute('''
        UPDATE documents
        SET scan_count=?, failed_attempts=?, status=?
        WHERE doc_id=?
    ''', (scan_count, failed_attempts, status, doc_id))

    conn.commit()
    conn.close()


def get_all_documents():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM documents ORDER BY uploaded_at DESC")
    result = c.fetchall()
    conn.close()
    return result


# ---------------- LOGS ----------------
def save_log(filename, result, verified_by):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO verification_logs (filename, result, verified_by) VALUES (?, ?, ?)",
              (filename, result, verified_by))
    conn.commit()
    conn.close()

def get_all_logs():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM verification_logs ORDER BY verified_at DESC LIMIT 50")
    result = c.fetchall()
    conn.close()
    return result


# ---------------- STATS ----------------
def get_stats():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM documents")
    total_docs = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM verification_logs")
    total_verifications = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM verification_logs WHERE result='TAMPERED'")
    total_tampered = c.fetchone()[0]

    conn.close()

    return {
        "total_docs": total_docs,
        "total_verifications": total_verifications,
        "total_tampered": total_tampered
    }