class VideoStream:
    def __init__(self, filename):
        self.frameList = []
        self.filename = filename
        try:
            self.file = open(filename, 'rb')
        except:
            raise IOError
        self.frameNum = 0
        self.totalSize = 0
        
    def nextFrame(self):
        """Get next frame."""
        #dataTotal = self.file.read()
        data = self.file.read(5) # Get the framelength from the first 5 bits
        if data: 
            framelength = int(data)
                            
            # Read the current frame
            data = self.file.read(framelength)
            self.frameList.append(data) # Add the frame to the list of frames
            self.frameNum += 1
            if self.frameNum > 255:
                loopIndex = self.frameNum % 256
                data = self.frameList[loopIndex]
        else:                
            loopIndex = self.frameNum % 256
            data = self.frameList[loopIndex]
            self.frameNum += 1
        return data
   
    def frameNbr(self):
        """Get frame number."""
        return self.frameNum
	
	