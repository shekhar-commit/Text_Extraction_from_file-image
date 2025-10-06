from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
from ocr_utils import extract_text_from_image  # For images (supports Hindi)
import csv  # For CSV handling

# For PDF handling (install via: pip install pypdf pdf2image)
from pypdf import PdfReader
from pdf2image import convert_from_path  # For converting PDF pages to images

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'  # Folder for temporary uploads
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max file size (increased for PDFs)

# Create upload folder if not exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'txt', 'pdf', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            extracted_text = ""
            previews = None  # List of preview URLs (single string or array for PDF pages)
            
            if filename.lower().endswith(('.png', '.jpg', 'jpeg', '.bmp')):
                # Handle image with OCR (supports English + Hindi)
                extracted_text = extract_text_from_image(filepath)
                if not extracted_text:
                    extracted_text = "कोई पाठ नहीं मिला। (No text found in the image.)"
                previews = f"/uploads/{filename}"  # Single preview
                
            elif filename.lower().endswith('.txt'):
                # Handle text file (supports Hindi via UTF-8)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        extracted_text = f.read().strip()
                except UnicodeDecodeError:
                    with open(filepath, 'r', encoding='latin-1') as f:
                        extracted_text = f.read().strip()
                if not extracted_text:
                    extracted_text = "फ़ाइल में कोई पाठ नहीं। (No text in the file.)"
                previews = None  # No preview
                
            elif filename.lower().endswith('.pdf'):
                # Handle PDF - extract text + convert pages to images for preview (shows images/graphs)
                try:
                    reader = PdfReader(filepath)
                    extracted_text = ""
                    for page_num, page in enumerate(reader.pages, 1):
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += f"--- पृष्ठ {page_num} --- (--- Page {page_num} ---)\n{page_text}\n\n"
                    
                    # Generate page previews (images/graphs)
                    previews = []
                    max_pages = 10  # Limit for performance
                    pages = min(len(reader.pages), max_pages)
                    pdf_images = convert_from_path(filepath, first_page=1, last_page=pages, dpi=150)  # Convert to images
                    for i, img in enumerate(pdf_images):
                        preview_filename = f"pdf_preview_{filename}_page_{i+1}.png"
                        preview_path = os.path.join(app.config['UPLOAD_FOLDER'], preview_filename)
                        img.save(preview_path, 'PNG')
                        previews.append(f"/uploads/{preview_filename}")
                    
                    if not extracted_text.strip():
                        extracted_text = "पीडीएफ में कोई पाठ नहीं मिला। (No text found in the PDF.)"
                    if not previews:
                        previews = None
                except Exception as pdf_error:
                    print(f"PDF Error: {pdf_error}")  # Optional logging
                    extracted_text = f"पीडीएफ निकालने में त्रुटि: {str(pdf_error)} (Error extracting PDF: {str(pdf_error)})"
                    previews = None
                # No original preview for PDF (use generated ones)
            
            elif filename.lower().endswith('.csv'):
                # Handle CSV - format as table (supports Hindi in cells via UTF-8)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        rows = list(reader)
                        if rows:
                            # Header
                            extracted_text += '| ' + ' | '.join(rows[0]) + ' |\n'
                            # Separator line
                            extracted_text += '| ' + ' | '.join(['---'] * len(rows[0])) + ' |\n'
                            # Data rows
                            for row in rows[1:]:
                                extracted_text += '| ' + ' | '.join(row) + ' |\n'
                        else:
                            extracted_text = "सीएसवी में कोई डेटा नहीं। (No data in the CSV.)"
                except UnicodeDecodeError:
                    # Fallback for non-UTF-8 CSV
                    with open(filepath, 'r', encoding='latin-1') as f:
                        reader = csv.reader(f)
                        rows = list(reader)
                        if rows:
                            extracted_text += '| ' + ' | '.join(rows[0]) + ' |\n'
                            extracted_text += '| ' + ' | '.join(['---'] * len(rows[0])) + ' |\n'
                            for row in rows[1:]:
                                extracted_text += '| ' + ' | '.join(row) + ' |\n'
                        else:
                            extracted_text = "सीएसवी पढ़ने में त्रुटि। (Error reading CSV.)"
                except Exception as csv_error:
                    # Fallback to raw text if formatting fails
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            extracted_text = f.read().strip()
                    except UnicodeDecodeError:
                        with open(filepath, 'r', encoding='latin-1') as f:
                            extracted_text = f.read().strip()
                    if not extracted_text:
                        extracted_text = f"सीएसवी पढ़ने में त्रुटि, कच्चा सामग्री: {extracted_text} (Error reading CSV, raw content: {extracted_text})"
                previews = None  # No preview for CSV (table is in text)
            
            # Clean up: Remove original file and any generated previews
            os.remove(filepath)
            if isinstance(previews, list):
                for preview_url in previews:
                    preview_file = preview_url.replace("/uploads/", "")
                    preview_path = os.path.join(app.config['UPLOAD_FOLDER'], preview_file)
                    if os.path.exists(preview_path):
                        os.remove(preview_path)
            
            return jsonify({
                'success': True,
                'extracted_text': extracted_text,
                'previews': previews  # Single string or list of URLs
            })
        
        except Exception as e:
            # Clean up on error
            if os.path.exists(filepath):
                os.remove(filepath)
            print(f"General Error: {e}")  # Optional logging
            return jsonify({'error': f'कुछ गलत हो गया: {str(e)} (Something went wrong: {str(e)})'}), 500
    
    return jsonify({'error': 'अनसपोर्टेड फ़ाइल प्रकार। केवल PNG, JPG, JPEG, BMP, TXT, PDF, CSV की अनुमति है। (Unsupported file type. Only PNG, JPG, JPEG, BMP, TXT, PDF, CSV allowed.)'}), 400

# Serve uploaded/generated files for preview
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
