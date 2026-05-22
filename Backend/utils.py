# backend/utils.py
import re

URL_REGEX = re.compile(r'(https?://\S+|www\.\S+)', re.IGNORECASE)
URGENT_KEYWORDS = [
    'urgent',
    'immediately',
    'verify',
    'update',
    'login',
    'password',
    'click',
    'suspend',
    'account',
    'bank',
    'transfer',
    'credentials',
    'ssn',
]


def compose_email_text(sender='', subject='', body='', extra=''):
    parts = [sender, subject, body, extra]
    return ' '.join(str(part).strip() for part in parts if part and str(part).strip())


def extract_urls(text):
    if not text:
        return []
    return URL_REGEX.findall(text)


def count_urgent_keywords(text):
    if not text:
        return 0
    t = text.lower()
    return sum(t.count(keyword) for keyword in URGENT_KEYWORDS)


def suspicious_sender(sender_text):
    """
    Simple heuristic: if email address domain looks odd (.xyz, .ru, contains numbers)
    or display name contains a brand but domain doesn't, flag as suspicious.
    sender_text might be "Name <user@domain.com>" or just "user@domain.com" or "Name".
    """
    if not sender_text:
        return False

    m = re.search(r'[\w\.-]+@[\w\.-]+', sender_text)
    if not m:
        return False

    email = m.group(0)
    domain = email.split('@')[-1].lower()

    if any(domain.endswith(tld) for tld in ['.xyz', '.ru', '.tk', '.cf']):
        return True
    if re.search(r'\d', domain):
        return True

    display = re.sub(r'<?[\w\.-]+@[\w\.-]+>?', '', sender_text).strip().lower()
    if display and any(brand in display for brand in ['bank', 'upi', 'aadhar', 'paypal', 'paytm', 'google']):
        if not any(brand in domain for brand in ['bank', 'upi', 'aadhar', 'paypal', 'paytm', 'google']):
            return True

    return False
