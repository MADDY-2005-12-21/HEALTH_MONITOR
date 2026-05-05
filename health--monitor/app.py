from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3, requests, math, json, os
from model import predict_risk, health_score, generate_tips
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"

# ── ANTHROPIC CONFIG ──
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ─────────────────────────────────────────────
#  DATABASE
# ─────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("health.db")
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT, password TEXT, role TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS doctors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, phone TEXT, location TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS records(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT, patient_number TEXT, patient_address TEXT,
        doctor_name TEXT, doctor_number TEXT, doctor_location TEXT,
        heart_rate REAL, spo2 REAL, temp REAL, result TEXT, score REAL)""")

    c.execute("""CREATE TABLE IF NOT EXISTS appointments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT, doctor_name TEXT, date TEXT, time TEXT)""")

    c.execute("SELECT * FROM doctors")
    if not c.fetchall():
        c.execute("INSERT INTO doctors(name,phone,location) VALUES('Dr. Ram','9876543210','Chennai')")
        c.execute("INSERT INTO doctors(name,phone,location) VALUES('Dr. Arun','9123456780','Bangalore')")

    conn.commit()
    conn.close()

init_db()

# ─────────────────────────────────────────────
#  GEO + DISTANCE
# ─────────────────────────────────────────────
def get_coordinates(place):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={place}&format=json"
        response = requests.get(url, headers={"User-Agent": "health-app"}, timeout=5)
        data = response.json()
        return float(data[0]['lat']), float(data[0]['lon'])
    except:
        return 20.59, 78.96

def calculate_distance(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)

def find_nearest_doctor(patient_address):
    conn = sqlite3.connect("health.db")
    c = conn.cursor()
    c.execute("SELECT * FROM doctors")
    doctors = c.fetchall()
    conn.close()

    p_lat, p_lon = get_coordinates(patient_address)
    nearest, min_dist = None, float("inf")

    for doc in doctors:
        d_lat, d_lon = get_coordinates(doc[3])
        dist = calculate_distance(p_lat, p_lon, d_lat, d_lon)
        if dist < min_dist:
            min_dist = dist
            nearest = doc

    return nearest

def check_emergency(result, patient_address):
    if result == "High Risk":
        doctor = find_nearest_doctor(patient_address)
        session['emergency'] = True
        session['emergency_doctor'] = doctor
        return f"🚨 EMERGENCY! Contact Dr. {doctor[1]} at {doctor[2]} immediately!"
    session['emergency'] = False
    return None

# ─────────────────────────────────────────────
#   AI CHATBOT — CLAUDE (Anthropic)
# ─────────────────────────────────────────────
def build_system_prompt():
    """Build a context-rich system prompt from current session vitals."""
    hr       = session.get('hr', 'unknown')
    spo2     = session.get('spo2', 'unknown')
    temp     = session.get('temp', 'unknown')
    result   = session.get('result', 'unknown')
    score    = session.get('score', 'unknown')
    emergency = session.get('emergency', False)

    emergency_doc = ""
    if emergency and session.get('emergency_doctor'):
        doc = session['emergency_doctor']
        emergency_doc = f"\nEMERGENCY CONTACT: Dr. {doc[1]} at {doc[2]} ({doc[3]})"

    return f"""You are HealthAI, a warm and knowledgeable AI health assistant embedded in a patient health monitoring app.

The patient's CURRENT vitals:
- Heart Rate: {hr} bpm  (normal: 60–100 bpm)
- SpO2: {spo2}%          (normal: ≥95%)
- Temperature: {temp}°C  (normal: ≤37.5°C)
- Risk Level: {result}
- Health Score: {score}/100
- Emergency active: {emergency}{emergency_doc}

