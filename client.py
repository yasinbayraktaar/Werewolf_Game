import socket

# Sunucu ayarları
HOST = input("Sunucu IP adresini giriniz (varsayılan: localhost): ") or 'localhost'
PORT = 5000

def connect_to_server():
    """Sunucuya bağlan"""
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((HOST, PORT))
        
        # Sunucudan mesaj al ve oyuncu ismini gönder
        message = client_socket.recv(1024).decode('utf-8')
        print(message, end='')
        
        player_name = input()
        client_socket.send(player_name.encode('utf-8'))
        
        # Bağlantı kabul mesajını al
        response = client_socket.recv(1024).decode('utf-8')
        print(response)
        
        print("Sunucuya bağlı kalınıyor... (Çıkmak için Ctrl+C)")
        
        # Bağlı kalma
        while True:
            pass
        
    except ConnectionRefusedError:
        print(f"[HATA] Sunucuya bağlanılamadı: {HOST}:{PORT}")
    except Exception as e:
        print(f"[HATA] {e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    connect_to_server()
