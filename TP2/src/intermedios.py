import sys
import socket
import datetime
import threading
import time
from RtpPacket import RtpPacket
from message import Message
import DNS
import random
#no serverIntermedios conectar-se a novas ligações caso estas estivessem inativas
#no inicianodo iniciar o flooding

#depois

#no serverIntermedios iniciar linhas na tabela de endereçamento caso receba mensagens novas
#no visinhos enviar msg pelo comaninho indicado na tabela(se não existe indicará broadcast)

# {}
# {nome do video: [nope,porta,[(c1,addr)]]} pergunta ao server
# {nome do video: [ready,porta,[c1]} recebe do server a porta
# {nome do video: [ready,porta,[c1,c2]]} recebe novos pedidos
# {nome do video: [ready,porta,[c2]]} acabam pedidos
# {nome do video: [nope,porta,[]]} acabam TODOS os pedidos
#
# 0 - not Ready
# 1 - Ready

class Intermedio:
    def __init__(self,host:int, vizinhos_ativos:list, videos_portas:list):
        self.host = host
        self.vizinhos_ativos = {DNS.dnsNodesInverse[elem]: True for elem in vizinhos_ativos}
        self.videos_portas = {video : porta for (video,porta) in videos_portas}
        self.queue = {DNS.dnsNodesInverse[elem]: [] for elem in vizinhos_ativos}
        self.tabela_end ={}
        self.videos = {}
        self.udp_socket = None
        self.queueEndVideo = {}

    def printAtivos(self):
        lista = []
        for elem,value in self.vizinhos_ativos.items():
            lista += [elem]
        return lista

    def get_vizinhos(self):
        return self.vizinhos_ativos.items()
    
    def todosInterAtivos(self):
        for ipVizinho, isActive in self.vizinhos_ativos.items():
            if not isActive and DNS.dnsNodes[ipVizinho][0] != 'c':
                return False
        return True
    def broadcast(self,msg,anterior):
        for ipVizinho, isActive in self.vizinhos_ativos.items():
            if isActive and DNS.dnsNodes[ipVizinho][0]!= 'c' and ipVizinho != anterior:
                #print("deveriam ser diferentes: ipVizinho<-/>anterior{}{}".format(ipVizinho,anterior))
                self.queue[ipVizinho].append(msg)

    def broadcast2(self,msg,destino):
        #msg.data = lista de nodos já visitados
        for ipVizinho, isActive in self.vizinhos_ativos.items():
            if isActive and DNS.dnsNodes[ipVizinho][0]!= 'c' and DNS.dnsNodes[ipVizinho][0]!= 'p' and ipVizinho not in msg.get_data():
                self.queue[ipVizinho].append(msg)

    #adiciona a queue a msg com fim no dest
    def addToQueue(self,msg,nodoAnterior,dest):
        if dest in self.tabela_end:
            print("Dest:{}".format(dest))
            if self.tabela_end[dest] !=-1:
                self.queue[self.tabela_end[dest]].append(msg)
            else: 
                self.broadcast(msg, nodoAnterior)         
        else:
            self.tabela_end[dest] = -1
            self.broadcast(msg, nodoAnterior)
    #atualiza a tabela de endereçamento
    def atualizarTE(self, origem ,nodoAnterior , dest):
        if origem not in self.tabela_end or self.tabela_end[origem] == -1:
            self.tabela_end[origem] = nodoAnterior
        if nodoAnterior not in self.tabela_end:
            self.tabela_end[nodoAnterior] = nodoAnterior
        if dest not in self.tabela_end:
            self.tabela_end[dest] = -1
    
    def atualizarManualTE(self, origem ,nodoAnterior):
        self.tabela_end[origem] = nodoAnterior
            


    def awaiting_notify(self):
        #Fica a espera de mensagens de notificacao
        print("A ESPERA DE NOTIFICACAO!")

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind(('', DNS.NOTIFY_PORT))
        while True:
            try:
                dados, addr = server_socket.recvfrom(2048)
                messageReceived = Message.deserialize(dados)

                print("Starting flooding..OF NOTIFY.")
                floodmsg = Message(Message.FLOODING, [self.host], self.host, '10.0.0.10')
                time.sleep(random.randint(0,3))
                self.broadcast(floodmsg,self.host)


                print("Notificacao recebida de {}: {}".format(addr[0],messageReceived.get_data()))
            except Exception as e:
                print(f"ERRO NO AWAITING_NOTIFY: {e}")


