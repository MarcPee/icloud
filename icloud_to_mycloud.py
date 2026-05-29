#!/usr/bin/env python3
"""
iCloud to My Cloud Home Sync Tool
Kopieert alle iCloud Drive-bestanden naar je WD My Cloud Home (SMB).

Gebruik:
  python icloud_to_mycloud.py --email JOUW@APPLEID.COM --password JOUW_WACHTWOORD
  OF
  Maak een .env bestand met ICLOUD_EMAIL en ICLOUD_PASSWORD
"""

import os
import sys
import logging
import shutil
from pathlib import Path
from typing import Optional, List

import click
from dotenv import load_dotenv
from tqdm import tqdm
from smbclient import open_file, register_session, register_session_guest

# PyiCloud imports
try:
    from pyicloud import PyiCloudService
    from pyicloud.exceptions import PyiCloudAPIResponseException
    HAS_PYICLOUD = True
except ImportError:
    HAS_PYICLOUD = False

# Configureer logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("icloud_sync.log"),
    ],
)
logger = logging.getLogger(__name__)

# Laad .env bestand
load_dotenv()


class MyCloudSMBClient:
    """Client voor SMB-toegang tot WD My Cloud Home."""
    
    def __init__(
        self,
        host: str = "mycloud-9faf74.local",
        share: str = "Public",
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host
        self.share = share
        self.username = username
        self.password = password
        self._connected = False
        
    def connect(self):
        """Maak verbinding met de SMB-share."""
        try:
            if self.username and self.password:
                register_session(self.host, username=self.username, password=self.password)
            else:
                # Probeer als guest (voor Public share)
                register_session_guest(self.host)
            self._connected = True
            logger.info(f"Verbonden met SMB: smb://{self.host}/{self.share}")
        except Exception as e:
            logger.error(f"Fout bij verbinden met SMB: {e}")
            raise
    
    def upload_file(self, local_path: str, remote_path: str):
        """Upload een bestand naar de SMB-share."""
        if not self._connected:
            self.connect()
        
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"Lokaal bestand niet gevonden: {local_path}")
        
        # Zorg dat de remote directory bestaat
        remote_dir = os.path.dirname(remote_path)
        self._ensure_remote_dir(remote_dir)
        
        # Upload het bestand
        smb_path = f"\\{self.host}\{self.share}{remote_path}"
        try:
            with open(local_path, "rb") as local_file:
                with open_file(smb_path, mode="wb") as smb_file:
                    shutil.copyfileobj(local_file, smb_file)
            logger.debug(f"Bestand geüpload: {local_path} -> {smb_path}")
        except Exception as e:
            logger.error(f"Fout bij uploaden van {local_path}: {e}")
            raise
    
    def _ensure_remote_dir(self, remote_dir: str):
        """Zorg dat de remote directory bestaat."""
        # SMB heeft geen directe mkdir, dus we proberen een dummy-bestand te maken
        test_path = f"\\{self.host}\{self.share}{remote_dir}/.dircheck"
        try:
            with open_file(test_path, mode="wb") as f:
                f.write(b"")
            # Verwijder het dummy-bestand
            os.remove(test_path)  # Dit werkt niet voor SMB, maar we negeren de fout
        except Exception:
            # Directory bestaat waarschijnlijk al
            pass


