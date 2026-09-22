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
            "webhook_url": "",
            "sendgrid_api_key": "",
            "sendgrid_sender": "",
            "google_client_id": "",
            "google_client_secret": ""
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

import base64

@app.route('/api/oauth/google/url')
def google_oauth_url():
    config = get_config()
    client_id = config.get('google_client_id')
    if not client_id:
        # Mock mode if no client ID is configured
        return jsonify({"url": "/api/oauth/google/mock"})
    
    redirect_uri = request.host_url.rstrip('/') + "/api/oauth/google/callback"
    scope = "https://www.googleapis.com/auth/gmail.send"
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={scope}&access_type=offline"
    return jsonify({"url": auth_url})

@app.route('/api/oauth/google/mock')
def google_oauth_mock():
    # A mock endpoint that simulates a successful Google OAuth login for demo purposes
    return """
    <html><body>
    <h2>Mock Google OAuth Login</h2>
    <p>Simulating successful login...</p>
    <script>
        // Send a fake token back to the parent window
        window.opener.postMessage({ type: 'oauth_success', token: 'mock_google_access_token_12345' }, '*');
        window.close();
    </script>
    </body></html>
    """

@app.route('/api/oauth/google/callback')
def google_oauth_callback():
    code = request.args.get('code')
    config = get_config()
    client_id = config.get('google_client_id')
    client_secret = config.get('google_client_secret')
    redirect_uri = request.host_url.rstrip('/') + "/api/oauth/google/callback"

    if code and client_id and client_secret:
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        resp = requests.post(token_url, data=payload)
        if resp.status_code == 200:
            access_token = resp.json().get('access_token')
            return f"""
            <script>
                window.opener.postMessage({{ type: 'oauth_success', token: '{access_token}' }}, '*');
                window.close();
            </script>
            """
    
    return "OAuth Failed. You can close this window."

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
            
    elif method == 'sendgrid':
        sg_api_key = config.get('sendgrid_api_key')
        sg_sender = config.get('sendgrid_sender')
        citizen_email = data.get('citizen_email', 'citizen@example.com')
        recipient = data.get('department_email')
        subject = f"System Mailer: {data.get('issue_title')} [Severity: {data.get('severity')}/10]"
        body = data.get('complaint_letter') + f"\n\nLocation: https://www.google.com/maps/search/?api=1&query={data.get('lat')},{data.get('lng')}"
        
        if sg_api_key and sg_sender:
            headers = {
                "Authorization": f"Bearer {sg_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "personalizations": [{"to": [{"email": recipient}]}],
                "from": {"email": sg_sender, "name": "CivicConnect System"},
                "reply_to": {"email": citizen_email},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}]
            }
            try:
                resp = requests.post("https://api.sendgrid.com/v3/mail/send", json=payload, headers=headers)
                if resp.status_code in [200, 202]:
                    return jsonify({'success': True, 'message': 'Email sent successfully via SendGrid Transactional Mailer!'})
                else:
                    return jsonify({'error': f'SendGrid Error: {resp.text}'}), 500
            except Exception as e:
                return jsonify({'error': f'SendGrid Request Error: {str(e)}'}), 500
        else:
            return jsonify({'success': True, 'message': f'[MOCK SENDGRID] Simulated Transactional Email sent! Reply-To set as {citizen_email}'})
            
    elif method == 'oauth':
        access_token = data.get('oauth_token')
        recipient = data.get('department_email')
        subject = f"Citizen Report: {data.get('issue_title')} [Severity: {data.get('severity')}/10]"
        body = data.get('complaint_letter') + f"\n\nLocation: https://www.google.com/maps/search/?api=1&query={data.get('lat')},{data.get('lng')}"
        
        if not access_token:
            return jsonify({'error': 'Missing OAuth Access Token.'}), 400
            
        if access_token == 'mock_google_access_token_12345':
            return jsonify({'success': True, 'message': '[MOCK GMAIL API] Simulated email sent directly from Citizen Gmail account via OAuth!'})
            
        # Real Gmail API Send
        try:
            msg = MIMEMultipart()
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            resp = requests.post("https://gmail.googleapis.com/upload/gmail/v1/users/me/messages/send", json={"raw": raw_msg}, headers=headers)
            
            if resp.status_code == 200:
                return jsonify({'success': True, 'message': 'Email sent successfully from Citizen Gmail Account (OAuth)!'})
            else:
                return jsonify({'error': f'Gmail API Error: {resp.text}'}), 500
        except Exception as e:
            return jsonify({'error': f'OAuth Request Error: {str(e)}'}), 500

    return jsonify({'error': 'Invalid server submission method'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
