"""Gestión del perfil de voz y pensamiento."""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils import get_project_root, setup_logging

logger = setup_logging()


class VoiceProfile:
    """Perfil de voz y pensamiento del usuario."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Inicializar perfil de voz."""
        if config_path is None:
            config_path = get_project_root() / "voz.yaml"
            if not config_path.exists():
                config_path = get_project_root() / "voz.example.yaml"
        
        self.config_path = config_path
        self.config = self._load_config()
        logger.info(f"Perfil de voz cargado desde: {config_path}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Cargar configuración desde archivo YAML."""
        if not self.config_path.exists():
            logger.warning(f"Archivo de configuración no encontrado: {self.config_path}")
            return self._get_default_config()
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Obtener configuración por defecto."""
        return {
            "temas": ["ética", "filosofía", "tecnología"],
            "tono": {
                "formal": True,
                "académico": True,
                "claro": True,
                "crítico": True,
                "sin_insultos": True,
                "sin_moralismo": True
            },
            "palabras_prohibidas": [],
            "patrones": [],
            "ejemplos": [],
            "estilo": {
                "longitud_preferida": "media",
                "uso_preguntas": True,
                "uso_ejemplos": True,
                "uso_citas": False,
                "uso_hashtags": "moderado",
                "uso_emojis": False,
                "uso_hilos": True
            },
            "generacion": {
                "temperatura": 0.7,
                "densidad_conceptual": "alta",
                "incluir_call_to_action": True,
                "max_hashtags": 2
            }
        }
    
    def save(self, config_path: Optional[Path] = None):
        """Guardar configuración a archivo."""
        if config_path is None:
            config_path = self.config_path
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)
        
        logger.info(f"Perfil de voz guardado en: {config_path}")
    
    @property
    def temas(self) -> List[str]:
        """Obtener temas prioritarios."""
        return self.config.get("temas", [])
    
    @property
    def tono(self) -> Dict[str, bool]:
        """Obtener configuración de tono."""
        return self.config.get("tono", {})
    
    @property
    def palabras_prohibidas(self) -> List[str]:
        """Obtener palabras prohibidas."""
        return self.config.get("palabras_prohibidas", [])
    
    @property
    def patrones(self) -> List[str]:
        """Obtener patrones argumentativos."""
        return self.config.get("patrones", [])
    
    @property
    def ejemplos(self) -> List[str]:
        """Obtener ejemplos de tweets."""
        return self.config.get("ejemplos", [])
    
    @property
    def estilo(self) -> Dict[str, Any]:
        """Obtener configuración de estilo."""
        return self.config.get("estilo", {})
    
    @property
    def generacion(self) -> Dict[str, Any]:
        """Obtener configuración de generación."""
        return self.config.get("generacion", {})
    
    def get_temperatura(self) -> float:
        """Obtener temperatura para generación."""
        return self.generacion.get("temperatura", 0.7)
    
    def get_max_hashtags(self) -> int:
        """Obtener máximo de hashtags."""
        return self.generacion.get("max_hashtags", 2)
    
    def get_densidad_conceptual(self) -> str:
        """Obtener densidad conceptual."""
        return self.generacion.get("densidad_conceptual", "alta")
    
    def incluir_call_to_action(self) -> bool:
        """Verificar si incluir call to action."""
        return self.generacion.get("incluir_call_to_action", True)
    
    def get_longitud_preferida(self) -> str:
        """Obtener longitud preferida de tweets."""
        return self.estilo.get("longitud_preferida", "media")
    
    def usar_preguntas(self) -> bool:
        """Verificar si usar preguntas."""
        return self.estilo.get("uso_preguntas", True)
    
    def usar_hilos(self) -> bool:
        """Verificar si usar hilos."""
        return self.estilo.get("uso_hilos", True)
    
    def get_uso_hashtags(self) -> str:
        """Obtener frecuencia de uso de hashtags."""
        return self.estilo.get("uso_hashtags", "moderado")
    
    def to_prompt(self) -> str:
        """Convertir perfil a prompt para LLM."""
        prompt_parts = []
        
        # Temas
        if self.temas:
            prompt_parts.append(f"Temas prioritarios: {', '.join(self.temas)}")
        
        # Tono
        tono_desc = []
        for key, value in self.tono.items():
            if value:
                tono_desc.append(key.replace("_", " "))
        if tono_desc:
            prompt_parts.append(f"Tono: {', '.join(tono_desc)}")
        
        # Patrones
        if self.patrones:
            prompt_parts.append("Patrones argumentativos:")
            for patron in self.patrones:
                prompt_parts.append(f"- {patron}")
        
        # Ejemplos
        if self.ejemplos:
            prompt_parts.append("\nEjemplos de tweets:")
            for ejemplo in self.ejemplos[:5]:  # Limitar a 5 ejemplos
                prompt_parts.append(f"- {ejemplo}")
        
        # Palabras prohibidas
        if self.palabras_prohibidas:
            prompt_parts.append(f"\nEvitar usar: {', '.join(self.palabras_prohibidas)}")
        
        return "\n".join(prompt_parts)