def vizinhos(vizinhoIP:int,nodo:Intermedio):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    portaVizinho = DNS.dnsNodesPorts[DNS.dnsNodes[vizinhoIP]]
    try:
        # print("Connecting to {}:{}".format(vizinhoIP, portaVizinho))
        client_socket.connect((vizinhoIP, portaVizinho))
        print("Connected to node {} - {}:{}".format(DNS.dnsNodes[vizinhoIP],vizinhoIP, portaVizinho))
        
        if portaVizinho != DNS.dnsNodesPorts['s1']:
        # ficar a espera de receber mensagens, e quando recebe envia para o proximo vizinho
            while (True):
                if not any(nodo.queue[vizinhoIP]):
                    time.sleep(5)
                else:
                    while(any(nodo.queue[vizinhoIP])):
                        m = nodo.queue[vizinhoIP].pop()
                        client_socket.send(m.serialize())
                        print("Message sent from {} to {}".format(DNS.dnsNodes[nodo.host], DNS.dnsNodes[vizinhoIP]))
            print("WHILE ACABOU INESPERADAMENTE!")
        else:
        # ficar a espera de receber mensagens, e quando recebe envia para o proximo vizinho
            while (True):
                if not any(nodo.queue[vizinhoIP]):
                    time.sleep(5)
                else:
                    while(any(nodo.queue[vizinhoIP])):
                        m = nodo.queue[vizinhoIP].pop()
                        client_socket.send(m.serialize()) 
                        message = client_socket.recv(2048)
                        messageReceived = Message.deserialize(message)
                        print(messageReceived.printmsg())
                        origem = messageReceived.sender
                        destino = messageReceived.dest
                        nodo.atualizarTE(origem, origem, destino)
                        if messageReceived.get_type() == Message.FLOODING:
                            print("wrong flood")
                        if messageReceived.get_type() == Message.START_VIDEO:
                            print(f"Streaming {messageReceived.get_data()[0]} at port{messageReceived.get_data()[1]}")
                            nodo.videos[messageReceived.get_data()[0]]['state'] += 1
                            #nodo.videos[messageReceived.get_data()[0]]['port'] = messageReceived.get_data()[1]
#                            print("111111111111111111111111111111111111111111111111111111111111")
                            nodo.addToQueue(messageReceived, origem, destino) 
                        elif messageReceived.get_type() == Message.ACK_END_STREAM:
                            nodo.videos[messageReceived.get_data()]['state'] = 0
                            nodo.videos[messageReceived.get_data()]['nodos'] = []
                            nodo.addToQueue(messageReceived, origem, destino) 
                        else:
                            nodo.addToQueue(messageReceived, origem, destino) 
                        print("MENSAGEM ADICIONADA A QUEUE")

    except Exception as e:
        #print("Error connecting to {}:{} - {}".format('0.0.0.0', portaVizinho, e))
        nodo.vizinhos_ativos[vizinhoIP] = False


def sendToClient(msgData, nodo):
    print(nodo.videos[msgData[0]])
    destinoComplexo = nodo.videos[msgData[0]]['nodos'][0][1]
    destino = nodo.videos[msgData[0]]['nodos'][0][0]
    msg = Message(Message.START_VIDEO, msgData, str(nodo.host), str(destino))
    nodo.udp_socket.sendto(msg.serialize(), destinoComplexo)
    print("Message video sent from {} to {}".format(nodo.host,destino))

def passaStreamParaAFrente(nodos,messageReceived):
    rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rtpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    rtpSocket.bind(('0.0.0.0', nodos.videos[messageReceived.get_data()]['port']))
    print(f"intermedio iniciou thread : {'0.0.0.0':{nodos.videos[messageReceived.get_data()]['port']}}")

    while True:
        try:
            data = rtpSocket.recv(20480)
            #print(data)
            if data:
                if nodos.videos[messageReceived.get_data()]['nodos'] is []:
                    rtpSocket.close()
                    print("a lista de nodos está vazia")
                    break
                    
                else:
                    for nodo in nodos.videos[messageReceived.get_data()]['nodos']:
                        sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        if DNS.dnsNodes[nodos.host][0] == 'p':
                            sckt.sendto(data, (nodo[0],nodos.videos_portas[messageReceived.get_data()]))
                        else:
                            sckt.sendto(data, (DNS.dnsNodesInverse[nodo], nodos.videos_portas[messageReceived.get_data()]))
            else:
                print("não existe data?")
        except:
            print("socket de receção a fechar")
            rtpSocket.close()
            break

