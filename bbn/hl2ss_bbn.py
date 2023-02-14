# hl2ss client<->redis-streamer (NYU) interface test
# same hl2ss client api

import struct
import asyncio
import websockets.client
import hl2ss

#------------------------------------------------------------------------------
# Network Bridge (HL2SS-Websockets)
#------------------------------------------------------------------------------

def get_stream_url(host, port):
    return f'ws://{host}:8000/data/{hl2ss.get_port_name(port)}/pull?header=0'


#------------------------------------------------------------------------------
# Network Client (Websockets)
#------------------------------------------------------------------------------

class _client:
    def open(self, host, port, max_size):
        url = get_stream_url(host, port)
        self._loop = asyncio.get_event_loop()
        self._client = self._loop.run_until_complete(websockets.client.connect(url, max_size=max_size, compression=None))

    def recv(self):
        while (True):
            data = self._loop.run_until_complete(self._client.recv())
            if (len(data) > 0):
                return data

    def close(self):
        self._loop.run_until_complete(self._client.close())


#------------------------------------------------------------------------------
# Packet Gatherer (Websockets)
#------------------------------------------------------------------------------

class _gatherer_basic:
    def __init__(self, host, port, max_size):
        self.host = host
        self.port = port
        self.max_size = max_size

    def open(self):
        self._client = _client()
        self._client.open(self.host, self.port, self.max_size)

    def get_next_packet(self):
        return hl2ss.unpack_packet(self._client.recv())
    
    def close(self):
        self._client.close()


class _gatherer_video:
    def __init__(self, host, port, max_size):
        self.host = host
        self.port = port
        self.max_size = max_size

    def open(self):
        self._genlock = False
        self._client = _client()
        self._client.open(self.host, self.port, self.max_size)

    def _fetch(self):
        data = self._client.recv()
        raw_packet = data[:-1]
        aliased_index = struct.unpack('<B', data[-1:])[0]
        return (aliased_index, raw_packet)
    
    def get_next_packet(self):
        aliased_index, data = self._fetch()
        while (not self._genlock):
            if (aliased_index == 0): 
                self._genlock = True
            else:
                aliased_index, data = self._fetch()
        return hl2ss.unpack_packet(data)
    
    def close(self):
        self._client.close()


#------------------------------------------------------------------------------
# Receiver Wrappers (Websockets-HL2SS)
#------------------------------------------------------------------------------

class rx_rm_vlc:
    def __init__(self, host, port, chunk, mode, profile, bitrate):
        self.host = host
        self.port = port
        self.chunk = chunk
        self.mode = mode
        self.profile = profile
        self.bitrate = bitrate

    def open(self):
        self._client = _gatherer_video(self.host, self.port, None)
        self._client.open()

    def get_next_packet(self):
        return self._client.get_next_packet()

    def close(self):
        self._client.close()


class rx_rm_depth_ahat:
    def __init__(self, host, port, chunk, mode, profile, bitrate):
        self.host = host
        self.port = port
        self.chunk = chunk
        self.mode = mode
        self.profile = profile
        self.bitrate = bitrate

    def open(self):
        self._client = _gatherer_video(self.host, self.port, None)
        self._client.open()

    def get_next_packet(self):
        return self._client.get_next_packet()

    def close(self):
        self._client.close()


class rx_rm_depth_longthrow:
    def __init__(self, host, port, chunk, mode, png_filter):
        self.host = host
        self.port = port
        self.chunk = chunk
        self.mode = mode
        self.png_filter = png_filter

    def open(self):
        self._client = _gatherer_basic(self.host, self.port, None)
        self._client.open()

    def get_next_packet(self):
        return self._client.get_next_packet()

    def close(self):
        self._client.close()


class rx_rm_imu:
    def __init__(self, host, port, chunk, mode):
        self.host = host
        self.port = port
        self.chunk = chunk
        self.mode = mode

    def open(self):
        self._client = _gatherer_basic(self.host, self.port, self.chunk, self.mode)
        self._client.open()

    def get_next_packet(self):
        return self._client.get_next_packet()

    def close(self):
        self._client.close()


