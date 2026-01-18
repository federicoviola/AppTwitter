"""Sistema de notificaciones para AppTwitter."""

import os
import subprocess
import requests
from .utils import setup_logging

logger = setup_logging()

class Notifier:
    """Gestiona el envío de notificaciones a múltiples canales."""
    
    def __init__(self):
        """Inicializar notificador con configuración del entorno."""
        self.enabled = os.getenv("NOTIFICATIONS_ENABLED", "true").lower() == "true"
        self.ntfy_topic = os.getenv("NTFY_TOPIC")
        self.desktop_enabled = os.getenv("DESKTOP_NOTIFICATIONS_ENABLED", "true").lower() == "true"
        
        if self.enabled:
            if self.ntfy_topic:
                logger.info(f"Notificaciones ntfy.sh habilitadas tópico: {self.ntfy_topic}")
            if self.desktop_enabled:
                logger.info("Notificaciones de escritorio habilitadas (notify-send)")

    def notify(self, title: str, message: str, platform: str = "app"):
        """
        Enviar notificación por todos los canales activos.
        
        Args:
            title: Título de la notificación.
            message: Contenido del mensaje.
            platform: 'twitter', 'linkedin' o 'app'.
        """
        if not self.enabled:
            return

        # Iconos según plataforma
        icons = {
            "twitter": "🐦",
            "linkedin": "💼",
            "app": "🚀"
        }
        icon = icons.get(platform, "📢")
        full_title = f"{icon} {title}"

        # 1. Notificación ntfy.sh
        if self.ntfy_topic:
            self._send_ntfy(full_title, message)

        # 2. Notificación de escritorio (Linux)
        if self.desktop_enabled:
            self._send_desktop(full_title, message)

    def _send_ntfy(self, title: str, message: str):
        """Enviar notificación vía ntfy.sh."""
        try:
            url = f"https://ntfy.sh/{self.ntfy_topic}"
            
            # Mapear iconos a tags de ntfy (nombres de emojis estándar)
            # ntfy traduce nombres como 'bird' o 'briefcase' a emojis
            tags = "loudspeaker"
            if "🐦" in title: tags = "bird,loudspeaker"
            elif "💼" in title: tags = "briefcase,loudspeaker"
            elif "🚀" in title: tags = "rocket,loudspeaker"
            
            # Limpiar el título de emojis para evitar problemas de encoding en headers
            clean_title = title.encode('ascii', 'ignore').decode('ascii').strip()
            
            requests.post(url, 
                         data=message.encode('utf-8'),
                         headers={
                             "Title": clean_title,
                             "Priority": "default",
                             "Tags": tags
                         },
                         timeout=5)
        except Exception as e:
            logger.error(f"Error enviando a ntfy.sh: {e}")

    def _send_desktop(self, title: str, message: str):
        """Enviar notificación de escritorio usando notify-send."""
        try:
            # -i es el icono, -t el tiempo en ms
            subprocess.run([
                "notify-send", 
                title, 
                message, 
                "-t", "5000",
                "-a", "AppTwitter"
            ], check=False)
        except Exception as e:
            logger.error(f"Error enviando notificación de escritorio: {e}")
