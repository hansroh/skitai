from datetime import datetime
import skitai
import hashlib
import base64
from .models import User, UserLog

PROVIDERS = {
    'naver': 'https://openapi.naver.com/v1/nid/me',
    'kakao': 'https://kapi.kakao.com/v2/user/me'
}

def get_uid_and_profile (provider, payload):
    def gender_code (v):
        if not v:
            return ''
        if v.lower () in ('m', 'male'):
            return 'male'
        elif v.lower () in ('f', 'female'):
            return 'female'
        return 'etc'

    profile = {}
    profile ['providerId'] = provider
    if provider == 'kakao':
        id = payload ['id']
        account = payload ['kakao_account']
        profile ['displayName'] = account ['profile'].get ('nickname', '')
        profile ['photoURL'] = account ['profile'].get ('thumbnail_image_url', '')

    elif provider == 'naver':
        account = payload ['response']
        id = account ['id']
        profile ['displayName'] = account.get ('nickname', '')
        profile ['photoURL'] = account.get ('profile_image', '')

    profile ['uid'] = id
    profile ['birthday'] = account.get ('birthday', '').replace ('-', '')
    profile ['email'] = account.get ('email', '')
    profile ['gender'] = gender_code (account.get ('gender', ''))
    profile ['name'] = account.get ('name', '')
    profile ['phoneNumber'] = ''
    profile ['emailVerified'] = True # assume all true

    # make 28 bytes UID
    uid = '{}-{}'.format (provider, id)
    uid = base64.encodestring (hashlib.md5 (uid.encode ()).digest () + b'-cust') [:-1].decode ().replace ('/', '-').replace ('+', '.')
    return uid, profile


class UserService:
    @staticmethod
    def handle_password (payload):
        if 'password' not in payload:
            return
        payload ['salt'], payload ['signature'] = skitai.was.encrypt_password (payload.pop ('password'))

    @classmethod
    def _get_id (cls, uid):
        return User.get (uid = uid).partial ('id')

    # basic ops ------------------------------
    @classmethod
    def get (cls, uid = None, nick_name = None, public = True):
        assert uid or nick_name, 'uid or nick_name required'
        task = User.get (uid = uid, nick_name = nick_name)
        if public:
            task.partial ("uid, email, email_verified, nick_name, phone_no, photo_url")
            task.partial ("provider, name, gender, birthday, status, created, last_updated, grp")
        return task.execute ()

    @classmethod
    def add (cls, uid, payload):
        payload ['uid'] = uid
        cls.handle_password (payload)
        User.add (payload).execute ().commit ()
        return cls.get (uid)

    @classmethod
    def set (cls, uid, payload):
        cls.handle_password (payload)
        User.set (payload, uid = uid).execute ().commit ()
        return cls.get (uid)

    @classmethod
    def delete (cls, uid):
        with User.transaction () as db:
            UserLog.remove (user_id = cls._get_id (uid)).execute ()
            User.remove (uid = uid).execute ()
            return db.commit ()

    # log -----------------------------------
    @classmethod
    def log (cls, uid, payload):
        payload ['user_id'] = cls._get_id (uid)
        return UserLog.add (payload).execute ()

    @classmethod
    def get_last_status (cls, uid):
        return UserLog.get (user_id = cls._get_id (uid)).order_by ('-id').limit (1).execute ()

    @classmethod
    def test (cls, payload):
        User.validate (payload)

    @classmethod
    def user_exists (cls, uid):
        users = cls.get (uid, public = False).fetch ()
        if not users:
            return None
        user = users [0]
        if user.status:
            if user.status == 'unverified':
                return user
            if user.status == 'resigned':
                if user.last_updated < datetime.datetime.today ().astimezone (datetime.timezone.utc) - datetime.timedelta (days=7):
                    cls.set (user.uid, {'uid': None}).commit ()
                    return None
                else:
                    return user
            user.suspended = user.status
            return user
        return user