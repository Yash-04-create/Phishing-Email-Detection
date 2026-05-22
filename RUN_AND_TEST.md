# Phishing Email Detector: Run and Test Guide

This project has two parts:
- `Backend/`: Flask API + trained phishing model
- `Frontend/`: browser UI for entering emails and seeing predictions

## 1. Start the backend

Open a terminal in the project root:

```powershell
cd "D:\Phishing Detector"
.\venv\Scripts\python.exe Backend\app.py
```

If you ever retrain the model, run:

```powershell
.\venv\Scripts\python.exe Backend\model\train.py
```

The backend should run on:
- `http://127.0.0.1:5000`

## 2. Open the frontend

With the Flask server running, open:

- `http://127.0.0.1:5000/`

The page lets you enter:
- Sender
- Subject
- Body

Then click **Analyze Email**.

## 3. Test with email entries

Use a mix of obviously phishing and normal emails.

### Sample phishing-style email

Sender:

```text
Security Team <security@bank-support-alert.com>
```

Subject:

```text
Urgent: verify your account immediately
```

Body:

```text
We noticed suspicious activity on your account. Click https://login-check.example/verify right now to prevent suspension.
```

Expected result:
- Label should usually be `phishing`
- Indicators should include the URL and urgent keywords

### Sample legitimate email

Sender:

```text
Alex Morgan <alex.morgan@company.com>
```

Subject:

```text
Weekly team meeting
```

Body:

```text
Hi team, the weekly meeting is moved to Thursday at 3 PM. Please review the agenda before then.
```

Expected result:
- Label should usually be `legitimate`
- Indicators should be low-risk or empty

## 4. Test the API directly

You can also test the backend with `curl` or PowerShell.

### PowerShell example

```powershell
$payload = @{
  sender  = "Security Team <security@bank-support-alert.com>"
  subject = "Urgent: verify your account immediately"
  body    = "Click https://login-check.example/verify right now."
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:5000/api/predict" `
  -Method Post `
  -ContentType "application/json" `
  -Body $payload
```

## 5. What the result means

The API returns:
- `label`: `phishing` or `legitimate`
- `probability`: model confidence for phishing
- `indicators`: heuristic signals such as URLs, urgent keywords, suspicious sender
- `top_features`: the strongest terms influencing the prediction

## 6. Notes

- The model is trained from `Data/Data_set.csv`.
- Every prediction is logged in `Backend/logs.db`.
- If the frontend cannot connect, make sure Flask is running on port `5000`.