def comsWithClient(nodos, server_socket):
    while(True):
        try:
            message, addr = server_socket.recvfrom(1024)
            name = DNS.dnsNodes.get(addr[0], "Unknown")
            messageReceived = Message.deserialize(message)
            origem = messageReceived.sender
            destino = messageReceived.dest
            nodos.atualizarTE(origem, addr, destino)
            
            if destino != nodos.host:
                nodos.addToQueue(messageReceived, addr, destino)
            else:
                if messageReceived.get_type() == Message.METRICS:
                    #quero todos os videos com "state" > 0 aqui
                    nomes = []
                    for nome, data in nodos.videos.items():
                        if data['state'] > 0:
                            nomes += [nome]
                    msg = Message(Message.METRICS, nomes, str(destino), str(origem))
                    msg.set_timestamp(messageReceived.get_timestamp())
                    server_socket.sendto(msg.serialize(), addr)
                    #print("Message sent from {} to {}".format(destino, origem))

                elif messageReceived.get_type() == Message.REQUEST_STREAM:
                    if messageReceived.get_data() in nodos.videos and nodos.videos[messageReceived.get_data()]['state'] > 0:
                        nodos.videos[messageReceived.get_data()]['nodos'] += [[origem,addr]]
                        nodos.videos[messageReceived.get_data()]['state'] += 1
                        msg = Message(Message.START_VIDEO, (messageReceived.get_data(),nodos.videos[messageReceived.get_data()]['port']), str(destino), str(origem))
                        server_socket.sendto(msg.serialize(), addr)
                        print("Message sent from {} to {}".format(destino, origem))
                    else:
                        nodos.videos[messageReceived.get_data()] = {'state' : 0,'port' : nodos.videos_portas[messageReceived.get_data()],'nodos' : [[origem,addr]]}
                        
                        #iniciar socket udp para receber
                        
                        #iniciar listener nessa socket
                        listener_thread = threading.Thread(target=passaStreamParaAFrente, args=(nodos,messageReceived))
                        listener_thread.daemon = True
                        listener_thread.start()
                        msg = Message(Message.REQUEST_STREAM, messageReceived.get_data(), str(destino), str(DNS.dnsNodesInverse['s1']))
                        nodos.addToQueue(msg, destino, DNS.dnsNodesInverse['s1'])
                    
                elif messageReceived.get_type() == Message.END_STREAM:
                    if nodos.videos[messageReceived.get_data()]['state'] == 1:#direita
                        nodos.queueEndVideo[messageReceived.get_data()] = addr
                        msg = Message(Message.END_STREAM, messageReceived.get_data(), str(destino), str(DNS.dnsNodesInverse['s1']))#manda para o servidor mas os proximos só passam se n tiverem mais nenhum
                        nodos.addToQueue(msg, destino, DNS.dnsNodesInverse['s1'])

                    else:#esquerda
                        for ip,tup in nodos.videos[messageReceived.get_data()]['nodos']:
                            if ip == origem:
                                lixo = [ip,tup]
                        nodos.videos[messageReceived.get_data()]['nodos'].remove(lixo)
                        nodos.videos[messageReceived.get_data()]['state'] -= 1
                        msg = Message(Message.ACK_END_STREAM, messageReceived.get_data(), str(addr[0]), str(origem))
                        server_socket.sendto(msg.serialize(), addr)

                ### aqui adiciona-se o codigo de processamento dos inputs conforme a flag
        except Exception as e:
            print("Error receiving message on comswithclient: {}".format(e))
    
