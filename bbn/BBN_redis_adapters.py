
import os
import time
import asyncio
import websockets.client
import hl2ss
import hl2ss_redis

# ----------------------------- Settings ------------------------------------- #

# HoloLens address
HL_HOST = os.getenv("HOLOLENS_URL") or "192.168.1.7"

# Data server login
API_HOST = os.getenv('API_URL') or 'localhost:8000'

# ----------------------------- Streaming Basics ----------------------------- #

class StreamUpload:
    def __init__(self, host=HL_HOST, api_url=API_HOST):
        self.host = host
        self.api_url = api_url

    def __call__(self):
        while True:
            asyncio.run(self.forward_async())
            time.sleep(3)

    def create_client(self):
        raise NotImplementedError

    async def forward_async(self):
        extension_gop = hl2ss_redis._extension_gop(self.gop_size)
        
        try:
            async with websockets.client.connect(hl2ss_redis._get_stream_url_push(self.api_url, self.port), close_timeout=10, compression=None) as ws:
                with self.create_client() as client:                
                    while True: # TODO: STOP
                        data = hl2ss.pack_packet(client.get_next_packet())
                        extension_gop.extend(data)
                        await ws.send(bytes(data))
                        await asyncio.sleep(0)
        except Exception as e:
            print(e)

# ------------------------------- Side Cameras ------------------------------- #

class rm_vlc_upload(StreamUpload):
    mode     = hl2ss.StreamMode.MODE_1  # TODO: Config
    profile  = hl2ss.VideoProfile.H264_MAIN  # TODO: Config
    bitrate  = 1 * 1024 * 1024  # TODO: Config
    gop_size = hl2ss.get_gop_size(profile, hl2ss.Parameters_RM_VLC.FPS)
    
    def create_client(self):        
        return hl2ss.rx_rm_vlc(self.host, self.port, hl2ss.ChunkSize.RM_VLC, self.mode, self.profile, self.bitrate)
    
class rm_vlc_leftfront_upload(rm_vlc_upload):
    port = hl2ss.StreamPort.RM_VLC_LEFTFRONT

class rm_vlc_leftleft_upload(rm_vlc_upload):
    port = hl2ss.StreamPort.RM_VLC_LEFTLEFT

class rm_vlc_rightfront_upload(rm_vlc_upload):
    port = hl2ss.StreamPort.RM_VLC_RIGHTFRONT

class rm_vlc_rightright_upload(rm_vlc_upload):
    port = hl2ss.StreamPort.RM_VLC_RIGHTRIGHT

# ----------------------------------- Depth ---------------------------------- #

class rm_depth_ahat_upload(StreamUpload):
    port     = hl2ss.StreamPort.RM_DEPTH_AHAT
    mode     = hl2ss.StreamMode.MODE_1  # TODO: Config
    profile  = hl2ss.VideoProfile.H264_MAIN  # TODO: Config
    bitrate  = 8*1024*1024  # TODO: Config
    gop_size = hl2ss.get_gop_size(profile, hl2ss.Parameters_RM_DEPTH_AHAT.FPS)

    def create_client(self):
        return hl2ss.rx_rm_depth_ahat(self.host, self.port, hl2ss.ChunkSize.RM_DEPTH_AHAT, self.mode, self.profile, self.bitrate)

class rm_depth_longthrow_upload(StreamUpload):
    port       = hl2ss.StreamPort.RM_DEPTH_LONGTHROW
    mode       = hl2ss.StreamMode.MODE_1  # TODO: Config
    png_filter = hl2ss.PngFilterMode.Paeth  # TODO: Config
    gop_size   = 0

    def create_client(self):
        return hl2ss.rx_rm_depth_longthrow(self.host, self.port, hl2ss.ChunkSize.RM_DEPTH_LONGTHROW, self.mode, self.png_filter)

# ------------------------------------ IMU ----------------------------------- #

