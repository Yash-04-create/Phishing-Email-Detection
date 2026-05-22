const form = document.getElementById('emailForm');
const analyzeBtn = document.getElementById('analyzeBtn');
const fillSampleBtn = document.getElementById('fillSampleBtn');
const resultDiv = document.getElementById('result');
const statusPill = document.getElementById('statusPill');
const meterFill = document.getElementById('meterFill');
const confidenceTag = document.getElementById('confidenceTag');
const API_BASE = window.location.origin === 'null' ? 'http://127.0.0.1:5000' : window.location.origin;

const sampleEmail = {
  sender: 'Security Team <security@bank-support-alert.com>',
  subject: 'Urgent: verify your account immediately',
  body: 'We noticed suspicious activity on your account. Click https://login-check.example/verify right now to prevent suspension.',
};

function setStatus(probability, label) {
  const percentage = Math.round(probability * 100);
  const isPhishing = label === 'phishing';

  statusPill.textContent = isPhishing ? 'Phishing' : 'Legitimate';
  statusPill.className = `status-pill ${isPhishing ? 'danger' : 'safe'}`;
  meterFill.style.width = `${percentage}%`;
  meterFill.className = `meter-fill ${isPhishing ? 'danger' : 'safe'}`;

  if (percentage >= 80) {
    confidenceTag.textContent = 'Very high confidence';
  } else if (percentage >= 60) {
    confidenceTag.textContent = 'Moderate confidence';
  } else {
    confidenceTag.textContent = 'Low confidence';
  }
}

function renderIndicatorList(items) {
  const indEl = document.getElementById('indicators');
  indEl.innerHTML = '';

  if (!items || !items.length) {
    const li = document.createElement('li');
    li.textContent = 'No indicators returned.';
    indEl.appendChild(li);
    return;
  }

  items.forEach((item) => {
    const li = document.createElement('li');
    li.textContent = item;
    indEl.appendChild(li);
  });
}

function renderTopFeatures(features) {
  const tfEl = document.getElementById('top_features');
  tfEl.innerHTML = '';

  if (!features || !features.length) {
    const li = document.createElement('li');
    li.textContent = 'No positive features returned for this message.';
    tfEl.appendChild(li);
    return;
  }

  features.forEach((feature) => {
    const li = document.createElement('li');
    li.textContent = `${feature.feature} (score: ${feature.score.toFixed(4)})`;
    tfEl.appendChild(li);
  });
}

async function analyzeEmail() {
  const sender = document.getElementById('sender').value.trim();
  const subject = document.getElementById('subject').value.trim();
  const body = document.getElementById('body').value.trim();

  analyzeBtn.disabled = true;
  analyzeBtn.textContent = 'Analyzing...';

  try {
    const res = await fetch(`${API_BASE}/api/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sender, subject, body }),
    });

    if (!res.ok) {
      throw new Error(`Backend returned ${res.status}`);
    }

    const data = await res.json();

    document.getElementById('label').textContent = data.label;
    document.getElementById('prob').textContent = `${(data.probability * 100).toFixed(2)}%`;
    document.getElementById('senderRisk').textContent = data.indicators.suspicious_sender ? 'Suspicious' : 'Not flagged';

    const indicatorLines = [];
    if (data.indicators.urls && data.indicators.urls.length) {
      data.indicators.urls.forEach((url) => indicatorLines.push(`URL: ${url}`));
    }
    indicatorLines.push(`Urgent keywords: ${data.indicators.urgent_keyword_count}`);
    indicatorLines.push(`Suspicious sender: ${data.indicators.suspicious_sender ? 'Yes' : 'No'}`);
    renderIndicatorList(indicatorLines);
    renderTopFeatures(data.top_features);

    setStatus(data.probability, data.label);
    resultDiv.style.display = 'block';
  } catch (error) {
    console.error('Error fetching backend:', error);
    statusPill.textContent = 'Error';
    statusPill.className = 'status-pill danger';
    resultDiv.style.display = 'block';
    document.getElementById('label').textContent = 'Unable to analyze';
    document.getElementById('prob').textContent = '-';
    document.getElementById('senderRisk').textContent = '-';
    renderIndicatorList(['Could not connect to the backend. Make sure Flask is running on port 5000.']);
    renderTopFeatures([]);
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = 'Analyze Email';
  }
}

fillSampleBtn.addEventListener('click', () => {
  document.getElementById('sender').value = sampleEmail.sender;
  document.getElementById('subject').value = sampleEmail.subject;
  document.getElementById('body').value = sampleEmail.body;
  resultDiv.style.display = 'none';
});

analyzeBtn.addEventListener('click', analyzeEmail);

form.addEventListener('submit', (event) => {
  event.preventDefault();
  analyzeEmail();
});
