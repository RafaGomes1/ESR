import random
import pickle


#(protocolo, msg, origem, destino)
class Message:
    START_SERVICE = 1
    REQUEST_NEIGHBORS = 2
    SEND_NEIGHBORS = 3
    REQUEST_STREAM = 4
    SEND_STREAM = 5
    NOTIFY_NEIGHBOR = 6
    FLOODING = 7
    CHECK_VIDEOS = 8
    START_VIDEO = 9
    METRICS = 10
    END_STREAM = 11
    ACK_END_STREAM = 12

    def __init__(self, type:int, data="", sender:str="", dest:str=""):
        self.type = type
        self.id:int = random.randint(0,100000)
        self.data = data
        self.sender = sender
        self.dest = dest
        self.timestamp = None #(Caso queiramos saber o tempo que demorou a ser entregue)

    def printmsg(self):
        return (f"Type: {self.type}\n"
                f"ID: {self.id}\n"
                f"Data: {self.data}\n"
                f"Sender: {self.sender}\n"
                f"Destination: {self.dest}\n"
                f"Timestamp: {self.timestamp}")
    
    def get_id(self):
        return self.id
    
    def get_type(self):
        return self.type
        
    def get_sender(self):
        return self.sender

    def get_dest(self):
        return self.dest
        
    def get_data(self):
        return self.data
        
    def set_data(self, data):
        self.data = data

    def serialize(self):
        return pickle.dumps(self)

    def deserialize(bytes):
        return pickle.loads(bytes)

    def get_timestamp(self):
        return self.timestamp

    def set_timestamp(self, time):
        self.timestamp = time