import picamera2 #camera module for RPi camera
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, MJPEGEncoder
from picamera2.outputs import FileOutput, CircularOutput
import io

import subprocess
from flask import Flask, render_template, Response
from flask_restful import Resource, Api, reqparse, abort
import atexit
from datetime import datetime
from threading import Condition
import time
import os

from libcamera import Transform

app = Flask(__name__, template_folder='template', static_url_path='/static')
api = Api(app)

encoder = H264Encoder()
output = CircularOutput()

class Camera:
    def __init__(self):
        self.camera = picamera2.Picamera2()
        self.camera.configure(self.camera.create_video_configuration(main={"size": (640, 480)}))
        self.still_config = self.camera.create_still_configuration()
        self.encoder = MJPEGEncoder(10000000)
        self.streamOut = StreamingOutput()
        self.streamOut2 = FileOutput(self.streamOut)
        self.encoder.output = [self.streamOut2]

        self.camera.start_encoder(self.encoder) 
        self.camera.start_recording(encoder, output) 

    def get_frame(self):
        self.camera.start()
        with self.streamOut.condition:
            self.streamOut.condition.wait()
            self.frame = self.streamOut.frame
        return self.frame
    
    def VideoSnap(self):
        print("Snap")
        timestamp = datetime.now().isoformat("_","seconds")
        print(timestamp)
        self.still_config = self.camera.create_still_configuration()
        self.file_output = "/home/allzero22/Webserver/webcam/static/pictures/snap_%s.jpg" % timestamp
        time.sleep(1)
        self.job = self.camera.switch_mode_and_capture_file(self.still_config, self.file_output, wait=False)
        self.metadata = self.camera.wait(self.job)
    
class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

#defines the function that generates our frames
camera = Camera()

#capture_config = camera.create_still_configuration()
def genFrames():
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

            
#defines the route that will access the video feed and call the feed function
class VideoFeed(Resource):
    def get(self):
        return Response(genFrames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
    
# Timestamp
def show_time():
    ''' Show current date time in text format '''
    rightNow = datetime.now()
    print(rightNow)
    currentTime = rightNow.strftime("%d-%m-%Y_%H:%M:%S")
    print("date and time =", currentTime)
        
    return currentTime

@app.route('/')
def index():
    """Video streaming home page."""
    
    return render_template('index.html')

@app.route('/home', methods = ['GET', 'POST'])
def home_func():
    """Video streaming home page."""
    
    return render_template("index.html")

@app.route('/info.html')
def info():
    """Info Pane"""
    
    return render_template('info.html')

@app.route('/startRec.html')
def startRec():
    """Start Recording Pane"""
    print("Video Record")
    basename = show_time()
    directory = basename
    parent_dir = "/home/allzero22/Webserver/webcam/static/video/"
    output.fileoutput = (parent_dir + "Bird_%s.h264"  %directory)
    output.start()
    
    return render_template('startRec.html')

@app.route('/stopRec.html')
def stopRec():
    """Stop Recording Pane"""
    print("Video Stop")
    output.stop()
    
    return render_template('stopRec.html')

@app.route('/srecord.html')
def srecord():
    """Sound Record Pane"""
    print("Recording Sound")
    timestamp = datetime.now().isoformat("_","seconds")
    print(timestamp)
    subprocess.Popen('arecord -D dmic_sv -d 30 -f S32_LE /home/allzero22/Webserver/webcam/static/sound/birdcam_$(date "+%b-%d-%y-%I:%M:%S-%p").wav -c 2', shell=True)
    
    return render_template('srecord.html')

@app.route('/snap.html')
def snap():
    """Snap Pane"""
    print("Taking a photo")
    camera.VideoSnap()
    
    return render_template('snap.html')

api.add_resource(VideoFeed, '/cam')


if __name__ == '__main__':
    app.run(debug = False, host = '0.0.0.0', port=5000)


