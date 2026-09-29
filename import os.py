import os
from dotenv import load_dotenv
from twilio.rest import Client

# Load environment variables
load_dotenv()

# Get values from .env
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
from_whatsapp = os.getenv("TWILIO_WHATSAPP_NUMBER")   # e.g. whatsapp:+14155238886
to_whatsapp = os.getenv("MY_WHATSAPP_NUMBER")         # e.g. whatsapp:+917980760722

# Twilio client
client = Client(account_sid, auth_token)

print("Sending WhatsApp Interactive Message...")

# Send interactive button message
message = client.messages.create(
    from_=from_whatsapp,
    to=to_whatsapp,
    interactive={
        "type": "button",
        "body": {
            "text": "Choose an option:"
        },
        "action": {
            "buttons": [
                {
                    "type": "reply",
                    "reply": {
                        "id": "yes_btn",
                        "title": "Yes 👍"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "no_btn",
                        "title": "No 👎"
                    }
                }
            ]
        }
    }
)

print("Message SID:", message.sid)
print("Status:", message.status)
