import socket
import threading
import sys
import ast

from message import Message
import oClient
import DNS
import intermedios
import oServer

#Porque é que o onode do server tem que começar numa thread


#cada nodo tem de ter um servidor e um cliente...
# o servidor será sempre iniciado logo de inicio
# o cliente tentará se ligar a todos os visinhos, os que derem pode aualizar a tabela de enderessamento
# o servidor tratará do receive msg 
# os clientes farão o envio das mensagens
#####NODOS######




#####CLIENTE#####



def connect_to_host(host):
    host_host, host_port = host.split(":")  # Assume "host:port" format
    host_port = int(host_port)
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        #print("Connecting to {}:{}".format(host_host, host_port))
        client_socket.connect((host_host, host_port))
        print("Connected to host {} - {}:{}".format(DNS.dnsNodes[host_host], host_host, host_port))
        send_messages(client_socket)
    except Exception as e:
        print("Error connecting to {}:{} - {}".format(host_host, host_port, e))


def send_messages(client_socket):
    try:
        message = "hello"
        m = Message(Message.START_SERVICE, message, str(client_socket.getsockname()[0]), str(client_socket.getpeername()[0]))
        client_socket.sendall(m.serialize())
        while True:
            message = client_socket.recv(2048)
            messageReceived = Message.deserialize(message)
            neighbours,videos = messageReceived.get_data()
            #guardar no dic os visinhos
            
            if neighbours[0][0] == 'c':
                oClient.menu_cliente(client_socket, neighbours, videos)
                break
            elif neighbours[0][0] == 'p' or neighbours[0][0] == 'o':
                #print("gothere2")
                intermedios.iniciaNodo(neighbours, videos)
                   
            else:
                print("Error in divice type")
            

    except Exception as e:
        print("Error in sending messages: {}".format(e))



if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Start server in a separate thread
        #server_thread = threading.Thread(target=oServer.oNode_server)
        #server_thread.start()
        #start server on main
        oServer.oNode_server()
    else:
        #cliente

        host = sys.argv[1]

        # Connect to host
        connect_to_host(host)
        
        #menu
