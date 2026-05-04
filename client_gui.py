"""
Kurt Adam Oyunu — Pygame İstemci
Çalıştır: python client.py
"""

import pygame
import sys
import math
import socket
import threading
import json
import time
import random

# ─── BAŞLATMA ───────────────────────────────────────────────
pygame.init()

# ─── SABITLER ───────────────────────────────────────────────
WIDTH, HEIGHT = 960, 680
FPS = 60
DEFAULT_PORT = 5000

# Renk paleti
NIGHT_BG = (8, 8, 20)
NIGHT_MID = (15, 15, 40)
MOON_YELLOW = (255, 240, 150)
BLOOD_RED = (160, 20, 20)
BLOOD_DARK = (100, 10, 10)
GRAY_LIGHT = (180, 180, 200)
GRAY_DIM = (100, 100, 130)
WHITE = (255, 255, 255)
TREE_DARK = (20, 15, 10)
ACCENT_BLUE = (80, 120, 200)
GOLD = (220, 180, 60)
GREEN = (60, 180, 80)

BTN_W, BTN_H = 280, 52
BTN_X = WIDTH // 2 - BTN_W // 2

# ─── EKRAN & CLOCK ──────────────────────────────────────────
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Kurt Adam Oyunu")
clock = pygame.time.Clock()

# ─── FONTLAR ────────────────────────────────────────────────
font_title = pygame.font.SysFont("Georgia", 52, bold=True)
font_sub = pygame.font.SysFont("Georgia", 20, italic=True)
font_btn = pygame.font.SysFont("Georgia", 22, bold=True)
font_label = pygame.font.SysFont("Georgia", 20)
font_input = pygame.font.SysFont("Courier New", 22)
font_small = pygame.font.SysFont("Georgia", 16)
font_chat = pygame.font.SysFont("Georgia", 17)
font_h2 = pygame.font.SysFont("Georgia", 28, bold=True)
font_h3 = pygame.font.SysFont("Georgia", 22, bold=True)

surf_baslik = font_title.render("KURT ADAM", True, MOON_YELLOW)

ROL_RENK = {
    "kurt_adam": BLOOD_RED,
    "köylü": GRAY_LIGHT,
    "doktor": (60, 160, 80),
    "?": GRAY_DIM,
}

ROL_IKON = {
    "kurt_adam": "W",  # "W" for Wolf
    "köylü": "P",  # "P" for Peasant
    "doktor": "D",  # "D" for Doctor
    "?": "?",
}


# ─── AĞ KATMANI (Socket) ────────────────────────────────────
class AgBaglantisi:
    def __init__(self):
        self.sock = None
        self.bagli = False
        self.hata = None
        self.gelen_kuyruk = []
        self.kilit = threading.Lock()
        self.running = True
        self._thread = None

    def baglan(self, host, port, isim):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((host, port))

            # Sunucu ilk bağlandığında ismi bekliyor
            self.sock.send((isim + "\n").encode("utf-8"))

            # Bağlantı onayını bekle (sadece bağlantının gerçekten kurulduğunu doğrula)
            resp = self.sock.recv(4096).decode("utf-8")
            if not resp:
                raise Exception("Sunucudan yanıt gelmedi")

            self.sock.settimeout(None)
            self.bagli = True
            self.hata = None

            # İlk gelen veriyi kuyruğa ekle (CONNECTION mesajı burada)
            with self.kilit:
                for hat in resp.split("\n"):
                    hat = hat.strip()
                    if hat:
                        self.gelen_kuyruk.append(hat)

            # Dinleme thread'ini başlat
            self._thread = threading.Thread(target=self._dinle, daemon=True)
            self._thread.start()
            return True

        except Exception as e:
            self.hata = "Bağlantı reddedildi veya sunucu bulunamadı."
            self.bagli = False
            return False

    def _dinle(self):
        buffer = ""
        while self.running and self.sock:
            try:
                data = self.sock.recv(4096).decode("utf-8")
                if not data:
                    self.bagli = False
                    break
                buffer += data
                while "\n" in buffer:
                    hat, buffer = buffer.split("\n", 1)
                    hat = hat.strip()
                    if hat:
                        with self.kilit:
                            self.gelen_kuyruk.append(hat)
            except Exception:
                if self.running:
                    time.sleep(0.05)

    def gonder(self, veri: str):
        if not self.sock or not self.bagli:
            return False
        try:
            self.sock.send(veri.encode("utf-8"))
            return True
        except Exception:
            self.bagli = False
            return False

    def mesajlari_al(self):
        with self.kilit:
            msgs = list(self.gelen_kuyruk)
            self.gelen_kuyruk.clear()
        return msgs

    def kapat(self):
        self.running = False
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass


