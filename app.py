from flask import Flask, render_template, request, redirect, send_file, session, url_for, flash, session, abort
import os
from config import Config
import uuid
from modules.process import PDFEstatementProcessor
import pandas as pd
from extensions import db
from sqlalchemy import or_
from flask_login import current_user

app = Flask(__name__)

app.config.from_object(Config)
db.init_app(app)

from models import *

app.secret_key = 'your-secret-key'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(BASE_DIR, 'output')

processor = PDFEstatementProcessor()

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

@app.before_request
def global_middleware():
    if request.endpoint in ('login', 'static'):
        return
    
    if request.path == '/login':
        if session.get('user_id'):
            return redirect('/dashboard')

    if request.path == '/':
        if session.get('user_id'):
            return redirect('/dashboard')
        else:
            return redirect('/login')

    protected_routes = {
        '/user': ['super_admin']
    }

    allowed_roles = protected_routes.get(request.path)
    if allowed_roles:
        user_role = session.get('role')
        if not user_role or user_role not in allowed_roles:
            return abort(403)  # Jika role tidak sesuai, return forbidden
        
@app.route('/converter', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['pdf_file']
        if file and file.filename.endswith('.pdf'):
            filename = f"{uuid.uuid4()}.pdf"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                result, _ = processor.process_pdf_file(filepath)
                session['data'] = result.to_json(orient='split')
                session['output_filename'] = filename.replace('.pdf', '.xlsx')
                return redirect(url_for('preview'))
            except Exception as e:
                return f"Error processing file: {str(e)}"
        else:
            return "Invalid file format. Only PDFs are supported."

    return render_template('converter/index.html', current_url=request.url, title="Converter")

@app.get('/login')
def login_view():
    return render_template('auth/login.html')

@app.post('/login')
def login_process():
    email, password = request.form['email'], request.form['password']
    
    user = User.query.filter_by(email=email).first()
    if(user and user.verify_password(password)):
        session['user_id'] = user.id
        session['username'] = user.username
        session['email'] = user.email
        session['role'] = user.role
        return redirect('/dashboard')
    else:
        flash("The credentials doesn't match our records!", "message")
        return redirect(request.referrer or '/')

@app.post('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('email', None)
    session.pop('role', None)
    flash("You’ve been logged out.", "message")
    return redirect('/')
    
@app.get('/dashboard')
def render_dashboard():
    return  render_template('dashboard/index.html', current_url=request.url, title="Dashboard")

@app.get('/user')
def render_user():
    users = User.query.filter(User.id != session.get('user_id')).all()
    return render_template('user/index.html', users=users, current_url=request.url, title="User Management")

@app.post('/user/<int:id>')
def update_user(id):
    method = request.form.get('_method', '').upper()
    if method == "PUT":
        username = request.form['username']
        email = request.form['email']
        password = request.form.get('password')
        role = request.form['role']

        user = User.query.get_or_404(id)
        user.username = username
        user.email = email
        user.role = role
        if password:
            user.password = password
        db.session.commit()

        flash("User updated!", "message")
        flash("true", "success")
        return redirect(request.referrer or '/dashboard')
    elif method == "DELETE":
        user = User.query.get_or_404(id)
        db.session.delete(user)
        db.session.commit()
        flash("User deleted!", "message")
        flash("true", "success")
        return redirect(request.referrer or '/dashboard')
    flash("Method not allowed!", "message")
    flash("false", "success")
    return redirect(request.referrer or '/dashboard')

@app.post('/user')
def create_user():
    username, email, password = request.form['username'], request.form['email'], request.form['password']

    if(not username or not email or not password):
       flash("Fill all of those credentials!", "message")
       flash("false", "success")
       return redirect(request.referrer or '/')
    
    prev_user = User.query.filter(or_(User.email == email, User.username == username)).first()
    if(prev_user):
        flash("The username or email already taken!", "message")
        flash("false", "success")
        return redirect(request.referrer or '/')
    
    user = User(
        email=email,
        username=username
    )
    user.password = password
    db.session.add(user)
    db.session.commit()

    flash("User created!", "message")
    flash("true", "success")
    return redirect(request.referrer or '/')


@app.route('/preview')
def preview():
    if 'data' in session:
        df = pd.read_json(session['data'], orient='split')
        table_html = df.to_html(classes='table table-striped', index=False)
        return render_template('converter/preview.html', title="Converter", table=table_html, current_url=request.url, filename=session['output_filename'])
    return redirect('/converter')


@app.route('/download/<filename>')
def download_file(filename):
    if 'data' in session:
        df = pd.read_json(session['data'], orient='split')
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        df.to_excel(output_path, index=False)
        return send_file(output_path, as_attachment=True)
    return "No file available to download."


if __name__ == '__main__':
    app.run(debug=True)
