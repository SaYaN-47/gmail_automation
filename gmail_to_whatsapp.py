import threading
from flask import Flask

import os
import json
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from twilio.rest import Client
from dotenv import load_dotenv


# ============================================================
# SETTINGS
# ============================================================

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

CHECK_INTERVAL = 30          # Check Gmail every 30 seconds
STATE_FILE = "gmail_state.json"


# ============================================================
# FLASK WEB SERVER
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Gmail to WhatsApp service is running!"


@app.route("/health")
def health():
    return "OK", 200


def start_web_server():

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )


# ============================================================
# TWILIO
# ============================================================

load_dotenv()

account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
from_whatsapp = os.getenv("TWILIO_WHATSAPP_NUMBER")
to_whatsapp = os.getenv("MY_WHATSAPP_NUMBER")


twilio_client = Client(
    account_sid,
    auth_token
)


# ============================================================
# GMAIL AUTHENTICATION
# ============================================================

def get_gmail_service():

    creds = None

    if os.path.exists("token.json"):

        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:

            creds.refresh(Request())

        else:

            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:

            token.write(
                creds.to_json()
            )

    return build(
        "gmail",
        "v1",
        credentials=creds
    )


# ============================================================
# STATE
# ============================================================

def load_state():

    if not os.path.exists(STATE_FILE):

        return {
            "initialized": False,
            "processed_ids": []
        }

    with open(STATE_FILE, "r") as file:

        return json.load(file)


def save_state(state):

    with open(STATE_FILE, "w") as file:

        json.dump(
            state,
            file,
            indent=4
        )


# ============================================================
# GET EMAIL INFORMATION
# ============================================================

def get_email(service, message_id):

    message = service.users().messages().get(
        userId="me",
        id=message_id
    ).execute()

    headers = message["payload"]["headers"]

    sender = ""
    subject = ""

    for header in headers:

        name = header["name"].lower()

        if name == "from":

            sender = header["value"]

        elif name == "subject":

            subject = header["value"]

    snippet = message.get(
        "snippet",
        ""
    )

    return {
        "id": message_id,
        "sender": sender,
        "subject": subject,
        "snippet": snippet
    }


# ============================================================
# SEND WHATSAPP
# ============================================================

def send_whatsapp(email):

    text = (
        "📧 NEW EMAIL\n\n"
        f"From: {email['sender']}\n\n"
        f"Subject: {email['subject']}\n\n"
        f"Preview:\n{email['snippet']}"
    )

    message = twilio_client.messages.create(
        from_=from_whatsapp,
        to=to_whatsapp,
        body=text
    )

    print("WhatsApp sent!")

    print(
        "SID:",
        message.sid
    )


# ============================================================
# CHECK FOR NEW EMAILS
# ============================================================

def check_for_new_emails(service, state):

    results = service.users().messages().list(
        userId="me",
        maxResults=20
    ).execute()

    messages = results.get(
        "messages",
        []
    )

    if not messages:
        return

    processed_ids = set(
        state["processed_ids"]
    )


    # --------------------------------------------------------
    # FIRST RUN
    # --------------------------------------------------------

    if not state["initialized"]:

        for message in messages:

            processed_ids.add(
                message["id"]
            )

        state["processed_ids"] = list(
            processed_ids
        )

        state["initialized"] = True

        save_state(state)

        print(
            "Initial Gmail state saved."
        )

        print(
            "Existing emails will not be forwarded."
        )

        return


    # --------------------------------------------------------
    # FIND NEW EMAILS
    # --------------------------------------------------------

    new_messages = []

    for message in messages:

        message_id = message["id"]

        if message_id not in processed_ids:

            new_messages.append(
                message
            )


    # Gmail returns newest first.
    # Reverse them so multiple new emails
    # are sent oldest → newest.

    new_messages.reverse()


    # --------------------------------------------------------
    # SEND NEW EMAILS
    # --------------------------------------------------------

    for message in new_messages:

        message_id = message["id"]

        try:

            email = get_email(
                service,
                message_id
            )

            print()
            print(
                "New email detected!"
            )

            print(
                "From:",
                email["sender"]
            )

            print(
                "Subject:",
                email["subject"]
            )

            send_whatsapp(
                email
            )

            processed_ids.add(
                message_id
            )

        except Exception as error:

            print(
                "Error processing email:"
            )

            print(error)


    # --------------------------------------------------------
    # SAVE STATE
    # --------------------------------------------------------

    state["processed_ids"] = list(
        processed_ids
    )

    # Keep only the most recent 100 IDs

    state["processed_ids"] = (
        state["processed_ids"][-100:]
    )

    save_state(state)


# ============================================================
# MAIN LOOP
# ============================================================

def main():

    # --------------------------------------------------------
    # START FLASK SERVER
    # --------------------------------------------------------

    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    web_thread.start()


    # --------------------------------------------------------
    # GMAIL → WHATSAPP
    # --------------------------------------------------------

    print("==============================")
    print(" Gmail → WhatsApp Forwarder")
    print("==============================")

    print(
        "Connecting to Gmail..."
    )

    service = get_gmail_service()

    print(
        "Gmail connected."
    )

    print()

    print(
        f"Checking Gmail every {CHECK_INTERVAL} seconds..."
    )

    print(
        "Press CTRL+C to stop."
    )

    print()

    state = load_state()


    # --------------------------------------------------------
    # CONTINUOUS LOOP
    # --------------------------------------------------------

    while True:

        try:
            print("Checking Gmail...")

            check_for_new_emails(
                service,
                state
            )

        except Exception as error:

            print()
            print("ERROR:")
            print(error)
            print()

        time.sleep(
            CHECK_INTERVAL
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()