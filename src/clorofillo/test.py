import socket
import subprocess
import re

# Funzione per ottenere l'indirizzo MAC Bluetooth
def get_bluetooth_mac():
    result = subprocess.run(["hciconfig"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = result.stdout.decode("utf-8")
    match = re.search(r"BD Address\s*[:=]\s*([0-9A-F:]{17})", output)
    if match:
        mac_address = match.group(1)
        return mac_address
    else:
        raise ValueError("Indirizzo MAC Bluetooth non trovato")

# Ottieni l'indirizzo MAC
bt_addr = get_bluetooth_mac()
print(bt_addr)
# Crea socket Bluetooth RFCOMM
server_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)

# Bind al MAC e canale 3
server_sock.bind((bt_addr, 3))

# Metti in ascolto
server_sock.listen(1)

print("In attesa di connessione Bluetooth sul canale 3...")

client_sock, client_info = server_sock.accept()
print(f"Connesso a {client_info}")

# Ricevi dati (massimo 1024 byte)
data = client_sock.recv(1024).decode()
print(f"Dati ricevuti: {data}")

# Chiudi connessioni
client_sock.close()
server_sock.close()
