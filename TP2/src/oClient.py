import sys
import socket
import datetime
import threading
import time
from tkinter import Tk, Toplevel
from message import Message
from ClientStream import Client
import DNS

#nos nodos de presença tem um servidor udp pronto a receber msgs
#
#as mensagens enviadas para o servidor de presença devem ter um timeout de receção de resposta(todos deverão ter resposta)
#podem ser de 2 tipos:
# -> ver o timestamp(quando foi enviado - quando foi recebido) (se der timeout incrementar uma variavel(confiabilidade))
#    -> e perguntar se já estão a streamar o video
# -> pedir um video (a resposta deve ser mais demorada)

class Cliente:

    def __init__(self, host: int, vizinhos_ativos:list, videos_portas:list):
        # (estado, tempo de resposta, timeouts)
        self.host = DNS.dnsNodesInverse[host]
        self.vizinhos_ativos = {DNS.dnsNodesInverse[elem]: { 'state':True,"responseTime": 99.9,"videosAtivos": [],"timeouts": 0} for elem in vizinhos_ativos}
        self.queue = {DNS.dnsNodesInverse[elem]: [] for elem in vizinhos_ativos}
        self.videos_portas = {video : porta for (video,porta) in videos_portas}
        self.numeroDeSessoes = 0+int(host[1])*10
        self.root = None
    
    def get_vizinhos(self):
        return self.vizinhos_ativos.items()
    
    def print_vizinhos_ativos(self):    
        for neighbor_ip, data in self.vizinhos_ativos.items():
            # Obter o nome do vizinho a partir do IP
            neighbor_name = DNS.dnsNodes.get(neighbor_ip, "Desconhecido")
            estado = "Ativo" if data['state'] else "Inativo"
            print("Nome: {}; IP: {}; Estado: {}; Tempo: {}, Timeouts: {}, Videos neste vizinho: {}".format(neighbor_name, DNS.dnsClientToP[neighbor_ip], estado,data["responseTime"],data["timeouts"],data["videosAtivos"]))

    def get_vizinhos_ativos(self):
        result = []
        for neighbor_ip, data in self.vizinhos_ativos.items():
            # Obter o nome do vizinho a partir do IP
            neighbor_name = DNS.dnsNodes.get(neighbor_ip, "Desconhecido")
            if data['state']:
                result.append(neighbor_name) # isto pode ser passado para IP
        return result

    def get_melhor_p(self, videoName):
        # Caso o video ja esteja em streaming num PoP
        for vizinho in self.vizinhos_ativos:
            if videoName in self.vizinhos_ativos[vizinho]["videosAtivos"]:
                return vizinho 
        # Encontrar o elemento com o menor responseTime
        melhor_p = min(self.vizinhos_ativos, key=lambda x: self.vizinhos_ativos[x]["responseTime"])
        return melhor_p


def calcula_metrica(ip, port, cliente):

    while(True):

        nr_requests = 5
        msg = Message(Message.METRICS, "teste", str(cliente.host), str(ip))
    
 
        sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
 
        try:
            p = (DNS.dnsClientToP[ip], port)
        
            for i in range(nr_requests):
                msg.set_timestamp(datetime.datetime.now().isoformat())
                msgEnvio = msg.serialize()
                sckt.sendto(msgEnvio,p)
 
            sucesso = 0
            tempo = 0
            media = 0.0
 
            for i in range(nr_requests):
                try:
                    dados, _ = sckt.recvfrom(2048) # espera a resposta do RP
                    nowRecebido = datetime.datetime.now()
                    try:
                        resposta = Message.deserialize(dados)
                        sucesso += 1
                        
                        tempo += (nowRecebido - datetime.datetime.fromisoformat(resposta.get_timestamp())).total_seconds()
                    except:
                        print("Erro ao fazer deserialize da mensagem do P")
 
                except socket.timeout:
                    print("Timeout da mensagem de resposta do P")
                    cliente.vizinhos_ativos[ip]["timeouts"] += 1
                    break
 
            if sucesso > 0:
                media = tempo / sucesso
            else:
                media = 99.9
            cliente.vizinhos_ativos[ip]["responseTime"] = media
            cliente.vizinhos_ativos[ip]["videosAtivos"] = resposta.get_data()
        finally:
            sckt.close()

        time.sleep(10)

