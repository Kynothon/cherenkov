#! /usr/bin/env python3

import sys
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
from gi.repository import GLib, GObject, Gst

class FTL_Media:
    def __init__(self):
        Gst.init(None)
        self.loop = GLib.MainLoop()
        self.pipe = Gst.Pipeline()

    def addElement(self, element_name, properties = {}):
        elm = Gst.ElementFactory.make(element_name)
        for prop, value in properties.items():
            elm.set_property(prop, value)
        self.pipe.add(elm)
        return elm

    def setup(self):

        videocaps = Gst.Caps.from_string("application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264, payload=(int)96, width=(string)1280, height=(string)720")
        audiocaps = Gst.Caps.from_string("application/x-rtp, media=audio, clock-rate=48000, encoding-name=OPUS, payload=97")

        self.udpsrc = self.addElement('udpsrc', {'port': 8309}) #, 'caps': videocaps})
        self.tee = self.addElement('tee')

        self.vfilter = self.addElement('capsfilter', {'caps': videocaps})
        self.vrtpbin = self.addElement('rtpbin')
        self.rtph264depay = self.addElement('rtph264depay')
        self.avdec_h264 = self.addElement('avdec_h264')
        self.xvimagesink = self.addElement('xvimagesink')

        self.afilter = self.addElement('capsfilter', {'caps': audiocaps})
        self.artpbin = self.addElement('rtpbin')
        self.rtpopusdepay = self.addElement('rtpopusdepay')
       	self.opusdec = self.addElement('opusdec')
       	self.audioconvert = self.addElement('audioconvert')
       	self.audioresample = self.addElement('audioresample')
       	self.autoaudiosink = self.addElement('autoaudiosink')    

        self.udpsrc.link(self.tee)

        tee_src_pad_template = self.tee.get_pad_template("src_%u")
        tee_video_pad = self.tee.request_pad(tee_src_pad_template, None, None)
        filter_pad = self.vfilter.get_static_pad("sink")
        tee_video_pad.link(filter_pad)

        tee_src_pad_template = self.tee.get_pad_template("src_%u")
        tee_audio_pad = self.tee.request_pad(tee_src_pad_template, None, None)
        filter_pad = self.afilter.get_static_pad("sink")
        tee_audio_pad.link(filter_pad)

        self.vfilter.link(self.vrtpbin)
        self.vrtpbin.link(self.rtph264depay)
        self.rtph264depay.link(self.avdec_h264)
        self.avdec_h264.link(self.xvimagesink)

        self.afilter.link(self.artpbin)
        self.artpbin.link(self.rtpopusdepay)
        self.rtpopusdepay.link(self.opusdec)
        self.opusdec.link(self.audioconvert)
        self.audioconvert.link(self.audioresample)
        self.audioresample.link(self.autoaudiosink)

        self.vrtpbin.connect('pad-added', self.on_pad_added_v)
        self.artpbin.connect('pad-added', self.on_pad_added_a)

        self.bus = self.pipe.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect ("message", self.bus_call, self.loop)

    def run(self):
        self.pipe.set_state(Gst.State.PLAYING)
        try:
            self.loop.run()
        except:
            print("Unexpected error:", sys.exc_info())
            pass
        print("Set State: NULL")
        self.pipe.set_state(Gst.State.NULL)
    
    def bus_call(self, bus, message, loop):
        t = message.type
        if t == Gst.MessageType.EOS:
            sys.stdout.write("End-of-stream\n")
            loop.quit()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            sys.stderr.write("Error: %s: %s\n" % (err, debug))
            loop.quit()
        return True

    def on_pad_added_v(self, element, pad):
        pad.link(self.rtph264depay.get_static_pad('sink'))

    def on_pad_added_a(self, element, pad):
        pad.link(self.rtpopusdepay.get_static_pad('sink'))


def main(args):
    print("Cherenkov Media")
    ftl_media = FTL_Media()
    ftl_media.setup()
    ftl_media.run()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
