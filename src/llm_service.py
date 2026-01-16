"""Servicio unificado para clientes LLM."""

import os
from typing import Optional, Dict, Any, List

from .utils import setup_logging
from .voice import VoiceProfile

logger = setup_logging()

class LLMClient:
    """Cliente unificado para múltiples proveedores de LLM."""
    
    PROVIDERS = ["gemini", "openai", "anthropic"]
    
    def __init__(self, voice: VoiceProfile):
        """Inicializar cliente."""
        self.voice = voice
        self.client = None
        self.provider = None
        
        self._init_client()
        
    def _init_client(self):
        """Inicializar el cliente disponible con mayor prioridad."""
        # 1. Gemini (Google) - Prioridad Alta
        if os.getenv("GEMINI_API_KEY"):
            try:
                import google.generativeai as genai
                genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
                # Usar Gemini 2.0 Flash
                self.client = genai.GenerativeModel('gemini-2.0-flash')
                self.provider = "gemini"
                logger.info("Cliente Gemini (Google) inicializado")
                return
            except ImportError:
                logger.warning("google-generativeai no instalado")
            except Exception as e:
                logger.warning(f"Error inicializando Gemini: {e}")
                
        # 2. OpenAI - Prioridad Media
        if os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                self.provider = "openai"
                logger.info("Cliente OpenAI inicializado")
                return
            except ImportError:
                logger.warning("openai no instalado")
            except Exception as e:
                logger.warning(f"Error inicializando OpenAI: {e}")
                
        # 3. Anthropic - Prioridad Baja
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                self.provider = "anthropic"
                logger.info("Cliente Anthropic inicializado")
                return
            except ImportError:
                logger.warning("anthropic no instalado")
            except Exception as e:
                logger.warning(f"Error inicializando Anthropic: {e}")
                
        logger.warning("No se pudo inicializar ningún cliente LLM")
        
    def generate(self, prompt: str, max_tokens: int = 500, system_instruction: str = "") -> Optional[str]:
        """Generar contenido usando el cliente activo."""
        if not self.client:
            logger.error("No hay cliente LLM disponible")
            return None
            
        try:
            if self.provider == "gemini":
                generation_config = {
                    "temperature": self.voice.get_temperatura(),
                    "max_output_tokens": max_tokens,
                }
                
                # Gemini no usa system prompts de la misma forma en generate_content,
                # pero podemos agregarlo al inicio si es necesario, o usar modelos que lo soporten nativamente.
                # Para simplificar, concatenamos si hay instrucción de sistema
                full_prompt = prompt
                if system_instruction:
                     full_prompt = f"INSTRUCCIÓN DEL SISTEMA: {system_instruction}\n\nUSUARIO: {prompt}"
                
                response = self.client.generate_content(
                    full_prompt,
                    generation_config=generation_config
                )
                return response.text.strip()
                
            elif self.provider == "openai":
                messages = []
                if system_instruction:
                     messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})
                
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=self.voice.get_temperatura(),
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content.strip()
                
            elif self.provider == "anthropic":
                messages = [{"role": "user", "content": prompt}]
                if system_instruction:
                    # Claude prefiere system prompts como parámetro separado si se usa la API nueva,
                    # o integrado. Usaremos el parámetro 'system' si la librería lo soporta,
                    # pero para asegurar compatibilidad universal en esta versión simple:
                    pass 
                
                # Nota: Anthropic SDK v0.18+ usa system param
                kwargs = {
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": max_tokens,
                    "temperature": self.voice.get_temperatura(),
                    "messages": messages
                }
                if system_instruction:
                    kwargs["system"] = system_instruction
                    
                response = self.client.messages.create(**kwargs)
                return response.content[0].text.strip()
                
            return None
            
        except Exception as e:
            logger.error(f"Error generando contenido con {self.provider}: {e}")
            return None
            
    def get_provider_name(self) -> str:
        """Obtener nombre del proveedor activo."""
        return self.provider or "none"
