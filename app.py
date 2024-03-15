from flask import Flask, request, render_template, redirect, url_for, flash, session 
from flask_sqlalchemy import SQLAlchemy
from markupsafe import escape
from datetime import datetime
import uuid
import os
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from base64 import urlsafe_b64encode, urlsafe_b64decode
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = 'SUPERSECRETKEY123@@#' #should be secure env var. keep the same to retain sessions. 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pastes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# log setup

if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
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

    def set_password(self, password):
        self.encryption_key = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.encryption_key, password)


    def __repr__(self):
        return f'<Paste {self.title}>'

with app.app_context():
    db.create_all()

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
    if request.method == 'POST':
        paste_title = escape(request.form['title'])
        paste_content = escape(request.form['content'])
        encrypt = request.form.get('encrypt')
        password = request.form.get('password')
        if encrypt == 'on' and password:  # Ensure 'encrypt' checkbox is checked and password is provided
            paste_content = encrypt_content(paste_content, password)
            new_paste = Paste(title=paste_title, content=paste_content, is_encrypted=True)
            new_paste.set_password(password)
        else:
            new_paste = Paste(title=paste_title, content=paste_content)
        db.session.add(new_paste)
        db.session.commit()
        app.logger.info(f'New paste created with UUID: {new_paste.uuid}')
        return redirect(url_for('view_paste', paste_uuid=new_paste.uuid))
    
    # Handle GET request here by fetching existing pastes and rendering index.html
    pastes = Paste.query.order_by(Paste.timestamp.desc()).all()
    return render_template('index.html', pastes=pastes)


@app.route('/p/<paste_uuid>')
def view_paste(paste_uuid):
    try:
        paste = Paste.query.filter_by(uuid=paste_uuid).first_or_404()
        decrypted_content = session.pop('decrypted_content', None)  # Retrieve and remove decrypted content from session
        encrypted = paste.is_encrypted and decrypted_content is None
        app.logger.info('Paste viewed with UUID: %s', paste_uuid)
        return render_template('paste.html', paste=paste, content=decrypted_content if decrypted_content else paste.content, encrypted=encrypted)
    except Exception as e:
        app.logger.error('Error viewing paste with UUID: %s', paste_uuid, exc_info=True)
        raise e



@app.errorhandler(404)
def page_not_found(e):
    app.logger.warning('404 error encountered', exc_info=False)
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    app.logger.error('500 internal server error encountered', exc_info=True)
    return render_template('500.html'), 500

def decrypt_content(content, password):
    try:
        key = generate_key(password)
        fernet = Fernet(key)
        return fernet.decrypt(content.encode()).decode()
    except Exception as e:
        app.logger.error(f'Decryption failed: {str(e)}')
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

