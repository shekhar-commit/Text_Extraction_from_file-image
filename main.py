from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
from ocr_utils import extract_text_from_image  # For images

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'  # Folder for temporary uploads
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if not exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'txt'}

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
            image_preview = None  # For image preview URL
            
            if filename.lower().endswith(('.png', '.jpg', 'jpeg', '.bmp')):
                # Handle image with OCR
                extracted_text = extract_text_from_image(filepath)
                if not extracted_text:
                    extracted_text = "No text found in the image."
                image_preview = f"/uploads/{filename}"  # Serve for preview
                
            elif filename.lower().endswith('.txt'):
                # Handle text file
                with open(filepath, 'r', encoding='utf-8') as f:
                    extracted_text = f.read().strip()
                if not extracted_text:
                    extracted_text = "No text in the file."
                image_preview = None  # No preview for TXT
            
            # Clean up uploaded file after processing
            os.remove(filepath)
            
            return jsonify({
                'success': True,
                'extracted_text': extracted_text,
                'image_preview': image_preview
            })
        
        except Exception as e:
            # Clean up on error
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': f'Something went wrong: {str(e)}'}), 500
    
    return jsonify({'error': 'Unsupported file type. Only PNG, JPG, JPEG, BMP, TXT allowed.'}), 400

# Serve uploaded images for preview
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
