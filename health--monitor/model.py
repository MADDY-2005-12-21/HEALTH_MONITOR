# ---------------- RISK PREDICTION ----------------

def predict_risk(hr, spo2, temp):
    """
    Advanced rule-based (ML-like scoring)
    """

    risk_score = 0

    # HEART RATE
    if hr < 50:
        risk_score += 25
    elif 50 <= hr <= 100:
        risk_score += 0
    elif 100 < hr <= 120:
        risk_score += 15
    else:
        risk_score += 30

    # SPO2
    if spo2 >= 95:
        risk_score += 0
    elif 90 <= spo2 < 95:
        risk_score += 20
    else:
        risk_score += 40

    # TEMPERATURE
    if temp <= 37.5:
        risk_score += 0
    elif 37.5 < temp <= 38.5:
        risk_score += 15
    else:
        risk_score += 30

    # FINAL CLASSIFICATION
    if risk_score < 20:
        return "Low Risk"
    elif 20 <= risk_score < 50:
        return "Moderate Risk"
    else:
        return "High Risk"


# ---------------- HEALTH SCORE ----------------

def health_score(hr, spo2, temp):
    """
    More realistic scoring system
    """

    score = 100

    # HEART RATE IMPACT
    if hr < 60:
        score -= 10
    elif hr > 100:
        score -= 15

    # SPO2 IMPACT
    if spo2 < 95:
        score -= (95 - spo2) * 2

    # TEMPERATURE IMPACT
    if temp > 37.5:
        score -= (temp - 37.5) * 10

    return max(int(score), 0)


# ---------------- HEALTH TIPS ----------------

def generate_tips(hr, spo2, temp):
    """
    Improved suggestions based on severity
    """

    tips = []

    # HEART RATE
    if hr > 100:
        tips.append("Your heart rate is high. Try to relax, avoid caffeine, and rest.")
    elif hr < 60:
        tips.append("Your heart rate is low. Monitor for dizziness or fatigue.")

    # SPO2
    if spo2 < 95:
        tips.append("Low oxygen level detected. Try deep breathing and seek fresh air.")
    if spo2 < 90:
        tips.append("Critical oxygen level! Seek medical attention immediately.")

    # TEMPERATURE
    if temp > 37.5:
        tips.append("You have fever. Stay hydrated and take proper rest.")
    if temp > 39:
        tips.append("High fever detected. Consult a doctor immediately.")

    # COMBINED CONDITIONS (SMART LOGIC)
    if hr > 110 and spo2 < 92:
        tips.append("Warning: High heart rate and low oxygen together can be dangerous.")

    if not tips:
        tips.append("Your vitals look stable. Maintain a healthy lifestyle.")

    return tips