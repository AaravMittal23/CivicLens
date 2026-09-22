import os
import json
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Gemini client lazily or handle missing key
client = None
try:
    client = genai.Client()
except Exception as e:
    print("Warning: Gemini client could not be initialized. Please set GEMINI_API_KEY in .env")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400
    
    lat = request.form.get('lat', 'Unknown')
    lng = request.form.get('lng', 'Unknown')
    address = request.form.get('address', 'Unknown location')
    
    if file:
        if not client:
            return jsonify({'error': 'Gemini API Key is missing. Please add it to the .env file.'}), 500

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Upload the file to Gemini
            uploaded_file = client.files.upload(file=filepath)
            
            prompt = f"""
            Analyze this image of a civic issue (e.g., pothole, garbage, broken streetlight, water leak).
            The incident location is: {address} (Lat: {lat}, Lng: {lng}).
            
            Generate a formal complaint letter addressed to the local Municipal Corporation.
            Identify the issue, its severity, and provide a plausible municipal department email address.
            """
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    uploaded_file,
                    prompt
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        properties={
                            "issue_title": genai.types.Schema(type=genai.types.Type.STRING, description="Short title of the issue"),
                            "category": genai.types.Schema(type=genai.types.Type.STRING, description="Category (e.g., Roads, Sanitation, Electricity, Water)"),
                            "severity": genai.types.Schema(type=genai.types.Type.INTEGER, description="Severity score from 1 to 10"),
                            "description": genai.types.Schema(type=genai.types.Type.STRING, description="Brief description of the problem"),
                            "department_email": genai.types.Schema(type=genai.types.Type.STRING, description="Plausible email for the concerned department (e.g., roads@municipality.gov)"),
                            "complaint_letter": genai.types.Schema(type=genai.types.Type.STRING, description="Formal complaint letter body. Include date, subject, and signature placeholders.")
                        },
                        required=["issue_title", "category", "severity", "description", "department_email", "complaint_letter"]
                    )
                )
            )
            
            result = json.loads(response.text)
            
            # Clean up the file from Gemini
            client.files.delete(name=uploaded_file.name)
            # Remove local file
            os.remove(filepath)
            
            return jsonify(result)
            
        except Exception as e:
            print(f"Error: {e}")
            return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
