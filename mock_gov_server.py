from flask import Flask, request, jsonify, render_template_string
from datetime import datetime

app = Flask(__name__)

# In-memory "Internal Database" for the Mock Government System
tickets_db = []

# HTML Template for the Municipal Dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Smart City Operations Center</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <meta http-equiv="refresh" content="3"> <!-- Auto-refresh every 3 seconds -->
</head>
<body class="bg-gray-100 p-8">
    <div class="max-w-6xl mx-auto">
        <div class="bg-indigo-900 text-white p-6 rounded-t-xl flex justify-between items-center">
            <h1 class="text-2xl font-bold">🏛️ Municipal Corp - Live Incident Dashboard</h1>
            <span class="bg-green-500 px-3 py-1 rounded-full text-xs font-bold animate-pulse">SYSTEM ONLINE</span>
        </div>
        <div class="bg-white p-6 rounded-b-xl shadow-lg">
            <h2 class="text-lg font-semibold mb-4 text-gray-700">Recent Automated API Tickets</h2>
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="bg-gray-50 border-b-2 border-gray-200 text-gray-600 text-sm">
                            <th class="p-3">Ticket ID</th>
                            <th class="p-3">Timestamp</th>
                            <th class="p-3">Category</th>
                            <th class="p-3">Severity</th>
                            <th class="p-3">Location (Lat, Lng)</th>
                            <th class="p-3">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% if not tickets %}
                        <tr>
                            <td colspan="6" class="p-6 text-center text-gray-400 italic">No tickets received yet. Waiting for API payloads...</td>
                        </tr>
                        {% endif %}
                        {% for t in tickets|reverse %}
                        <tr class="border-b border-gray-100 hover:bg-gray-50 transition">
                            <td class="p-3 font-mono text-sm text-indigo-600">{{ t.id }}</td>
                            <td class="p-3 text-sm text-gray-500">{{ t.time }}</td>
                            <td class="p-3 font-semibold">{{ t.category }}</td>
                            <td class="p-3">
                                <span class="px-2 py-1 rounded text-xs font-bold {% if t.severity >= 8 %}bg-red-100 text-red-700{% elif t.severity >= 5 %}bg-orange-100 text-orange-700{% else %}bg-yellow-100 text-yellow-700{% endif %}">
                                    {{ t.severity }}/10
                                </span>
                            </td>
                            <td class="p-3 text-sm font-mono text-gray-500">{{ t.lat|round(4) }}, {{ t.lng|round(4) }}</td>
                            <td class="p-3"><span class="bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs font-bold">OPEN</span></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML, tickets=tickets_db)

@app.route('/webhook', methods=['POST'])
def receive_ticket():
    data = request.json
    
    # Store the JSON payload in our mock internal database
    ticket = {
        "id": f"TKT-{len(tickets_db) + 1001}",
        "time": datetime.now().strftime("%H:%M:%S"),
        "category": data.get("complaint_category", "Unknown"),
        "severity": data.get("severity", 0),
        "lat": data.get("geolocation", {}).get("lat", 0),
        "lng": data.get("geolocation", {}).get("lng", 0),
        "description": data.get("description", ""),
        "source": data.get("source", "Unknown")
    }
    
    tickets_db.append(ticket)
    print(f"\n[GOV SERVER] 🚨 New Ticket Received from API: {ticket['id']} - {ticket['category']}\n")
    
    return jsonify({"status": "Ticket successfully ingested into Govt DB", "ticket_id": ticket['id']}), 201

if __name__ == '__main__':
    # Run on port 5001 so it doesn't conflict with the main app on 5000
    app.run(debug=True, port=5001)