ag = AgBaglantisi()


# ─── İSTEMCİ DURUMU ─────────────────────────────────────────
class IstDurum:
    def __init__(self):
        self.ekran = "baglanti"
        self.kullanici = ""
        self.sunucu_host = "localhost"
        self.aktif_input = None
        self.input_degerler = {
            "host": "localhost",
            "isim": "",
            "chat": "",
        }
        self.t = 0.0
        self.hata_mesaji = ""
        self.hata_t = 0.0

        # Oyun Durumu
        self.benim_rolum = "?"
        self.oyun_durumu = "bekleme"
        self.oyuncular = []
        self.mesajlar = []
        self.scroll_y = 0
        self.oy_hedef = None
        self.gece_hedef = None
        self.kurban_secenekler = []
        self.is_admin = False  # Admin mı?

        self.ag_baglandi = False
        self.baglanti_denemede = False

    def hata_goster(self, mesaj):
        self.hata_mesaji = mesaj
        self.hata_t = self.t

    def input_val(self, key):
        return self.input_degerler.get(key, "")

    def mesaj_ekle(self, icerik, tip="sistem", yazar=""):
        # Emoji veya problemli karakterleri ayıklayalım (basitçe)
        icerik = icerik.replace("\u2600\ufe0f", "")  # Güneş
        icerik = icerik.replace("\u263e", "")  # Ay
        icerik = icerik.replace("\ud83d\udc80", "")  # Kafatası
        icerik = icerik.replace("\u23f1\ufe0f", "")  # Kronometre
        icerik = icerik.replace("\ud83d\udcca", "")  # Bar chart
        icerik = icerik.replace("\ud83c\udfae", "")  # Oyun kolu
        icerik = icerik.replace("\ud83c\udfc1", "")  # Bayrak
        icerik = icerik.replace("\u2705", "")  # Tick
        icerik = icerik.replace("\u274c", "")  # Çarpı

        self.mesajlar.append({"tip": tip, "yazar": yazar, "icerik": icerik.strip()})
        self.scroll_y = 0

    def sunucu_mesaji_isle(self, raw: str):
        if raw.startswith("MESSAGE:"):
            try:
                parca = raw[8:].split(":", 1)
                if len(parca) != 2:
                    return
                tip, json_str = parca
                data = json.loads(json_str)

                if tip == "ROLE":
                    rol = data.get("role", "?")
                    self.benim_rolum = rol
                    self.mesaj_ekle(f"Senin rolün: {rol} {ROL_IKON.get(rol, '')}", "sistem")
                    self.ekran = "oyun"

                elif tip == "GAME_EVENT":
                    state = data.get("state", "")
                    message = data.get("message", "")
                    if state == "GECE":
                        self.oyun_durumu = "gece"
                        self.ekran = "oyun"
                        ag.gonder("PLAYERS")
                    elif state == "GÜN":
                        self.oyun_durumu = "gunduz"
                        self.ekran = "oyun"
                        ag.gonder("PLAYERS")
                    elif state == "OY_VERME":
                        self.oyun_durumu = "oy_verme"
                    elif state == "SABAH":
                        self.oyun_durumu = "sabah"
                    elif state == "OYUN_BAŞLADI":
                        self.oyun_durumu = "basliyor"
                        self.ekran = "oyun"
                        ag.gonder("PLAYERS")
                    elif state == "OYUN_BİTTİ":
                        self.oyun_durumu = "bitti"
                        self.ekran = "bitti"
                    self.mesaj_ekle(message, "sistem")

                elif tip == "ACTION_REQUEST":
                    action = data.get("action", "")
                    if action == "select_victim":
                        self.kurban_secenekler = data.get("options", [])
                        self.mesaj_ekle(data.get("message", "Kimi secersin?"), "sistem")

                elif tip == "CHAT":
                    oyuncu = data.get("player", "?")
                    mesaj = data.get("message", "")
                    self.mesaj_ekle(mesaj, "chat", oyuncu)

                elif tip == "SYSTEM":
                    self.mesaj_ekle(data.get("message", ""), "sistem")
                    ag.gonder("PLAYERS")

                elif tip == "PLAYERS_LIST":
                    liste = data.get("players", [])
                    temiz_liste = []
                    for p in liste:
                        ad = p.split(" (")[0]
                        if "(Canlı)" in p:
                            temiz_liste.append(ad)
                    self.oyuncular = temiz_liste

                elif tip == "CONNECTION":
                    is_admin = data.get("is_admin", False)
                    self.is_admin = is_admin
                    admin_text = " (ADMIN)" if is_admin else ""
                    self.mesaj_ekle(data.get("message", "") + admin_text, "sistem")

            except Exception:
                pass