class rm_imu_upload(StreamUpload):
    mode     = hl2ss.StreamMode.MODE_1  # TODO: Config
    gop_size = 0

    def create_client(self):        
        return hl2ss.rx_rm_imu(self.host, self.port, self.chunk_size, self.mode)

class rm_imu_accelerometer_upload(rm_imu_upload):
    port       = hl2ss.StreamPort.RM_IMU_ACCELEROMETER
    chunk_size = hl2ss.ChunkSize.RM_IMU_ACCELEROMETER

class rm_imu_gyroscope_upload(rm_imu_upload):
    port       = hl2ss.StreamPort.RM_IMU_GYROSCOPE
    chunk_size = hl2ss.ChunkSize.RM_IMU_GYROSCOPE

class rm_imu_magnetometer_upload(rm_imu_upload):
    port       = hl2ss.StreamPort.RM_IMU_MAGNETOMETER
    chunk_size = hl2ss.ChunkSize.RM_IMU_MAGNETOMETER

# -------------------------------- Main Camera ------------------------------- #

class personal_video_upload(StreamUpload):
    port    = hl2ss.StreamPort.PERSONAL_VIDEO
    mode    = hl2ss.StreamMode.MODE_1 # TODO: Config
    bitrate = 5*1024*1024 # TODO: Config
    profile = hl2ss.VideoProfile.H264_MAIN # TODO: Config

    def __init__(self, *a, width=760, height=428, fps=15, **kw):
        self.width = width
        self.height = height
        self.fps = fps
        self.gop_size = hl2ss.get_gop_size(self.profile, self.fps)
        super().__init__(*a, **kw)

    def create_client(self):
        return hl2ss_redis._extension_rx_pv(self.host, self.port, hl2ss.ChunkSize.PERSONAL_VIDEO, self.mode, self.width, self.height, self.fps, self.profile, self.bitrate)

# -------------------------------- Microphone -------------------------------- #

class microphone_upload(StreamUpload):
    port     = hl2ss.StreamPort.MICROPHONE
    profile  = hl2ss.AudioProfile.AAC_24000 # TODO: Config
    gop_size = 0

    def create_client(self):
        return hl2ss.rx_microphone(self.host, self.port, hl2ss.ChunkSize.MICROPHONE, self.profile)

# -------------------------------- Spatial Input ----------------------------- #

class spatial_input_upload(StreamUpload):
    port     = hl2ss.StreamPort.SPATIAL_INPUT
    gop_size = 0

    def create_client(self):
        return hl2ss.rx_si(self.host, self.port, hl2ss.ChunkSize.SPATIAL_INPUT)

# ---------------------------------------------------------------------------- #

# HL2SS IPC ports not supported
# PV + RM Depth AHAT not working in current versions of the HoloLens OS
# RM Depth AHAT + RM Depth Longthrow not supported by the Research Mode API
port_manifest = [
    hl2ss.StreamPort.RM_VLC_LEFTFRONT,
    hl2ss.StreamPort.RM_VLC_LEFTLEFT,
    hl2ss.StreamPort.RM_VLC_RIGHTFRONT,
    hl2ss.StreamPort.RM_VLC_RIGHTRIGHT,
    hl2ss.StreamPort.RM_DEPTH_AHAT,
    hl2ss.StreamPort.RM_DEPTH_LONGTHROW,
    hl2ss.StreamPort.RM_IMU_ACCELEROMETER,
    hl2ss.StreamPort.RM_IMU_GYROSCOPE,
    hl2ss.StreamPort.RM_IMU_MAGNETOMETER,
    hl2ss.StreamPort.PERSONAL_VIDEO,
    hl2ss.StreamPort.MICROPHONE,
    hl2ss.StreamPort.SPATIAL_INPUT
]