class rx_pv:
    def __init__(self, host, port, chunk, mode, width, height, framerate, profile, bitrate):
        self.host = host
        self.port = port
        self.chunk = chunk
        self.mode = mode
        self.width = width
        self.height = height
        self.framerate = framerate
        self.profile = profile
        self.bitrate = bitrate

    def open(self):
        self._client = _gatherer_video(self.host, self.port, None)
        self._client.open()

    def get_next_packet(self):
        return self._client.get_next_packet()

    def close(self):
        self._client.close()


class rx_microphone:
    def __init__(self, host, port, chunk, profile):
        self.host = host
        self.port = port
        self.chunk = chunk
        self.mode = hl2ss.StreamMode.MODE_0
        self.profile = profile

    def open(self):
        self._client = _gatherer_basic(self.host, self.port, None)
        self._client.open()

    def get_next_packet(self):
        return self._client.get_next_packet()

    def close(self):
        self._client.close()


class rx_si:
    def __init__(self, host, port, chunk):
        self.host = host
        self.port = port
        self.chunk = chunk
        self.mode = hl2ss.StreamMode.MODE_0

    def open(self):
        self._client = _gatherer_basic(self.host, self.port, self.chunk)
        self._client.open()

    def get_next_packet(self):
        return self._client.get_next_packet()

    def close(self):
        self._client.close()


#------------------------------------------------------------------------------
# Decoded Receivers (HL2SS)
#------------------------------------------------------------------------------

class rx_decoded_rm_vlc:
    def __init__(self, host, port, chunk, mode, profile, bitrate):
        self._client = rx_rm_vlc(host, port, chunk, mode, profile, bitrate)
        self._codec = hl2ss.decode_rm_vlc(profile)

    def open(self):
        self._codec.create()
        self._client.open()
        self.get_next_packet()

    def get_next_packet(self):
        data = self._client.get_next_packet()
        data.payload = self._codec.decode(data.payload)
        return data

    def close(self):
        self._client.close()


class rx_decoded_rm_depth_ahat:
    def __init__(self, host, port, chunk, mode, profile, bitrate):
        self._client = rx_rm_depth_ahat(host, port, chunk, mode, profile, bitrate)
        self._codec = hl2ss.decode_rm_depth_ahat(profile)

    def open(self):
        self._codec.create()
        self._client.open()
        self.get_next_packet()

    def get_next_packet(self):
        data = self._client.get_next_packet()
        data.payload = self._codec.decode(data.payload)
        return data

    def close(self):
        self._client.close()


class rx_decoded_rm_depth_longthrow:
    def __init__(self, host, port, chunk, mode, png_filter):
        self._client = rx_rm_depth_longthrow(host, port, chunk, mode, png_filter)

    def open(self):
        self._client.open()

    def get_next_packet(self):
        data = self._client.get_next_packet()
        data.payload = hl2ss.decode_rm_depth_longthrow(data.payload)
        return data

    def close(self):
        self._client.close()


class rx_decoded_pv:
    def __init__(self, host, port, chunk, mode, width, height, framerate, profile, bitrate, format):
        self._client = rx_pv(host, port, chunk, mode, width, height, framerate, profile, bitrate)
        self._codec = hl2ss.decode_pv(profile)
        self._format = format

    def open(self):        
        self._codec.create()
        self._client.open()
        self.get_next_packet()

    def get_next_packet(self):
        data = self._client.get_next_packet()
        data.payload = hl2ss.unpack_pv(data.payload)
        data.payload.image = self._codec.decode(data.payload.image, self._format)
        return data

    def close(self):
        self._client.close()


class rx_decoded_microphone:
    def __init__(self, host, port, chunk, profile):
        self._client = rx_microphone(host, port, chunk, profile)
        self._codec = hl2ss.decode_microphone(profile)
        
    def open(self):
        self._codec.create()
        self._client.open()

    def get_next_packet(self):
        data = self._client.get_next_packet()
        data.payload = self._codec.decode(data.payload)
        return data

    def close(self):
        self._client.close()

