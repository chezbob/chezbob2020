#!/usr/bin/env python3
import argparse
import nfc
from threading import Thread
import evdev
import binascii
from barcodequeue import BarcodeQueue
import pyudev
import time
import os
import sys
# Chez Bob barcode reading service.
# Primary task: look for certain scanners, wait for events, and publish them.

#GLOBAL VAR: DEBOUNCETIME measures in seconds a cool-down period for NFC scans.
# otherwise they just appear continuously as long as the tag is present.

DEBOUNCE_TIME = 5

#GLOBAL VAR: A list of threads, as this is a pretty simple application spinning up
# only a handful of well-defined threads.
THREAD_LIST = []


# once we found a nfc scanner, just keep reading it until it disappears.
def poll_nfc():
    try:
        clf = nfc.ContactlessFrontend()
        clf.open("usb")
        barcodequeue = BarcodeQueue()
        print("OPENED: NFC scanner opened on ", clf)

        previousbarcode = None
        last_scan_time = time.time()
        while True:
            tag = clf.connect(rdwr={'on-connect': lambda tag: False})
            if tag:
                newbarcode = binascii.hexlify(tag.identifier)
                if (newbarcode != previousbarcode or time.time() > last_scan_time + DEBOUNCE_TIME):
                    previousbarcode = newbarcode
                    last_scan_time = time.time()
                    barcodequeue.sendBarcode("NFC", newbarcode)
            else:
                break
    #on error, return to the outer udev loop.
    except OSError as e:
        print("OSError ", e, file  = sys.stderr)
        return
    except usb1.USBErrorIO as e:
        print("USBErrorIO ", e, file  = sys.stderr)
        return
    except KeyboardInterrupt:
        exit(0)




# once we found our keyboard scanner, just keep reading it until it disappears.
# this has to read and process all the key up and key down events.
def poll_evdev_scanner(device_node):
    try:
        device = evdev.InputDevice(device_node)
        device.grab()
        shifted = False
        buf = []
        barcodequeue = BarcodeQueue()
        print("OPENED: HID scanner opened and grabbed on ", device_node)

        for event in device.read_loop():
            if event.type != evdev.events.EV_KEY:
                continue
            name = evdev.events.keys[event.code]

            if event.value != evdev.events.KeyEvent.key_down:
                continue

            name = evdev.events.keys[event.code]
            short_name = name[4:]

            if short_name == "SHIFT" or short_name == "LEFTSHIFT":
                if event.value == evdev.events.KeyEvent.key_down:
                    shifted = True
                    continue
                elif event.value == evdev.events.KeyEvent.key_up:
                    shifted = False
                    continue
            
            if len(short_name) == 1:
                # only add single character key names, a.k.a. alphanumeric keys
                # ex. KEY_A -> A (short name) -> A or a depending on shift
                # NOTE: This implictly filters out any special characters, since they have long names (e.g. KEY_SPACE)
                if shifted:
                    buf.append(short_name)
                else:
                    buf.append(short_name.lower())

            if short_name == "ENTER" or short_name == "KPENTER":
                barcode = ''.join(buf)
                barcodequeue.sendBarcode("bar",barcode)
                buf = []
                continue

    except OSError as e:
        print("OSError ", e, file  = sys.stderr)
        # Got an error, likely due to the device disconnecting.
        # We just exit our loop here, falling back to the udev monitor loop.
        return


def poll_stdin():
    barcodequeue = BarcodeQueue()
    try:
        while True:
            barcode = input()
            barcodequeue.sendBarcode("bar",barcode)
    except EOFError:
        print("EOF on stdin", file = sys.stderr)
        return


def main():
    global THREAD_LIST
    commandparser = argparse.ArgumentParser()



    commandparser.add_argument("-H","--hid-vendor-product", help="Vendor and Product IDs of a keyboard-style barcode scanner, format vvvv or vvvv:pppp")
    commandparser.add_argument("-N","--nfc-vendor-product", help="Vendor and Product IDs of a USB nfc scanner, format vvvv or vvvv:pppp")
    commandparser.add_argument("-S","--serial", help="serial device properties for detecting a scanner")
    commandparser.add_argument("-r","--read-stdin", help="wait for barcodes to be entered on stdin", action="store_true")


    args = commandparser.parse_args()

    THREAD_LIST = []
    

    if (args.read_stdin):
        stdinthread = Thread(target=poll_stdin, args=[])
        stdinthread.start()
        THREAD_LIST.append(stdinthread)

    if (args.hid_vendor_product or args.nfc_vendor_product):
        #loop forever waiting for devices to appear (hotplugging)
        infinite_udev_loop( args.hid_vendor_product, args.nfc_vendor_product)

    for thread in THREAD_LIST:
        thread.join()

    print("main barcodedaemon thread shutting down", file = sys.stderr)

# a simple udev loop trying to find specific keyboard-like input devices.
def infinite_udev_loop(hid_vendor_product, nfc_vendor_product):
    global THREAD_LIST
    udevcontext = pyudev.Context()
    for device in udevcontext.list_devices(subsystem="input"):
        investigate_hid_input_device("enumerate", device, hid_vendor_product)
    #nfc devices just show up as USB
    for device in udevcontext.list_devices(subsystem="usb"):
        investigate_usb_nfc_device("enumerate", device, nfc_vendor_product)
    monitor = pyudev.Monitor.from_netlink(udevcontext)
    monitor.filter_by('usb')
    monitor.filter_by('input')
    for device in iter(monitor.poll, None):
        THREAD_LIST = [thread for thread in THREAD_LIST if thread.is_alive()]
        investigate_hid_input_device(device.action, device, hid_vendor_product)
        investigate_usb_nfc_device(device.action, device, nfc_vendor_product)

def match_device_vendor_product(device, vendorproductID):
    if (not vendorproductID):
        return False
    #split supplied IDs on a colon
    #if no product model id supplied, then just check the vendor ID
    ids = vendorproductID.split(":")
    if (device.get("ID_VENDOR_ID") != ids[0]):
        return False
    if (len(ids) >= 2):
        if (device.get("ID_MODEL_ID") != ids[1]):
            return False
    return True

# when an input device appears, check to see if we should start reading it.
def investigate_hid_input_device(action, device, vendorproductID):
    global THREAD_LIST
    if (device.subsystem != "input" or not match_device_vendor_product(device,vendorproductID) or action == "remove" or not device.device_node):
        return
    print("HOTPLUG: Detected HID scanner")
    hid_thread = Thread(target=poll_evdev_scanner, args=[device.device_node])
    hid_thread.start()
    THREAD_LIST.append(hid_thread)

# when a usb device appears, check to see if we should start reading it.
def investigate_usb_nfc_device(action, device, vendorproductID):
    global THREAD_LIST
    if (device.subsystem != "usb" or not match_device_vendor_product(device,vendorproductID) or action == "remove"):
        return
    print("HOTPLUG: Detected NFC Scanner")
    nfc_thread = Thread(target=poll_nfc, args=[])
    nfc_thread.start()
    THREAD_LIST.append(nfc_thread)



try:
    main()
except KeyboardInterrupt:
    print("main interrupt")
    #sys.exit doesn't actually stop threads. This os call is a bit more forceful.
    os._exit(0)
