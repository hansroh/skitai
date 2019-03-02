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
from collections import Iterator
from aquests.athreads import trigger


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
    from .wastuff import futures
    from .wastuff.api import API
    
    if not response.is_responsable ():
        # already called response.done () or diconnected channel
        return
            
    if content is None: # Possibly no return mistake
        raise AssertionError ("Content or part should not be None")
    
    if not content: # explicit empty not content
        trigger.wakeup (lambda p=response: (p.done(),))
        return
            
    if type (content) not in (list, tuple):
        content = (content,) # make iterable
        
    if isinstance (content [0], futures.Futures):
        return
    
    if response ["content-type"] is None: 
        response ["Content-Type"] = "text/html"
                
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
    

def catch (format = 0, exc_info = None):
    if exc_info is None:
        exc_info = sys.exc_info()
    t, v, tb = exc_info
    tbinfo = []
    assert tb # Must have a traceback
    while tb:
        tbinfo.append((
            tb.tb_frame.f_code.co_filename,
            tb.tb_frame.f_code.co_name,
            str(tb.tb_lineno)
            ))
        tb = tb.tb_next

    del tb
    file, function, line = tbinfo [-1]
    
    # format 0 - text
    # format 1 - html
    # format 2 - list
    try:
        v = str (v)
    except:
        v = repr (v)
        
    if format == 1:
        if v.find ('\n') != -1:
            v = v.replace ("\r", "").replace ("\n", "<br>")
        buf = ["<h3>%s</h3><h4>%s</h4>" % (t.__name__.replace (">", "&gt;").replace ("<", "&lt;"), v)]
        buf.append ("<b>at %s at line %s, %s</b>" % (file, line, function == "?" and "__main__" or "function " + function))
        buf.append ("<ul type='square'>")
        buf += ["<li>%s <span class='f'>%s</span> <span class='n'><b>%s</b></font></li>" % x for x in tbinfo]
        buf.append ("</ul>")        
        return "\n".join (buf)

    buf = []
    buf.append ("%s %s" % (t, v))
    buf.append ("in file %s at line %s, %s" % (file, line, function == "?" and "__main__" or "function " + function))
    buf += ["%s %s %s" % x for x in tbinfo]
    if format == 0:
        return "\n".join (buf)
    return buf    
