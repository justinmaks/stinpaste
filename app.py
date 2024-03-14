from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
#from flask import escape
from markupsafe import escape
from datetime import datetime
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pastes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


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
    # test

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Sanitize the inputs
        paste_title = escape(request.form['title'])
        paste_content = escape(request.form['content'])
        
        new_paste = Paste(title=paste_title, content=paste_content)
        db.session.add(new_paste)
        db.session.commit()

        return redirect(url_for('view_paste', paste_uuid=new_paste.uuid))

    pastes = Paste.query.order_by(Paste.id.desc()).all()
    return render_template('index.html', pastes=pastes)

@app.route('/p/<paste_uuid>')
def view_paste(paste_uuid):
    paste = Paste.query.filter_by(uuid=paste_uuid).first_or_404()
    return render_template('paste.html', paste=paste)

@app.errorhandler(404)
def page_not_found(e):
    # e = error object
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    # e is the error object
    return render_template('500.html'), 500
