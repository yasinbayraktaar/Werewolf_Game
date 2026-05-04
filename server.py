import socket
import threading
import json
import random
import time
from enum import Enum


# Otomatik yerel IP bulucu
def get_local_ip():
    try:
        # Geçici bir UDP soketi oluşturarak dışarıya (Google DNS) bir rota çizip kendi IP'mizi öğreniyoruz
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # İnternet bağlantısı yoksa veya hata olursa fallback olarak localhost dön
        return '127.0.0.1'


# Oyun durumları
class GameState(Enum):
    WAITING = "BEKLEME"
    NIGHT = "GECE"
    DAY = "GÜN"
    VOTING = "OY_VERME"
    GAME_OVER = "OYUN_BİTTİ"


# Sunucu ayarları
HOST = "0.0.0.0"             # Tüm ağ arayüzlerinden bağlantı kabul et
DISPLAY_IP = get_local_ip()  # Sadece ekranda göstermek için
PORT = 5000
MAX_CLIENTS = 10
MIN_PLAYERS = 3  # Oyun başlamak için minimum oyuncu

# Global değişkenler
clients = {} # {socket: {'name': str, 'role': str, 'alive': bool, 'was_voted': bool, 'is_admin': bool}}
clients_lock = threading.Lock()
game_state = GameState.WAITING
game_lock = threading.Lock()
round_number = 0
game_started = False  # Admin tarafından başlatıldı mı?
admin_socket = None  # İlk giren oyuncu (admin)
night_kills = {}  # {kurt_adam_name: victim_name}
day_votes = {}  # {oyuncu_name: suçlanan_name}

def send_message(client_socket, msg_type, data):
    """Client'a JSON formatında mesaj gönder"""
    try:
        message = f"MESSAGE:{msg_type}:{json.dumps(data)}\n"
        client_socket.send(message.encode('utf-8'))
    except:
        pass

def broadcast_message(msg_type, data, exclude_role=None):
    """Tüm oyunculara veya belirli role mesaj gönder"""
    with clients_lock:
        for client_socket, player_info in clients.items():
            try:
                # Eğer exclude_role varsa, o role sahip olanları atla
                if exclude_role and player_info['role'] == exclude_role:
                    continue

                if not player_info['alive']:  # Ölü oyuncuya mesaj gönderme
                    continue

                send_message(client_socket, msg_type, data)
            except:
                pass

def get_alive_players():
    """Canlı oyunculuların listesini döndür"""
    with clients_lock:
        return [info for info in clients.values() if info['alive']]

def get_players_by_role(role):
    """Belirli role sahip oyunculuların listesini döndür"""
    with clients_lock:
        return [info for info in clients.values() if info['role'] == role and info['alive']]

def check_game_over():
    """Oyun bitme koşullarını kontrol et"""
    alive_players = get_alive_players()
    werewolves = get_players_by_role('kurt_adam')
    villagers = get_players_by_role('köylü')

    # Kurt adamlar sayı olarak fazla oldu
    if len(werewolves) >= len(villagers):
        return True, "Kurt adamlar kazandı!"

    # Kurt adam kalmadı
    if len(werewolves) == 0:
        return True, "Köylüler kazandı! Tüm kurt adamlar öldürüldü."

    return False, ""