def serverIntermedios(host, port, nodos):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("Server listening on {}:{}".format(host, port))
    server_socket.bind((host, port))
    server_socket.listen(1)
    
    if DNS.dnsNodes[nodos.host][0] == 'p':
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind((host, port))
        nodos.udp_socket = udp_socket
        udp_thread = threading.Thread(target=comsWithClient, args=(nodos, udp_socket))
        udp_thread.daemon = True
        udp_thread.start()
    
    while(True):
        try:
            client_socket, addr = server_socket.accept()
            print("Connection established with {}".format(addr))
            name = DNS.dnsNodes[addr[0]] 

            if nodos.vizinhos_ativos[DNS.dnsNodesInverse[name]] == False:
                vizinho_thread = threading.Thread(target=vizinhos, args=(DNS.dnsNodesInverse[name],nodos))
                vizinho_thread.daemon = True
                vizinho_thread.start()
                nodos.vizinhos_ativos[DNS.dnsNodesInverse[name]] = True
            #falta uma thread para receber de cada addr msgs e processa-las
            threading.Thread(target=receive_messages, args=(client_socket,name, DNS.dnsNodesInverse[name], nodos), daemon=True).start()

        except Exception as e:
            print("Unexpected error with cliente {}: {}".format(addr,e))
            
def receive_messages(client_socket,name, addr, nodo):
    try:
        while (True):
            message = client_socket.recv(2048)
            print("received a message from {}".format(name))
            messageReceived = Message.deserialize(message)
            origem = messageReceived.sender
            destino = messageReceived.dest
            nodo.atualizarTE(origem, addr, destino)
            
            if destino != nodo.host:
                if messageReceived.get_type() == Message.REQUEST_STREAM:
                    #está a ser pedido um video já em streaming
                    if messageReceived.get_data() in nodo.videos and nodo.videos[messageReceived.get_data()]['state'] > 0:
                        nodo.videos[messageReceived.get_data()]['state'] += 1
                        nodo.videos[messageReceived.get_data()]['nodos'] += [DNS.dnsNodes[addr]]
                        msg = Message(Message.START_VIDEO, (messageReceived.get_data(),nodo.videos[messageReceived.get_data()]['port']), str(nodo.host), str(origem))
                        nodo.addToQueue(msg, nodo.host, origem)
                    #está a pedir um video que já existe mas não está a em stream
                    #ou
                    #está a ser pedido um video novo
                    else:
                        nodo.videos[messageReceived.get_data()] = {'state' : 0,'port' : nodo.videos_portas[messageReceived.get_data()],'nodos' : [DNS.dnsNodes[addr]]}
                        listener_thread = threading.Thread(target=passaStreamParaAFrente, args=(nodo,messageReceived))
                        listener_thread.daemon = True
                        listener_thread.start()
                        nodo.addToQueue(messageReceived, addr, destino)

                elif messageReceived.get_type() == Message.ACK_END_STREAM:
                    nodo.videos[messageReceived.get_data()]['nodos'] = []
                    nodo.videos[messageReceived.get_data()]['state'] = 0
                    nodo.addToQueue(messageReceived, addr[0], destino)

                elif messageReceived.get_type() == Message.END_STREAM:
                    if nodo.videos[messageReceived.get_data()]['state'] == 1:
                        nodo.addToQueue(messageReceived, addr[0], DNS.dnsNodesInverse['s1'])
                    else:
                        nodo.videos[messageReceived.get_data()]['nodos'].remove(DNS.dnsNodes[addr])
                        nodo.videos[messageReceived.get_data()]['state'] -= 1 
                        msg = Message(Message.ACK_END_STREAM, messageReceived.get_data(), str(nodo.host), str(origem))
                        nodo.addToQueue(msg, addr[0], origem)

                elif messageReceived.get_type() == Message.START_VIDEO:
                    print(f"Streaming {messageReceived.get_data()[0]} at port{messageReceived.get_data()[1]}")
                    nodo.videos[messageReceived.get_data()[0]]['state'] += 1
                    #nodo.videos[messageReceived.get_data()[0]]['port'] = messageReceived.get_data()[1]
                    nodo.addToQueue(messageReceived, addr, destino)
                elif messageReceived.get_type() == Message.FLOODING:
                    
                    if destino == DNS.dnsNodesInverse['s1']:
                        messageReceived.data += [DNS.dnsNodesInverse[DNS.dnsNodes[nodo.host]]]
                        nodo.broadcast2(messageReceived, destino)
                    else:
                        print("got a flooding from:{}".format(origem))
                        if messageReceived.get_data()[0] == '1':
                            nodo.atualizarManualTE(origem, addr)
                        nodo.addToQueue(messageReceived, addr, destino)
                else:
                    nodo.addToQueue(messageReceived, addr, destino)
            else:
                if messageReceived.get_type() == Message.FLOODING:
                    print("got a flooding from:{}".format(origem))
                    if messageReceived.get_data()[0] == '1':
                        nodo.atualizarManualTE(origem, addr)
                
                elif messageReceived.get_type() == Message.START_VIDEO:
                    print(f"Streaming {messageReceived.get_data()[0]} at port{messageReceived.get_data()[1]}")
                    nodo.videos[messageReceived.get_data()[0]]['state'] += 1
                    #nodo.videos[messageReceived.get_data()[0]]['port'] = messageReceived.get_data()[1]
                    sendToClient(messageReceived.get_data(), nodo)

                elif messageReceived.get_type() == Message.ACK_END_STREAM:#esquerda
                    nodo.videos[messageReceived.get_data()]['nodos'] = []
                    nodo.videos[messageReceived.get_data()]['state'] = 0
                    destinoCompleto = nodo.queueEndVideo[messageReceived.get_data()]
                    msg = Message(Message.ACK_END_STREAM, messageReceived.get_data(), str(nodo.host), str(destinoCompleto[0]))
                    nodo.udp_socket.sendto(msg.serialize(), destinoCompleto)
                    print("Message video sent from {} to {}".format(nodo.host,destino))

                else:
                    print(f"not implemented yet: server response{messageReceived.get_type()}")
                ### aqui adiciona-se o codigo de processamento dos inputs conforme a flag
    except Exception as e:
        print("Error receiving message from {}: {}".format(addr, e))
        print("(nodo foi à vida)")
        nodo.vizinhos_ativos[addr] = False
        for dest,next in nodo.tabela_end.items():
            if next == addr:
                nodo.tabela_end[dest] = -1
    finally:
        client_socket.close()

