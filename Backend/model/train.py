import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

SCRIPT_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
PROJECT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, '..'))

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from utils import compose_email_text  # noqa: E402

DATA_CANDIDATES = [
    os.path.join(PROJECT_DIR, 'Data', 'Data_set.csv'),
    os.path.join(PROJECT_DIR, 'Data', 'sample_emails.csv'),
    os.path.join(PROJECT_DIR, 'data', 'Data_set.csv'),
    os.path.join(PROJECT_DIR, 'data', 'sample_emails.csv'),
]
OUT_MODEL_DIR = SCRIPT_DIR


def make_synthetic(n=50):
    phishing_samples = [
        "Account Verification Required. Click the link.",
        "Payment failed, update now.",
        "Confirm your Aadhaar immediately.",
        "Urgent action needed.",
        "Claim your prize, click here.",
    ]
    legit_samples = [
        "Meeting rescheduled to Friday.",
        "Dinner tomorrow?",
        "Monthly report attached.",
        "See you at the event.",
        "Invoice attached for your review.",
    ]

    rows = []
    for _ in range(n):
        rows.append((1, "Phishing Email", np.random.choice(phishing_samples), ""))
        rows.append((0, "Legit Email", np.random.choice(legit_samples), ""))

    return pd.DataFrame(rows, columns=['label', 'subject', 'body', 'sender'])


def resolve_data_path():
    for path in DATA_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def normalize_label_column(series):
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(int)

    normalized = series.astype(str).str.strip().str.lower()
    mapping = {
        '1': 1,
        '0': 0,
        'phishing': 1,
        'spam': 1,
        'malicious': 1,
        'legitimate': 0,
        'legit': 0,
        'ham': 0,
        'safe': 0,
        'true': 1,
        'false': 0,
        'yes': 1,
        'no': 0,
    }
    mapped = normalized.map(mapping)
    if mapped.isna().any():
        fallback = pd.to_numeric(series, errors='coerce')
        if fallback.isna().any():
            raise ValueError("Label column must be numeric or map cleanly to phishing/legitimate values.")
        return fallback.astype(int)
    return mapped.astype(int)


def build_text(row):
    extra = row.get('urls', '')
    extra_token = ''
    if pd.notna(extra) and str(extra).strip() and str(extra).strip().lower() != 'nan':
        extra_token = f"url_{str(extra).strip()}"
    return compose_email_text(
        row.get('sender', ''),
        row.get('subject', ''),
        row.get('body', ''),
        extra_token,
    )


def load_data():
    data_path = resolve_data_path()
    if data_path is None:
        print("No dataset found. Using synthetic sample.")
        df = make_synthetic(50)
        df['text'] = df.apply(build_text, axis=1)
        return df

    df = pd.read_csv(data_path)
    df.columns = [col.strip().lower() for col in df.columns]

    if 'label' not in df.columns:
        raise ValueError("CSV must include a 'label' column.")
    if 'subject' not in df.columns:
        df['subject'] = ''
    if 'body' not in df.columns:
        df['body'] = ''
    if 'sender' not in df.columns:
        df['sender'] = ''
    if 'urls' not in df.columns:
        df['urls'] = ''

    df = df.dropna(subset=['label']).copy()
    df['label'] = normalize_label_column(df['label'])
    df['text'] = df.apply(build_text, axis=1)

    if df['label'].nunique() < 2 or len(df) < 4:
        print("Dataset too small or only one class detected, using synthetic data instead.")
        df = make_synthetic(50)
        df['text'] = df.apply(build_text, axis=1)

    print("Label distribution:\n", df['label'].value_counts())
    return df


def train():
    df = load_data()
    X = df['text']
    y = df['label']
    stratify = y if y.nunique() > 1 and y.value_counts().min() >= 2 else None

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=stratify,
    )

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=20000, stop_words='english')
    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)

    model = LogisticRegression(max_iter=1000, class_weight='balanced')
    model.fit(X_train_tfidf, y_train)

    preds = model.predict(X_test_tfidf)
    print("Accuracy:", accuracy_score(y_test, preds))
    print(classification_report(y_test, preds))

    joblib.dump(vectorizer, os.path.join(OUT_MODEL_DIR, 'vectorizer.pkl'))
    joblib.dump(model, os.path.join(OUT_MODEL_DIR, 'model.pkl'))
    print("Saved vectorizer and model to", OUT_MODEL_DIR)


if __name__ == "__main__":
    train()
