"""Cliente para la API de X (Twitter)."""

import json
import time
from typing import Dict, Optional

from .utils import get_env, setup_logging

logger = setup_logging()


class XClient:
    """Cliente para interactuar con la API de X."""
    
    def __init__(self):
        """Inicializar cliente de X."""
        self.client = None
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
    
    def post_tweet(self, text: str) -> Optional[Dict]:
        """Publicar tweet."""
        if not self.api_available:
            logger.error("API de X no disponible. Usar modo exportación.")
            return None
        
        try:
            response = self.client.create_tweet(text=text)
            
            if response and response.data:
                tweet_id = response.data.get("id")
                logger.info(f"Tweet publicado exitosamente. ID: {tweet_id}")
                
                return {
                    "success": True,
                    "tweet_id": tweet_id,
                    "response": json.dumps(response.data)
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
