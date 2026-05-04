# Kurt Adam Oyunu (Werewolf Game) - Python Socket Projesi

## Proje Açıklaması
Multiplayer Werewolf (Kurt Adam) oyunu - Socket programını kullanarak Python'da yapılan client-server mimarili ağ uygulaması.

## Proje Aşamaları

### ✅ Aşama 1: Lokal Sunucu Kurulumu (TAMAMLANDI)
- Socket kütüphanesi kullanarak sunucu oluşturuldu
- Server bağlantıları accept ediyor
- Client'dan oyuncu ismi alıyor
- Bağlantı kabulü mesajı gönderiyor
- Thread-based multi-client bağlantı

### ✅ Aşama 2: Mesajlaşma Sistemi (TAMAMLANDI)
- ✨ **Broadcast fonksiyonu** - Tüm client'lara aynı mesaj gönderme
- 💬 **Chat Sistemi** - Oyuncular birbirlerine mesaj gönderebiliyor
- 🎨 **Tkinter GUI** - Kullanıcı dostu arayüz
- 👥 **Oyuncu Yönetimi** - Kim bağlandı/ayrıldı bilgileri

**Dosyalar:**
- `server.py` - Broadcast ve chat serveri
- `client.py` - Basit terminal client (opsiyonel)
- `client_gui.py` - ⭐ Tkinter GUI client (Ana oyun istemcisi)
- `README.md` - Bu dosya

**Çalıştırma (Yeni yöntem):**
```bash
# Terminal 1 - Sunucuyu başlat
python server.py

# Terminal 2, 3, vb - GUI Client'ları bağla
python client_gui.py
```

**Arayüz Özellikleri:**
- 👤 Oyuncu ismi girişi
- 💬 Renkli chat bölümü
  - 🟠 Sistem mesajları (sarı)
  - 🔵 Diğer oyuncu mesajları (mavi)
  - 🟢 Kendi mesajlarınız (yeşil)
- 📤 Mesaj gönderme (Enter tuşu veya buton)
- 👥 Çevrimiçi oyuncuları görme
- 🌙 Gece/Gün döngüsü için hazır

---

### ✅ Aşama 3: Gece/Gün Döngüsü & Rol Sistemi (TAMAMLANDI)
- 🌙 **Gece Rotasyonu** - Kurt adamlar kimi öldürecekler
- ☀️ **Gün Rotasyonu** - Herkes tartışıp suçlayabiliyor
- 👹 **Rol Atama** - Kurt Adam vs. Köylü
- 🎮 **Oyun Döngüsü** - BEKLEME → GECE → GÜN → OY_VERME → ... (otomatik)
- 📊 **Oy Verme Sistemi** - Gün rotasyonunda en çok oy alan oyuncu dışarı çıkıyor
- 🏁 **Oyun Bitme Koşulları** - Kurt Adam sayısı >= Köylü sayısı veya Kurt Adam sayısı = 0
- 🔄 **Durum Göstergesi** - Üst panel'de oyunun şu anki durumu

**Oyun Akışı:**
1. Minimum 3 oyuncu bağlanırsa oyun başlıyor
2. Tüm oyunculara rol atanıyor (Kurt Adam = 1/3, Köylü = 2/3)
3. **GECE (30 saniye):** Kurt adamlar kurban seçerler
4. **SABAH:** Seçilen oyuncu öldürülür ve herkes bilgilendirilir
5. **GÜN (30 saniye):** Tüm oyuncular tartışırlar
6. **OY VERME (20 saniye):** Herkes birini suçlar (VOTE:adı)
7. En çok oy alan oyuncu dışarı çıkarılır
8. Oyun bitme kontrolü yapılır → Tekrar GECE'ye dön

**Komutlar:**
- `VOTE:oyuncuAdı` - Oy ver (Gün rotasyonunda)
- KILL seçeneği - GUI'de button ile (Kurt adamlar için)

**Çalıştırma:**
```bash
# Terminal 1 - Sunucuyu başlat
python server.py

# Terminal 2, 3, 4... - 3+ istemci bağla
python client_gui.py
```

---

### ⏳ Aşama 4: Oyun Sonu Şartları (Otomatik İmplemente Edildi)
- ✅ Kurt Adam sayı kontrolü (≥ Köylü sayısı = Kurt Adam kazanır)
- ✅ Köylü kontrol (Kurt Adam sayısı = 0 = Köylü kazanır)
- ✅ Oyun bitme mesajları
- ✅ Yukarı Tema kısmı otomatik tekrar başlıyor

---

## Teknoloji Stack
- Python 3.x
- `socket` - Socket programlaması
- `threading` - Multi-client işleme

## Notlar
- Şu anda Stage 1 tamamlandı
- Her aşama öncekine temel oluşturuyor
- Thread-safe işlemler için Lock kullanılıyor

---

## 🌐 Ağ Üzerinden Bağlantı (Başka Bilgisayarlar)

### Kurulum Adımları:

**1. Sunucu Bilgisayarında:**
- `server.py` dosyasını çalıştırın
- Terminal'de sunucunun IP adresini bulun:
  ```bash
  # Windows'ta
  ipconfig
  # Linux/Mac'te  
  ifconfig
  ```
- IPv4 adresini yazın (örn: `192.168.1.100`)

**2. Client Bilgisayarında:**
- Aşağıdaki dosyaları sunucu bilgisayarından al:
  - `client_gui.py` (GUI client)
  - `client.py` (Terminal client)
  - `test_game.py` (Test scripti)
  
- **GUI Client çalıştır:**
  ```bash
  python client_gui.py
  ```
  - Sunucu IP adresini sor popup'ta gir: `192.168.1.100`
  - Oyuncu ismini gir
  
- **Terminal Client çalıştır:**
  ```bash
  python client.py
  ```
  - Sunucu IP adresini gir: `192.168.1.100`
  - Oyuncu ismini gir

### Gereksinimler:
- ✅ Tüm bilgisayarlar **aynı WiFi/ağda** olmalı
- ✅ Sunucu bilgisayarının IP adresi bilinmeli
- ✅ Firewall'da 5000 portuna izin olmalı (Windows Defender açılabilir)

### Firewall Açmak (Windows):
1. **Windows Defender Firewall** → Gelişmiş ayarlar
2. **Gelen Kuralları** → Yeni Kural
3. Port: `5000`, Protokol: `TCP`
4. Ağın türü: Özel/Genel seçin
