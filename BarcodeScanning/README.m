#Barcode Scanning Daemon


Handles hotpluggable scanners. Currently just prints barcodes into the system journal.

#Note if running not as root as a system service:

add user to plugdev to get usb access -- `sudo adduser <username> plugdev`
add user to input group to get exclusive keyboard access

this suffices under raspbian
