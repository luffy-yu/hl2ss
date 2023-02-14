
#------------------------------------------------------------------------------
# File I/O
#------------------------------------------------------------------------------

class _Header:
    def __init__(self, header):
        self.port = header[0]
        self.mode = header[1]
        self.profile = header[2]


class writer:
    def open(self, filename, port, mode, profile):
        self._data = open(filename, 'wb')
        self._data.write(struct.pack('<HBB', port, mode, profile if (profile is not None) else _RANGEOF.U8_MAX))

    def write(self, packet):
        self._data.write(pack_packet(packet))

    def close(self):
        self._data.close()


class reader:
    def open(self, filename, chunk_size):
        self._data = open(filename, 'rb')        
        self._header = _Header(struct.unpack('<HBB', self._data.read(_SIZEOF.WORD + 2 * _SIZEOF.BYTE)))
        self._unpacker = _unpacker(self._header.mode)
        self._chunk_size = chunk_size
        self._eof = False

    def get_header(self):
        return self._header
        
    def read(self):
        while (True):
            if (self._unpacker.unpack()):
                return self._unpacker.get()
            if (self._eof):
                return None

            chunk = self._data.read(self._chunk_size)
            self._eof = len(chunk) < self._chunk_size
            self._unpacker.extend(chunk)

    def close(self):
        self._data.close()

