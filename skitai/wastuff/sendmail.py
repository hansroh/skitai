import os

SMTP_SERVER = None # "smtp.gmail.com:465"
AUTH = None # AUTH = ("your_account@gmail.com", "your_passwrd")
SENDER = None # "Your Name<noreply@gmail.com>"

def configure (smtp_server, auth, sender):
    global SMTP_SERVER, AUTH, SENDER
    SMTP_SERVER, AUTH, SENDER = smtp_server, auth, sender

if os.name == "posix":
    def send (was, subject, to, msg):
        email = was.email (subject, SENDER, to)
        email.set_smtp (SMTP_SERVER, AUTH [0], AUTH [1], ssl = False)
        email.add_content (msg, "text/html")
        email.send ()

else:
    import smtplib
    from email.mime.text import MIMEText

    def send (was, subject, to, msg):
        smtp = smtplib.SMTP_SSL (SMTP_SERVER, 465)
        smtp.login (*AUTH)
        msg = MIMEText (msg, 'html')
        msg['Subject'] = subject
        msg['From'] = SENDER
        msg['To'] = to
        res = smtp.sendmail(AUTH [0], to, msg.as_string())
        smtp.quit()
        return res
