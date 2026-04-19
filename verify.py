from hasher import generate_hash
from database import (
    get_document_by_doc_id,
    update_document_status
)

# ---------------- VERIFY USING FILE ----------------
def verify_document(file_path, original_filename):
    new_hash = generate_hash(file_path)

    # ⚠️ NOTE: You may need to adjust this if filename is not unique
    from database import get_all_documents
    docs = get_all_documents()

    doc = None
    for d in docs:
        if d["filename"] == original_filename:
            doc = d
            break

    if doc is None:
        return "NOT_FOUND", "Document not registered in the system.", None

    stored_hash = doc["hash"]

    # ---------------- HASH CHECK ----------------
    if new_hash == stored_hash:
        result = "VERIFIED"
        message = "Document is authentic and unmodified!"
    else:
        result = "TAMPERED"
        message = "Document has been tampered or modified!"

        # 🚨 Increase failed attempts
        failed_attempts = doc["failed_attempts"] + 1
        scan_count = doc["scan_count"]
        status = doc["status"]

        if failed_attempts > 5:
            status = "BLOCKED"

        update_document_status(doc["doc_id"], scan_count, failed_attempts, status)

    return result, message, doc


# ---------------- VERIFY USING QR ----------------
def verify_qr(doc_id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM documents WHERE id=?", (doc_id,))
    doc = c.fetchone()

    if not doc:
        return {
            "status": "INVALID",
            "message": "❌ Invalid QR Code"
        }

    scan_count = doc[10] + 1
    failed_attempts = doc[11]
    status = doc[12]

    if scan_count > 10:
        status = "SUSPICIOUS"

    if failed_attempts > 5:
        status = "BLOCKED"

    # update
    c.execute("UPDATE documents SET scan_count=?, failed_attempts=?, status=? WHERE id=?",
              (scan_count, failed_attempts, status, doc_id))

    conn.commit()
    conn.close()

    return {
        "status": status,
        "message": "✅ Document Verified",
        "scan_count": scan_count
    }