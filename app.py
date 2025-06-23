
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import *
from linebot.exceptions import InvalidSignatureError
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
INITIAL_ADMIN_ID = os.environ.get('INITIAL_ADMIN_ID')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(128), unique=True, nullable=False)

with app.app_context():
    db.create_all()
    if not Admin.query.filter_by(user_id=INITIAL_ADMIN_ID).first():
        db.session.add(Admin(user_id=INITIAL_ADMIN_ID))
        db.session.commit()

@app.route("/")
def index():
    return "Blessed Guardian Railway + PostgreSQL is running!"

@app.route("/callback", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return 'OK', 200
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

def get_admins():
    return [a.user_id for a in Admin.query.all()]

def add_admin(user_id):
    if not Admin.query.filter_by(user_id=user_id).first():
        db.session.add(Admin(user_id=user_id))
        db.session.commit()

def is_admin(user_id):
    return Admin.query.filter_by(user_id=user_id).first() is not None

def extract_mention(event):
    if hasattr(event.message, 'mention') and event.message.mention and event.message.mention.mentionees:
        return event.message.mention.mentionees[0].user_id
    return None

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()
    group_id = getattr(event.source, 'group_id', None)

    if text.startswith("!"):
        if not is_admin(user_id):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage("❌ You are not an admin.")
            )
            return

        if text == "!admins":
            admin_list = '\n'.join(get_admins())
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(f"👑 Current admins:\n{admin_list}")
            )

        elif text.startswith("!admin"):
            mention_id = extract_mention(event)
            if mention_id:
                add_admin(mention_id)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage("✅ User promoted to admin.")
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage("⚠️ Please mention a user to promote.")
                )

        elif text.startswith("!kick"):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage("❌ Sorry, I cannot kick users automatically.")
            )

        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage("⚠️ Unknown command.")
            )

    elif text == "whoami":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(f"Your user ID: {user_id}")
        )

@handler.add(JoinEvent)
def handle_join(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage("👋 Blessed Guardian is online on Railway!")
    )

if __name__ == "__main__":
    app.run(port=5000)
