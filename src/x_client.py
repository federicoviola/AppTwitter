"""Cliente para la API de X (Twitter)."""

import json
import os
import tempfile
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests

from .utils import get_env, setup_logging

logger = setup_logging()


class XClient:
    """Cliente para interactuar con la API de X."""
    
    def __init__(self):
        """Inicializar cliente de X."""
        self.client = None
        self.api_v1 = None  # Para subir media
        self.api_available = False
        
        # Intentar inicializar cliente
        self._init_client()
    
    def _init_client(self):
        """Inicializar cliente de Tweepy."""
        try:
            import tweepy
            
            # Obtener credenciales
            api_key = get_env("X_API_KEY")
            api_secret = get_env("X_API_SECRET")
            access_token = get_env("X_ACCESS_TOKEN")
            access_token_secret = get_env("X_ACCESS_TOKEN_SECRET")
            
            if not all([api_key, api_secret, access_token, access_token_secret]):
                logger.warning("Credenciales de X API no configuradas. Modo exportación activado.")
                return
            
            # Autenticación
            auth = tweepy.OAuthHandler(api_key, api_secret)
            auth.set_access_token(access_token, access_token_secret)
            
            # API v1.1 (para subir media)
            self.api_v1 = tweepy.API(auth)
            
            # Cliente API v2
            self.client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret
            )
            
            # Verificar credenciales
            try:
                user = self.client.get_me()
                if user and user.data:
                    self.api_available = True
                    logger.info(f"Cliente X inicializado correctamente. Usuario: @{user.data.username}")
                else:
                    logger.warning("No se pudo verificar usuario de X")
            except Exception as e:
                logger.warning(f"Error verificando credenciales de X: {e}")
        
        except ImportError:
            logger.warning("tweepy no instalado. Modo exportación activado.")
        except Exception as e:
            logger.error(f"Error inicializando cliente de X: {e}")
    
    def _get_og_image(self, url: str) -> Optional[str]:
        """Obtener imagen Open Graph de una URL."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; AppTwitter/1.0)"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Buscar meta og:image
            from html.parser import HTMLParser
            
            class OGParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.og_image = None
                
                def handle_starttag(self, tag, attrs):
                    if tag == "meta":
                        attrs_dict = dict(attrs)
                        if attrs_dict.get("property") == "og:image" or attrs_dict.get("name") == "og:image":
                            self.og_image = attrs_dict.get("content")
                        # También buscar twitter:image
                        elif attrs_dict.get("property") == "twitter:image" or attrs_dict.get("name") == "twitter:image":
                            if not self.og_image:
                                self.og_image = attrs_dict.get("content")
            
            parser = OGParser()
            parser.feed(response.text)
            
            if parser.og_image:
                logger.info(f"Imagen OG encontrada: {parser.og_image[:50]}...")
                return parser.og_image
            else:
                logger.warning(f"No se encontró imagen OG en: {url}")
                return None
                
        except Exception as e:
            logger.warning(f"Error obteniendo imagen OG de {url}: {e}")
            return None
    
    def _download_image(self, image_url: str) -> Optional[str]:
        """Descargar imagen a archivo temporal."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; AppTwitter/1.0)"
            }
            response = requests.get(image_url, headers=headers, timeout=15, stream=True)
            response.raise_for_status()
            
            # Determinar extensión
            content_type = response.headers.get("Content-Type", "image/jpeg")
            if "png" in content_type:
                ext = ".png"
            elif "gif" in content_type:
                ext = ".gif"
            elif "webp" in content_type:
                ext = ".webp"
            else:
                ext = ".jpg"
            
            # Guardar a archivo temporal
            fd, temp_path = tempfile.mkstemp(suffix=ext)
            with os.fdopen(fd, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Imagen descargada: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.warning(f"Error descargando imagen: {e}")
            return None
    
    def _upload_media(self, image_path: str) -> Optional[str]:
        """Subir imagen a Twitter y obtener media_id."""
        if not self.api_v1:
            logger.warning("API v1.1 no disponible para subir media")
            return None
        
        try:
            media = self.api_v1.media_upload(filename=image_path)
            media_id = media.media_id_string
            logger.info(f"Media subida a Twitter. ID: {media_id}")
            return media_id
        except Exception as e:
            logger.error(f"Error subiendo media a Twitter: {e}")
            return None
    
    def post_tweet(self, text: str, media_ids: Optional[List[str]] = None, 
                   article_url: Optional[str] = None, auto_image: bool = True) -> Optional[Dict]:
        """
        Publicar tweet, opcionalmente con imagen.
        
        Args:
            text: Texto del tweet
            media_ids: Lista de IDs de media ya subida
            article_url: URL del artículo (para extraer imagen OG automáticamente)
            auto_image: Si True, intenta extraer imagen OG del article_url
        """
        if not self.api_available:
            logger.error("API de X no disponible. Usar modo exportación.")
            return None
        
        temp_image_path = None
        
        try:
            # Si hay URL y auto_image habilitado, intentar obtener imagen
            if article_url and auto_image and not media_ids:
                og_image_url = self._get_og_image(article_url)
                if og_image_url:
                    temp_image_path = self._download_image(og_image_url)
                    if temp_image_path:
                        media_id = self._upload_media(temp_image_path)
                        if media_id:
                            media_ids = [media_id]
            
            # Publicar tweet
            if media_ids:
                response = self.client.create_tweet(text=text, media_ids=media_ids)
            else:
                response = self.client.create_tweet(text=text)
            
            if response and response.data:
                tweet_id = response.data.get("id")
                logger.info(f"Tweet publicado exitosamente. ID: {tweet_id}" + 
                           (" (con imagen)" if media_ids else ""))
                
                return {
                    "success": True,
                    "tweet_id": tweet_id,
                    "response": json.dumps(response.data),
                    "has_image": bool(media_ids)
                }
            else:
                logger.error("Respuesta inesperada de la API de X")
                return None
        
        except Exception as e:
            logger.error(f"Error publicando tweet: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        
        finally:
            # Limpiar archivo temporal
            if temp_image_path and os.path.exists(temp_image_path):
                try:
                    os.remove(temp_image_path)
                except:
                    pass
    
    def post_thread(self, tweets: list[str]) -> Optional[Dict]:
        """Publicar hilo de tweets."""
        if not self.api_available:
            logger.error("API de X no disponible. Usar modo exportación.")
            return None
        
        tweet_ids = []
        previous_tweet_id = None
        
        try:
            for i, text in enumerate(tweets):
                # Agregar numeración si no está
                if not text.startswith(("1/", "2/", "3/", "4/", "5/", "6/")):
                    text = f"{i+1}/ {text}"
                
                # Publicar tweet
                if previous_tweet_id:
                    response = self.client.create_tweet(
                        text=text,
                        in_reply_to_tweet_id=previous_tweet_id
                    )
                else:
                    response = self.client.create_tweet(text=text)
                
                if response and response.data:
                    tweet_id = response.data.get("id")
                    tweet_ids.append(tweet_id)
                    previous_tweet_id = tweet_id
                    logger.info(f"Tweet {i+1}/{len(tweets)} publicado. ID: {tweet_id}")
                    
                    # Esperar entre tweets para evitar rate limits
                    if i < len(tweets) - 1:
                        time.sleep(2)
                else:
                    logger.error(f"Error publicando tweet {i+1}/{len(tweets)}")
                    break
            
            return {
                "success": len(tweet_ids) == len(tweets),
                "tweet_ids": tweet_ids,
                "count": len(tweet_ids)
            }
        
        except Exception as e:
            logger.error(f"Error publicando hilo: {e}")
            return {
                "success": False,
                "error": str(e),
                "tweet_ids": tweet_ids
            }
    
    def delete_tweet(self, tweet_id: str) -> bool:
        """Eliminar tweet."""
        if not self.api_available:
            logger.error("API de X no disponible")
            return False
        
        try:
            response = self.client.delete_tweet(tweet_id)
            
            if response:
                logger.info(f"Tweet eliminado: {tweet_id}")
                return True
            else:
                logger.error(f"Error eliminando tweet: {tweet_id}")
                return False
        
        except Exception as e:
            logger.error(f"Error eliminando tweet: {e}")
            return False
    
    def export_to_clipboard(self, text: str) -> bool:
        """Exportar tweet al portapapeles."""
        try:
            import pyperclip
            pyperclip.copy(text)
            logger.info("Tweet copiado al portapapeles")
            return True
        except ImportError:
            logger.warning("pyperclip no instalado. No se puede copiar al portapapeles.")
            return False
        except Exception as e:
            logger.error(f"Error copiando al portapapeles: {e}")
            return False
    
    def export_to_file(self, tweets: list[str], output_file: str) -> bool:
        """Exportar tweets a archivo markdown."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# Tweets para publicar\n\n")
                f.write(f"Generado: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")
                
                for i, tweet in enumerate(tweets, 1):
                    f.write(f"## Tweet {i}\n\n")
                    f.write(f"{tweet}\n\n")
                    f.write(f"**Caracteres:** {len(tweet)}\n\n")
                    f.write("---\n\n")
            
            logger.info(f"Tweets exportados a: {output_file}")
            return True
        
        except Exception as e:
            logger.error(f"Error exportando tweets: {e}")
            return False
    
    def is_available(self) -> bool:
        """Verificar si la API está disponible."""
        return self.api_available
    
    def get_rate_limit_status(self) -> Optional[Dict]:
        """Obtener estado de rate limits."""
        if not self.api_available:
            return None
        
        try:
            # Nota: Tweepy v2 no expone directamente rate limits
            # Esto es un placeholder para futuras implementaciones
            logger.info("Verificación de rate limits no implementada en API v2")
            return {"status": "unknown"}
        
        except Exception as e:
            logger.error(f"Error obteniendo rate limits: {e}")
            return None
