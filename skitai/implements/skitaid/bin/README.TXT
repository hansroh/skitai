================================================
Service Installation
================================================

1. Linux
	edit etc/skitaid/skitaid.conf
	edit skitaid.sh
	edit etc/init/skitaid.conf
	
	sudo cp etc/skitaid /etc/
	sudo cp etc/init/skitaid.conf /etc/init
	
	sudo start skitaid
	sudo stop skitaid
	
2. Win32
	run 'cmd.exe' as administrator
	
	edit etc\skitai.conf
	edit win32service\install_win32_service.py
	pyhton win32service\install_win32_service.py --startup auto install
	
