# HealthAI – Smart Patient Monitoring System

A Flask-based web application that monitors patient vitals in real-time, predicts health risk, and provides intelligent alerts with an AI-powered chatbot.

---

## 🚀 Features

* Real-time patient vitals monitoring (HR, SpO2, Temperature)
* Risk prediction system (Low / Moderate / High)
* Health score calculation
* Smart health tips generation
* Emergency alert system (nearest doctor suggestion)
* AI chatbot (Anthropic API)
* Patient & Doctor dashboards
* Appointment management
* Analytics and history tracking

---

## 🛠 Tech Stack

* Backend: Python (Flask)
* Frontend: HTML, CSS, JavaScript
* Database: SQLite
* APIs: OpenStreetMap (geolocation), Anthropic Claude
* Charts: Chart.js

---

## 📁 Project Structure

```
project/
│── app.py
│── model.py
│── requirements.txt
│── Procfile
│── health.db
│
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── doctor.html
│   ├── patient.html
│   ├── analytics.html
│   ├── history.html
│   ├── appointments.html
│
├── static/
│   └── style.css
```

---

## ⚙️ Installation (Local Setup)

1. Clone the repository

```
git clone https://github.com/your-username/health-ai.git
cd health-ai
```

2. Install dependencies

```
pip install -r requirements.txt
```

3. Run the application

```
python app.py
```

4. Open in browser

```
http://127.0.0.1:5000
```

---

## 🌐 Deployment (Render)

1. Push project to GitHub
2. Go to Render → New Web Service
3. Connect your repository

### Build Command

```
pip install -r requirements.txt
```

### Start Command

```
gunicorn app:app
```

4. Add Environment Variable

```
ANTHROPIC_API_KEY=your_api_key
```

5. Deploy

---

## ⚠️ Important Notes

* SQLite is used → data may reset on redeploy
* Secret key is hardcoded (not secure for production)
* API key must be set in environment variables
* Not production-ready without improvements

---

## 🧠 Core Logic

* Risk prediction is rule-based using vitals
* Health score decreases based on abnormal values
* Emergency triggered for high-risk patients
* Nearest doctor calculated via geolocation

---

## 📌 Future Improvements

* Replace SQLite with PostgreSQL
* Add authentication security (JWT / OAuth)
* Improve chatbot intelligence
* Optimize real-time data handling
* Deploy with custom domain

---

## 👨‍💻 Author

Madhavan V

---

## 📜 License

This project is for educational purposes only.
