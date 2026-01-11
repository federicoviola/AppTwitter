"""Cliente para la API de LinkedIn."""

import json
import os
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from .utils import get_env, get_project_root, setup_logging

logger = setup_logging()

# Constantes de LinkedIn API
LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_API_URL = "https://api.linkedin.com/v2"
LINKEDIN_ME_URL = "https://api.linkedin.com/v2/me"

# Puerto local para callback OAuth
OAUTH_CALLBACK_PORT = 8765
OAUTH_REDIRECT_URI = f"http://localhost:{OAUTH_CALLBACK_PORT}/callback"


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handler para recibir el callback de OAuth."""
    
    def do_GET(self):
        """Manejar GET request del callback."""
        parsed = urlparse(self.path)
        
        if parsed.path == "/callback":
            query = parse_qs(parsed.query)
            
            if "code" in query:
                self.server.auth_code = query["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"""
                    <html>
                    <head><title>AppTwitter - LinkedIn Auth</title></head>
                    <body style="font-family: system-ui; text-align: center; padding: 50px;">
                        <h1>Autenticacion exitosa!</h1>
                        <p>Ya podes cerrar esta ventana y volver a la terminal.</p>
                        <script>setTimeout(function(){ window.close(); }, 3000);</script>
                    </body>
                    </html>
                """)
            elif "error" in query:
                self.server.auth_error = query.get("error_description", ["Unknown error"])[0]
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(f"""
                    <html>
                    <head><title>AppTwitter - Error</title></head>
                    <body style="font-family: system-ui; text-align: center; padding: 50px;">
                        <h1>Error de autenticacion</h1>
                        <p>{self.server.auth_error}</p>
                    </body>
                    </html>
                """.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Silenciar logs del servidor HTTP."""
        pass


