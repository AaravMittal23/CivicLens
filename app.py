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
    api_key = request.form.get('api_key')
    if not api_key:
        return jsonify({'error': 'Please provide your Gemini API key in the frontend.'}), 400

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return jsonify({'error': f'Failed to initialize Gemini Client: {str(e)}'}), 400

    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400
    
    lat = request.form.get('lat', 'Unknown')
    lng = request.form.get('lng', 'Unknown')
    address = request.form.get('address', 'Unknown location')
    
    if file:
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
            if os.path.exists(filepath):
                 os.remove(filepath)
            return jsonify({'error': str(e)}), 500

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

@app.route('/api/send_email', methods=['POST'])
def send_email():
    data = request.json
    recipient = data.get('recipient')
    subject = data.get('subject')
    body = data.get('body')
    
    # Mocking SMTP for Demo unless credentials are provided
    smtp_user = data.get('smtp_user')
    smtp_pass = data.get('smtp_pass')
    
    if smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # Defaulting to Gmail SMTP for demo purposes
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
            return jsonify({'success': True, 'message': 'Email sent successfully via SMTP!'})
        except Exception as e:
            return jsonify({'error': f'SMTP Error: {str(e)}'}), 500
    else:
        # Mock successful send
        print(f"[MOCK SMTP] Sending email to {recipient} with subject '{subject}'")
        return jsonify({'success': True, 'message': 'Simulated automated email sent! (Provide SMTP credentials in settings for real delivery)'})

@app.route('/api/submit_municipal', methods=['POST'])
def submit_municipal():
    data = request.json
    api_url = data.get('api_url')
    
    payload = {
        "complaint_category": data.get('category'),
        "geolocation": {
            "lat": data.get('lat'),
            "lng": data.get('lng')
        },
        "severity": data.get('severity'),
        "description": data.get('description'),
        "title": data.get('title'),
        "letter_body": data.get('letter'),
        "status": "OPEN",
        "source": "CivicSense_AI"
    }
    
    if api_url:
        try:
            response = requests.post(api_url, json=payload, timeout=5)
            return jsonify({'success': True, 'message': f'Payload submitted to Municipal API! Status: {response.status_code}'})
        except Exception as e:
            return jsonify({'error': f'API Connection Error: {str(e)}'}), 500
    else:
        # Mock successful API call
        print(f"[MOCK API GATEWAY] Submitted JSON payload: {json.dumps(payload, indent=2)}")
        return jsonify({'success': True, 'message': 'Simulated JSON Payload sent to Municipal API gateway! (Provide Webhook URL in settings for real delivery)'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