def assign_roles():
    """Oyunculara rol ata"""
    alive_players = get_alive_players()
    num_players = len(alive_players)
    num_werewolves = max(1, num_players // 3)  # 1/3 kurt adam

    # Tüm oyunculuya köylü rolü ata
    with clients_lock:
        for client_socket, player_info in clients.items():
            if player_info['alive']:
                player_info['role'] = 'köylü'
                player_info['was_voted'] = False

    # Rastgele kurt adam seç
    with clients_lock:
        werewolf_indices = random.sample(range(len(alive_players)), num_werewolves)
        for idx in werewolf_indices:
            alive_players[idx]['role'] = 'kurt_adam'

    # Oyunculara rollerini bildir
    with clients_lock:
        for client_socket, player_info in clients.items():
            send_message(client_socket, 'ROLE', {
                'role': player_info['role'],
                'message': f"Senin rolün: {player_info['role']}"
            })

def night_phase():
    """Gece rotasyonu - Kurt adamlar kimi öldürecekler"""
    global night_kills, round_number
    night_state = GameState.NIGHT

    night_kills = {}
    day_votes.clear()

    # Tüm oyunculara "Gece oldu" mesajı
    broadcast_message('GAME_EVENT', {
        'state': 'GECE',
        'message': '🌙 GECE OLDU - Herkes gözlerini kapatsın!'
    })

    time.sleep(1)

    # Kurt adamlara özel mesaj
    werewolves = get_players_by_role('kurt_adam')

    for werewolf in werewolves:
        # Kurt adam socket'ini bul
        for client_socket, player_info in clients.items():
            if player_info == werewolf:
                villagers = get_players_by_role('köylü')
                villain_names = [v['name'] for v in villagers]

                # İlk gece kurt adam kimse öldüremez
                if round_number == 1:
                    send_message(client_socket, 'ACTION_REQUEST', {
                        'action': 'select_victim',
                        'message': f'Bu birinci gece! Henüz kimse öldüremezsin. (Seçenekler: {", ".join(villain_names)})',
                        'options': []
                    })
                else:
                    send_message(client_socket, 'ACTION_REQUEST', {
                        'action': 'select_victim',
                        'message': f'Kimi öldüreceksin? (Seçenekler: {", ".join(villain_names)})',
                        'options': villain_names
                    })
                break

    # Kurt adamların seçim yapması için bekleme (30 saniye)
    print("[GÜN] Kurt adamlar kararlarını veriyor...")
    time.sleep(30)

    # Öldürülen oyuncuyu belirle (ilk gece sadece bekleme)
    if night_kills and round_number > 1:
        victim_name = list(night_kills.values())[0]  # İlk seçimi al
        with clients_lock:
            for client_socket, player_info in clients.items():
                if player_info['name'] == victim_name:
                    player_info['alive'] = False
                    break

        broadcast_message('GAME_EVENT', {
            'state': 'SABAH',
            'message': f'☀️ SABAH OLDU! Kötü bir haberle uyandınız: {victim_name} öldü! 💀'
        })
        print(f"[ÖLDÜRÜLDÜ] {victim_name}")
    else:
        broadcast_message('GAME_EVENT', {
            'state': 'SABAH',
            'message': '☀️ SABAH OLDU! Kurt adamlar kimseyi öldürmediler...'
        })

    time.sleep(2)

def day_phase():
    """Gün rotasyonu - Herkes tartışıp suçlayabilir"""
    # Tüm oyunculara gün mesajı
    broadcast_message('GAME_EVENT', {
        'state': 'GÜN',
        'message': '☀️ GÜN OLDU - Tartışıp birini suçlayabilirsiniz!\nTartışmaya başlayın!'
    })

    day_votes.clear()

    print("[GÜN] Oyuncular tartışıyor ve suçluyorlar...")
    # Tartışma için 30 saniye
    time.sleep(30)

    broadcast_message('GAME_EVENT', {
        'state': 'OY_VERME',
        'message': '⏱️ OY VERME BAŞLADI! Kimi dışarı göndermek istiyorsunuz?\nKomut: VOTE:<adı>'
    })

    # Oy verme için 20 saniye
    print("[OY_VERME] Oyuncular oy veriyorlar...")
    time.sleep(20)

    # Oy sonuçlarını belirle
    if day_votes:
        voted_counts = {}
        for voted_player in day_votes.values():
            voted_counts[voted_player] = voted_counts.get(voted_player, 0) + 1

        most_voted = max(voted_counts.items(), key=lambda x: x[1])[0]

        with clients_lock:
            for client_socket, player_info in clients.items():
                if player_info['name'] == most_voted:
                    player_info['alive'] = False
                    break

        broadcast_message('GAME_EVENT', {
            'state': 'OY_SONUCU',
            'message': f'📊 OY SONUCU: {most_voted} dışarı gönderildi! 💀'
        })
        print(f"[DIŞARI GÖNDERILEN] {most_voted}")
    else:
        broadcast_message('GAME_EVENT', {
            'state': 'OY_SONUCU',
            'message': '📊 OY SONUCU: Kimse oy vermedi!'
        })

    time.sleep(2)

def game_loop():
    """Ana oyun döngüsü"""
    global game_state, round_number, game_started

    while True:
        # Oyun başlanması için admin tarafından başlatılması bekleme
        while True:
            with clients_lock:
                num_alive = len([c for c in clients.values() if c['alive']])
            # Minimum oyuncu ve admin tarafından başlatıldı mı kontrol et
            if num_alive >= MIN_PLAYERS and game_started:
                break
            time.sleep(1)

        with game_lock:
            if game_state == GameState.WAITING:
                with clients_lock:
                    num_alive = len([c for c in clients.values() if c['alive']])

                if num_alive >= MIN_PLAYERS and game_started:
                    # Oyunu başlat
                    game_state = GameState.NIGHT
                    round_number += 1
                    game_started = False  # Bir sonraki oyun için sıfırla

                    # Tüm oyunculuya oyun başladı mesajı
                    broadcast_message('GAME_EVENT', {
                        'state': 'OYUN_BAŞLADI',
                        'message': f'🎮 OYUN BAŞLADI! {num_alive} oyuncu ile...',
                        'round': round_number
                    })

                    print(f"\n[OYUN BAŞLADI] Round {round_number} - {num_alive} oyuncu")

                    # Rolleri ata
                    assign_roles()
                    time.sleep(2)

            elif game_state == GameState.NIGHT:
                night_phase()
                game_state = GameState.DAY

                # Oyun bitme kontrolü
                game_over, reason = check_game_over()
                if game_over:
                    game_state = GameState.GAME_OVER
                    broadcast_message('GAME_EVENT', {
                        'state': 'OYUN_BİTTİ',
                        'message': f'🏁 OYUN BİTTİ!\n{reason}'
                    })
                    print(f"[OYUN BİTTİ] {reason}")
                    game_state = GameState.WAITING
                    time.sleep(5)

            elif game_state == GameState.DAY:
                day_phase()
                game_state = GameState.NIGHT

                # Oyun bitme kontrolü
                game_over, reason = check_game_over()
                if game_over:
                    game_state = GameState.GAME_OVER
                    broadcast_message('GAME_EVENT', {
                        'state': 'OYUN_BİTTİ',
                        'message': f'🏁 OYUN BİTTİ!\n{reason}'
                    })
                    print(f"[OYUN BİTTİ] {reason}")
                    game_state = GameState.WAITING
                    time.sleep(5)

def handle_client(client_socket, client_address):
    """Her client bağlantısını ayrı thread'de işle"""
    global admin_socket, game_started
    player_name = None
    try:
        # Client'tan oyuncunun ismini al
        player_name = client_socket.recv(1024).decode('utf-8').strip()

        if not player_name:
            return

        # Client bilgisini kaydet
        with clients_lock:
            # İlk giren oyuncu admin olur
            is_admin = admin_socket is None
            if is_admin:
                admin_socket = client_socket
            
            clients[client_socket] = {
                'name': player_name,
                'role': None,
                'alive': True,
                'address': client_address,
                'is_admin': is_admin
            }

        send_message(client_socket, 'CONNECTION', {
            'status': 'success',
            'message': f'Bağlantı kabul edildi, {player_name}!',
            'is_admin': is_admin
        })

        print(f"[BAĞLANDI] {player_name} ({client_address})" + (" [ADMIN]" if is_admin else ""))

        # Tüm client'lara bildiri
        with clients_lock:
            num_players = len([c for c in clients.values() if c['alive']])

        broadcast_message('SYSTEM', {
            'message': f'✅ {player_name} katıldı! (Oyuncular: {num_players}/{MIN_PLAYERS})'
        })

        # Client mesajlarını dinle
        while True:
            data = client_socket.recv(1024).decode('utf-8').strip()
            if not data:
                break

            # Protokol: MESSAGE:TYPE:DATA
            if data.startswith("MESSAGE:"):
                parts = data[8:].split(":", 1)
                if len(parts) == 2:
                    msg_type, content = parts
                    handle_client_message(client_socket, player_name, msg_type, content)

            # CHAT protokolü (eski)
            elif data.startswith("CHAT:"):
                message_content = data[5:]
                broadcast_message('CHAT', {
                    'player': player_name,
                    'message': message_content
                })

            # Komutlar
            elif data.startswith("VOTE:"):
                victim_name = data[5:]
                day_votes[player_name] = victim_name
                print(f"[OY] {player_name} -> {victim_name}")

            elif data.startswith("KILL:"):
                victim_name = data[5:]
                night_kills[player_name] = victim_name
                print(f"[ÖLDÜRME] {player_name} -> {victim_name}")

            elif data == "PLAYERS":
                with clients_lock:
                    players_list = [f"{c['name']} ({'Ölü' if not c['alive'] else 'Canlı'})"
                                   for c in clients.values()]
                send_message(client_socket, 'PLAYERS_LIST', {
                    'players': players_list
                })
            
            elif data == "START_GAME":
                # Sadece admin başlatabilir
                with clients_lock:
                    if client_socket in clients and clients[client_socket].get('is_admin'):
                        game_started = True
                        print("[OYUN] Admin tarafından oyun başlatıldı!")
                        broadcast_message('SYSTEM', {
                            'message': f'🎮 Admin oyunu başlattı! Hazırlıklar devam ediyor...'
                        })

    except Exception as e:
        print(f"[HATA] {client_address}: {e}")

    finally:
        # Client bağlantısını kapat
        if player_name:
            with clients_lock:
                if client_socket in clients:
                    if clients[client_socket].get('is_admin'):
                        admin_socket = None  # Admin ayrıldı
                    del clients[client_socket]

            with clients_lock:
                num_players = len([c for c in clients.values() if c['alive']])

            broadcast_message('SYSTEM', {
                'message': f'❌ {player_name} ayrıldı! (Kalan: {num_players} oyuncu)'
            })
            print(f"[AYRILAN] {player_name}")

        client_socket.close()

def handle_client_message(client_socket, player_name, msg_type, content):
    """Client mesajlarını işle"""
    if msg_type == "CHAT":
        try:
            content = json.loads(content)
            broadcast_message('CHAT', {
                'player': player_name,
                'message': content.get('message', '')
            })
        except:
            pass

def start_server():
    """Sunucuyu başlat ve client bağlantılarını dinle"""
    # Oyun döngüsünü başlat
    game_thread = threading.Thread(target=game_loop, daemon=True)
    game_thread.start()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(MAX_CLIENTS)
        print(f"[SUNUCU] Tüm arayüzlerde :{PORT} portu dinleniyor")
        print(f"[SUNUCU] LAN'dan bağlanmak için IP: {DISPLAY_IP}:{PORT}")
        print(f"[SUNUCU] Aynı bilgisayardan: localhost:{PORT} veya 127.0.0.1:{PORT}")
        print(f"[SUNUCU] Maksimum {MAX_CLIENTS} oyuncu | Oyun {MIN_PLAYERS} ile başlar\n")

        while True:
            client_socket, client_address = server_socket.accept()
            thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
            thread.daemon = True
            thread.start()

    except KeyboardInterrupt:
        print("\n[SUNUCU] Kapatılıyor...")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_server()