Your guidelines:
1. Use the patient's ACTUAL vitals — give personalised, specific advice, never generic.
2. Detect symptoms in their message (fever, dizziness, headache, breathlessness, chest pain, fatigue) and ask one clarifying follow-up question.
3. If risk is 'High Risk', remind them to contact the doctor or press SOS immediately.
4. Be warm, concise, and clear. Keep each reply to 2–3 sentences maximum.
5. NEVER diagnose diseases. Always recommend consulting a doctor for serious concerns.
6. For emergencies, always direct them to call the SOS button or emergency contact.
7. Format responses in plain text — no markdown, no bullet points, no asterisks.
"""

def ai_chat_reply(message, history):
    """Call Anthropic Claude API for a chat reply."""
    if not ANTHROPIC_API_KEY:
        print("⚠️  No ANTHROPIC_API_KEY — using fallback")
        return fallback_reply(message)

    try:
        # Build messages list (Claude API format)
        messages = []
        for msg in history[-10:]:
            # Convert OpenAI-style roles to Anthropic (same names, so direct map)
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        messages.append({"role": "user", "content": message})

        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 300,
            "system": build_system_prompt(),
            "messages": messages
        }

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json=payload,
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()

    except Exception as e:
        print("Claude API ERROR:", e)
        return fallback_reply(message)


def fallback_reply(msg):
    """Rule-based fallback if API key is not set or call fails."""
    m      = msg.lower()
    hr     = session.get('hr')
    spo2   = session.get('spo2')
    temp   = session.get('temp')
    result = session.get('result')
    score  = session.get('score')

    symptoms = []
    if any(w in m for w in ['fever','hot','temperature']): symptoms.append('fever')
    if any(w in m for w in ['dizzy','dizziness','lightheaded']): symptoms.append('dizziness')
    if any(w in m for w in ['headache','head pain']): symptoms.append('headache')
    if any(w in m for w in ['breath','breathless','shortness']): symptoms.append('breathing difficulty')
    if any(w in m for w in ['chest','pain','tight']): symptoms.append('chest discomfort')
    if symptoms:
        return f"I noticed you mentioned {', '.join(symptoms)}. Since when have you been experiencing this? Do you also have fever or trouble breathing?"

    if any(w in m for w in ['hi','hello','hey']): return "Hello! I'm HealthAI. I can help you with your heart rate, oxygen, temperature, risk level, or symptoms. What would you like to know?"
    if 'heart' in m or 'hr' in m:    return f"Your heart rate is {hr} bpm. Normal range is 60–100 bpm." if hr else "I don't have your heart rate on record yet."
    if 'oxygen' in m or 'spo2' in m: return f"Your SpO2 is {spo2}%. Normal is ≥95%." if spo2 else "No SpO2 reading recorded yet."
    if 'temp' in m:                   return f"Your temperature is {temp}°C. Normal is ≤37.5°C." if temp else "No temperature recorded yet."
    if 'risk' in m or 'condition' in m: return f"Your current risk level is: {result}." if result else "No risk data available yet."
    if 'score' in m:                  return f"Your health score is {score}/100." if score else "No score available yet."
    if 'safe' in m:
        if result == 'Low Risk': return "You are safe! All your vitals look stable. Keep monitoring regularly."
        return f"Your condition is {result}. Please monitor your vitals closely and consult a doctor if symptoms worsen."
    if 'tip' in m or 'advice' in m:   return "Stay hydrated, get 7–9 hours of sleep, exercise regularly, and monitor your vitals daily."
    if 'emergency' in m or 'sos' in m: return "In an emergency, press the SOS button on your dashboard to call your doctor immediately."
    if 'doctor' in m:                 return "Your nearest doctor has been assigned. Use the SOS button for emergencies."
    if 'normal' in m:                 return "Normal ranges: Heart rate 60–100 bpm, SpO2 ≥95%, Temperature ≤37.5°C."
    if 'thank' in m:                  return "You're welcome! Stay healthy and keep monitoring your vitals regularly."

    return "You can ask me about your heart rate, oxygen level, temperature, risk level, or describe any symptoms like fever or dizziness."

# ─────────────────────────────────────────────
#  ROUTES — AUTH
# ─────────────────────────────────────────────
@app.route('/')
def home():
    return render_template("login.html")

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        conn = sqlite3.connect("health.db")
        c = conn.cursor()
        hashed = generate_password_hash(request.form['password'])
        c.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",
                  (request.form['username'], hashed, request.form['role']))
        conn.commit()
        conn.close()
        return redirect('/')
    return render_template("register.html")

@app.route('/login', methods=['POST'])
def login():
    conn = sqlite3.connect("health.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND role=?",
              (request.form['username'], request.form['role']))
    user = c.fetchone()
    conn.close()

    if user and check_password_hash(user[2], request.form['password']):
        session['user'] = request.form['username']
        session['role'] = request.form['role']
        return redirect('/patient' if session['role'] == "patient" else '/doctor')
    return "Invalid Login"

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ─────────────────────────────────────────────
#  ROUTES — PATIENT
# ─────────────────────────────────────────────
@app.route('/patient')
def patient():
    if session.get('role') != "patient":
        return redirect('/')
    conn = sqlite3.connect("health.db")
    c = conn.cursor()
    c.execute("SELECT * FROM doctors")
    doctors = c.fetchall()
    conn.close()
    return render_template("patient.html", doctors=doctors)

@app.route('/predict', methods=['POST'])
def predict():
    data = request.form
    conn = sqlite3.connect("health.db")
    c = conn.cursor()

    c.execute("SELECT * FROM doctors WHERE id=?", (data['doctor_id'],))
    doctor = c.fetchone()

    hr   = float(data['heart_rate'])
    spo2 = float(data['spo2'])
    temp = float(data['temp'])

    result        = predict_risk(hr, spo2, temp)
    score         = health_score(hr, spo2, temp)
    tips          = generate_tips(hr, spo2, temp)
    emergency_msg = check_emergency(result, data['patient_address'])

    c.execute("""INSERT INTO records(
        patient_name, patient_number, patient_address,
        doctor_name, doctor_number, doctor_location,
        heart_rate, spo2, temp, result, score
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (
        data['patient_name'], data['patient_number'], data['patient_address'],
        doctor[1], doctor[2], doctor[3],
        hr, spo2, temp, result, score
    ))
    conn.commit()
    conn.close()

    session['hr']     = hr
    session['spo2']   = spo2
    session['temp']   = temp
    session['result'] = result
    session['score']  = score
    session['chat_history'] = []

    p_lat, p_lon = get_coordinates(data['patient_address'])
    d_lat, d_lon = get_coordinates(doctor[3])

    return render_template("dashboard.html",
        data=data, doctor=doctor,
        result=result, score=score, tips=tips,
        emergency_msg=emergency_msg,
        p_lat=p_lat, p_lon=p_lon,
        d_lat=d_lat, d_lon=d_lon
    )

