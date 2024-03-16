from flask import Flask, request, render_template, redirect, url_for, flash, session 
from flask_sqlalchemy import SQLAlchemy
from markupsafe import escape
import uuid
import os
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from base64 import urlsafe_b64encode, urlsafe_b64decode
from datetime import datetime, timedelta
from sqlalchemy import or_
from flask_apscheduler import APScheduler

app = Flask(__name__)
app.config['SECRET_KEY'] = 'SUPERSECRETKEY123@@#' #should be secure env var. keep the same to retain sessions. 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pastes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#app.config['SCHEDULER_API_ENABLED'] = True
db = SQLAlchemy(app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# log setup

if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10485760, backupCount=10)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('StinPaste application startup')

class Paste(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_encrypted = db.Column(db.Boolean, default=False, nullable=False)
    encryption_key = db.Column(db.String(128))  # Storing a hashed password
    expires_at = db.Column(db.DateTime, nullable=True) 
    visitor_ip = db.Column(db.String(45), nullable=True) # ipv6 can be up to 46 char

    def set_password(self, password):
        self.encryption_key = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.encryption_key, password)


    def __repr__(self):
        return f'<Paste {self.title}>'

with app.app_context():
    db.create_all()

scheduler = APScheduler()
scheduler.init_app(app)
app.config['SCHEDULER_API_ENABLED'] = True

@scheduler.task('interval', id='delete_expired_pastes', seconds=3600, misfire_grace_time=900)
def delete_expired_pastes():
    with app.app_context():
        now = datetime.utcnow()
        expired_pastes = Paste.query.filter(Paste.expires_at <= now).all()
        for paste in expired_pastes:
            db.session.delete(paste)
        db.session.commit()
        app.logger.info("Deleted expired pastes.")

def generate_key(password):
    # Use a constant salt; in a real app, make this to be static but unique per user or encryption
    salt = b'some_constant_salt'  # Make sure to use the same salt for encryption and decryption
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def encrypt_content(content, password):
    key = generate_key(password)
    fernet = Fernet(key)
    return fernet.encrypt(content.encode()).decode()

@app.route('/', methods=['GET', 'POST'])
def index():

    visitor_ip = request.headers.get('CF-Connecting-IP', request.remote_addr)

    if request.method == 'POST':
        paste_title = escape(request.form['title'])
        paste_content = escape(request.form['content'])
        encrypt = request.form.get('encrypt')
        password = request.form.get('password')
        expiration_hours = int(request.form.get('expiration', 0))
        expires_at = None
        visitor_ip = request.headers.get('CF-Connecting-IP', request.remote_addr)  # Capture visitor IP
        
        if expiration_hours > 0:
            expires_at = datetime.utcnow() + timedelta(hours=expiration_hours)
        
        if encrypt == 'on' and password:  # Ensure 'encrypt' checkbox is checked and password is provided
            paste_content = encrypt_content(paste_content, password)
            new_paste = Paste(title=paste_title, content=paste_content, is_encrypted=True, expires_at=expires_at, visitor_ip=visitor_ip)
            new_paste.set_password(password)
        else:
            new_paste = Paste(title=paste_title, content=paste_content, expires_at=expires_at, visitor_ip=visitor_ip)
        db.session.add(new_paste)
        db.session.commit()
        app.logger.info(f'New paste created with UUID: {new_paste.uuid}, IP: {visitor_ip}')
        return redirect(url_for('view_paste', paste_uuid=new_paste.uuid))

    
    # Use or_() to combine the conditions properly

    app.logger.info(f'Main page accessed, IP: {visitor_ip}')
    pastes = Paste.query.filter(or_(Paste.expires_at > datetime.utcnow(), Paste.expires_at.is_(None))
    ).order_by(Paste.timestamp.desc()).all()
    
    return render_template('index.html', pastes=pastes)



@app.route('/p/<paste_uuid>')
def view_paste(paste_uuid):
    try:
        paste = Paste.query.filter_by(uuid=paste_uuid).first_or_404()
        decrypted_content = session.pop('decrypted_content', None)  # Retrieve and remove decrypted content from session
        encrypted = paste.is_encrypted and decrypted_content is None
        visitor_ip = request.headers.get('CF-Connecting-IP', request.remote_addr)
        app.logger.info('Paste viewed with UUID: %s, IP: %s', paste_uuid, visitor_ip)
        return render_template('paste.html', paste=paste, content=decrypted_content if decrypted_content else paste.content, encrypted=encrypted)
    except Exception as e:
        visitor_ip = request.headers.get('CF-Connecting-IP', request.remote_addr)
        app.logger.error('Error viewing paste with UUID: %s, IP: %s', paste_uuid, visitor_ip, exc_info=True)
        raise e



@app.errorhandler(404)
def page_not_found(e):
    visitor_ip = request.headers.get('CF-Connecting-IP', request.remote_addr)
    app.logger.warning('404 error encountered, IP: %s, URL: %s', visitor_ip, request.url)
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    visitor_ip = request.headers.get('CF-Connecting-IP', request.remote_addr)
    app.logger.error('500 internal server error encountered, IP: %s, URL: %s', visitor_ip, request.url, exc_info=True)
    return render_template('500.html'), 500


def decrypt_content(content, password):
    try:
        key = generate_key(password)
        fernet = Fernet(key)
        decrypted = fernet.decrypt(content.encode()).decode()
        return decrypted
    except Exception as e:
        app.logger.error(f'Decryption failed: {e.__class__.__name__} - {str(e)}')
        return None



@app.route('/decrypt/<paste_uuid>', methods=['POST'])
def decrypt_paste(paste_uuid):
    password = request.form['password']
    try:
        paste = Paste.query.filter_by(uuid=paste_uuid).first_or_404()
        if paste.check_password(password):
            decrypted_content = decrypt_content(paste.content, password)
            if decrypted_content is not None:
                # Store decrypted content in session for retrieval after redirect
                session['decrypted_content'] = decrypted_content
                flash('Paste decrypted successfully.', 'success')
                return redirect(url_for('view_paste', paste_uuid=paste_uuid))
            else:
                flash('Decryption failed. Please try again.', 'error')
        else:
            flash('Incorrect password. Please try again.', 'error')
    except Exception as e:
        app.logger.error('Error decrypting paste with UUID: %s', paste_uuid, exc_info=True)
        flash('An error occurred while decrypting the paste.', 'error')
    return redirect(url_for('view_paste', paste_uuid=paste_uuid))

# # DRY!!!
# @app.context_processor
# def inject_google_analytics_id():
#     return dict(google_analytics_id=os.getenv('GOOGLE_ANALYTICS_ID', ''))

if __name__ == "__main__":
    scheduler.start()  # Start the scheduler after defining jobs
    app.run(debug=True)