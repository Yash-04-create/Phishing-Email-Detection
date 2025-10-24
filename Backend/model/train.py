# backend/model/train.py
import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
import joblib 
# '..' means one folder-up and '.' current folder
DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'sample_emails.csv')
OUT_MODEL_DIR = os.path.join(os.path.dirname(__file__), '.')

def make_synthetic(n=50):
    phishing_samples = [
        "Account Verification Required. Click the link.",
        "Payment failed, update now.",
        "Confirm your Aadhaar immediately.",
        "Urgent action needed.",
        "Claim your prize, click here."
    ]
    legit_samples = [
        "Meeting rescheduled to Friday.",
        "Dinner tomorrow?",
        "Monthly report attached.",
        "See you at the event.",
        "Invoice attached for your review."
    ]
    
    rows = []
    for i in range(n):
        rows.append((1, "Phishing Email", np.random.choice(phishing_samples)))
        rows.append((0, "Legit Email", np.random.choice(legit_samples)))

    df = pd.DataFrame(rows, columns=['label', 'subject', 'body'])
    return df


def load_data():
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
        if 'label' not in df.columns or 'subject' not in df.columns or 'body' not in df.columns:
            raise ValueError("CSV must have 'label','subject','body' columns")
        if df['label'].nunique() < 2 or len(df) < 4:
            print("⚠️ Dataset too small or only one sample per class — using synthetic data instead.")
            df = make_synthetic(50)
    else:
        print("No dataset found. Using synthetic sample.")
        df = make_synthetic(50)

    df['text'] = df['subject'].fillna('') + ' ' + df['body'].fillna('')
    df['label'] = df['label'].astype(int)
    print("Label distribution:\n", df['label'].value_counts())
    return df


def train():
    df = load_data()
    X = df['text']
    y = df['label']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    vectorizer = TfidfVectorizer(ngram_range=(1,2), max_features=20000, stop_words='english')
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
