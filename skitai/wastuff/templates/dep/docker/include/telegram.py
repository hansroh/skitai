#! /usr/bin/env python3

# pip3 install python-telegram-bot
# BotFather /setprivacy disable
# add to group

import telegram

class Telegram:
    def __init__ (self, token, chat_id = None):
        self.token = token
        self.chat_id = chat_id
        self.bot = telegram.Bot(token = token)

    def show_messages (self):
        updates = self.bot.getUpdates()
        for u in updates:
            print(u.message)

    def updates (self):
        return self.bot.getUpdates()

    def send (self, msg, chat_id = None):
        msgs = self.updates ()
        if msgs and self.chat_id is None:
            self.chat_id = msgs [-1].message.chat.id

        self.bot.sendMessage (
            chat_id or self.chat_id,
            msg
        )


if __name__ == "__main__":
    import sys, os
    import time
    from telegram.error import TimedOut

    token = os.environ.get ('TELEGRAM_TOKEN')
    if not token:
        raise SystemExit ('telegram token reqired')
    chat_id = os.environ.get ('TELEGRAM_CHAT_ID')
    commit_title = os.environ.get ("CI_COMMIT_TITLE", "")
    if commit_title.find ('--tg-silent') != -1:
        sys.exit ()

    bot = Telegram (token, chat_id)
    for i in range (7):
        try:
            bot.send (' '.join (sys.argv [1:]))
        except TimedOut:
            time.sleep (2)
            continue
        break
