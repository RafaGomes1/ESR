import socket
import threading
import sys
import ast
from message import Message
import DNS
import responseServer
import json
from VideoStream import VideoStream
import time


#ips dos nodos visinhos partindo do nodo em questao
nodeNeighbors = {'s1' : ['s1', 'o1' , 'o2'],#s1
                 'o1' : ['o1','s1' , 'o3' , 'o4'],#01 '10.0.1.1' '10.0.12.2' '10.0.6.2'
                 'o2' : ['o2','s1' , 'o3'],#02 '10.0.24.1' '10.0.2.2'
                 'o3' : ['o3','o6' , 'o1' , 'o2'],#03 '10.0.12.1' '10.0.3.1' '10.0.26.2'
                 'o4' : ['o4','o1' , 'o5', 'p1'],#04 '10.0.5.1' '10.0.11.2' '10.0.11.2'
                 'o5' : ['o5','o6' , 'o4' , 'o7'],#05 '10.0.28.2' '10.0.9.1'
                 'o6' : ['o6','o3' , 'o5' , 'p3'],#06 '10.0.10.1' '10.0.27.1' '10.0.14.1'
                 'o7' : ['o7','p1' , 'p2' , 'o5'],#07 '10.0.9.2' '10.0.15.1' '10.0.13.1'
                 'p1' : ['p1','o4' , 'o7' , 'c1' , 'c2' , 'c3' , 'c4'],#p1 '10.0.25.2' '10.0.11.2' '10.0.16.1'
                 'p2' : ['p2','o7' , 'c1' , 'c2' , 'c3' , 'c4'],#p2 '10.0.13.2' '10.0.17.1' '10.0.18.1'
                 'p3' : ['p3','o6' , 'c1' , 'c2' , 'c3' , 'c4'],#p3 '10.0.14.2' '10.0.19.1'
                 'c1' : ['c1','p1' , 'p2' , 'p3'], #c1 '10.0.21.20'
                 'c2' : ['c2','p1' , 'p2' , 'p3'],#c2 '10.0.21.21'
                 'c3' : ['c3','p1' , 'p2' , 'p3'],#c3 '10.0.23.20'
                 'c4' : ['c4','p1' , 'p2' , 'p3']#C4 '10.0.23.21'
                  }

#ips dos nodos visinhos partindo do server
inverseNodeNeighbors = {'s1' : ['10.0.1.2' , '10.0.2.2'],
                        'o1' : ['10.0.10.2' , '10.0.6.2'],
                        'o2' : ['10.0.6.2'],
                        'o3' : ['10.0.1.2' , '10.0.2.2' , '10.0.8.2'],
                        'o4' : ['10.0.1.2' , '10.0.19.2' , '10.0.15.2'],
                        'o5' : ['10.0.10.2' , '10.0.8.2' , '10.0.16.2'],
                        'o6' : ['10.0.6.2' , '10.0.15.2' , '10.0.20.2'],
                        'o7' : ['10.0.19.2' , '10.0.15.2' , '10.0.18.2'],
                        'p1' : ['10.0.10.2' , '10.0.16.2' , '10.0.25.21' , '10.0.25.20' , '10.0.29.21' , '10.0.29.20'],
                        'p2' : ['10.0.16.2' , '10.0.25.21' , '10.0.25.20' , '10.0.29.21' , '10.0.29.20'],
                        'p3' : ['10.0.8.2' , '10.0.25.21' , '10.0.25.20' , '10.0.29.21' , '10.0.29.20'],
                        'c1' : ['10.0.20.2', '10.0.19.2' , '10.0.18.2' ],
                        'c2' : ['10.0.19.2' , '10.0.18.2' , '10.0.20.2'],
                        'c3' : ['10.0.19.2' , '10.0.18.2' , '10.0.20.2'],
                        'c4' : ['10.0.19.2' , '10.0.18.2' , '10.0.20.2']
}

videosServer = {}




######SERVIDOR######

###### Lê ficheiro JSON ############
def read_json(filepath):
    porta = 13002
    with open(filepath) as f:
        data = json.load(f)
    for video in data["videos"]:
        videosServer[video] = {'state' : 0,'port' : porta,'nodos' : [], 'objectVideoStream' : VideoStream(f'./videos/{video}')} # Confirmar se esta certo!!!
        porta+=1

