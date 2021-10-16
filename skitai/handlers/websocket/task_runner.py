# Websocket Communicating Background Task Management
# Hans Roh, Feb, 2018

from rs4.psutil import Puppet
import sys

class Task (Puppet):
  def __init__ (self, userid, websocket, cmd):
    self.userid = userid
    self.websocket = websocket
    self.cmd = cmd # ex. [sys.excutable, 'task.py', '--id', 4, '--clips', 10]
    super ().__init__ ()

  def log (self, line, *args):
    if not self.websocket:
        return
    self.websocket.send (line)

  def start (self):
    super ().start (self.cmd)


USERS = {}
def kill (user):
    if not has_task (user):
        return
    task = USERS.pop (user)
    task.kill ()
    return task.is_active ()

def add_task (user, task):
    USERS [user]= task

def has_task (user):
    if user not in USERS:
        return False
    if USERS [user].is_active ():
        return True
    del USERS [user]
    return False

def attach (user, websocket):
    if has_task (user):
         USERS [user].websocket = websocket
         USERS [user].log ("websocket reconected: {}".format (USERS [user].id))

def dettach (user):
    if has_task (user):
         USERS [user].websocket = None
