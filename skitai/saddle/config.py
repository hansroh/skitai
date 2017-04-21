from aquests.lib import attrdict

def Config ():
	cf = attrdict.AttrDict ()
	cf.max_post_body_size = 5 * 1024 * 1024
	cf.max_cache_size = 5 * 1024 * 1024
	cf.max_multipart_body_size = 20 * 1024 * 1024
	cf.max_upload_file_size = 20000000
	return cf