###### SERVÇO LISTA DE VIDEOS ############


def pedidos_cliente():
    print("a espera de pedidos de clientes!")

    sc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sc.bind(('', DNS.REQUESTS_PORT))
    while True:
        try:
            dados, addr = sc.recvfrom(1024)
            print("Pedido recebido de {}: {}".format(addr[0],dados.decode()))

            print("A enviar a lista dos Ps disponiveis")

            lista = '10.0.25.2, 10.0.13.2, 10.0.14.2'

            l = lista.encode()

            sc.sendto(l, (addr[0],DNS.REQUESTS_PORT))
        except Exception as e:
            print("ERRO NO PEDIDOS_CLIENTE: {}".format(e))

def notify_neighbor(addr):
    # Lista de vizinhos do node que se desconectou
    print("Notificar vizinhos")
    node = DNS.dnsNodes[addr]
    print("NO = {}".format(node))
    if node[0] != 'c':

        print("Vizinhos = {}".format(inverseNodeNeighbors[node]))
        neighbors = inverseNodeNeighbors[node]
        try:
            for neighbor in inverseNodeNeighbors['c1']:
                sc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                m = Message(Message.NOTIFY_NEIGHBOR, "flooding", "10.0.0.10", neighbor)
                sc.sendto(m.serialize(), (neighbor, DNS.NOTIFY_PORT))
                time.sleep(1)
                sc.close()
        except:
            print("ERRO NO NOTIFY_NEIGHBOR")

        
def receive_messages(client_socket,addr):
    i = 0
    try:
        while i != -1:
            # Recebe mensagem do cliente com timeout
            message = client_socket.recv(2048)
            messageReceived = Message.deserialize(message)
            if not messageReceived.get_data():  # Verifica se a conexao foi fechada
                print("Conexao fechada pelo cliente.")
                print("EXECUTAR NOTIFY")
                print("addr = {}".format(addr))
                notify_neighbor(addr[0])
                break  # Sai do loop, terminando o processamento para esse cliente

            print("Received: {}".format(messageReceived.get_data()))

            # Tratamento especifico para a primeira mensagem
            if i == 0:
                print("Sent: {}".format(str(nodeNeighbors[DNS.dnsNodes[addr[0]]])))
                aux = []
                for video, data in videosServer.items():
                    aux.append((video, data['port']))
                m = Message(Message.SEND_NEIGHBORS, (nodeNeighbors[DNS.dnsNodes[addr[0]]],aux), str(client_socket.getsockname()[0]), str(client_socket.getpeername()[0]))
                messageResponse = m.serialize()
                #messageResponse = str(nodeNeighbors[dnsNodes[addr[0]]])
            else:
                # Processa pedidos de streaming
                print("Sent: {}".format("not implemented yet"))
                m = Message(Message.SEND_NEIGHBORS, "not implemented yet", str(client_socket.getsockname()[0]), str(client_socket.getpeername()[0]))
                messageResponse = m.serialize()

            # Envia resposta ao cliente
            client_socket.send(messageResponse)
            i += 1


    except Exception as e:
        print("Error in receiving messages: {}".format(e))
        print(inverseNodeNeighbors[DNS.dnsNodes[addr[0]]])
        print("Unexpected error with clientee {}: {}".format(addr,e))
        print("EXECUTAR NOTIFY")
        print("addr = {}".format(addr))
        notify_neighbor(addr[0])



def oNode_server(host='10.0.0.10', port=DNS.CONNECT_PORT):
    read_json("s1.json")
    #request_thread = threading.Thread(target=pedidos_cliente)
    #request_thread.start()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print("Server listening on {}:{}".format(host, port))
    #8881 response server
    request_thread = threading.Thread(target=responseServer.serverDeResposta,args=(DNS.dnsNodesPorts['s1'],nodeNeighbors['s1'],videosServer))
    request_thread.daemon = True
    request_thread.start()

    while(True): #8888 bootstraper
        try:
            client_socket, addr = server_socket.accept()
            print("Connection established with {}".format(addr))

            message_thread = threading.Thread(target=receive_messages, args=(client_socket,addr,))
            message_thread.daemon = True
            message_thread.start()
        except Exception as e:
            print("Unexpected error with cliente {}: {}".format(addr,e))
            