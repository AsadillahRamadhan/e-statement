from flask import Flask, render_template, request, redirect, send_file, session, url_for, flash, session, abort
import os
from config import Config
import uuid
from modules.process import PDFEstatementProcessor
import pandas as pd
from extensions import db
from sqlalchemy import or_, asc
from datetime import datetime
from io import StringIO

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
            return abort(403)
        
@app.route('/converter', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        session.pop('data', None)
        session.pop('data_month', None)
        session.pop('output_filename', None)
        files = request.files.getlist('pdf_file[]')
        niks = request.form.getlist('nik[]')
        mobile_phones = request.form.getlist('mobile_phone[]')
        names = request.form.getlist('name[]')
        sources = request.form.getlist('source[]') 
        month = request.form.get('month')
        emails = request.form.getlist('email[]')
        emails_pass = request.form.getlist('email_pass[]')
        users = request.form.getlist('user[]')
        users_pass = request.form.getlist('user_pass[]')

        if not files or not niks or not mobile_phones or not names or not sources or not month:
            return "All fields are required."

        if not (len(files) == len(niks) == len(mobile_phones) == len(names) == len(sources)):
            return "Mismatch between number of files and data fields."

        month = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
        combined_results = []

        for idx, file in enumerate(files):
            if file and file.filename.endswith('.pdf'):
                filename = f"{uuid.uuid4()}.pdf"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                try:
                    data = TransferUser.query.all()
                    bank_code = BankCode.query.filter(BankCode.bank_name.like(f"%{sources[idx]}%")).order_by(asc(BankCode.id)).first()
                    result, _ = processor.process_pdf_file(filepath, BankCode, data, niks[idx], mobile_phones[idx], sources[idx], bank_code.bank_code, emails[idx], emails_pass[idx], users[idx], users_pass[idx])
                    combined_results.append(result)
                except Exception as e:
                    return f"Error processing file {file.filename}: {str(e)}"
            else:
                return f"Invalid file format for {file.filename}. Only PDFs are supported."

        if combined_results:
            final_df = pd.concat(combined_results, ignore_index=True)
            table_html = final_df.to_html(classes='table table-striped', index=False)
            csv_data = final_df.to_csv(index=False)
            return render_template('converter/preview.html', title="Converter", data=csv_data, table=table_html, month=month, filename=f"export_{month}.xlsx", current_url=request.url)

        return "No valid files processed."

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


# @app.post('/preview')
# def preview():
#     if 'data' in session:
#         df = pd.read_json(session['data'], orient='split')
#         table_html = df.to_html(classes='table table-striped', index=False)
#         return render_template('converter/preview.html', title="Converter", table=table_html, month=session['data_month'], current_url=request.url, filename=session['output_filename'])
#     return redirect('/converter')


@app.post('/download/<filename>')
def download_file(filename):
    data = request.form.get('data')
    
    if data:
        try:
            csv_buffer = StringIO(data)
            
            df = pd.read_csv(csv_buffer, dtype={'% A Bank Code': str, '% B Bank Code': str})

            output_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
            
            df.to_excel(output_path, index=False)

            return send_file(output_path, as_attachment=True)

        except Exception as e:
            return f"Error processing CSV data: {str(e)}"

    return "No file available to download."


if __name__ == '__main__':
    app.run(debug=True)