gs = IstDurum()

# ─── ARKA PLAN VE ÇİZİM YARDIMCILARI ─────────────────────────
_bg_surface = None


def arkaplan_olustur():
    global _bg_surface
    _bg_surface = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        oran = y / HEIGHT
        r = int(NIGHT_BG[0] + (NIGHT_MID[0] - NIGHT_BG[0]) * oran)
        g = int(NIGHT_BG[1] + (NIGHT_MID[1] - NIGHT_BG[1]) * oran)
        b = int(NIGHT_BG[2] + (NIGHT_MID[2] - NIGHT_BG[2]) * oran)
        pygame.draw.line(_bg_surface, (r, g, b), (0, y), (WIDTH, y))


arkaplan_olustur()
_rng_yildiz = random.Random(42)
_yildizlar = [(_rng_yildiz.randint(0, WIDTH), _rng_yildiz.randint(0, HEIGHT // 2), _rng_yildiz.randint(1, 2)) for _ in
              range(120)]


def arkaplan_ciz(t):
    screen.blit(_bg_surface, (0, 0))
    for sx, sy, r in _yildizlar:
        p = int(160 + 80 * math.sin(t * 2 + sx + sy))
        p = max(0, min(255, p))
        pygame.draw.circle(screen, (p, p, p), (sx, sy), r)


def sis_ciz(t):
    sis = pygame.Surface((WIDTH, 60), pygame.SRCALPHA)
    for iy in range(60):
        alpha = int(35 * (1 - iy / 60) * (0.7 + 0.3 * math.sin(t + iy * 0.1)))
        pygame.draw.line(sis, (80, 80, 120, alpha), (0, iy), (WIDTH, iy))
    screen.blit(sis, (0, HEIGHT - 100))


def panel_ciz(x, y, w, h, alpha=200, border=BLOOD_RED):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((8, 5, 15, alpha))
    pygame.draw.rect(s, (*border, 140), (0, 0, w, h), 2)
    screen.blit(s, (x, y))


def buton_ciz(metin, x, y, w=BTN_W, h=BTN_H, aktif=True):
    fare = pygame.mouse.get_pos()
    rect = pygame.Rect(x, y, w, h)
    hover = rect.collidepoint(fare) and aktif
    txt_renk = GRAY_DIM if not aktif else (MOON_YELLOW if hover else GRAY_LIGHT)
    if hover:
        hov_s = pygame.Surface((w, h), pygame.SRCALPHA)
        hov_s.fill((255, 240, 150, 18))
        screen.blit(hov_s, (x, y))
    border = MOON_YELLOW if hover else (BLOOD_RED if aktif else GRAY_DIM)
    pygame.draw.rect(screen, border, rect, 1, border_radius=6)
    txt = font_btn.render(metin, True, txt_renk)
    screen.blit(txt, (x + (w - txt.get_width()) // 2, y + (h - txt.get_height()) // 2))
    return rect


def input_box_ciz(label, key, x, y, w, h=46):
    aktif = gs.aktif_input == key
    etiket = font_label.render(label, True, GRAY_LIGHT)
    screen.blit(etiket, (x, y - 28))
    rect = pygame.Rect(x, y, w, h)
    border = MOON_YELLOW if aktif else BLOOD_RED
    pygame.draw.rect(screen, (20, 14, 30), rect, border_radius=4)
    pygame.draw.rect(screen, border, rect, 2, border_radius=4)
    val = gs.input_val(key)
    goster = val + ("|" if aktif and int(gs.t * 2) % 2 == 0 else "")
    txt = font_input.render(goster, True, WHITE)
    screen.blit(txt, (x + 10, y + (h - txt.get_height()) // 2))
    return rect


def tiklandi(event, rect):
    return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and rect is not None and rect.collidepoint(
        event.pos)


def hata_ciz():
    if not gs.hata_mesaji: return
    sure = gs.t - gs.hata_t
    if sure > 4.0:
        gs.hata_mesaji = ""
        return
    alpha = int(255 * max(0, 1 - sure / 4))
    hata_s = font_label.render(f"Hata: {gs.hata_mesaji}", True, BLOOD_RED)
    bx = WIDTH // 2 - hata_s.get_width() // 2 - 10
    by = HEIGHT - 48
    bg = pygame.Surface((hata_s.get_width() + 20, 36), pygame.SRCALPHA)
    bg.fill((80, 0, 0, min(180, alpha)))
    screen.blit(bg, (bx, by))
    hata_s.set_alpha(alpha)
    screen.blit(hata_s, (bx + 10, by + 6))


# ─── EKRAN ÇİZİMLERİ ─────────────────────────────────────────
def baglanti_ekrani_ciz():
    panel_ciz(WIDTH // 2 - 230, 50, 460, 140)
    screen.blit(surf_baslik, (WIDTH // 2 - surf_baslik.get_width() // 2, 65))

    px, py, pw = WIDTH // 2 - 230, 240, 460
    panel_ciz(px, py, pw, 300)

    baslik = font_h2.render("— Sunucu Bağlantısı —", True, MOON_YELLOW)
    screen.blit(baslik, (WIDTH // 2 - baslik.get_width() // 2, py + 18))

    host_rect = input_box_ciz("Sunucu IP / Host", "host", px + 30, py + 80, pw - 60)
    isim_rect = input_box_ciz("Oyuncu Adı", "isim", px + 30, py + 168, pw - 60)

    aktif = bool(gs.input_val("isim").strip() and gs.input_val("host").strip())

    if gs.baglanti_denemede:
        bag_btn = buton_ciz("Baglaniyor...", px + 30, py + 236, pw - 60, 46, aktif=False)
    else:
        bag_btn = buton_ciz("Baglan & Giris Yap", px + 30, py + 236, pw - 60, 46, aktif=aktif)

    hint = font_small.render("Enter ile de baglanabilirsin", True, GRAY_DIM)
    screen.blit(hint, (px + 30, py + 295))

    return {"host": host_rect, "isim": isim_rect, "baglan": bag_btn}


def bekleme_ekrani_ciz():
    panel_ciz(WIDTH // 2 - 280, 40, 560, 100)
    bas = font_h2.render("Bekleme Odası", True, MOON_YELLOW)
    screen.blit(bas, (WIDTH // 2 - bas.get_width() // 2, 56))

    admin_txt = " [ADMIN]" if gs.is_admin else ""
    alt_t = font_sub.render(f"Sunucu: {gs.sunucu_host}:{DEFAULT_PORT}  -  Sen: {gs.kullanici}{admin_txt}", True, GRAY_LIGHT)
    screen.blit(alt_t, (WIDTH // 2 - alt_t.get_width() // 2, 104))

    panel_ciz(WIDTH // 2 - 280, 158, 560, 330)
    bas_s = font_h3.render("Mevcut Oyuncular", True, MOON_YELLOW)
    screen.blit(bas_s, (WIDTH // 2 - bas_s.get_width() // 2, 170))

    if gs.oyuncular:
        for i, o in enumerate(gs.oyuncular):
            row = i // 3;
            col = i % 3
            ox = WIDTH // 2 - 240 + col * 180
            oy = 212 + row * 50
            renk = MOON_YELLOW if o == gs.kullanici else GRAY_LIGHT
            label = font_label.render(f"{o}", True, renk)
            screen.blit(label, (ox, oy))
    else:
        bekl = font_label.render("Oyuncular bekleniyor...", True, GRAY_DIM)
        screen.blit(bekl, (WIDTH // 2 - bekl.get_width() // 2, 260))

    panel_ciz(WIDTH // 2 - 280, 498, 560, 90, border=BLOOD_DARK)
    for i, m in enumerate(gs.mesajlar[-3:]):
        ms = font_small.render(m["icerik"][:70], True, MOON_YELLOW)
        screen.blit(ms, (WIDTH // 2 - 270, 508 + i * 28))

    if gs.is_admin:
        hint = font_small.render("Oyunu başlatmak için aşağıdaki butona bas", True, GOLD)
    else:
        hint = font_small.render("Admin oyunu başlatmasını bekle...", True, GRAY_DIM)
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 460))

    # Start button - only if admin
    if gs.is_admin:
        num_players = len(gs.oyuncular)
        start_aktif = num_players >= 3
        basla_btn = buton_ciz("Oyunu Başlat", BTN_X, 515, BTN_W, 40, aktif=start_aktif)
        cikis_btn = buton_ciz("Bağlantıyı Kes", BTN_X, 563, BTN_W, 40)
        return {"basla": basla_btn, "cikis": cikis_btn}
    else:
        cikis_btn = buton_ciz("Bağlantıyı Kes", BTN_X, 540, BTN_W, 40)
        return {"cikis": cikis_btn}


def oyun_ekrani_ciz():
    CHAT_X, CHAT_Y, CHAT_W, CHAT_H = 0, 50, 460, HEIGHT - 50
    OY_X, OY_W = 460, WIDTH - 460

    DURUM_TXT = {
        "gece": "GECE - Roller Uyanıyor",
        "gunduz": "GÜNDÜZ - Tartışma",
        "oy_verme": "OY VERME - Kimi Çıkaralım?",
        "sabah": "SABAH - Sonuçlar",
        "basliyor": "OYUN BAŞLIYOR",
        "bekleme": "Bekleniyor...",
    }

    # Üst bar
    dus = pygame.Surface((WIDTH, 50), pygame.SRCALPHA)
    dus.fill((40, 40, 80, 55))
    screen.blit(dus, (0, 0))

    fs = font_btn.render(DURUM_TXT.get(gs.oyun_durumu, ""), True, MOON_YELLOW)
    screen.blit(fs, (WIDTH // 2 - fs.get_width() // 2, 12))

    rol_s = font_small.render(f"Rolün: {gs.benim_rolum}", True, ROL_RENK.get(gs.benim_rolum, GRAY_DIM))
    screen.blit(rol_s, (WIDTH - rol_s.get_width() - 12, 14))

    # Chat paneli
    panel_ciz(CHAT_X, CHAT_Y, CHAT_W, CHAT_H, alpha=215, border=BLOOD_RED)
    screen.blit(font_btn.render("Sohbet", True, MOON_YELLOW), (CHAT_X + 14, CHAT_Y + 10))
    pygame.draw.line(screen, BLOOD_DARK, (CHAT_X + 10, CHAT_Y + 38), (CHAT_X + CHAT_W - 10, CHAT_Y + 38), 1)

    clip = pygame.Rect(CHAT_X, CHAT_Y + 44, CHAT_W, CHAT_H - 90)
    screen.set_clip(clip)
    my = CHAT_Y + 48 + gs.scroll_y
    for m in gs.mesajlar:
        yazar, icerik, tip = m.get("yazar", ""), m.get("icerik", ""), m.get("tip", "chat")

        if tip == "sistem":
            renk = MOON_YELLOW;
            prefix = "* "
        elif yazar == gs.kullanici:
            renk = (120, 200, 140);
            prefix = "Sen: "
        else:
            renk = GRAY_LIGHT;
            prefix = f"{yazar}: " if yazar else ""

        satir, satirlar = "", []
        for k in (prefix + icerik).split():
            test = satir + (" " if satir else "") + k
            if font_chat.size(test)[0] > CHAT_W - 28:
                if satir: satirlar.append(satir)
                satir = k
            else:
                satir = test
        if satir: satirlar.append(satir)
        for s in satirlar:
            screen.blit(font_chat.render(s, True, renk), (CHAT_X + 12, my))
            my += 22
        my += 4
    screen.set_clip(None)

    ci = pygame.Rect(CHAT_X + 8, CHAT_Y + CHAT_H - 46, CHAT_W - 72, 38)
    pygame.draw.rect(screen, (20, 14, 30), ci, border_radius=4)
    pygame.draw.rect(screen, MOON_YELLOW if gs.aktif_input == "chat" else BLOOD_DARK, ci, 1, border_radius=4)

    ci_txt = font_chat.render(gs.input_val("chat"), True, WHITE)
    screen.blit(ci_txt, (ci.x + 8, ci.y + (38 - ci_txt.get_height()) // 2))

    send_r = pygame.Rect(CHAT_X + CHAT_W - 62, CHAT_Y + CHAT_H - 46, 58, 38)
    pygame.draw.rect(screen, BLOOD_RED, send_r, border_radius=4)
    gon = font_small.render("Gonder", True, WHITE)
    screen.blit(gon, (send_r.x + (58 - gon.get_width()) // 2, send_r.y + (38 - gon.get_height()) // 2))

    # Sağ panel
    panel_ciz(OY_X, CHAT_Y, OY_W, CHAT_H, alpha=215, border=(80, 40, 100))
    sag_bas_txt = "Kimi Çıkaralım?" if gs.oyun_durumu == "oy_verme" else (
        "Kurban Seç" if gs.oyun_durumu == "gece" and gs.kurban_secenekler else "Oyuncular")
    screen.blit(font_btn.render(sag_bas_txt, True, MOON_YELLOW), (OY_X + 14, CHAT_Y + 10))
    pygame.draw.line(screen, (80, 40, 100), (OY_X + 10, CHAT_Y + 36), (OY_X + OY_W - 10, CHAT_Y + 36), 1)

    oy_rektleri = {}
    liste = gs.kurban_secenekler if (gs.oyun_durumu == "gece" and gs.kurban_secenekler) else gs.oyuncular

    for idx, ad in enumerate(liste):
        if ad == gs.kullanici: continue  # Kendine tıklayamasın

        r = pygame.Rect(OY_X + 14, CHAT_Y + 48 + idx * 49, OY_W - 28, 42)
        secili = (gs.oy_hedef == ad) or (gs.gece_hedef == ad)

        pygame.draw.rect(screen, BLOOD_RED if secili else BLOOD_DARK, r, border_radius=5)
        pygame.draw.rect(screen, MOON_YELLOW if secili else (80, 40, 100), r, 1, border_radius=5)

        oy_txt = font_btn.render(("" if secili else "") + ad, True, MOON_YELLOW if secili else GRAY_LIGHT)
        screen.blit(oy_txt, (r.x + 12, r.y + (42 - oy_txt.get_height()) // 2))
        oy_rektleri[ad] = r

    gonder_aktif = bool(gs.oy_hedef or gs.gece_hedef)
    oyku_r = pygame.Rect(OY_X + 14, CHAT_Y + CHAT_H - 54, OY_W - 28, 44)
    pygame.draw.rect(screen, BLOOD_RED if gonder_aktif else BLOOD_DARK, oyku_r, border_radius=5)
    pygame.draw.rect(screen, BLOOD_RED, oyku_r, 1, border_radius=5)

    ok_s = font_btn.render("Kararı Gonder ->", True, MOON_YELLOW if gonder_aktif else GRAY_DIM)
    screen.blit(ok_s, (oyku_r.x + (oyku_r.w - ok_s.get_width()) // 2, oyku_r.y + (44 - ok_s.get_height()) // 2))

    return {"chat_input": ci, "send": send_r, "oy_gonder": oyku_r, **oy_rektleri}


def bitti_ekrani_ciz():
    panel_ciz(WIDTH // 2 - 300, 80, 600, 460, alpha=240)
    bas = font_h2.render("Oyun Bitti", True, MOON_YELLOW)
    screen.blit(bas, (WIDTH // 2 - bas.get_width() // 2, 100))
    pygame.draw.line(screen, BLOOD_RED, (WIDTH // 2 - 260, 145), (WIDTH // 2 + 260, 145), 1)

    for i, m in enumerate([m for m in gs.mesajlar if m.get("tip") == "sistem"][-8:]):
        s = font_chat.render(m.get("icerik", ""), True, MOON_YELLOW)
        screen.blit(s, (WIDTH // 2 - s.get_width() // 2, 160 + i * 36))

    return {"cikis": buton_ciz("Cikis", BTN_X, 480, BTN_W, 42)}


# ─── ANA BAĞLANTI HELPER ─────────────────────────────────────
def baglanmaya_calis():
    host, isim = gs.input_val("host").strip(), gs.input_val("isim").strip()
    if not host or not isim:
        gs.hata_goster("Host ve isim bos birakilamaz!")
        return

    gs.baglanti_denemede = True
    gs.sunucu_host = host

    def _baglan():
        if ag.baglan(host, DEFAULT_PORT, isim):
            gs.kullanici = isim
            gs.ekran = "bekleme"
            gs.mesaj_ekle("Sunucuya basariyla baglandiniz!", "sistem")
        else:
            gs.hata_goster(f"Hata: {ag.hata}")
        gs.baglanti_denemede = False

    threading.Thread(target=_baglan, daemon=True).start()


# ─── ANA DÖNGÜ ───────────────────────────────────────────────
def main():
    while True:
        gs.t += clock.tick(FPS) / 1000.0
        gs.ag_baglandi = ag.bagli

        for raw in ag.mesajlari_al():
            gs.sunucu_mesaji_isle(raw)

        arkaplan_ciz(gs.t)
        sis_ciz(gs.t)

        if gs.ekran == "baglanti":
            rektler = baglanti_ekrani_ciz()
        elif gs.ekran == "bekleme":
            rektler = bekleme_ekrani_ciz()
        elif gs.ekran == "oyun":
            rektler = oyun_ekrani_ciz()
        elif gs.ekran == "bitti":
            rektler = bitti_ekrani_ciz()
        else:
            rektler = {}

        hata_ciz()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                ag.kapat();
                pygame.quit();
                sys.exit()

            if gs.ekran == "baglanti":
                for key in ("host", "isim"):
                    if tiklandi(event, rektler.get(key)): gs.aktif_input = key

                if event.type == pygame.KEYDOWN and gs.aktif_input in ("host", "isim"):
                    if event.key == pygame.K_BACKSPACE:
                        gs.input_degerler[gs.aktif_input] = gs.input_degerler[gs.aktif_input][:-1]
                    elif event.key == pygame.K_TAB:
                        gs.aktif_input = "isim" if gs.aktif_input == "host" else "host"
                    elif event.key == pygame.K_RETURN:
                        baglanmaya_calis()
                    else:
                        gs.input_degerler[gs.aktif_input] += event.unicode

                if tiklandi(event, rektler.get("baglan")) and not gs.baglanti_denemede:
                    baglanmaya_calis()

            elif gs.ekran == "bekleme":
                if tiklandi(event, rektler.get("cikis")):
                    ag.kapat();
                    pygame.quit();
                    sys.exit()
                
                if gs.is_admin and tiklandi(event, rektler.get("basla")):
                    # Start game - send message to server
                    num_players = len(gs.oyuncular)
                    if num_players >= 3:
                        ag.gonder("START_GAME\n")
                        gs.mesaj_ekle("Oyun başlatılıyor...", "sistem")

            elif gs.ekran == "oyun":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    gs.aktif_input = "chat" if rektler.get("chat_input") and rektler["chat_input"].collidepoint(
                        event.pos) else None

                if event.type == pygame.KEYDOWN and gs.aktif_input == "chat":
                    if event.key == pygame.K_BACKSPACE:
                        gs.input_degerler["chat"] = gs.input_degerler["chat"][:-1]
                    elif event.key == pygame.K_RETURN:
                        val = gs.input_val("chat").strip()
                        if val and ag.gonder(f"MESSAGE:CHAT:{json.dumps({'message': val})}\n"):
                            gs.input_degerler["chat"] = ""
                    else:
                        gs.input_degerler["chat"] += event.unicode

                if tiklandi(event, rektler.get("send")):
                    val = gs.input_val("chat").strip()
                    if val and ag.gonder(f"MESSAGE:CHAT:{json.dumps({'message': val})}\n"):
                        gs.input_degerler["chat"] = ""

                liste = gs.kurban_secenekler if (gs.oyun_durumu == "gece" and gs.kurban_secenekler) else gs.oyuncular
                for ad in liste:
                    if tiklandi(event, rektler.get(ad)):
                        if gs.oyun_durumu == "oy_verme":
                            gs.oy_hedef = ad
                        elif gs.oyun_durumu == "gece":
                            gs.gece_hedef = ad

                if tiklandi(event, rektler.get("oy_gonder")):
                    if gs.oyun_durumu == "oy_verme" and gs.oy_hedef:
                        ag.gonder(f"VOTE:{gs.oy_hedef}\n")
                        gs.oy_hedef = None
                    elif gs.oyun_durumu == "gece" and gs.gece_hedef:
                        ag.gonder(f"KILL:{gs.gece_hedef}\n")
                        gs.gece_hedef = None
                        gs.kurban_secenekler = []

                if event.type == pygame.MOUSEWHEEL:
                    gs.scroll_y = min(0, gs.scroll_y + event.y * 18)

            elif gs.ekran == "bitti":
                if tiklandi(event, rektler.get("cikis")):
                    ag.kapat();
                    pygame.quit();
                    sys.exit()

        pygame.display.update()


if __name__ == "__main__":
    main()