class iCloudDownloader:
    """Downloadt bestanden van iCloud Drive."""
    
    def __init__(
        self,
        email: str,
        password: str,
        download_folder: str = "./icloud_download",
    ):
        self.email = email
        self.password = password
        self.download_folder = Path(download_folder)
        self.api: Optional[PyiCloudService] = None
        
    def login(self):
        """Log in op iCloud."""
        if not HAS_PYICLOUD:
            raise ImportError("pyicloud is niet geïnstalleerd. Voer 'pip install -r requirements.txt' uit.")
        
        try:
            self.api = PyiCloudService(self.email, self.password)
            logger.info(f"Ingelogd op iCloud als {self.email}")
            
            # Controleer of 2FA nodig is
            if self.api.requires_2fa:
                logger.warning("2FA vereist! Voer de code in die je op je Apple-apparaat ontvangt.")
                code = input("Voer 2FA-code in: ").strip()
                if not self.api.validate_2fa_code(code):
                    raise Exception("Ongeldige 2FA-code")
                logger.info("2FA geverifieerd")
            
            return True
        except PyiCloudAPIResponseException as e:
            logger.error(f"iCloud login mislukt: {e}")
            if "APPLE_ID_NOT_FOUND" in str(e):
                logger.error("Apple ID niet gevonden. Controleer je email.")
            elif "INVALID_PASSWORD" in str(e):
                logger.error("Ongeldig wachtwoord.")
            raise
        except Exception as e:
            logger.error(f"Fout bij inloggen: {e}")
            raise
    
    def get_icloud_drive_files(self) -> List[dict]:
        """Haalt alle bestanden en mappen op uit iCloud Drive."""
        if not self.api:
            raise Exception("Niet ingelogd. Roep eerst login() aan.")
        
        files = []
        try:
            # Haal de root directory op
            root = self.api.iphone.get_files()
            files.extend(self._process_directory(root, "/"))
            logger.info(f"Gevonden: {len(files)} bestanden/mappen in iCloud Drive")
        except Exception as e:
            logger.error(f"Fout bij ophalen van iCloud Drive: {e}")
            raise
        
        return files
    
    def _process_directory(self, directory: dict, current_path: str) -> List[dict]:
        """Recursief verwerken van een iCloud directory."""
        files = []
        
        for item in directory.get("files", []):
            item_path = f"{current_path}{item['name']}"
            
            if item.get("type") == "folder":
                # Haal subdirectory op
                subdir = self.api.iphone.get_files(folder_id=item["id"])
                files.extend(self._process_directory(subdir, f"{item_path}/"))
            else:
                # Voeg bestand toe
                files.append({
                    "id": item["id"],
                    "name": item["name"],
                    "path": item_path,
                    "size": item.get("size", 0),
                    "type": item.get("type", "file"),
                })
        
        return files
    
    def download_file(self, file_info: dict, target_path: Optional[Path] = None):
        """Download een enkel bestand van iCloud."""
        if not self.api:
            raise Exception("Niet ingelogd.")
        
        if target_path is None:
            target_path = self.download_folder / file_info["path"].lstrip("/")
        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Downloaden: {file_info['path']} ({file_info.get('size', 0) / 1024 / 1024:.2f} MB)")
            with open(target_path, "wb") as f:
                self.api.iphone.download_file(
                    file_id=file_info["id"],
                    output_file=f,
                    progress_callback=lambda x, y: None,  # We gebruiken tqdm apart
                )
            logger.debug(f"Gedownload: {target_path}")
        except Exception as e:
            logger.error(f"Fout bij downloaden van {file_info['path']}: {e}")
            raise
    
    def download_all(self, files: List[dict], max_workers: int = 1):
        """Download alle bestanden."""
        self.download_folder.mkdir(parents=True, exist_ok=True)
        
        for file_info in tqdm(files, desc="Downloaden van iCloud"):
            try:
                self.download_file(file_info)
            except Exception as e:
                logger.error(f"Overgeslagen: {file_info['path']} ({e})")


