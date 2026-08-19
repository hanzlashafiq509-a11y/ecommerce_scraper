(function () {
  const API_URL = "http://localhost:8000/chat";
  let conversationHistory = [];
  let selectedLanguage = null;
  let selectedIntent = null;

  const DOT = "\u00B7";
  const ARROW = "\u2192";
  const BUBBLE_ICON = "\uD83D\uDCAC";

  const TEXT = {
    en: {
      welcome: "Hello! How can I assist you today?",
      chooseIntent: "What would you like help with?",
      infoBtn: "I need information",
      productBtn: "I want to buy a product",
      placeholder: "Type a message...",
      send: "Send",
      error: "Connection issue. Please try again shortly.",
    },
    ur: {
      welcome: "Assalam-o-Alaikum! Main aapki kis tarah madad kar sakta hoon?",
      chooseIntent: "Aapko kis cheez mein madad chahiye?",
      infoBtn: "Information chahiye",
      productBtn: "Product khareedna hai",
      placeholder: "Kuch bhi likhein...",
      send: "Bhejein",
      error: "Connection mein masla aa gaya. Thori dair baad try karein.",
    },
  };

  const style = document.createElement("style");
  style.textContent = `
    @import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Inter:wght@400;500;600;700&display=swap');

    #dn-chat-bubble {
      position: fixed; bottom: 24px; right: 24px; width: 60px; height: 60px;
      border-radius: 50%; background: #0B0B0D; color: #C9A227; display: flex;
      align-items: center; justify-content: center; cursor: pointer;
      box-shadow: 0 6px 24px rgba(0,0,0,0.35), 0 0 0 2px #C9A227;
      z-index: 999999; font-size: 24px; transition: transform 0.2s ease;
    }
    #dn-chat-bubble:hover { transform: scale(1.08); }
    #dn-chat-bubble::after {
      content: ""; position: absolute; inset: -2px; border-radius: 50%;
      border: 2px solid #C9A227; opacity: 0.6; animation: dn-pulse 2.2s ease-out infinite;
    }
    @keyframes dn-pulse {
      0% { transform: scale(1); opacity: 0.6; }
      100% { transform: scale(1.5); opacity: 0; }
    }
    #dn-chat-panel {
      position: fixed; bottom: 96px; right: 24px; width: 360px; max-width: 92vw;
      height: 520px; max-height: 76vh; background: #0F0F12; border-radius: 18px;
      box-shadow: 0 20px 50px rgba(0,0,0,0.45); display: none; flex-direction: column;
      overflow: hidden; z-index: 999999; font-family: 'Inter', system-ui, -apple-system, sans-serif;
      border: 1px solid #232326; opacity: 0; transform: translateY(12px);
      transition: opacity 0.2s ease, transform 0.2s ease;
    }
    #dn-chat-panel.dn-open { opacity: 1; transform: translateY(0); }
    #dn-chat-header {
      background: #0B0B0D; padding: 16px 18px; flex-shrink: 0;
      display: flex; align-items: center; gap: 10px; border-bottom: 1px solid #232326;
    }
    #dn-chat-avatar {
      width: 34px; height: 34px; border-radius: 50%; background: #C9A227;
      color: #0B0B0D; display: flex; align-items: center; justify-content: center;
      font-family: 'Archivo Black', sans-serif; font-size: 15px; flex-shrink: 0;
    }
    #dn-chat-header-text { display: flex; flex-direction: column; gap: 1px; overflow: hidden; }
    #dn-chat-title {
      font-family: 'Archivo Black', sans-serif; color: #F5F3EE; font-size: 14px;
      letter-spacing: 0.2px; white-space: nowrap;
    }
    #dn-chat-subtitle { color: #8A8A90; font-size: 10.5px; letter-spacing: 0.3px; white-space: nowrap; }
    #dn-chat-body { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-height: 0; }
    #dn-chat-messages {
      flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px;
      background: #0F0F12; min-height: 0;
    }
    #dn-chat-messages::-webkit-scrollbar { width: 5px; }
    #dn-chat-messages::-webkit-scrollbar-thumb { background: #2A2A2E; border-radius: 4px; }
    .dn-msg { max-width: 85%; padding: 10px 13px; border-radius: 14px; font-size: 13.5px; line-height: 1.5; overflow-wrap: anywhere; word-break: break-word; }
    .dn-msg-user {
      align-self: flex-end; background: #C9A227; color: #0B0B0D; font-weight: 500;
      border-bottom-right-radius: 3px;
    }
    .dn-msg-bot {
      align-self: flex-start; background: #1B1B1F; color: #E9E7E0;
      border-bottom-left-radius: 3px; white-space: pre-wrap; border: 1px solid #232326;
    }
    .dn-carousel {
      display: flex; flex-direction: row; align-items: flex-start; gap: 10px;
      overflow-x: auto; overflow-y: hidden; padding: 4px 2px 10px 2px;
      scroll-snap-type: x proximity; align-self: flex-start; max-width: 100%;
      height: 194px; flex-shrink: 0; width: 100%; box-sizing: border-box;
    }
    .dn-carousel::-webkit-scrollbar { height: 5px; }
    .dn-carousel::-webkit-scrollbar-thumb { background: #2A2A2E; border-radius: 4px; }
    .dn-product-card {
      flex: 0 0 130px; width: 130px; height: 182px; background: #1B1B1F;
      border: 1px solid #232326; border-radius: 12px; overflow: hidden;
      scroll-snap-align: start; text-decoration: none; display: block;
      transition: border-color 0.15s ease; box-sizing: border-box;
    }
    .dn-product-card:hover { border-color: #C9A227; }
    .dn-product-img {
      width: 130px; height: 105px; object-fit: cover; background: #232326; display: block;
    }
    .dn-product-img-fallback {
      width: 130px; height: 105px; background: #232326; display: flex; align-items: center;
      justify-content: center; color: #C9A227; font-family: 'Archivo Black', sans-serif; font-size: 20px;
      box-sizing: border-box;
    }
    .dn-product-info { padding: 8px 9px; height: 77px; box-sizing: border-box; }
    .dn-product-name {
      color: #E9E7E0; font-size: 11px; font-weight: 600; line-height: 1.3;
      display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
      margin-bottom: 4px; height: 28px;
    }
    .dn-product-price { color: #C9A227; font-size: 12px; font-weight: 700; }
    .dn-product-cta {
      margin-top: 6px; font-size: 10px; color: #0B0B0D; background: #C9A227; text-align: center;
      padding: 4px 0; border-radius: 6px; font-weight: 700; letter-spacing: 0.2px;
    }
    #dn-chat-input-row {
      display: flex; border-top: 1px solid #232326; padding: 10px; gap: 8px; flex-shrink: 0;
      background: #0F0F12;
    }
    #dn-chat-input {
      flex: 1; border: 1px solid #2A2A2E; background: #1B1B1F; color: #F5F3EE;
      border-radius: 9px; padding: 9px 12px; font-size: 13px; outline: none; font-family: inherit;
    }
    #dn-chat-input::placeholder { color: #6A6A70; }
    #dn-chat-input:focus { border-color: #C9A227; }
    #dn-chat-send {
      background: #C9A227; color: #0B0B0D; border: none; border-radius: 9px; padding: 0 16px;
      cursor: pointer; font-size: 12.5px; font-weight: 700; transition: opacity 0.15s;
    }
    #dn-chat-send:hover { opacity: 0.88; }
    .dn-typing { align-self: flex-start; display: flex; gap: 4px; padding: 8px 12px; }
    .dn-typing span {
      width: 6px; height: 6px; border-radius: 50%; background: #C9A227; opacity: 0.4;
      animation: dn-bounce 1.1s infinite ease-in-out;
    }
    .dn-typing span:nth-child(2) { animation-delay: 0.15s; }
    .dn-typing span:nth-child(3) { animation-delay: 0.3s; }
    @keyframes dn-bounce { 0%, 60%, 100% { opacity: 0.4; transform: translateY(0); } 30% { opacity: 1; transform: translateY(-3px); } }
    .dn-choice-screen {
      flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
      gap: 16px; padding: 28px; text-align: center; overflow-y: auto; background: #0F0F12;
    }
    .dn-choice-mark {
      width: 46px; height: 46px; border-radius: 50%; background: #C9A227; color: #0B0B0D;
      display: flex; align-items: center; justify-content: center; font-family: 'Archivo Black', sans-serif;
      font-size: 19px; margin-bottom: 2px;
    }
    .dn-choice-title { font-size: 13.5px; font-weight: 600; color: #F5F3EE; line-height: 1.4; }
    .dn-choice-btn {
      background: #C9A227; color: #0B0B0D; border: none; border-radius: 10px; padding: 12px 20px;
      font-size: 13px; font-weight: 700; cursor: pointer; width: 100%; max-width: 230px;
      transition: opacity 0.15s; font-family: inherit;
    }
    .dn-choice-btn:hover { opacity: 0.88; }
    .dn-choice-btn-outline { background: transparent; color: #F5F3EE; border: 1.5px solid #3A3A3E; }
    .dn-choice-btn-outline:hover { border-color: #C9A227; opacity: 1; }
  `;
  document.head.appendChild(style);

  const bubble = document.createElement("div");
  bubble.id = "dn-chat-bubble";
  bubble.innerText = BUBBLE_ICON;
  document.body.appendChild(bubble);

  const panel = document.createElement("div");
  panel.id = "dn-chat-panel";
  panel.innerHTML = `
    <div id="dn-chat-header">
      <div id="dn-chat-avatar">H</div>
      <div id="dn-chat-header-text">
        <div id="dn-chat-title">HANZLA CREATION</div>
        <div id="dn-chat-subtitle">Streetwear ${DOT} Watches ${DOT} Accessories</div>
      </div>
    </div>
    <div id="dn-chat-body"></div>
  `;
  document.body.appendChild(panel);

  const bodyEl = panel.querySelector("#dn-chat-body");

  bubble.addEventListener("click", () => {
    const isOpen = panel.style.display === "flex";
    if (isOpen) {
      panel.classList.remove("dn-open");
      setTimeout(() => { panel.style.display = "none"; }, 150);
    } else {
      panel.style.display = "flex";
      requestAnimationFrame(() => panel.classList.add("dn-open"));
    }
  });

  showLanguageScreen();

  function showLanguageScreen() {
    bodyEl.innerHTML = `
      <div class="dn-choice-screen">
        <div class="dn-choice-mark">H</div>
        <div class="dn-choice-title">Please choose a language<br/>Zaban chunain</div>
        <button class="dn-choice-btn" id="dn-lang-en">English</button>
        <button class="dn-choice-btn dn-choice-btn-outline" id="dn-lang-ur">Roman Urdu</button>
      </div>
    `;
    document.getElementById("dn-lang-en").onclick = () => { selectedLanguage = "en"; showIntentScreen(); };
    document.getElementById("dn-lang-ur").onclick = () => { selectedLanguage = "ur"; showIntentScreen(); };
  }

  function showIntentScreen() {
    const t = TEXT[selectedLanguage];
    bodyEl.innerHTML = `
      <div class="dn-choice-screen">
        <div class="dn-choice-mark">H</div>
        <div class="dn-choice-title">${t.welcome}</div>
        <div class="dn-choice-title" style="font-weight:400; color:#8A8A90;">${t.chooseIntent}</div>
        <button class="dn-choice-btn" id="dn-intent-product">${t.productBtn}</button>
        <button class="dn-choice-btn dn-choice-btn-outline" id="dn-intent-info">${t.infoBtn}</button>
      </div>
    `;
    document.getElementById("dn-intent-product").onclick = () => { selectedIntent = "product"; startChat(); };
    document.getElementById("dn-intent-info").onclick = () => { selectedIntent = "info"; startChat(); };
  }

  function startChat() {
    const t = TEXT[selectedLanguage];
    bodyEl.innerHTML = `
      <div id="dn-chat-messages"></div>
      <div id="dn-chat-input-row">
        <input id="dn-chat-input" type="text" placeholder="${t.placeholder}" />
        <button id="dn-chat-send">${t.send}</button>
      </div>
    `;
    const messagesEl = bodyEl.querySelector("#dn-chat-messages");
    const inputEl = bodyEl.querySelector("#dn-chat-input");
    const sendBtn = bodyEl.querySelector("#dn-chat-send");

    addBotMessage(messagesEl, t.welcome);

    sendBtn.addEventListener("click", () => sendMessage(messagesEl, inputEl));
    inputEl.addEventListener("keydown", (e) => { if (e.key === "Enter") sendMessage(messagesEl, inputEl); });
    inputEl.focus();
  }

  function addUserMessage(messagesEl, text) {
    const div = document.createElement("div");
    div.className = "dn-msg dn-msg-user";
    div.innerText = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function addBotMessage(messagesEl, text) {
    const div = document.createElement("div");
    div.className = "dn-msg dn-msg-bot";
    div.innerText = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function addProductCarousel(messagesEl, products) {
    const row = document.createElement("div");
    row.className = "dn-carousel";
    products.slice(0, 8).forEach((p) => {
      const card = document.createElement("a");
      card.className = "dn-product-card";
      card.href = p.product_url || "#";
      card.target = "_blank";
      card.rel = "noopener noreferrer";

      const imgWrap = document.createElement("div");
      if (p.image) {
        const img = document.createElement("img");
        img.className = "dn-product-img";
        img.src = p.image;
        img.alt = p.name || "";
        img.onerror = function () {
          imgWrap.innerHTML = '<div class="dn-product-img-fallback">H</div>';
        };
        imgWrap.appendChild(img);
      } else {
        imgWrap.innerHTML = '<div class="dn-product-img-fallback">H</div>';
      }

      const info = document.createElement("div");
      info.className = "dn-product-info";
      info.innerHTML = `
        <div class="dn-product-name">${escapeHtml(p.name || "")}</div>
        <div class="dn-product-price">Rs. ${escapeHtml(String(p.price || ""))}</div>
        <div class="dn-product-cta">View ${ARROW}</div>
      `;

      card.appendChild(imgWrap);
      card.appendChild(info);
      row.appendChild(card);
    });
    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function escapeHtml(str) {
    const d = document.createElement("div");
    d.innerText = str;
    return d.innerHTML;
  }

  async function sendMessage(messagesEl, inputEl) {
    const text = inputEl.value.trim();
    if (!text) return;
    const t = TEXT[selectedLanguage];
    addUserMessage(messagesEl, text);
    inputEl.value = "";

    const typing = document.createElement("div");
    typing.className = "dn-typing";
    typing.innerHTML = "<span></span><span></span><span></span>";
    messagesEl.appendChild(typing);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          history: conversationHistory,
          language: selectedLanguage,
          intent: selectedIntent,
        }),
      });
      const data = await res.json();
      typing.remove();
      addBotMessage(messagesEl, data.reply || t.error);

      conversationHistory.push({ role: "user", text: text });
      conversationHistory.push({ role: "bot", text: data.reply || "" });
      if (conversationHistory.length > 12) conversationHistory = conversationHistory.slice(-12);

      if (data.show_links && data.products && data.products.length) {
        addProductCarousel(messagesEl, data.products);
      }
    } catch (err) {
      typing.remove();
      addBotMessage(messagesEl, t.error);
    }
  }
})();
