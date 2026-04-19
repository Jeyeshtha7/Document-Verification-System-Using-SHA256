from flask_mail import Mail, Message

mail = Mail()

def init_mail(app):
    app.config['MAIL_SERVER']   = 'smtp.gmail.com'
    app.config['MAIL_PORT']     = 587
    app.config['MAIL_USE_TLS']  = True
    app.config['MAIL_USERNAME'] = 'jeyeshtha.pendharkar23@vit.edu'      # ← your Gmail
    app.config['MAIL_PASSWORD'] = 'nwom bbgx pqpf fion'       # ← your app password
    app.config['MAIL_DEFAULT_SENDER'] = 'jeyeshtha.pendharkar23@vit.edu'
    mail.init_app(app)

def send_tamper_alert(admin_email, filename, verified_by):
    subject = f" ALERT: Tampered Document Detected — {filename}"
    body = f"""
Hello Admin,

A tampered document was detected in your DocVerify system.

Details:
──────────────────────────
Document Name  : {filename}
Detected By    : {verified_by}
Status         : TAMPERED 
──────────────────────────

Please log in to your dashboard immediately to review this activity.

http://127.0.0.1:5000/dashboard

— DocVerify Security System
    """
    try:
        msg = Message(subject=subject, recipients=[admin_email], body=body)
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False