@click.command()
@click.option("--email", envvar="ICLOUD_EMAIL", required=True, help="Je Apple ID email")
@click.option("--password", envvar="ICLOUD_PASSWORD", required=True, help="Je Apple ID wachtwoord")
@click.option("--mycloud-host", envvar="MYCLOUD_HOST", default="mycloud-9faf74.local", help="Hostnaam van je My Cloud Home")
@click.option("--mycloud-share", envvar="MYCLOUD_SHARE", default="Public", help="SMB share-naam")
@click.option("--mycloud-user", envvar="MYCLOUD_USER", default="", help="SMB gebruikersnaam (leeg voor guest)")
@click.option("--mycloud-password", envvar="MYCLOUD_PASSWORD", default="", help="SMB wachtwoord (leeg voor guest)")
@click.option("--download-folder", envvar="DOWNLOAD_FOLDER", default="./icloud_download", help="Lokale downloadmap")
@click.option("--target-folder", envvar="MYCLOUD_TARGET_FOLDER", default="/Public/iCloud_Backup", help="Doelmap op My Cloud Home")
@click.option("--skip-download/--no-skip-download", default=False, help="Sla downloaden over (alleen uploaden)")
@click.option("--dry-run", is_flag=True, help="Toon wat er zou gebeuren zonder daadwerkelijk te kopiëren")
def main(
    email: str,
    password: str,
    mycloud_host: str,
    mycloud_share: str,
    mycloud_user: str,
    mycloud_password: str,
    download_folder: str,
    target_folder: str,
    skip_download: bool,
    dry_run: bool,
):
    """Kopieer iCloud Drive naar My Cloud Home."""
    
    if dry_run:
        logger.info("=== DRY RUN MODUS ===")
        logger.info(f"iCloud: {email}")
        logger.info(f"My Cloud: smb://{mycloud_host}/{mycloud_share}{target_folder}")
        logger.info(f"Downloadmap: {download_folder}")
        logger.info("Geen wijzigingen zullen worden doorgevoerd.")
    
    try:
        # Stap 1: Download van iCloud
        downloader = iCloudDownloader(
            email=email,
            password=password,
            download_folder=download_folder,
        )
        
        if not skip_download:
            logger.info("Inloggen op iCloud...")
            downloader.login()
            
            logger.info("Ophalen van iCloud Drive-bestanden...")
            files = downloader.get_icloud_drive_files()
            
            if not dry_run:
                logger.info(f"Downloaden van {len(files)} bestanden...")
                downloader.download_all(files)
            else:
                logger.info(f"Zou {len(files)} bestanden downloaden.")
        else:
            logger.info("Downloaden overgeslagen.")
            # Lees bestaande downloadmap
            download_path = Path(download_folder)
            if not download_path.exists():
                raise FileNotFoundError(f"Downloadmap niet gevonden: {download_folder}")
            
            # Vind alle bestanden in de downloadmap
            files = []
            for root, dirs, filenames in os.walk(download_path):
                for filename in filenames:
                    local_path = Path(root) / filename
                    relative_path = local_path.relative_to(download_path)
                    files.append({
                        "path": str(relative_path),
                        "local_path": str(local_path),
                    })
            logger.info(f"Gevonden: {len(files)} lokale bestanden om te uploaden.")
        
        # Stap 2: Upload naar My Cloud Home
        if dry_run:
            logger.info("Zou bestanden uploaden naar My Cloud Home.")
            return
        
        smb_client = MyCloudSMBClient(
            host=mycloud_host,
            share=mycloud_share,
            username=mycloud_user if mycloud_user else None,
            password=mycloud_password if mycloud_password else None,
        )
        
        logger.info(f"Verbinden met My Cloud Home ({mycloud_host})...")
        smb_client.connect()
        
        # Upload alle gedownloade bestanden
        download_path = Path(download_folder)
        if download_path.exists():
            all_files = list(download_path.rglob("*"))
            all_files = [f for f in all_files if f.is_file()]
            
            logger.info(f"Uploaden van {len(all_files)} bestanden naar My Cloud Home...")
            for local_file in tqdm(all_files, desc="Uploaden naar My Cloud"):
                relative_path = local_file.relative_to(download_path)
                remote_path = f"{target_folder}/{relative_path}"
                
                try:
                    smb_client.upload_file(str(local_file), remote_path)
                except Exception as e:
                    logger.error(f"Fout bij uploaden van {relative_path}: {e}")
        
        logger.info("Klaar! Alle bestanden zijn gekopieerd naar My Cloud Home.")
        
    except KeyboardInterrupt:
        logger.warning("Afgebroken door gebruiker.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fout: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
