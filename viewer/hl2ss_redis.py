# hl2ss client<->redis-streamer (NYU) interface test
# same hl2ss client api

import struct
import asyncio
import websockets.client
import hl2ss


#------------------------------------------------------------------------------
# Extensions
#------------------------------------------------------------------------------

class _extension_rx_pv(hl2ss._rx_pv):
    def open(self):
        hl2ss.start_subsystem_pv(self.host, self.port)
        super().open()

    def close(self):
        super().close()
        hl2ss.stop_subsystem_pv(self.host, self.port)


class _extension_gop:
    def __init__(self, gop_size):
        self.aliased_index = 0
        self.gop_size = gop_size

    def extend(self, data):
        if (self.gop_size > 0):
            data.extend(struct.pack('<B', self.aliased_index))
            self.aliased_index = (self.aliased_index + 1) % self.gop_size


#------------------------------------------------------------------------------
# API redis-streamer
#------------------------------------------------------------------------------

def _get_stream_url_push(host, port):
    return f'ws://{host}/data/{hl2ss.get_port_name(port)}/push?header=0'


def _get_stream_url_pull(host, port):
    return f'ws://{host}/data/{hl2ss.get_port_name(port)}/pull?header=0'


#------------------------------------------------------------------------------
# Network Client (Websockets)
#------------------------------------------------------------------------------

class _client:
    def open(self, host, port, max_size):
        self._loop = asyncio.get_event_loop()
        self._client = self._loop.run_until_complete(websockets.client.connect(_get_stream_url_pull(host, port), max_size=max_size, compression=None))

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

class _rx_rm_vlc(hl2ss._rx_rm_vlc):
    def open(self):
        self._client = _gatherer_video(self.host, self.port, None)
        self._client.open()

    def get_next_packet(self):
        return self._client.get_next_packet()

    def close(self):
        self._client.close()


class _rx_rm_depth_ahat(hl2ss._rx_rm_depth_ahat):
    def open(self):
        self._client = _gatherer_video(self.host, self.port, None)
        self._client.open()

    def get_next_packet(self):
        return self._client.get_next_packet()

    def close(self):
        self._client.close()


class _rx_rm_depth_longthrow(hl2ss._rx_rm_depth_longthrow):
    def open(self):
        self._client = _gatherer_basic(self.host, self.port, None)
        self._client.open()

    def get_next_packet(self):
        return self._client.get_next_packet()

    def close(self):
        self._client.close()


class _rx_rm_imu(hl2ss._rx_rm_imu):
    def open(self):
        self._client = _gatherer_basic(self.host, self.port, None)
        self._client.open()

    def get_next_packet(self):
        return self._client.get_next_packet()

    def close(self):
        self._client.close()


class _rx_pv(hl2ss._rx_pv):
    def open(self):
        self._client = _gatherer_video(self.host, self.port, None)
        self._client.open()

    def get_next_packet(self):
        return self._client.get_next_packet()

    def close(self):
        self._client.close()


class _rx_microphone(hl2ss._rx_microphone):
    def open(self):
        self._client = _gatherer_basic(self.host, self.port, None)
        self._client.open()

    def get_next_packet(self):
        return self._client.get_next_packet()

    def close(self):
        self._client.close()


class _rx_si(hl2ss._rx_si):
    def open(self):
        self._client = _gatherer_basic(self.host, self.port, None)
        self._client.open()

    def get_next_packet(self):
        return self._client.get_next_packet()

    def close(self):
        self._client.close()

