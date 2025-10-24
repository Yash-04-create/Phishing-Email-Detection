# backend/app.py
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import joblib
import numpy as np
import sqlite3
import json
from datetime import datetime, timezone
from utils import extract_urls, count_urgent_keywords, suspicious_sender

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'model')
VECT_PATH = os.path.join(MODEL_DIR, 'vectorizer.pkl')
MODEL_PATH = os.path.join(MODEL_DIR, 'model.pkl')
DB_PATH = os.path.join(os.path.dirname(__file__), 'logs.db')

app = Flask(__name__, static_folder='../frontend', static_url_path='/')
CORS(app)

# Load model + vectorizer
if not os.path.exists(VECT_PATH) or not os.path.exists(MODEL_PATH):
    raise RuntimeError("Model or vectorizer not found. Run backend/model/train.py first.")

vectorizer = joblib.load(VECT_PATH)
model = joblib.load(MODEL_PATH)

# Ensure logs DB
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            subject TEXT,
            body TEXT,
            probability REAL,
            label INTEGER,
            indicators TEXT,
            top_features TEXT,
            ts TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def top_contributing_features(text, top_n=6):
    vec = vectorizer.transform([text])
    feature_names = vectorizer.get_feature_names_out()
    # Handle binary classifiers (coef_.shape = (1, n_features))
    if model.coef_.ndim == 1 or (model.coef_.ndim == 2 and model.coef_.shape[0] == 1):
        coef_vector = model.coef_[0] if model.coef_.ndim == 2 else model.coef_
    else:
            coef_vector = model.coef_.mean(axis=0)
    contributions = vec.toarray()[0] * coef_vector
    # pick features with largest positive contribution
    idx = np.argsort(contributions)[-top_n:][::-1]
    features = []
    for i in idx:
        if contributions[i] <= 0:
            continue
        features.append({'feature': feature_names[i], 'score': float(contributions[i])})
    return features

@app.route('/api/predict', methods=['POST'])
def predict():
    data = request.get_json()
    sender = data.get('sender', '')
    subject = data.get('subject', '')
    body = data.get('body', '')
    text = (subject or '') + ' ' + (body or '')

    X = vectorizer.transform([text])
    # find probability of positive class (label=1)
    # `model.classes_` ordering may vary, so find index of class '1' if present
    if 1 in list(model.classes_):
        idx_pos = list(model.classes_).index(1)
    else:
        # fallback: assume second column is positive
        idx_pos = 1 if len(model.classes_) > 1 else 0
    probs = model.predict_proba(X)[0]
    prob_phish = float(probs[idx_pos])

    label = 1 if prob_phish >= 0.5 else 0

    # heuristics / indicators
    urls = extract_urls(text)
    urgent_count = count_urgent_keywords(text)
    sender_flag = suspicious_sender(sender)
    indicators = {
        'urls': urls,
        'urgent_keyword_count': urgent_count,
        'suspicious_sender': sender_flag
    }

    top_features = top_contributing_features(text, top_n=8)

    # store log
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO logs(sender, subject, body, probability, label, indicators, top_features, ts)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (sender, subject, body, prob_phish, label, json.dumps(indicators), json.dumps(top_features), datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()

    return jsonify({
        'probability': prob_phish,
        'label': 'phishing' if label==1 else 'legitimate',
        'indicators': indicators,
        'top_features': top_features
    })

# optional: serve frontend index
@app.route('/')
def index():
    static_folder = app.static_folder or os.path.join(os.path.dirname(__file__), '../frontend')
    return send_from_directory(static_folder, 'index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
