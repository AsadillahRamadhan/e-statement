from flask import Flask, render_template, request, redirect, send_file, session, url_for
import os
import uuid
from modules.process import PDFEstatementProcessor
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # diperlukan untuk session
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(BASE_DIR, 'output')

processor = PDFEstatementProcessor()

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
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

    return render_template('index.html')


@app.route('/preview')
def preview():
    if 'data' in session:
        df = pd.read_json(session['data'], orient='split')
        table_html = df.to_html(classes='table table-striped', index=False)
        return render_template('preview.html', table=table_html, filename=session['output_filename'])
    return redirect('/')


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