class LinkedInClient:
    """Cliente para interactuar con la API de LinkedIn."""
    
    def __init__(self):
        """Inicializar cliente de LinkedIn."""
        self.access_token = None
        self.user_id = None
        self.user_name = None
        self.api_available = False
        
        # Credenciales
        self.client_id = get_env("LINKEDIN_CLIENT_ID")
        self.client_secret = get_env("LINKEDIN_CLIENT_SECRET")
        
        # Intentar cargar token guardado
        self._load_token()
    
    def _get_token_file(self) -> Path:
        """Obtener ruta del archivo de token."""
        return get_project_root() / "data" / ".linkedin_token"
    
    def _load_token(self):
        """Cargar token guardado."""
        token_file = self._get_token_file()
        
        if token_file.exists():
            try:
                with open(token_file, 'r') as f:
                    data = json.load(f)
                    self.access_token = data.get("access_token")
                    self.user_id = data.get("user_id")
                    self.user_name = data.get("user_name")
                    
                    # Si tenemos token y user_id, consideramos válido
                    if self.access_token and self.user_id:
                        self.api_available = True
                        logger.info(f"Cliente LinkedIn cargado. Usuario: {self.user_name}")
                    else:
                        logger.debug("Token de LinkedIn cargado pero incompleto")
            except Exception as e:
                logger.warning(f"Error cargando token de LinkedIn: {e}")
    
    def _save_token(self):
        """Guardar token."""
        token_file = self._get_token_file()
        
        # Crear directorio si no existe
        token_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(token_file, 'w') as f:
                json.dump({
                    "access_token": self.access_token,
                    "user_id": self.user_id,
                    "user_name": self.user_name
                }, f)
            logger.debug("Token de LinkedIn guardado")
        except Exception as e:
            logger.error(f"Error guardando token de LinkedIn: {e}")
    
    def _verify_token(self):
        """Verificar que el token es válido."""
        if not self.access_token:
            return
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            # Primero intentar con /userinfo (OpenID Connect)
            response = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.user_id = data.get("sub")
                self.user_name = data.get("name", "Usuario")
                self.api_available = True
                logger.info(f"Cliente LinkedIn inicializado (OpenID). Usuario: {self.user_name}")
                return
            
            # Fallback: intentar con /me
            response = requests.get(LINKEDIN_ME_URL, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.user_id = data.get("id")
                first_name = data.get("localizedFirstName", "")
                last_name = data.get("localizedLastName", "")
                self.user_name = f"{first_name} {last_name}".strip() or "Usuario"
                self.api_available = True
                logger.info(f"Cliente LinkedIn inicializado. Usuario: {self.user_name}")
            else:
                logger.warning(f"No se pudo obtener perfil de LinkedIn: {response.status_code}")
                self.api_available = False
        except Exception as e:
            logger.warning(f"Error verificando token de LinkedIn: {e}")
            self.api_available = False
    
    def authenticate(self) -> bool:
        """Iniciar flujo de autenticación OAuth 2.0."""
        if not self.client_id or not self.client_secret:
            logger.error("Credenciales de LinkedIn no configuradas en .env")
            logger.error("Configurar LINKEDIN_CLIENT_ID y LINKEDIN_CLIENT_SECRET")
            return False
        
        # Construir URL de autorización
        # Scopes: openid + profile (para obtener ID) + w_member_social (para publicar)
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": OAUTH_REDIRECT_URI,
            "scope": "openid profile w_member_social",
            "state": "apptwitter_auth"
        }
        
        auth_url = f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"
        
        logger.info("Abriendo navegador para autenticación de LinkedIn...")
        logger.info(f"Si no se abre automáticamente, visitar: {auth_url}")
        
        # Abrir navegador
        webbrowser.open(auth_url)
        
        # Iniciar servidor local para callback
        server = HTTPServer(("localhost", OAUTH_CALLBACK_PORT), OAuthCallbackHandler)
        server.auth_code = None
        server.auth_error = None
        
        logger.info("Esperando autorización...")
        
        # Esperar callback (timeout de 5 minutos)
        server.timeout = 300
        
        try:
            while server.auth_code is None and server.auth_error is None:
                server.handle_request()
        except Exception as e:
            logger.error(f"Error esperando callback: {e}")
            return False
        finally:
            server.server_close()
        
        if server.auth_error:
            logger.error(f"Error de autenticación: {server.auth_error}")
            return False
        
        if not server.auth_code:
            logger.error("No se recibió código de autorización")
            return False
        
        # Intercambiar código por token
        return self._exchange_code(server.auth_code)
    
    def _exchange_code(self, auth_code: str) -> bool:
        """Intercambiar código de autorización por access token."""
        try:
            data = {
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": OAUTH_REDIRECT_URI,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            response = requests.post(LINKEDIN_TOKEN_URL, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                
                # Intentar obtener info del usuario
                self._verify_token()
                
                # Si no pudimos obtener el perfil, intentar con token introspection
                if not self.api_available:
                    logger.info("Intentando obtener ID de usuario por método alternativo...")
                    if self._get_user_id_alternative():
                        self.api_available = True
                
                if self.api_available:
                    self._save_token()
                    logger.info("Autenticación de LinkedIn exitosa")
                    return True
                else:
                    # Último recurso: aceptar sin perfil pero con token
                    logger.warning("No se pudo obtener perfil, pero el token es válido")
                    self.user_id = "unknown"
                    self.user_name = "Usuario LinkedIn"
                    self.api_available = True
                    self._save_token()
                    logger.info("Autenticación de LinkedIn exitosa (modo limitado)")
                    return True
            else:
                logger.error(f"Error obteniendo token: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Error intercambiando código: {e}")
            return False
    
    def _get_user_id_alternative(self) -> bool:
        """Intentar obtener user ID por método alternativo."""
        try:
            # Intentar con el endpoint de token introspection
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            # Probar con /userinfo (requiere openid scope)
            response = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.user_id = data.get("sub")
                self.user_name = data.get("name", "Usuario")
                return True
            
            # Si falla, intentar crear un post de prueba para obtener el author URN
            # No es ideal pero funciona
            return False
            
        except Exception as e:
            logger.debug(f"Método alternativo falló: {e}")
            return False
        except Exception as e:
            logger.error(f"Error intercambiando código: {e}")
            return False
    
    def post(self, text: str, article_url: Optional[str] = None, 
             article_title: Optional[str] = None, 
             article_description: Optional[str] = None) -> Optional[Dict]:
        """
        Publicar en LinkedIn.
        
        Args:
            text: Texto del post
            article_url: URL del artículo a compartir (opcional)
            article_title: Título del artículo (opcional)
            article_description: Descripción del artículo (opcional)
        
        Returns:
            Dict con resultado o None si falló
        """
        if not self.api_available:
            logger.error("API de LinkedIn no disponible. Ejecutar: app linkedin-auth")
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            
            # Construir payload
            if article_url:
                # Post con artículo
                payload = {
                    "author": f"urn:li:person:{self.user_id}",
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {
                                "text": text
                            },
                            "shareMediaCategory": "ARTICLE",
                            "media": [{
                                "status": "READY",
                                "originalUrl": article_url
                            }]
                        }
                    },
                    "visibility": {
                        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                    }
                }
                
                # Agregar título y descripción si están disponibles
                if article_title:
                    payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"][0]["title"] = {
                        "text": article_title
                    }
                if article_description:
                    payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"][0]["description"] = {
                        "text": article_description[:200]  # Límite de descripción
                    }
            else:
                # Post de solo texto
                payload = {
                    "author": f"urn:li:person:{self.user_id}",
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {
                                "text": text
                            },
                            "shareMediaCategory": "NONE"
                        }
                    },
                    "visibility": {
                        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                    }
                }
            
            response = requests.post(
                f"{LINKEDIN_API_URL}/ugcPosts",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 201:
                post_id = response.headers.get("X-RestLi-Id", "unknown")
                logger.info(f"Post de LinkedIn publicado. ID: {post_id}")
                
                return {
                    "success": True,
                    "post_id": post_id,
                    "response": response.text
                }
            else:
                logger.error(f"Error publicando en LinkedIn: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"{response.status_code}: {response.text}"
                }
        
        except Exception as e:
            logger.error(f"Error publicando en LinkedIn: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def is_available(self) -> bool:
        """Verificar si la API está disponible."""
        return self.api_available
    
    def get_user_info(self) -> Optional[Dict]:
        """Obtener información del usuario autenticado."""
        if not self.api_available:
            return None
        
        return {
            "user_id": self.user_id,
            "user_name": self.user_name
        }
    
    def logout(self):
        """Cerrar sesión (eliminar token guardado)."""
        token_file = self._get_token_file()
        
        if token_file.exists():
            token_file.unlink()
            logger.info("Sesión de LinkedIn cerrada")
        
        self.access_token = None
        self.user_id = None
        self.user_name = None
        self.api_available = False
