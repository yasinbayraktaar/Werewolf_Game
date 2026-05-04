#!/usr/bin/env python3
"""
Werewolf Oyunu - Test Script
Birden fazla client'ı otomatik olarak bağlayıp test etmek için
"""
import socket
import threading
import time
import json

def test_client(client_id, player_name, server_host='localhost'):
    """Test client - otomatik mesaj gönder"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server_host, 5000))
        
        # İsmini gönder
        sock.send(player_name.encode('utf-8'))
        print(f"[CLIENT {client_id}] {player_name} bağlandı")
        
        # Mesaj almayı başlat
        def receive():
            while True:
                try:
                    data = sock.recv(1024).decode('utf-8')
                    if data:
                        if "MESSAGE:" in data:
                            parts = data.split(":", 2)
                            if len(parts) >= 3:
                                msg_type = parts[1]
                                json_data = parts[2]
                                try:
                                    parsed = json.loads(json_data)
                                    print(f"[CLIENT {client_id}] {msg_type}: {parsed.get('message', parsed.get('role', str(parsed)))}")
                                except:
                                    pass
                        time.sleep(0.1)
                except:
                    break
        
        recv_thread = threading.Thread(target=receive, daemon=True)
        recv_thread.start()
        
        # Oyun boyunca bağlı kal ve rastgele komutlar gönder
        wait_time = 0
        while wait_time < 300:  # 5 dakika test
            time.sleep(1)
            wait_time += 1
            
            # Gece aşamasında (her 30-50 saniyede)
            if wait_time % 40 == 0 and client_id == 0:
                sock.send("KILL:oyuncu2".encode('utf-8'))
                print(f"[CLIENT {client_id}] Kurban seçimi yapıldı")
            
            # Gün aşamasında (her 50-70 saniyede)
            if wait_time % 60 == 0:
                sock.send(f"VOTE:oyuncu3".encode('utf-8'))
                print(f"[CLIENT {client_id}] Oy verdi")
            
            # Her 20 saniyede sohbet
            if wait_time % 20 == 0:
                msg = f"Merhaba, ben {player_name}! (Zaman: {wait_time}s)"
                sock.send(f"CHAT:{msg}".encode('utf-8'))
        
        sock.close()
        print(f"[CLIENT {client_id}] Bağlantı kapandı")
        
    except Exception as e:
        print(f"[CLIENT {client_id}] Hata: {e}")

# Test başlat
print("[TEST] 3 Client'ı başlatıyoruz...")
print("[TEST] Her client 5 dakika bağlı kalacak\n")

server_host = input("Sunucu IP adresini giriniz (varsayılan: localhost): ") or 'localhost'
print(f"[TEST] Bağlanılacak sunucu: {server_host}\n")

clients = [
    (0, "Ali"),
    (1, "Fatma"),
    (2, "Mehmet"),
]

threads = []
for client_id, name in clients:
    t = threading.Thread(target=test_client, args=(client_id, name, server_host), daemon=True)
    threads.append(t)
    t.start()
    time.sleep(0.5)  # Bağlantıları sırasıyla aç

print("[TEST] Tüm client'lar başladı. Sunucu çıktısını izleyin...\n")

for t in threads:
    t.join(timeout=305)

print("\n[TEST] Test tamamlandı!")
