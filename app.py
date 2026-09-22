import os
import json
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from google import genai
from google.genai import types
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
CONFIG_FILE = 'config.json'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Default Config
def get_config():
    if not os.path.exists(CONFIG_FILE):
        return {
            "gemini_api_key": "",
            "submission_method": "native",
            "smtp_user": "",
            "smtp_pass": "",
            "webhook_url": ""
        }
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/api/admin/config', methods=['GET', 'POST'])
def admin_config():
    if request.method == 'POST':
        new_config = request.json
        save_config(new_config)
        return jsonify({"success": True})
    return jsonify(get_config())

@app.route('/analyze', methods=['POST'])
def analyze():
    config = get_config()
    api_key = config.get('gemini_api_key')
    
    if not api_key:
        return jsonify({'error': 'System not configured. Admin must set Gemini API key.'}), 500

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return jsonify({'error': f'Failed to initialize Gemini Client: {str(e)}'}), 500

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
            uploaded_file = client.files.upload(file=filepath)
            
            prompt = f"""
            Analyze this image of a civic issue (e.g., pothole, garbage, broken streetlight, water leak).
            The incident location is: {address} (Lat: {lat}, Lng: {lng}).
            
            Generate a formal complaint letter addressed to the local Municipal Corporation.
            Identify the issue, its severity, and provide a plausible municipal department email address.
            """
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[uploaded_file, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        properties={
                            "issue_title": genai.types.Schema(type=genai.types.Type.STRING, description="Short title of the issue"),
                            "category": genai.types.Schema(type=genai.types.Type.STRING, description="Category"),
                            "severity": genai.types.Schema(type=genai.types.Type.INTEGER, description="Severity score from 1 to 10"),
                            "description": genai.types.Schema(type=genai.types.Type.STRING, description="Brief description"),
                            "department_email": genai.types.Schema(type=genai.types.Type.STRING, description="Plausible email"),
                            "complaint_letter": genai.types.Schema(type=genai.types.Type.STRING, description="Formal complaint letter body")
                        },
                        required=["issue_title", "category", "severity", "description", "department_email", "complaint_letter"]
                    )
                )
            )
            
            result = json.loads(response.text)
            client.files.delete(name=uploaded_file.name)
            os.remove(filepath)
            
            # Inject submission method into response so frontend knows what to do
            result['sys_submission_method'] = config.get('submission_method', 'native')
            
            return jsonify(result)
            
        except Exception as e:
            if os.path.exists(filepath):
                 os.remove(filepath)
            return jsonify({'error': str(e)}), 500

@app.route('/api/submit', methods=['POST'])
def submit():
    config = get_config()
    data = request.json
    method = config.get('submission_method', 'native')
    
    if method == 'smtp':
        smtp_user = config.get('smtp_user')
        smtp_pass = config.get('smtp_pass')
        recipient = data.get('department_email')
        subject = f"URGENT: {data.get('issue_title')} [Severity: {data.get('severity')}/10]"
        body = data.get('complaint_letter') + f"\n\nLocation: https://www.google.com/maps/search/?api=1&query={data.get('lat')},{data.get('lng')}"
        
        if smtp_user and smtp_pass:
            try:
                msg = MIMEMultipart()
                msg['From'] = smtp_user
                msg['To'] = recipient
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))
                
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
                server.quit()
                return jsonify({'success': True, 'message': 'Email sent successfully via Municipal SMTP!'})
            except Exception as e:
                return jsonify({'error': f'SMTP Error: {str(e)}'}), 500
        else:
            return jsonify({'success': True, 'message': '[MOCK SMTP] Simulated automated email sent! (Admin must provide SMTP credentials)'})
            
    elif method == 'api':
        api_url = config.get('webhook_url')
        payload = {
            "complaint_category": data.get('category'),
            "geolocation": {"lat": data.get('lat'), "lng": data.get('lng')},
            "severity": data.get('severity'),
            "description": data.get('description'),
            "title": data.get('issue_title'),
            "letter_body": data.get('complaint_letter'),
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
            return jsonify({'success': True, 'message': '[MOCK API] Simulated JSON Payload sent! (Admin must provide Webhook URL)'})
            
    return jsonify({'error': 'Invalid server submission method'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
