import os
import sys

# A barcode queue class.
# Each might need its own connection, so each thread should have its own BarcodeQueue.
# Once created, just feed it barcode events as needed.

class BarcodeQueue:
    scannerID = None
    def __init__(self):
        self.scannerID = os.environ.get('CB_BARCODE_IDENTITY')

    def sendBarcode(self, barcode_type, barcode):
        print(self.scannerID, "found", barcode_type,":",barcode)
        sys.stdout.flush()

