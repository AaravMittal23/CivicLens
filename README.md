# CivicLens

### Live Demo

Click here to use the prototype:
[https://AaravMittal23.github.io/CivicLens/demo/](https://AaravMittal23.github.io/CivicLens/demo/)

---

## Features (Working Demo for 3-minute pitch)
1. **AI Image Analysis**: Upload a photo, and the AI automatically identifies the issue, its category, and assigns a severity rating (out of 10).
2. **Auto-Generated Letters**: The app generates a formal complaint letter addressed to the relevant municipal department.
3. **Live Geolocation**: Automatically captures GPS coordinates and displays the issue on an interactive Leaflet map.
4. **Native Email Integration**: Click "Send Complaint" to open the device's default mail app with the email, subject, and generated letter pre-filled (No SMTP setup required—perfect for quick demos).

## How to Run the Flask App locally (For Developers)

1. **Prerequisites**: Python 3 and a Gemini API Key.
   Get an API key from Google AI Studio: https://aistudio.google.com/app/apikey

2. **Setup Environment Variables**:
   Copy `.env.example` to a new file named `.env` and paste your Gemini API key inside.
   ```bash
   cp .env.example .env
   # Edit .env and add your key
   ```

3. **Install Dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Start the App**:
   ```bash
   python app.py
   ```

5. **Demo**: Open your browser to `http://127.0.0.1:5000`.

## Demo Script Idea
1. **Show the UI**: Open the app. Explain the goal (reduce friction for citizens to report issues).
2. **Take action**: Click the upload box, select a pre-downloaded image of a pothole (or take a live photo if on mobile).
3. **Wait for AI**: Let the AI analyze (shows loading). The app will populate the title, severity badge, description, map marker, and the generated letter.
4. **Final step**: Click "Send Complaint" which instantly opens the mail app. Boom. Done!
