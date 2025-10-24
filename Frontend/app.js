const form = document.getElementById('emailForm');
const analyzeBtn = document.getElementById('analyzeBtn');
const resultDiv = document.getElementById('result');

analyzeBtn.addEventListener('click', async () => {
  const sender = document.getElementById('sender').value;
  const subject = document.getElementById('subject').value;
  const body = document.getElementById('body').value;

  const payload = { sender, subject, body };
  console.log("Sending payload:", payload);

  try {
    const res = await fetch('http://127.0.0.1:5000/api/predict', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    console.log("Backend returned:", data);

    // Display results persistently
    document.getElementById('label').innerText = data.label;
    document.getElementById('prob').innerText = (data.probability*100).toFixed(2) + '%';

    const indEl = document.getElementById('indicators');
    indEl.innerHTML = '';
    if (data.indicators.urls && data.indicators.urls.length) {
      data.indicators.urls.forEach(u => {
        const li = document.createElement('li');
        li.innerText = 'URL: ' + u;
        indEl.appendChild(li);
      });
    }
    indEl.appendChild(Object.assign(document.createElement('li'), {innerText: `Urgent keywords: ${data.indicators.urgent_keyword_count}`}));
    indEl.appendChild(Object.assign(document.createElement('li'), {innerText: `Suspicious sender: ${data.indicators.suspicious_sender}`}));

    const tfEl = document.getElementById('top_features');
    tfEl.innerHTML = '';
    data.top_features.forEach(f => {
      const li = document.createElement('li');
      li.innerText = `${f.feature} (score: ${f.score.toFixed(4)})`;
      tfEl.appendChild(li);
    });

    resultDiv.style.display = 'block';      // force it visible
    resultDiv.style.visibility = 'visible';  // extra precaution

  } catch(err) {
    console.error("Error fetching backend:", err);
    alert("Failed to connect to backend. Make sure Flask server is running.");
  }
});
