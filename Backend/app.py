import json
import os
import sqlite3
from datetime import datetime, timezone

import joblib
import numpy as np
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from utils import compose_email_text, count_urgent_keywords, extract_urls, suspicious_sender

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'model')
VECT_PATH = os.path.join(MODEL_DIR, 'vectorizer.pkl')
MODEL_PATH = os.path.join(MODEL_DIR, 'model.pkl')
DB_PATH = os.path.join(os.path.dirname(__file__), 'logs.db')

app = Flask(__name__, static_folder='../Frontend', static_url_path='/')
CORS(app)

if not os.path.exists(VECT_PATH) or not os.path.exists(MODEL_PATH):
    raise RuntimeError("Model or vectorizer not found. Run backend/model/train.py first.")

vectorizer = joblib.load(VECT_PATH)
model = joblib.load(MODEL_PATH)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        '''
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
        '''
    )
    conn.commit()
    conn.close()


init_db()


def top_contributing_features(text, top_n=6):
    if not hasattr(model, 'coef_'):
        return []

    vec = vectorizer.transform([text])
    feature_names = vectorizer.get_feature_names_out()

    if model.coef_.ndim == 1 or (model.coef_.ndim == 2 and model.coef_.shape[0] == 1):
        coef_vector = model.coef_[0] if model.coef_.ndim == 2 else model.coef_
    else:
        coef_vector = model.coef_.mean(axis=0)

    contributions = vec.toarray()[0] * coef_vector
    idx = np.argsort(contributions)[-top_n:][::-1]

    features = []
    for i in idx:
        if contributions[i] <= 0:
            continue
        features.append({'feature': feature_names[i], 'score': float(contributions[i])})
    return features


def heuristic_phish_score(sender, text):
    urls = extract_urls(text)
    urgent_count = count_urgent_keywords(text)
    sender_flag = suspicious_sender(sender)
    lower_text = text.lower()

    cue_words = ['verify', 'suspend', 'suspended', 'click', 'immediately', 'account', 'login', 'password', 'bank']
    cue_hits = sum(1 for cue in cue_words if cue in lower_text)

    score = 0.0
    score += min(len(urls), 3) * 0.18
    score += min(urgent_count, 8) * 0.05
    score += min(cue_hits, 4) * 0.08
    score += 0.2 if sender_flag else 0.0

    return min(score, 1.0), {
        'urls': urls,
        'urgent_keyword_count': urgent_count,
        'suspicious_sender': sender_flag,
        'cue_hits': cue_hits,
    }


@app.route('/api/predict', methods=['POST'])
def predict():
    data = request.get_json(silent=True) or {}
    sender = data.get('sender', '')
    subject = data.get('subject', '')
    body = data.get('body', '')
    text = compose_email_text(sender, subject, body)

    X = vectorizer.transform([text])
    classes = list(getattr(model, 'classes_', []))
    if 1 in classes:
        idx_pos = classes.index(1)
    else:
        idx_pos = 1 if len(classes) > 1 else 0
    probs = model.predict_proba(X)[0]
    model_prob_phish = float(probs[idx_pos])
    heuristic_score, indicators = heuristic_phish_score(sender, text)

    # Strong phishing cues should be able to override a borderline model score.
    combined_prob = (0.45 * model_prob_phish) + (0.55 * heuristic_score)
    strong_phishing_signal = (
        indicators['suspicious_sender']
        or indicators['urgent_keyword_count'] >= 5
        or indicators['cue_hits'] >= 3
        or len(indicators['urls']) > 0 and indicators['cue_hits'] >= 2
    )
    prob_phish = max(combined_prob, 0.72 if strong_phishing_signal else combined_prob)
    label = 1 if (strong_phishing_signal or prob_phish >= 0.5) else 0

    top_features = top_contributing_features(text, top_n=8)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        '''
        INSERT INTO logs(sender, subject, body, probability, label, indicators, top_features, ts)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            sender,
            subject,
            body,
            prob_phish,
            label,
            json.dumps(indicators),
            json.dumps(top_features),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    return jsonify(
        {
            'probability': prob_phish,
            'model_probability': model_prob_phish,
            'label': 'phishing' if label == 1 else 'legitimate',
            'indicators': indicators,
            'top_features': top_features,
        }
    )


@app.route('/')
def index():
    static_folder = app.static_folder or os.path.join(os.path.dirname(__file__), '../Frontend')
    return send_from_directory(static_folder, 'index.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
