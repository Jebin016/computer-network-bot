import os
from flask import Flask, jsonify, render_template_string, request
from google import genai
from google.genai import types

app = Flask(__name__)

# Initialize the Gemini Client (automatically picks up GEMINI_API_KEY environment variable)
client = genai.Client()

# System prompt forcing the chatbot to specialize in Computer Networks
NETWORK_SYSTEM_PROMPT = """
You are CN_BOT, a highly accurate academic and industry expert specializing exclusively in Computer Networks and Data Communications.

Your Core Mandate:
1. Provide precise, accurate, and structured answers to all questions regarding Computer Networks.
2. Structure technical answers clearly using headings, bullet points, code blocks, or packet diagrams where appropriate.
3. Be proficient across all key networking domains:
   - **Models:** OSI 7-Layer Model, TCP/IP Protocol Suite.
   - **Protocols:** IP (IPv4/IPv6), TCP, UDP, HTTP/HTTPS, DNS, DHCP, ARP, ICMP, BGP, OSPF, RIP, TLS/SSL, SSH, FTP.
   - **Addressing & Subnetting:** CIDR, Subnet masks, NAT, MAC addresses, Private vs. Public IPs.
   - **Routing & Switching:** VLANs, STP, Link-State, Distance-Vector, Packet Switching vs. Circuit Switching.
   - **Network Security:** Firewalls, VPNs, IDS/IPS, Encryption, Wireshark packet analysis concepts.
   - **Congestion & Flow Control:** Sliding Window, Go-Back-N, Selective Repeat, TCP Slow Start, SYN Flooding.

Rules:
1. ONLY answer questions related to computer networks, data communications, telecommunications, and network security.
2. If a user asks a question completely unrelated to networking (e.g., biology, cooking, generic coding), politely decline by stating:
   "I am NetExpert, a dedicated Computer Networks bot. Please ask me a question related to networking, protocols, or data communication."
3. When subnetting or calculating IP ranges, double-check your math step-by-step to guarantee 100% accuracy.
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NetExpert - Computer Networks AI Tutor</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #e2e8f0; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        #chat-container { width: 100%; max-width: 800px; background: #1e293b; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); display: flex; flex-direction: column; height: 85vh; border: 1px solid #334155; }
        #chat-header { background: #0284c7; color: white; padding: 18px 20px; font-size: 1.2rem; font-weight: bold; border-top-left-radius: 12px; border-top-right-radius: 12px; display: flex; align-items: center; justify-content: space-between; }
        #chat-box { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
        .message { padding: 12px 18px; border-radius: 10px; max-width: 85%; word-wrap: break-word; white-space: pre-wrap; line-height: 1.5; font-size: 0.95rem; }
        .user { align-self: flex-end; background: #0284c7; color: #ffffff; border-bottom-right-radius: 2px; }
        .bot { align-self: flex-start; background: #334155; color: #f1f5f9; border-bottom-left-radius: 2px; border: 1px solid #475569; }
        #input-form { display: flex; padding: 15px; background: #0f172a; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; border-top: 1px solid #334155; }
        #user-input { flex: 1; padding: 12px 16px; background: #1e293b; border: 1px solid #475569; border-radius: 6px; font-size: 1rem; color: #fff; outline: none; }
        #user-input:focus { border-color: #0284c7; }
        button { padding: 12px 24px; background: #0284c7; color: white; border: none; font-weight: bold; border-radius: 6px; margin-left: 10px; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #0369a1; }
    </style>
</head>
<body>
    <div id="chat-container">
        <div id="chat-header">
            <span>🌐Computer Networks Tutor</span>
            <small style="font-size: 0.8rem; opacity: 0.8;">CN_BOT</small>
        </div>
        <div id="chat-box">
            <div class="message bot">Hello! I am <b>CN_BOT</b>. Ask me any question about Computer Networks (OSI Model, TCP/IP, Subnetting, Routing Protocols, DNS, HTTP, Security, etc.)!</div>
        </div>
        <form id="input-form">
            <input type="text" id="user-input" placeholder="e.g., Explain the difference between TCP and UDP with examples..." required autocomplete="off">
            <button type="submit">Send</button>
        </form>
    </div>

    <script>
        const chatBox = document.getElementById('chat-box');
        const form = document.getElementById('input-form');
        const input = document.getElementById('user-input');

        function appendMessage(text, sender) {
            const msgDiv = document.createElement('div');
            msgDiv.classList.add('message', sender);
            msgDiv.innerHTML = text;
            chatBox.appendChild(msgDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const message = input.value.trim();
            if (!message) return;

            // Escaping simple HTML tags for user message display
            const safeMessage = message.replace(/</g, "&lt;").replace(/>/g, "&gt;");
            appendMessage(safeMessage, 'user');
            input.value = '';

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });
                const data = await response.json();
                if (data.reply) {
                    appendMessage(data.reply, 'bot');
                } else {
                    appendMessage("<b>Error:</b> " + (data.error || "Failed to fetch response."), 'bot');
                }
            } catch (err) {
                appendMessage("<b>Error:</b> Could not connect to local server.", 'bot');
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get("message", "")
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    try:
        # Call Gemini model via the official google-genai SDK
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=NETWORK_SYSTEM_PROMPT,
                temperature=0.2 # Lower temperature for higher factual accuracy
            )
        )
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
   
