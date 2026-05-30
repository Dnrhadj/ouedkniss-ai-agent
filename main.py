import os
import requests
import smtplib
from flask import Flask
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# --- SECURE CONFIGURATIONS ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

OUEDKNISS_GRAPHQL_URL = "https://api.ouedkniss.com/graphql"

@app.route('/')
def home():
    return "Ouedkniss Agent is Live and Running 24/7!", 200

@app.route('/run-agent')
def run_agent():
    print("[Agent] Triggering Ouedkniss check...")
    
    # 1. Fetch data from Ouedkniss GraphQL
    graphql_query = {
        "query": """
        query SearchQuery($q: String, $page: Int) {
          search(q: $q, page: $page) {
            data {
              id
              title
              price
              description
              cities { name }
            }
          }
        }
        """,
        "variables": {"q": "iPhone", "page": 1} # Change "iPhone" to whatever you want to hunt for!
    }
    
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    
    try:
        res = requests.post(OUEDKNISS_GRAPHQL_URL, json=graphql_query, headers=headers)
        listings = res.json()['data']['search']['data'][:10]
    except Exception as e:
        return f"Scraper Failed: {str(e)}", 500

    # 2. Format listings for Google AI Studio
    formatted_listings = ""
    for item in listings:
        formatted_listings += f"Title: {item.get('title')} | Price: {item.get('price')} DA | City: {item.get('cities',[{}])[0].get('name','Inconnu')}\n---\n"

    # 3. Hit Google AI Studio Gemini API
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": f"Here are the latest items:\n\n{formatted_listings}"}]}],
        "systemInstruction": {
            "parts": [{"text": "You are an expert Algerian Market Broker. Analyze these Ouedkniss listings and write a clean email report in French highlighting the best 3 deals based on price. Use brief bullet points."}]
        }
    }

    try:
        gemini_res = requests.post(gemini_url, json=payload, headers={"Content-Type": "application/json"})
        report = gemini_res.json()['candidates'][0]['content']['parts'][0]['text']
        
        # 4. Email the results
        send_email(report)
        return "Success! Check your email inbox.", 200
    except Exception as e:
        return f"AI Generation/Email Failed: {str(e)}", 500

def send_email(content):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = "🇩🇿 [Ouedkniss Agent] Market Deals Summary"
    msg.attach(MIMEText(content, 'plain'))
    
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
    server.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
