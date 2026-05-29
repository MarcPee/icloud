# iCloud to My Cloud Home Sync 📁➡️🖥️

Een Python-tool om **alle iCloud Drive-bestanden** (foto's, documenten, video's, etc.) te kopiëren naar je **WD My Cloud Home** in je lokale netwerk.

---

## 📌 Vereisten

- **Python 3.8+** (of Docker)
- **WD My Cloud Home** bereikbaar in je lokale netwerk (bijv. `mycloud-9faf74.local`)
- **Apple ID** met toegang tot iCloud Drive
- **2FA (Tweestapsverificatie)** ingeschakeld op je Apple ID (aanbevolen)

---

## 🚀 Snelle Start

### Optie 1: Direct met Python

1. **Kloon de repository** (of download de bestanden):
   ```bash
   git clone https://github.com/MarcPee/icloud.git
   cd icloud
   ```

2. **Installeer afhankelijkheden**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Maak een `.env` bestand** (kopieer van `.env.example`):
   ```bash
   cp .env.example .env
   ```
   
   Bewerk `.env` met je gegevens:
   ```ini
   ICLOUD_EMAIL=jouw@appleid.com
   ICLOUD_PASSWORD=jouw_wachtwoord
   MYCLOUD_HOST=mycloud-9faf74.local
   MYCLOUD_SHARE=Public
   ```

4. **Voer de tool uit**:
   ```bash
   python icloud_to_mycloud.py
   ```

   - Als je **2FA** hebt, wordt je gevraagd om de code in te voeren.
   - Bestanden worden eerst gedownload naar `./icloud_download` en daarna geüpload naar je My Cloud Home.

---

### Optie 2: Met Docker (aanbevolen)

1. **Bouw de Docker-image**:
   ```bash
   docker build -t icloud-to-mycloud .
   ```

2. **Voer de container uit** (met je `.env` bestand):
   ```bash
   docker run --rm -it \
     --env-file .env \
     -v $(pwd)/icloud_download:/app/icloud_download \
     icloud-to-mycloud
   ```

   - De gedownloade bestanden worden opgeslagen in `./icloud_download` op je host.

---

## 🔧 Gebruik

### Basiscommando's

| Commando | Beschrijving |
|----------|--------------|
| `python icloud_to_mycloud.py` | Voer uit met `.env` instellingen |
| `python icloud_to_mycloud.py --email JOUW@EMAIL --password WACHTWOORD` | Direct opgeven van inloggegevens |
| `python icloud_to_mycloud.py --dry-run` | Toon wat er zou gebeuren (geen wijzigingen) |
| `python icloud_to_mycloud.py --skip-download` | Upload alleen (als je al gedownload hebt) |

### Voorbeelden

1. **Alleen downloaden (geen upload)**:
   ```bash
   python icloud_to_mycloud.py --skip-download false
   ```

2. **Alleen uploaden (als je al gedownload hebt)**:
   ```bash
   python icloud_to_mycloud.py --skip-download true
   ```

3. **Aangepaste doelmap op My Cloud Home**:
   ```bash
   python icloud_to_mycloud.py --target-folder /Public/iCloud_Backup_2024
   ```

4. **Met SMB-authenticatie** (als je My Cloud Home een wachtwoord heeft):
   ```bash
   python icloud_to_mycloud.py \
     --mycloud-user admin \
     --mycloud-password JOUW_MYCLOUD_WACHTWOORD
   ```

---

## ⚙️ Configuratie

| Variabele | Beschrijving | Standaard |
|-----------|--------------|-----------|
| `ICLOUD_EMAIL` | Je Apple ID email | - |
| `ICLOUD_PASSWORD` | Je Apple ID wachtwoord | - |
| `MYCLOUD_HOST` | Hostnaam/IP van My Cloud Home | `mycloud-9faf74.local` |
| `MYCLOUD_SHARE` | SMB share-naam | `Public` |
| `MYCLOUD_USER` | SMB gebruikersnaam (leeg voor guest) | - |
| `MYCLOUD_PASSWORD` | SMB wachtwoord | - |
| `DOWNLOAD_FOLDER` | Lokale downloadmap | `./icloud_download` |
| `MYCLOUD_TARGET_FOLDER` | Doelmap op My Cloud Home | `/Public/iCloud_Backup` |

---

## 🔍 Problemen Oplossen

### 1. **iCloud Login Mislukt**
- **Fout**: `APPLE_ID_NOT_FOUND` → Controleer je email.
- **Fout**: `INVALID_PASSWORD` → Controleer je wachtwoord.
- **2FA vereist**: Voer de code in die je op je Apple-apparaat ontvangt.

### 2. **SMB Verbinding Mislukt**
- **Controleer of je My Cloud Home bereikbaar is**:
  ```bash
  ping mycloud-9faf74.local
  ```
- **Controleer of SMB werkt**:
  ```bash
  smbclient -L //mycloud-9faf74.local -N
  ```
- **Als je een wachtwoord hebt**, geef dan `--mycloud-user` en `--mycloud-password` op.

### 3. **Langzame downloads**
- iCloud heeft **rate limits**. Als je veel bestanden hebt, kan het lang duren.
- Gebruik `--skip-download` om alleen nieuwe bestanden te uploaden.

### 4. **Bestanden worden niet geüpload**
- Controleer of de **Public share** schrijfrechten heeft.
- Probeer handmatig een bestand te kopiëren naar `\\mycloud-9faf74.local\Public` (Windows) of `smb://mycloud-9faf74.local/Public` (macOS/Linux).

---

## 📂 Bestandsstructuur

```
.
├── icloud_to_mycloud.py  # Hoofdscript
├── requirements.txt       # Python afhankelijkheden
├── Dockerfile            # Docker configuratie
├── .env.example          # Voorbeeld configuratie
├── .env                  # Je eigen configuratie (niet commiten!)
└── icloud_download/      # Tijdelijke downloadmap
```

---

## 🔒 Veiligheid

- **Nooit** je `.env` bestand commiten naar Git!
- Gebruik **2FA** voor extra beveiliging.
- Als je Docker gebruikt, **verwijder de container na gebruik** om gegevens te beschermen:
  ```bash
  docker rm -f icloud-to-mycloud
  ```

---

## 🤝 Bijdragen

1. Fork de repository.
2. Maak een feature branch (`git checkout -b feature/nieuwe-functie`).
3. Commit je wijzigingen (`git commit -am 'Voeg nieuwe functie toe'`).
4. Push naar de branch (`git push origin feature/nieuwe-functie`).
5. Open een Pull Request.

---

## 📜 Licentie

MIT License – zie [LICENSE](LICENSE) voor details.
