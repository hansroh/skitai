import re, sys, os
try:
    from urllib.parse import unquote, unquote_plus
except ImportError:
    from urlparse import unquote
    from urllib import unquote_plus    
import json
from hashlib import md5
import random
from rs4 import producers
from .wastuff.api import API
from collections import Iterator

####################################################################################
# Utitlities
####################################################################################
REQUEST = re.compile ('([^ ]+) ([^ ]+)(( HTTP/([0-9.]+))$|$)')
CONNECTION = re.compile ('Connection: (.*)', re.IGNORECASE)

def crack_query (r):
    if type (r) is bytes:
        r = r.decode ("utf8")

    if not r: return {}
    if r[0]=='?': r=r[1:]    
    arg={}
    q = [x.split('=', 1) for x in r.split('&')]
    
    for each in q:
        k = unquote_plus (each[0])
        try: 
            t, k = k.split (":", 1)
        except ValueError:
            t = "str"
            
        if len (each) == 2:        
            v = unquote_plus(each[1])
            if t == "str":
                pass
            elif t == "int":
                v = int (v)
            elif t == "float":
                v = float (v)
            elif t == "list":
                v = v.split (",")
            elif t == "bit":
                v = v.lower () in ("1", "true", "yes")
            elif t == "json":
                v = json.loads (v)
                
        else:
            v = ""            
            if t == "str":
                pass
            elif t == "int":
                v = 0
            elif t == "float":
                v = 0.0
            elif t == "list":
                v = []
            elif t == "bit":
                v = False
            elif t == "json":
                v = {}
                
        if k in arg:
            if type (arg [k]) is not type ([]):
                arg[k] = [arg[k]]
            arg[k].append (v)
            
        else:
            arg[k] = v
            
    return arg
    
def crack_request (r):
    m = REQUEST.match (r)
    if m.end() == len(r):        
        uri=m.group(2)        
        if m.group(3):
            version = m.group(5)
        else:
            version = None    
        return m.group(1).lower(), uri, version
    else:
        return None, None, None

def join_headers (headers):
    r = []
    for i in range(len(headers)):
        if headers[i][0] in ' \t':    
            r[-1] = r[-1] + headers[i][1:]
        else:
            r.append (headers[i])
    return r

def get_header (head_reg, lines, group=1):
    for line in lines:
        m = head_reg.match (line)
        if m and m.end() == len(line):
            return m.group (group)
    return ''

def get_header_match (head_reg, lines):
    for line in lines:
        m = head_reg.match (line)
        if m and m.end() == len(line):
            return m
    return ''        

def get_extension (path):
    dirsep = path.rfind ('/')
    dotsep = path.rfind ('.')
    if dotsep > dirsep:
        return path[dotsep+1:]
    else:
        return ''

ALNUM = '0123456789abcdefghijklmnopqrstuvwxyz'
def md5uniqid (length = 13):    
    global ALNUM
    _id = ''
    for i in range (0, length):
        _id += random.choice(ALNUM)
    return md5 (_id.encode ("utf8")).hexdigest ()[length:]


def make_pushables (response, content):
    if not response.is_responsable ():
        # already called response.done () or diconnected channel
        return
        
    if content is None: # Possibly no return mistake
        raise AssertionError ("Content or part should not be None")
    
    if not content: # explicit empty not content
        trigger.wakeup (lambda p=response: (p.done(),))
        return
            
    if response ["content-type"] is None: 
        response ["Content-Type"] = "text/html"
    
    if type (content) not in (list, tuple):
        content = (content,) # make iterable

    will_be_push = []
    if len (response) == 0:
        content_length = 0
    else:
        content_length = None
    
    for part in content:                
        # like Django response
        try: part = part.content
        except AttributeError: pass
            
        type_of_part = type (part)
        
        if isinstance (part, API):
            response.update ("Content-Type", part.get_content_type ())
            part = part.to_string ().encode ("utf8")
            will_be_push.append (part)
            
        elif type_of_part in (bytes, str):
            if len (part) == 0:
                continue
            if type_of_part is not bytes:
                try: 
                    part = part.encode ("utf8")
                except AttributeError:
                    raise AssertionError ("%s is not supportable content type" % str (type (part)).replace ("<", "&lt;").replace (">", "&gt;"))                                
                type_of_part = bytes
                
            if type_of_part is bytes:
                if content_length is not None:
                    content_length += len (part)
                will_be_push.append (part)
        
        else:    
            if hasattr (part, "read"):
                part = producers.closing_stream_producer (part)                
            elif type (part) is list:
                part = producers.list_producer (part)
            elif isinstance(part, Iterator): # flask etc.
                part = producers.iter_producer (part)
            
            if hasattr (part, "more"):
                # producer
                content_length = None
                # automatic close    when channel suddenly closed
                hasattr (part, "close") and response.die_with (part)
                # streaming obj
                hasattr (part, "ready") and response.set_streaming ()
                will_be_push.append (part)
            
            else:
                raise AssertionError ("Unsupoorted response object")
    
    if content_length is not None:
        response ["Content-Length"] = content_length
    
    return will_be_push    
    