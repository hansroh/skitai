from aquests.lib import attrdict

def set_default (cf):
	cf.max_post_body_size = 5 * 1024 * 1024
	cf.max_cache_size = 5 * 1024 * 1024
	cf.max_multipart_body_size = 20 * 1024 * 1024
	cf.max_upload_file_size = 20000000
	
def Config (preset = False):
	cf = attrdict.AttrDict ()
	if preset:
		set_default (cf)		
	return cf
