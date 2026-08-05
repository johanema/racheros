import time
import re
import os

# Archivos que vamos a vigilar
AUTH_LOG = '/var/log/auth.log'
SYSLOG_FILE = '/var/log/syslog'

# Patrones Regex para detectar ataques
# 1. Fuerza bruta SSH
SSH_PATTERN = re.compile(r"Failed password for .* from ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)")
# 2. Anomalías/Fuerza bruta en Mosquitto MQTT
MQTT_PATTERN = re.compile(r"Client connection from ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)")

ips_bloqueadas = set()

def bloquear_atacante(ip, servicio):
    if ip not in ips_bloqueadas:
        print(f"[!] ¡ACCIÓN DEFENSIVA! Bloqueando la IP {ip} (Ataque a {servicio})...")
        comando_firewall = f"iptables -A INPUT -s {ip} -j DROP"
        os.system(comando_firewall)
        ips_bloqueadas.add(ip)
        print(f"[V] ÉXITO: La IP {ip} ha sido bloqueada en el firewall.")

def monitor_logs():
    print("[*] Iniciando SecOps: Monitoreando SSH y MQTT en tiempo real...")
    
    try:
        # Abrimos ambos archivos
        file_ssh = open(AUTH_LOG, 'r')
        file_mqtt = open(SYSLOG_FILE, 'r')
        
        # Vamos al final de ambos archivos para leer solo lo nuevo
        file_ssh.seek(0, os.SEEK_END)
        file_mqtt.seek(0, os.SEEK_END)
        
        while True:
            # Leemos líneas de ambos archivos
            linea_ssh = file_ssh.readline()
            linea_mqtt = file_mqtt.readline()
            
            if not linea_ssh and not linea_mqtt:
                time.sleep(0.5)
                continue
            
            # Revisamos alertas de SSH
            if linea_ssh:
                match_ssh = SSH_PATTERN.search(linea_ssh)
                if match_ssh:
                    ip = match_ssh.group(1)
                    print("-" * 50)
                    print("[!] ALERTA CRÍTICA: Intento de fuerza bruta en SSH.")
                    bloquear_atacante(ip, "SSH")
                    print("-" * 50)
            
            # Revisamos alertas de Mosquitto
            if linea_mqtt:
                match_mqtt = MQTT_PATTERN.search(linea_mqtt)
                if match_mqtt:
                    ip = match_mqtt.group(1)
                    print("-" * 50)
                    print("[!] ALERTA CRÍTICA: Anomalía/Fallo de conexión en Mosquitto")
                    bloquear_atacante(ip, "Mosquitto")
                    print("-" * 50)

    except PermissionError:
        print("[X] Error: Ejecuta el script con sudo.")

if __name__ == "__main__":
    monitor_logs()