if __name__ == '__main__':
    import fire
    fire.Fire({ hl2ss.get_port_name(port) : globals()[hl2ss.get_port_name(port) + '_upload'] for port in port_manifest})





        #'rm_vlc': RMVLCUpload,
        #'rm_depth_ahat' : RMDepthAHATUpload,
        #'rm_depth_longthrow': RMDepthLongthrowUpload,
        #'rm_imu_accelerometer': RMIMUAccelerometerUpload,
        #'rm_imu_gyroscope': RMIMUGyroscopeUpload,
        #'rm_imu_magnetometer': RMIMUMagnetometerUpload,
        #'personal_video': PVUpload,
        #'microphone' : MicrophoneUpload,
        #'spatial_input' : SIUpload

    #def __init__(self, host=HL_HOST, cam_idx=0, **kw):
    #    self.port = self.ports[cam_idx]        
    #    super().__init__(host, **kw)
    #ports = [
    #    hl2ss.StreamPort.RM_VLC_LEFTFRONT,
    #    hl2ss.StreamPort.RM_VLC_LEFTLEFT,        
    #    hl2ss.StreamPort.RM_VLC_RIGHTFRONT,
    #    hl2ss.StreamPort.RM_VLC_RIGHTRIGHT,
    #]

#port: int
#WSURL = f'ws://{API_HOST}'
#api_url=WSURL):
        #f'{self.api_url}/data/{self.stream_id}/push?header=0'
                    #self.stream_id = hl2ss.get_port_name(self.port)



#import cv2
#import struct
#import numpy as np
#from numpy.lib.recfunctions import structured_to_unstructured

#import BBN_redis_frame_load as holoframe

#print(            self.host, self.port,             hl2ss.ChunkSize.PERSONAL_VIDEO,             hl2ss.StreamMode.MODE_1,             self.width, self.height, self.fps,             self.profile, self.bitrate, 'encoded')
    # Encoded stream average bits per second
    # Must be > 0
    # Encoded stream average bits per second
    # Must be > 0
    #bitrate = 1 * 1024 * 1024
    #port = hl2ss.StreamPort.PERSONAL_VIDEO
    # Encoded stream average bits per second
    # Must be > 0
#port2stream_id = {port : hl2ss.get_port_name}




# stream name and type ID mappers
# port2stream_id = {
#     hl2ss.StreamPort.PERSONAL_VIDEO: hl2ss.get_port_name(),
#     hl2ss.StreamPort.RM_VLC_LEFTLEFT: 'gll',
#     hl2ss.StreamPort.RM_VLC_LEFTFRONT: 'glf',
#     hl2ss.StreamPort.RM_VLC_RIGHTFRONT: 'grf',
#     hl2ss.StreamPort.RM_VLC_RIGHTRIGHT: 'grr',
#     hl2ss.StreamPort.RM_DEPTH_LONGTHROW: 'depthlt',
#     hl2ss.StreamPort.RM_IMU_ACCELEROMETER: 'imuaccel',
#     hl2ss.StreamPort.RM_IMU_GYROSCOPE: 'imugyro',
#     hl2ss.StreamPort.RM_IMU_MAGNETOMETER: 'imumag',
# }

# port2sensor_type = {
#     hl2ss.StreamPort.PERSONAL_VIDEO: holoframe.SensorType.PV,
#     hl2ss.StreamPort.RM_VLC_LEFTLEFT: holoframe.SensorType.GLL,
#     hl2ss.StreamPort.RM_VLC_LEFTFRONT: holoframe.SensorType.GLF,
#     hl2ss.StreamPort.RM_VLC_RIGHTFRONT: holoframe.SensorType.GRF,
#     hl2ss.StreamPort.RM_VLC_RIGHTRIGHT: holoframe.SensorType.GRR,
#     hl2ss.StreamPort.RM_DEPTH_LONGTHROW: holoframe.SensorType.DepthLT,
#     hl2ss.StreamPort.RM_IMU_ACCELEROMETER: holoframe.SensorType.Accel,
#     hl2ss.StreamPort.RM_IMU_GYROSCOPE: holoframe.SensorType.Gyro,
#     hl2ss.StreamPort.RM_IMU_MAGNETOMETER: holoframe.SensorType.Mag,
# }


        #hl2ss.start_subsystem_pv(self.host, self.port)
    #def destroy_client(self):        
        #hl2ss.stop_subsystem_pv(self.host, self.port)