######### o ip está mal!!!! não está a dar para iniciar o server intermédio, also há a questão de o servidor nao é conhecido pelos 2 nodos
def iniciaNodo(messageList,videos_porta):
    ip = DNS.dnsNodesInverse[messageList[0]]
    novoNodo = Intermedio(ip,messageList[1:],videos_porta)

    request_thread = threading.Thread(target=serverIntermedios,args=('0.0.0.0',DNS.dnsNodesPorts[messageList[0]],novoNodo))
    request_thread.daemon = True
    request_thread.start()

    for ipVizinho, isActive in novoNodo.vizinhos_ativos.items():
        if isActive:
            
            vizinho_thread = threading.Thread(target=vizinhos, args=(ipVizinho,novoNodo))
            vizinho_thread.daemon = True
            vizinho_thread.start()
    i = 1
    while(True):
        if messageList[0][0] == 'p':
            #é um node de presença
            while (not novoNodo.todosInterAtivos()):
                print("Waiting for other nodes to be active...")
                time.sleep(5)
            #flouding
            print("Starting flooding...")
            floodmsg = Message(Message.FLOODING, [novoNodo.host], novoNodo.host, '10.0.0.10')
            novoNodo.broadcast(floodmsg,ip)
            
            if i == 1:
                notify_thread = threading.Thread(target=novoNodo.awaiting_notify, args=())
                notify_thread.daemon = True
                notify_thread.start()  
                i+=1

            # criar dicionario para troca e processar cenas
        # else:
            # Caso seja necessario implementar algo para os Os
            #print("not needed yet:(intermedios ultimo else)")
        time.sleep(150)











#    3->0 -> a ->X -> 1   
#    4->0 -> b ->X -> 1
#    3<-0 <-Ra <-5 <- 1 
#    4->0 -> c ->5 -> 1
#   
#    TE
#    
#    Dest3 -> Env 0
#    Dest1 -> Env -1
#    Dest4 -> Env 0
#      
#  
#    QUEUE
#    ProxNodo   |   Msg
#    5          |  a 
#    0          |  
#    2          |  a
#    
