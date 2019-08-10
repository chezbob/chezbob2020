# Run at your own risk

sudo sh pipdeps.txt

sudo cp barcodedaemon.service /etc/systemd/system/barcodedaemon.service

sudo mkdir /usr/bin/local/barcodedaemon

sudo cp barcodedaemon.py barcodequeue.py /usr/bin/local/barcodedaemon/

sudo chmod +x /usr/bin/local/barcodedaemon.py


sudo systemctl daemon-reload

sudo systemctl enable barcodedaemon.service
sudo systemctl start barcodedaemon.service
