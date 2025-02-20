from tkinter import *
import tkinter.messagebox as tkMessageBox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os
from message import Message
from RtpPacket import RtpPacket
import DNS

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
    INIT = 0
    READY = 1
    PLAYING = 2
    state = READY
    
    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3
    
    # Initiation..
    def __init__(self, master, serveraddr, serverport, rtpport, filename,sessionID, ipCliente):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
        self.createWidgets()
        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.cliente = ipCliente
        self.fileName = filename
        self.rtspSeq = 0
        self.sessionId = sessionID
        self.requestSent = -1
        self.teardownAcked = 0
        #self.connectToServer()
        self.frameNbr = 0
        self.paused = 0
        self.playMovie()
        self.error = 0
        
    def createWidgets(self):
        """Build GUI."""
        
        # Create Play button        
        self.start = Button(self.master, width=20, padx=3, pady=3)
        self.start["text"] = "Play"
        self.start["command"] = self.playMovie
        self.start.grid(row=1, column=1, padx=2, pady=2)
        
        # Create Pause button            
        self.pause = Button(self.master, width=20, padx=3, pady=3)
        self.pause["text"] = "Pause"
        self.pause["command"] = self.pauseMovie
        self.pause.grid(row=1, column=2, padx=2, pady=2)
        
        # Create Teardown button
        self.teardown = Button(self.master, width=20, padx=3, pady=3)
        self.teardown["text"] = "Teardown"
        self.teardown["command"] =  self.exitClient
        self.teardown.grid(row=1, column=3, padx=2, pady=2)
        
        # Create a label to display the movie
        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 
    

    def exitClient(self):
        """Teardown button handler."""
        m = Message(Message.END_STREAM, self.fileName,str(self.cliente),str(self.serverAddr))
        sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sckt.sendto(m.serialize(), (DNS.dnsClientToP[self.serverAddr],DNS.dnsNodesPorts[DNS.dnsNodes[self.serverAddr]]))

        try:
            msg, _ = sckt.recvfrom(2048)
            if msg:
                messageReceived = Message.deserialize(msg)
                if messageReceived.get_type() == Message.ACK_END_STREAM:
                    self.teardownAcked = 1

        except Exception as e:
            print(f"Erro: {e}")
                
        
        self.master.destroy() # Close the gui window
        os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete the cache image from video
        print("Stream encerrada com sucesso!")

    def pauseMovie(self):
        """Pause button handler."""
        if self.paused == 0:
            self.paused = 1
        else: 
            self.paused = 0
    
    def playMovie(self):
        """Play button handler."""
        if self.paused == 0 and self.state == self.READY:
            # Create a new thread to listen for RTP packets
            self.state = self.PLAYING
            threading.Thread(target=self.listenRtp).start()
        else:
            self.paused = 0
    
    def listenRtp(self):        
        """Listen for RTP packets."""
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.rtpSocket.bind(('0.0.0.0',self.rtpPort))
        print(f"listening on '0.0.0.0': {self.rtpPort}")
        while True:
            try:
                data = self.rtpSocket.recv(20480)
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)
                    currFrameNbr = rtpPacket.seqNum()
                    if currFrameNbr == 0:
                        self.frameNbr = -1

                    if currFrameNbr > self.frameNbr: # Discard the late packet
                        self.frameNbr = currFrameNbr
                        if not self.paused:
                            self.updateMovie(self.writeFrame(rtpPacket.getPayload()))

            except:
                
                # Upon receiving ACK for TEARDOWN request,
                # close the RTP socket
                if self.teardownAcked == 1:
                    #self.rtpSocket.shutdown(socket.SHUT_RDWR)
                    self.rtpSocket.close()
                    break
                    
    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        file = open(cachename, "wb")
        file.write(data)
        file.close()
        
        return cachename
    
    def updateMovie(self, imageFile):
        """Update the image file as video frame in the GUI."""
        try:
            photo = ImageTk.PhotoImage(Image.open(imageFile))
            self.label.configure(image = photo, height=288) 
            self.label.image = photo
        except:
            self.error += 1
        

    def handler(self):
        """Handler on explicitly closing the GUI window."""
        self.pauseMovie()
        if tkMessageBox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exitClient()
        else: # When the user presses cancel, resume playing.
            self.playMovie()

