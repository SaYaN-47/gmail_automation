import os
from dotenv import load_dotenv
from twilio.rest import Client

# Load environment variables from .env
load_dotenv()

# Access the variables
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
from_whatsapp = os.getenv("TWILIO_WHATSAPP_NUMBER")
to_whatsapp = os.getenv("MY_WHATSAPP_NUMBER")

# Twilio client
client = Client(account_sid, auth_token)

print("SID:", os.getenv("TWILIO_ACCOUNT_SID"))
print("TOKEN:", os.getenv("TWILIO_AUTH_TOKEN"))


# Send test message

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
                        "id": "btn_yes",
                        "title": "Yes"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "btn_no",
                        "title": "No"
                    }
                }
            ]
        }
    }
)

print("Message SID:", message.sid)

# message = client.messages.create(
#     from_=from_whatsapp,
#     body="Hi bro",
#     to=to_whatsapp
# )

print("Message SID:", message.sid)
print(message.status)
