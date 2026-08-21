// Sidebar toggle (mobile)
function toggleSidebar() {
  document.querySelector('.sidebar')?.classList.toggle('open');
}

function getCookie(name) {
  const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
  return v ? v.pop() : '';
}

// ---------- AI chat widget ----------
async function aiSend(message, boxId = 'aiMessages', inputId = null) {
  const box = document.getElementById(boxId);
  if (!box) return;
  addBubble(box, message, 'me');
  if (inputId) document.getElementById(inputId).value = '';
  const typing = addBubble(box, '<i class="fa-solid fa-ellipsis fa-fade"></i>', 'bot');
  try {
    const res = await fetch(AI_REPLY_URL, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken')},
      body: JSON.stringify({message})
    });
    const data = await res.json();
    typing.innerHTML = `<i class="fa-solid ${data.icon} me-2 text-primary"></i>${data.reply}`;
    renderChips(data.suggestions, boxId, inputId);
  } catch (e) {
    typing.innerHTML = 'Sorry, I could not reach the assistant.';
  }
  box.scrollTop = box.scrollHeight;
}

function addBubble(box, html, cls) {
  const d = document.createElement('div');
  d.className = 'chat-bubble ' + cls;
  d.innerHTML = html;
  box.appendChild(d);
  box.scrollTop = box.scrollHeight;
  return d;
}

function renderChips(list, boxId, inputId) {
  if (!list) return;
  const box = document.getElementById(boxId);
  const wrap = document.createElement('div');
  wrap.className = 'mb-2';
  list.forEach(s => {
    const c = document.createElement('span');
    c.className = 'chip';
    c.textContent = s;
    c.onclick = () => aiSend(s, boxId, inputId);
    wrap.appendChild(c);
  });
  box.appendChild(wrap);
  box.scrollTop = box.scrollHeight;
}

function aiFormSubmit(ev, inputId, boxId) {
  ev.preventDefault();
  const val = document.getElementById(inputId).value.trim();
  if (val) aiSend(val, boxId, inputId);
}
