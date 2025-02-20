import socket
import threading
import sys
import ast
from message import Message
import DNS
from RtpPacket import RtpPacket

class ResponseServer:
    def __init__(self,host:int, vizinhos_ativos:list,videosServer:dict):
        self.host = host
        self.vizinhos_ativos = {DNS.dnsNodesInverse[elem]: False for elem in vizinhos_ativos}
        self.tabela_end = {}
        self.videosServer = videosServer
        self.saltos = {}


    def get_nextN_from_TE(self, dest):
        return self.tabela_end[dest]

    def get_vizinhos(self):
        return self.vizinhos_ativos.items()

    def atualizarManualTE(self, origem ,nodoAnterior):
        self.tabela_end[origem] = nodoAnterior

    #atualiza a tabela de endereçamento
    def atualizarTE(self, origem ,nodoAnterior , dest):
        if origem not in self.tabela_end or self.tabela_end[origem] == -1:
            self.tabela_end[origem] = nodoAnterior
        if nodoAnterior not in self.tabela_end:
            self.tabela_end[nodoAnterior] = nodoAnterior
        if dest not in self.tabela_end:
            self.tabela_end[dest] = -1

        #print("TABELA DE ENDEREÇAMENTO")
        #print(self.tabela_end)
    def printCenas(self):
        for video, details in self.videosServer.items():
            print(f"Video: {video}")
            print(f"  State: {details['state']}")
            print(f"  Port: {details['port']}")
            print(f"  Nodos: {details['nodos']}")
            print('-' * 40)  # Separator line for better readability

def makeRtp(payload, frameNbr):
		"""RTP-packetize the video data."""
		version = 2
		padding = 0
		extension = 0
		cc = 0
		marker = 0
		pt = 26 # MJPEG type
		seqnum = frameNbr
		ssrc = 0 
		
		rtpPacket = RtpPacket()
		
		rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)
		
		return rtpPacket.getPacket()

def sendRtp(servidor,video, addr):
    print(f"vai iniciar o send, video: {video} ")
    rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while(True):
        servidor.videosServer[video]['event'].wait(0.05)
        if servidor.videosServer[video]['event'].isSet(): 
            rtpSocket.close()
            print("Fechou Socket")
            break 
        
        data = servidor.videosServer[video]['objectVideoStream'].nextFrame()
        if data: 

            frameNumber = servidor.videosServer[video]['objectVideoStream'].frameNbr()

            if frameNumber > 255:
                frameNumber = frameNumber % 256
            try:
                for nodo in servidor.videosServer[video]['nodos']:
                    rtpSocket.sendto(makeRtp(data, frameNumber),(nodo,servidor.videosServer[video]['port']))
            except Exception as e:
                print(f"Connection Error: {e}")

def receive_messages(client_socket, addr, servidor):
    try:
        while (True):
            message = client_socket.recv(2048)
            messageReceived = Message.deserialize(message)
            origem = messageReceived.sender
            destino = messageReceived.dest
            print(messageReceived.printmsg())
            servidor.atualizarTE(origem, addr, destino)
            if destino == servidor.host:

                if messageReceived.get_type() == Message.FLOODING:
                    print("got a flooding from:{}".format(origem))
                    if (origem not in servidor.saltos or servidor.saltos[origem] > len(messageReceived.get_data())):
                        servidor.saltos[origem] = len(messageReceived.get_data())
                        servidor.atualizarManualTE(origem, addr)

                    if(addr == servidor.get_nextN_from_TE(origem)):
                        m = Message(Message.FLOODING, "1", servidor.host, origem) #main node
                    else:
                        m = Message(Message.FLOODING, "0", servidor.host, origem) #others
                    client_socket.send(m.serialize())
                    
                elif messageReceived.get_type() == Message.REQUEST_STREAM:
                    video = messageReceived.get_data()

                    if video in servidor.videosServer:
                        print("vai iniciar o streaming")
                        servidor.videosServer[video]['state'] = 1
                        servidor.videosServer[video]['nodos'].append(addr[0]) 
                        #inserir streaming
                        servidor.videosServer[video]['event'] = threading.Event()
                        worker_thread = threading.Thread(target=sendRtp,args=(servidor,video,addr))
                        worker_thread.daemon = True
                        worker_thread.start()

                        msg = Message(Message.START_VIDEO, (video,servidor.videosServer[video]['port']), str(DNS.dnsNodesInverse['s1']), str(origem))
                        client_socket.send(msg.serialize())
                    else:
                        print("Not implemented yet: No video!")

                elif messageReceived.get_type() == Message.END_STREAM:
                    video = messageReceived.get_data()
                    servidor.videosServer[video]['state'] -= 1
                    servidor.videosServer[video]['nodos'].remove(addr[0])
                    if servidor.videosServer[video]['state'] == 0:
                        servidor.videosServer[video]['event'].set()
                    msg = Message(Message.ACK_END_STREAM, video, str(DNS.dnsNodesInverse['s1']), str(origem))
                    client_socket.send(msg.serialize())
               

    except Exception as e:
        print("Error receiving message from {}: {}".format(addr, e))
        print("(nodo foi à vida)")
        servidor.vizinhos_ativos[addr] = False
        for dest,next in servidor.tabela_end.items():
            if next == addr:
                servidor.tabela_end[dest] = -1
        servidor.saltos = {}
    finally:
        client_socket.close()



def serverDeResposta(port, messageList, videosServer):
    servidor = ResponseServer(DNS.dnsNodesInverse[messageList[0]],messageList[1:],videosServer)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0',port))
    server_socket.listen(1)
    print("Server listening on {}:{}".format('0.0.0.0', port))

    while(True):
        try:
            client_socket, addr = server_socket.accept()
            print("Connection established with {}".format(addr))

            #falta uma thread para receber de cada addr msgs e processa-las
            threading.Thread(target=receive_messages, args=(client_socket, addr, servidor),daemon=True).start()

        except Exception as e:
            print("Unexpected error with cliente {}: {}".format(addr,e))
