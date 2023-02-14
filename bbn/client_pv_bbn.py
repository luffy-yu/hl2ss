#------------------------------------------------------------------------------
# This script receives encoded video from the HoloLens front RGB camera and
# plays it. The camera support various resolutions and framerates. See
# etc/hl2_capture_formats.txt for a list of supported formats. The default
# configuration is 1080p 30 FPS. The stream supports three operating modes:
# 0) video, 1) video + camera pose, 2) query calibration (single transfer).
# Press esc to stop. Note that the ahat stream cannot be used while the pv
# subsystem is on.
#------------------------------------------------------------------------------

from pynput import keyboard

import hl2ss
import hl2ss_bbn
import cv2

# Settings --------------------------------------------------------------------

# HoloLens address
host = "127.0.0.1"

# Port
port = hl2ss.StreamPort.PERSONAL_VIDEO

# Video encoding profile
profile = hl2ss.VideoProfile.H264_MAIN

# Decoded format
decoded_format = 'bgr24'

#------------------------------------------------------------------------------

enable = True

def on_press(key):
    global enable
    enable = key != keyboard.Key.esc
    return enable

listener = keyboard.Listener(on_press=on_press)
listener.start()

client = hl2ss_bbn.rx_decoded_pv(host, port, hl2ss.ChunkSize.PERSONAL_VIDEO, 0, 0, 0, 0, profile, 0, decoded_format)
client.open()

while (enable):
    data = client.get_next_packet()
    print('Pose at time {ts}'.format(ts=data.timestamp))
    print(data.pose)
    print('Focal length')
    print(data.payload.focal_length)
    print('Principal point')
    print(data.payload.principal_point)
    cv2.imshow('Video', data.payload.image)
    cv2.waitKey(1)

client.close()
listener.join()
