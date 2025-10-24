# backend/utils.py
import re
from urllib.parse import urlparse

URL_REGEX = re.compile(r'(https?://\S+|www\.\S+)', re.IGNORECASE)
URGENT_KEYWORDS = ['urgent', 'immediately', 'verify', 'update', 'login', 'password', 'click', 'suspend', 'account', 'bank', 'transfer', 'credentials', 'ssn']

def extract_urls(text):
    if not text:
        return []
    return URL_REGEX.findall(text)

def count_urgent_keywords(text):
    if not text:
        return 0
    t = text.lower()
    return sum(t.count(k) for k in URGENT_KEYWORDS)

def suspicious_sender(sender_text):
    """
    Simple heuristic: if email address domain looks odd (.xyz, .ru, contains numbers) or display name contains brand but domain doesn't,
    we flag as suspicious. sender_text might be "Name <user@domain.com>" or just "user@domain.com" or "Name".
    """
    if not sender_text:
        return False
    s = sender_text
    # extract email
    m = re.search(r'[\w\.-]+@[\w\.-]+', s)
    if not m:
        return False
    email = m.group(0)
    domain = email.split('@')[-1].lower()
    # suspicious TLDs or numeric domains
    if any(domain.endswith(t) for t in ['.xyz', '.ru', '.tk', '.cf']):
        return True
    if re.search(r'\d', domain):
        return True
    # if display name contains a brand but domain doesn't (e.g., "State Bank <random@gmail.com>")
    display = re.sub(r'<?[\w\.-]+@[\w\.-]+>?', '', s).strip().lower()
    if display and any(brand in display for brand in ['bank', 'upi', 'aadhar', 'paypal', 'paytm', 'google']):
        if not any(brand in domain for brand in ['bank', 'upi', 'aadhar', 'paypal', 'paytm', 'google']):
            return True
    return False
