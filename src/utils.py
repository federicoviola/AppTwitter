"""Utilidades comunes para la aplicación."""

import hashlib
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


def get_project_root() -> Path:
    """Obtener la raíz del proyecto."""
    return Path(__file__).parent.parent


def get_data_dir() -> Path:
    """Obtener el directorio de datos."""
    data_dir = get_project_root() / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


def get_logs_dir() -> Path:
    """Obtener el directorio de logs."""
    logs_dir = get_project_root() / "logs"
    logs_dir.mkdir(exist_ok=True)
    return logs_dir


def setup_logging(level: str = None) -> logging.Logger:
    """Configurar logging."""
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    
    log_file = get_logs_dir() / "app.log"
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger("apptwitter")


def normalize_text(text: str) -> str:
    """Normalizar texto para comparación."""
    # Convertir a minúsculas
    text = text.lower()
    # Eliminar URLs
    text = re.sub(r'http\S+|www\.\S+', '', text)
    # Eliminar menciones y hashtags
    text = re.sub(r'[@#]\w+', '', text)
    # Eliminar puntuación y espacios extra
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def hash_text(text: str) -> str:
    """Generar hash de un texto normalizado."""
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode()).hexdigest()


def get_env(key: str, default: Any = None, required: bool = False) -> Any:
    """Obtener variable de entorno con validación."""
    value = os.getenv(key, default)
    
    if required and not value:
        raise ValueError(f"Variable de entorno requerida no encontrada: {key}")
    
    return value


def get_env_bool(key: str, default: bool = False) -> bool:
    """Obtener variable de entorno como booleano."""
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')


def get_env_int(key: str, default: int = 0) -> int:
    """Obtener variable de entorno como entero."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def format_datetime(dt: datetime) -> str:
    """Formatear datetime para display."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_datetime(dt_str: str) -> datetime:
    """Parsear string a datetime."""
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        # Intentar otros formatos
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        raise ValueError(f"No se pudo parsear la fecha: {dt_str}")


def truncate_text(text: str, max_length: int = 280, suffix: str = "...") -> str:
    """Truncar texto a longitud máxima."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def count_chars(text: str) -> int:
    """Contar caracteres de un tweet (considerando URLs)."""
    # Twitter cuenta las URLs como 23 caracteres
    url_pattern = r'http\S+|www\.\S+'
    urls = re.findall(url_pattern, text)
    
    # Reemplazar URLs por placeholder de 23 caracteres
    text_without_urls = re.sub(url_pattern, 'X' * 23, text)
    
    return len(text_without_urls)


def validate_tweet_length(text: str, max_length: int = 280) -> bool:
    """Validar que un tweet no exceda la longitud máxima."""
    return count_chars(text) <= max_length


def fetch_article_content(url: str) -> Optional[Dict[str, str]]:
    """Obtener contenido y metadata de una URL."""
    try:
        # Headers para simular navegador
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Eliminar elementos no deseados para el texto
        for script in soup(["script", "style", "nav", "footer", "header", "iframe"]):
            script.decompose()
            
        # Obtener texto
        text = soup.get_text()
        
        # Limpiar espacios
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Obtener título y metadata
        title = soup.title.string if soup.title else ""
        
        # Obtener imagen (og:image)
        image_url = ""
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            image_url = og_image["content"]
        
        return {
            "text": text,
            "title": title,
            "image_url": image_url
        }
            
    except Exception as e:
        # Logging solo advertencia para no ensuciar logs si falla una URL
        logging.getLogger("apptwitter").warning(f"Error obteniendo contenido de {url}: {e}")
        return None