#self.client.close()

            #self.client.open()
        #return 2*self.client.framerate
        #self.sensor_type = port2sensor_type[self.port]
        #port2stream_id[self.port]

    # def adapt_data(self, data) -> bytes:
    #     '''Pack image as JPEG with header.'''
    #     img_str = cv2.imencode('.jpg', data.payload)[1].tobytes()
    #     pose_info = (
    #         data.pose.astype('f').tobytes() + 
    #         data.focal_length.astype('f').tobytes() + 
    #         data.principal_point.astype('f').tobytes())
    #     nyu_header = struct.pack(
    #         "<BBQIIII", self.header_version, self.sensor_type, 
    #         data.timestamp, data.payload.shape[1], data.payload.shape[0], 
    #         len(img_str), len(pose_info))
    #     return nyu_header + img_str + pose_info

#aliased_index = 0
           


            
    # def adapt_data(self, data) -> bytes:
    #     '''Pack image as JPEG with header.'''
    #     img_str = cv2.imencode('.jpg', data.payload, [int(cv2.IMWRITE_JPEG_QUALITY), 70])[1].tobytes()
    #     pose_info = data.pose.astype('f').tobytes()
    #     nyu_header = struct.pack(
    #         "<BBQIIII", self.header_version, self.sensor_type, 
    #         data.timestamp, data.payload.shape[1], data.payload.shape[0], 
    #         len(img_str), len(pose_info))
    #     return nyu_header + img_str + pose_info


    # def adapt_data(self, data) -> bytes:
    #     depth_img_str = data.payload.depth.tobytes()
    #     ab_img_str = cv2.imencode('.jpg', data.payload.ab, [int(cv2.IMWRITE_JPEG_QUALITY), 70])[1].tobytes()
    #     pose_info = data.pose.astype('f').tobytes()
    #     nyu_header = struct.pack(
    #         "<BBQIIII", self.header_version, self.sensor_type, data.timestamp, 
    #         data.payload.depth.shape[1], data.payload.depth.shape[0], 
    #         len(depth_img_str), len(pose_info)+len(ab_img_str))
    #     return nyu_header + depth_img_str + pose_info + ab_img_str

    # def adapt_data(self, data) -> bytes:
    #     imu_array = np.frombuffer(data.payload, dtype = ("u8,u8,f4,f4,f4"))
    #     imu_data = structured_to_unstructured(imu_array[['f2', 'f3', 'f4']]).tobytes()
    #     imu_timestamps = imu_array['f0'].tobytes()
    #     nyu_header = struct.pack(
    #         "<BBQIIII", self.header_version, self.sensor_type, 
    #         data.timestamp, 3, imu_array.shape[0], 4, len(imu_timestamps))
    #     return nyu_header + imu_data + imu_timestamps


    

#------------------------------------------------------------------------------
# Network Bridge (HL2SS-Websockets)
#------------------------------------------------------------------------------
'''
async def redis_bridge(redis_host, hl2_rx, gop_size):
    aliased_index = 0
    url = get_stream_url_push(redis_host, hl2_rx.port)
    async with websockets.client.connect(url) as ws:
        hl2_rx.open()

        try:
            while (True): # TODO: STOP
                data = hl2ss.pack_packet(hl2_rx.get_next_packet())
                if (gop_size > 0):
                    data.extend(struct.pack('<B', aliased_index))
                    aliased_index = (aliased_index + 1) % gop_size
                await ws.send(bytes(data))
                await asyncio.sleep(0)
        finally:
            hl2_rx.close()
'''



    #research_mode = False
    # NYU Header Version
    #header_version = 2