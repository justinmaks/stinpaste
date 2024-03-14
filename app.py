from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from markupsafe import escape
from datetime import datetime
import uuid
import os
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
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


    def __repr__(self):
        return f'<Paste {self.title}>'

with app.app_context():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            paste_title = escape(request.form['title'])
            paste_content = escape(request.form['content'])
            new_paste = Paste(title=paste_title, content=paste_content)
            db.session.add(new_paste)
            db.session.commit()
            app.logger.info(f'New paste created with UUID: {new_paste.uuid}')
            return redirect(url_for('view_paste', paste_uuid=new_paste.uuid))
        except Exception as e:
            app.logger.error('Error creating a new paste', exc_info=True)
            raise e  # Re-raise

    try:
        pastes = Paste.query.order_by(Paste.id.desc()).all()
    except Exception as e:
        app.logger.error('Error retrieving pastes from the database', exc_info=True)
        raise e  # Re-raise excp
    return render_template('index.html', pastes=pastes)

@app.route('/p/<paste_uuid>')
def view_paste(paste_uuid):
    try:
        paste = Paste.query.filter_by(uuid=paste_uuid).first_or_404()
        app.logger.info(f'Paste viewed with UUID: {paste_uuid}')
        return render_template('paste.html', paste=paste)
    except Exception as e:
        app.logger.error(f'Error viewing paste with UUID: {paste_uuid}', exc_info=True)
        raise e  # Re-raise excp

@app.errorhandler(404)
def page_not_found(e):
    app.logger.warning('404 error encountered', exc_info=False)
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    app.logger.error('500 internal server error encountered', exc_info=True)
    return render_template('500.html'), 500