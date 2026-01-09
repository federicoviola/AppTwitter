"""Motor de generación de tweets."""

import json
import random
from typing import Dict, List, Optional

from .db import Database
from .filters import TweetFilter
from .utils import hash_text, setup_logging, truncate_text, validate_tweet_length
from .voice import VoiceProfile

logger = setup_logging()


class TweetGenerator:
    """Generador de tweets."""
    
    TWEET_TYPES = ["promo", "thought", "question", "thread"]
    
    def __init__(self, db: Database, voice: VoiceProfile, tweet_filter: TweetFilter):
        """Inicializar generador."""
        self.db = db
        self.voice = voice
        self.filter = tweet_filter
        self.llm_client = None
        
        # Intentar inicializar cliente LLM
        self._init_llm_client()
    
    def _init_llm_client(self):
        """Inicializar cliente de LLM si está disponible."""
        import os
        
        # Intentar Gemini (Google)
        if os.getenv("GEMINI_API_KEY"):
            try:
                import google.generativeai as genai
                genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
                self.llm_client = genai.GenerativeModel('gemini-2.0-flash')
                self.llm_provider = "gemini"
                logger.info("Cliente Gemini (Google) inicializado")
                return
            except ImportError:
                logger.warning("google-generativeai no instalado. Instalar con: poetry install -E llm-gemini")
            except Exception as e:
                logger.warning(f"Error inicializando Gemini: {e}")
        
        # Intentar OpenAI
        if os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI
                self.llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                self.llm_provider = "openai"
                logger.info("Cliente OpenAI inicializado")
                return
            except ImportError:
                logger.warning("openai no instalado. Instalar con: poetry install -E llm-openai")
            except Exception as e:
                logger.warning(f"Error inicializando OpenAI: {e}")
        
        # Intentar Anthropic
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                from anthropic import Anthropic
                self.llm_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                self.llm_provider = "anthropic"
                logger.info("Cliente Anthropic inicializado")
                return
            except ImportError:
                logger.warning("anthropic no instalado. Instalar con: poetry install -E llm-anthropic")
            except Exception as e:
                logger.warning(f"Error inicializando Anthropic: {e}")
        
        logger.info("No hay cliente LLM disponible. Usando generación basada en plantillas.")
    
    def generate(self, tweet_type: str, article_id: Optional[int] = None, count: int = 1) -> List[Dict]:
        """Generar tweets."""
        if tweet_type not in self.TWEET_TYPES:
            raise ValueError(f"Tipo de tweet inválido: {tweet_type}. Opciones: {self.TWEET_TYPES}")
        
        generated = []
        
        for _ in range(count):
            if self.llm_client:
                tweet = self._generate_with_llm(tweet_type, article_id)
            else:
                tweet = self._generate_with_template(tweet_type, article_id)
            
            if tweet:
                generated.append(tweet)
        
        return generated
    
    def _generate_with_llm(self, tweet_type: str, article_id: Optional[int] = None) -> Optional[Dict]:
        """Generar tweet usando LLM."""
        prompt = self._build_prompt(tweet_type, article_id)
        
        try:
            if self.llm_provider == "gemini":
                # Configurar generación con Gemini
                generation_config = {
                    "temperature": self.voice.get_temperatura(),
                    "max_output_tokens": 300,
                }
                
                response = self.llm_client.generate_content(
                    prompt,
                    generation_config=generation_config
                )
                content = response.text.strip()
            
            elif self.llm_provider == "openai":
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Eres un asistente que genera tweets en español siguiendo un perfil de voz específico."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.voice.get_temperatura(),
                    max_tokens=300
                )
                content = response.choices[0].message.content.strip()
            
            elif self.llm_provider == "anthropic":
                response = self.llm_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=300,
                    temperature=self.voice.get_temperatura(),
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                content = response.content[0].text.strip()
            
            else:
                return None
            
            # Limpiar contenido (remover comillas si las hay)
            content = content.strip('"').strip("'")
            
            # Validar longitud
            if not validate_tweet_length(content):
                logger.warning(f"Tweet generado excede longitud: {len(content)} caracteres")
                content = truncate_text(content, 280)
            
            # Crear tweet
            tweet = {
                "content": content,
                "content_hash": hash_text(content),
                "tweet_type": tweet_type,
                "article_id": article_id,
                "metadata": json.dumps({"generator": "llm", "provider": self.llm_provider})
            }
            
            # Validar con filtros
            is_valid, reason = self.filter.validate(content)
            if not is_valid:
                logger.warning(f"Tweet generado no pasó validación: {reason}")
                return None
            
            return tweet
            
        except Exception as e:
            logger.error(f"Error generando tweet con LLM: {e}")
            return None
    
    def _generate_with_template(self, tweet_type: str, article_id: Optional[int] = None) -> Optional[Dict]:
        """Generar tweet usando plantillas."""
        if tweet_type == "promo" and article_id:
            content = self._generate_promo_template(article_id)
        elif tweet_type == "thought":
            content = self._generate_thought_template()
        elif tweet_type == "question":
            content = self._generate_question_template()
        elif tweet_type == "thread":
            content = self._generate_thread_template(article_id)
        else:
            logger.warning(f"No se puede generar tipo {tweet_type} sin artículo")
            return None
        
        if not content:
            return None
        
        # Validar longitud
        if not validate_tweet_length(content):
            logger.warning(f"Tweet generado excede longitud: {len(content)} caracteres")
            content = truncate_text(content, 280)
        
        # Crear tweet
        tweet = {
            "content": content,
            "content_hash": hash_text(content),
            "tweet_type": tweet_type,
            "article_id": article_id,
            "metadata": json.dumps({"generator": "template"})
        }
        
        # Validar con filtros
        is_valid, reason = self.filter.validate(content)
        if not is_valid:
            logger.warning(f"Tweet generado no pasó validación: {reason}")
            return None
        
        return tweet
    
    def _generate_promo_template(self, article_id: int) -> Optional[str]:
        """Generar tweet de promoción de artículo."""
        article = self.db.fetchone("SELECT * FROM articulos WHERE id = ?", (article_id,))
        
        if not article:
            logger.error(f"Artículo no encontrado: {article_id}")
            return None
        
        templates = [
            f"Nuevo artículo: {article['titulo']}\n\n{article['resumen']}\n\n{article['url']}",
            f"{article['titulo']}\n\n{article['resumen']}\n\nLeer más: {article['url']}",
            f"Reflexión sobre {article['tags'].split(',')[0] if article['tags'] else 'este tema'}:\n\n{article['titulo']}\n\n{article['url']}",
        ]
        
        return random.choice(templates)
    
    def _generate_thought_template(self) -> str:
        """Generar tweet de pensamiento."""
        # Usar ejemplos del perfil de voz
        if self.voice.ejemplos:
            # Variación de un ejemplo existente
            base = random.choice(self.voice.ejemplos)
            return base
        
        # Plantillas genéricas basadas en temas
        temas = self.voice.temas
        if temas:
            tema = random.choice(temas)
            templates = [
                f"La {tema} no es solo teoría: es una forma de mirar el mundo.",
                f"Pensar la {tema} hoy exige cuestionar las categorías heredadas.",
                f"La pregunta por la {tema} es también una pregunta por nosotros mismos.",
            ]
            return random.choice(templates)
        
        return "Pensar es cuestionar lo dado, no repetir lo sabido."
    
    def _generate_question_template(self) -> str:
        """Generar tweet con pregunta."""
        temas = self.voice.temas
        if temas:
            tema = random.choice(temas)
            templates = [
                f"¿Qué significa realmente hablar de {tema} hoy?",
                f"¿Cómo pensamos la {tema} sin caer en el moralismo?",
                f"¿Qué condiciones hacen posible nuestra comprensión de la {tema}?",
            ]
            return random.choice(templates)
        
        return "¿Qué significa pensar en lugar de repetir?"
    
    def _generate_thread_template(self, article_id: Optional[int] = None) -> str:
        """Generar primer tweet de un hilo."""
        if article_id:
            article = self.db.fetchone("SELECT * FROM articulos WHERE id = ?", (article_id,))
            if article:
                return f"🧵 Hilo sobre {article['titulo']}\n\n1/ {article['resumen'][:200]}..."
        
        tema = random.choice(self.voice.temas) if self.voice.temas else "este tema"
        return f"🧵 Algunas reflexiones sobre {tema}\n\n1/ Empecemos por cuestionar las categorías que damos por sentadas..."
    
    def _build_prompt(self, tweet_type: str, article_id: Optional[int] = None) -> str:
        """Construir prompt para LLM."""
        prompt_parts = [
            "Genera un tweet en español siguiendo este perfil de voz:",
            "",
            self.voice.to_prompt(),
            "",
        ]
        
        if tweet_type == "promo" and article_id:
            article = self.db.fetchone("SELECT * FROM articulos WHERE id = ?", (article_id,))
            if article:
                prompt_parts.extend([
                    "Tipo de tweet: Promoción de artículo",
                    f"Título: {article['titulo']}",
                    f"Resumen: {article['resumen']}",
                    f"URL: {article['url']}",
                    "",
                    "Genera un tweet que:",
                    "- Presente el artículo de forma atractiva",
                    "- Incluya un hook que genere interés",
                    "- Incluya el enlace al final",
                    "- No exceda 280 caracteres",
                ])
        
        elif tweet_type == "thought":
            prompt_parts.extend([
                "Tipo de tweet: Pensamiento breve",
                "",
                "Genera un tweet que:",
                "- Exprese una tesis o reflexión breve",
                "- Sea conceptualmente denso pero claro",
                "- No incluya enlaces",
                "- No exceda 280 caracteres",
            ])
        
        elif tweet_type == "question":
            prompt_parts.extend([
                "Tipo de tweet: Pregunta abierta",
                "",
                "Genera un tweet que:",
                "- Plantee una pregunta filosófica o conceptual",
                "- Invite a la reflexión",
                "- No sea retórica ni obvia",
                "- No exceda 280 caracteres",
            ])
        
        elif tweet_type == "thread":
            prompt_parts.extend([
                "Tipo de tweet: Primer tweet de un hilo",
                "",
                "Genera el primer tweet de un hilo que:",
                "- Introduzca un tema complejo",
                "- Indique que es un hilo (con 🧵 o '1/')",
                "- Genere expectativa",
                "- No exceda 280 caracteres",
            ])
        
        prompt_parts.append("\nGenera SOLO el texto del tweet, sin comillas ni explicaciones adicionales.")
        
        return "\n".join(prompt_parts)
    
    def save_tweet(self, tweet: Dict) -> int:
        """Guardar tweet candidato en base de datos."""
        return self.db.insert("tweet_candidates", tweet)
    
    def generate_batch(self, mix: Dict[str, int]) -> List[int]:
        """Generar lote de tweets según mix especificado."""
        tweet_ids = []
        
        # Obtener artículos disponibles para promoción
        articles = self.db.fetchall(
            """
            SELECT id FROM articulos
            WHERE id NOT IN (
                SELECT DISTINCT article_id 
                FROM tweet_candidates 
                WHERE article_id IS NOT NULL
            )
            ORDER BY fecha_publicacion DESC
            """
        )
        
        article_pool = [a["id"] for a in articles]
        
        for tweet_type, count in mix.items():
            for i in range(count):
                # Para promos, usar artículos disponibles
                article_id = None
                if tweet_type == "promo" and article_pool:
                    article_id = article_pool[i % len(article_pool)]
                
                tweet = self.generate(tweet_type, article_id, count=1)
                
                if tweet:
                    tweet_id = self.save_tweet(tweet[0])
                    tweet_ids.append(tweet_id)
                    logger.info(f"Tweet generado y guardado: {tweet_type} (ID: {tweet_id})")
        
        return tweet_ids
