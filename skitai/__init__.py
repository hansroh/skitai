# 2014. 12. 9 by Hans Roh hansroh@gmail.com

VERSION = "0.10.0"
version_info = tuple (map (lambda x: not x.isdigit () and x or int (x),  VERSION.split (".")))