def vizinhos(vizinhoIP:int,nodo:Cliente):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(vizinhoIP)
    portaVizinho = DNS.dnsNodesPorts[DNS.dnsNodes[vizinhoIP]]
    try:
        # ficar a espera de receber mensagens, e quando recebe envia para o proximo vizinho
        while (True):
            if not any(nodo.queue[vizinhoIP]):
                time.sleep(5)
            else:
                while(any(nodo.queue[vizinhoIP])):
                    m = nodo.queue[vizinhoIP].pop()
                    client_socket.sendto(m.serialize(), (vizinhoIP,portaVizinho))
                    print("message sent to {}".format(DNS.dnsNodes[vizinhoIP]))
        print("WHILE ACABOU INESPERADAMENTE!")
    except Exception as e:
        print("Error connecting to {}:{} - {}".format('0.0.0.0', portaVizinho, e))
        nodo.vizinhos_ativos[vizinhoIP] = False

def menu_de_stream(ip,streamingdoor,videoName,sessionID, ipCliente,cliente):
    if cliente.root is None:
        cliente.root = Tk()
        cliente.root.withdraw()
        ready=0
    else:
        ready=1    
    new_window = Toplevel(cliente.root)
    new_window.title("Streaming Menu")
    app = Client(new_window, ip,  DNS.dnsNodesPorts[DNS.dnsNodes[ip]], streamingdoor, videoName,sessionID, ipCliente)
    app.master.protocol("RTPClient Teste")
    new_window.protocol("WM_DELETE_WINDOW", new_window.destroy)
    if ready == 0:
        cliente.root.mainloop()



def menu_cliente(client_socket,messageList,videos):
    cliente = Cliente(messageList[0], messageList[1:],videos)
    for ipVizinho, data in cliente.vizinhos_ativos.items():
        if data['state']:
            #vizinho_thread = threading.Thread(target=vizinhos, args=(ipVizinho,cliente))
            #vizinho_thread.daemon = True
            #vizinho_thread.start()
            metrics_thread = threading.Thread(target=calcula_metrica, args=(ipVizinho, DNS.dnsNodesPorts[DNS.dnsNodes[ipVizinho]],cliente))
            metrics_thread.daemon = True
            metrics_thread.start()

    while True:
        print("\n===== MENU =====")
        print("1. Pedir video ao servidor")
        print("2. Conhecer vizinhos")
        print("3. Desconectar")
        option = input("Escolha uma opcao: ")
        
        if option == '1':
            print("que video deseja...")
            i = 1
            for video in cliente.videos_portas:
                print(f'{i} - {video}\n')
                i = i+1
            
            option = input("Escolha uma opcao: ") 
            videoName = list(cliente.videos_portas)[int(option) - 1]
            ip = cliente.get_melhor_p(videoName)
            m = Message(Message.REQUEST_STREAM, videoName,str(cliente.host),str(ip))            
            p = (DNS.dnsClientToP[ip], DNS.dnsNodesPorts[DNS.dnsNodes[ip]])

            
            #preparar para receber pacotes de streaming
            cliente.numeroDeSessoes +=1
            interface_thread = threading.Thread(target=menu_de_stream, args=(ip, cliente.videos_portas[videoName], videoName,cliente.numeroDeSessoes, cliente.host,cliente))
            interface_thread.daemon = True
            interface_thread.start()
            #pedir pacotes
            sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sckt.sendto(m.serialize(), p)
            try:
                
                data, addr = sckt.recvfrom(2048)
                messageReceived = Message.deserialize(data)
                print(f"o video está disponivel na porta:{messageReceived.get_data()}")
            
            
            except socket.timeout:
                print(f"Timeout ao tentar receber a resposta CHECK_VIDEO")

            
            
                
            
        elif option == '2':
            ip = DNS.dnsNodesInverse[messageList[0]]
            node = messageList[0]

            print("Vizinhos do nó {}:\n".format(node))
            cliente.print_vizinhos_ativos()

        elif option == '3':
            # Fechar todas as threads
            client_socket.close()
            print("Desconectado!")
            break

        else:
            print("Opção inválida. Por favor, escolha novamente.")