# ─────────────────────────────────────────────
#  ROUTES — DOCTOR
# ─────────────────────────────────────────────
@app.route('/doctor')
def doctor():
    if session.get('role') != "doctor":
        return redirect('/')
    conn = sqlite3.connect("health.db")
    c = conn.cursor()
    c.execute("SELECT * FROM records ORDER BY id DESC")
    data = c.fetchall()
    conn.close()
    return render_template("doctor.html", data=data)

# ─────────────────────────────────────────────
#  ROUTES — APPOINTMENTS / HISTORY / ANALYTICS
# ─────────────────────────────────────────────
@app.route('/book', methods=['POST'])
def book():
    conn = sqlite3.connect("health.db")
    c = conn.cursor()
    c.execute("INSERT INTO appointments(patient_name,doctor_name,date,time) VALUES(?,?,?,?)", (
        request.form['patient_name'], request.form['doctor_name'],
        request.form['date'], request.form['time']
    ))
    conn.commit()
    conn.close()
    return redirect('/patient')

@app.route('/appointments')
def appointments():
    conn = sqlite3.connect("health.db")
    c = conn.cursor()
    c.execute("SELECT * FROM appointments ORDER BY date, time")
    data = c.fetchall()
    conn.close()
    return render_template("appointments.html", data=data)

@app.route('/history')
def history():
    conn = sqlite3.connect("health.db")
    c = conn.cursor()
    c.execute("SELECT * FROM records ORDER BY id DESC")
    data = c.fetchall()
    conn.close()
    return render_template("history.html", data=data)

@app.route('/analytics')
def analytics():
    conn = sqlite3.connect("health.db")
    c = conn.cursor()
    c.execute("SELECT heart_rate, spo2, temp, score FROM records ORDER BY id")
    data = c.fetchall()
    conn.close()
    hr    = [row[0] for row in data]
    spo2  = [row[1] for row in data]
    temp  = [row[2] for row in data]
    score = [row[3] for row in data]
    return render_template("analytics.html", hr=hr, spo2=spo2, temp=temp, score=score)

# ─────────────────────────────────────────────
#  ROUTES — AI CHATBOT (Claude-powered)
# ─────────────────────────────────────────────
@app.route('/chat', methods=['POST'])
def chat():
    msg = request.form.get('message', '').strip()
    if not msg:
        return jsonify({"reply": "Please type a message."})

    if 'chat_history' not in session:
        session['chat_history'] = []

    history = session['chat_history']

    # Emergency shortcut
    if session.get('emergency'):
        doc = session.get('emergency_doctor')
        reply = f"🚨 Emergency detected! Contact Dr. {doc[1]} at {doc[2]} immediately or press the SOS button."
        history.append({"role": "user", "content": msg})
        history.append({"role": "assistant", "content": reply})
        session['chat_history'] = history[-20:]
        return jsonify({"reply": reply})

    reply = ai_chat_reply(msg, history)

    history.append({"role": "user", "content": msg})
    history.append({"role": "assistant", "content": reply})
    session['chat_history'] = history[-20:]

    return jsonify({"reply": reply})

# ─────────────────────────────────────────────
#  ROUTES — LIVE DATA API
# ─────────────────────────────────────────────
@app.route('/live-data')
def live_data():
    conn = sqlite3.connect("health.db")
    c = conn.cursor()
    c.execute("SELECT heart_rate, spo2, temp, result, score FROM records ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({"hr": row[0], "spo2": row[1], "temp": row[2], "result": row[3], "score": row[4]})
    return jsonify({})

@app.route('/device-data', methods=['POST'])
def device_data():
    data = request.json
    hr   = float(data['heart_rate'])
    spo2 = float(data['spo2'])
    temp = float(data['temp'])

    result = predict_risk(hr, spo2, temp)
    score  = health_score(hr, spo2, temp)

    conn = sqlite3.connect("health.db")
    c = conn.cursor()
    c.execute("""INSERT INTO records(patient_name,patient_number,patient_address,
        doctor_name,doctor_number,doctor_location,heart_rate,spo2,temp,result,score)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        ("Live","000","City","AutoDoc","111","City",hr,spo2,temp,result,score))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "result": result, "score": score})

#if __name__ == "__main__": app.run(debug=True, port=5001)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    