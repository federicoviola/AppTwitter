"""Motor de generación de posts para LinkedIn."""

import json
import random
from typing import Dict, List, Optional

from .db import Database
from .utils import hash_text, setup_logging
from .voice import VoiceProfile

logger = setup_logging()


class LinkedInGenerator:
    """Generador de posts para LinkedIn."""
    
    POST_TYPES = ["promo", "thought", "story", "insight"]
    MAX_LENGTH = 3000  # LinkedIn permite hasta 3000 caracteres
    
    def __init__(self, db: Database, voice: VoiceProfile):
        """Inicializar generador."""
        self.db = db
        self.voice = voice
        self.llm_client = None
        self.llm_provider = None
        
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
                logger.info("Cliente Gemini (Google) inicializado para LinkedIn")
                return
            except ImportError:
                logger.warning("google-generativeai no instalado")
            except Exception as e:
                logger.warning(f"Error inicializando Gemini: {e}")
        
        # Intentar OpenAI
        if os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI
                self.llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                self.llm_provider = "openai"
                logger.info("Cliente OpenAI inicializado para LinkedIn")
                return
            except ImportError:
                logger.warning("openai no instalado")
            except Exception as e:
                logger.warning(f"Error inicializando OpenAI: {e}")
        
        # Intentar Anthropic
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                from anthropic import Anthropic
                self.llm_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                self.llm_provider = "anthropic"
                logger.info("Cliente Anthropic inicializado para LinkedIn")
                return
            except ImportError:
                logger.warning("anthropic no instalado")
            except Exception as e:
                logger.warning(f"Error inicializando Anthropic: {e}")
        
        logger.info("No hay cliente LLM disponible para LinkedIn.")
    
    def generate(self, post_type: str, article_id: Optional[int] = None, count: int = 1) -> List[Dict]:
        """Generar posts de LinkedIn."""
        if post_type not in self.POST_TYPES:
            raise ValueError(f"Tipo de post inválido: {post_type}. Opciones: {self.POST_TYPES}")
        
        generated = []
        
        for _ in range(count):
            if self.llm_client:
                post = self._generate_with_llm(post_type, article_id)
            else:
                post = self._generate_with_template(post_type, article_id)
            
            if post:
                generated.append(post)
        
        return generated
    
    def _generate_with_llm(self, post_type: str, article_id: Optional[int] = None) -> Optional[Dict]:
        """Generar post usando LLM."""
        prompt = self._build_prompt(post_type, article_id)
        
        try:
            if self.llm_provider == "gemini":
                generation_config = {
                    "temperature": self.voice.get_temperatura(),
                    "max_output_tokens": 1000,
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
                        {"role": "system", "content": "Eres un asistente que genera posts profesionales para LinkedIn en español."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.voice.get_temperatura(),
                    max_tokens=1000
                )
                content = response.choices[0].message.content.strip()
            
            elif self.llm_provider == "anthropic":
                response = self.llm_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    temperature=self.voice.get_temperatura(),
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                content = response.content[0].text.strip()
            
            else:
                return None
            
            # Limpiar contenido
            content = content.strip('"').strip("'")
            
            # Validar longitud
            if len(content) > self.MAX_LENGTH:
                logger.warning(f"Post generado excede longitud: {len(content)} caracteres")
                content = content[:self.MAX_LENGTH - 3] + "..."
            
            # Obtener artículo si hay
            article_url = None
            article_title = None
            if article_id:
                article = self.db.fetchone("SELECT * FROM articulos WHERE id = ?", (article_id,))
                if article:
                    article_url = article.get("url")
                    article_title = article.get("titulo")
            
            # Crear post
            post = {
                "content": content,
                "content_hash": hash_text(content),
                "post_type": post_type,
                "article_id": article_id,
                "article_url": article_url,
                "article_title": article_title,
                "metadata": json.dumps({"generator": "llm", "provider": self.llm_provider})
            }
            
            return post
            
        except Exception as e:
            logger.error(f"Error generando post de LinkedIn con LLM: {e}")
            return None
    
    def _generate_with_template(self, post_type: str, article_id: Optional[int] = None) -> Optional[Dict]:
        """Generar post usando plantillas."""
        if post_type == "promo" and article_id:
            content, article_url, article_title = self._generate_promo_template(article_id)
        elif post_type == "thought":
            content = self._generate_thought_template()
            article_url = None
            article_title = None
        elif post_type == "story":
            content = self._generate_story_template()
            article_url = None
            article_title = None
        elif post_type == "insight":
            content = self._generate_insight_template()
            article_url = None
            article_title = None
        else:
            logger.warning(f"No se puede generar tipo {post_type} sin artículo")
            return None
        
        if not content:
            return None
        
        post = {
            "content": content,
            "content_hash": hash_text(content),
            "post_type": post_type,
            "article_id": article_id,
            "article_url": article_url,
            "article_title": article_title,
            "metadata": json.dumps({"generator": "template"})
        }
        
        return post
    
    def _generate_promo_template(self, article_id: int) -> tuple:
        """Generar post de promoción de artículo."""
        article = self.db.fetchone("SELECT * FROM articulos WHERE id = ?", (article_id,))
        
        if not article:
            logger.error(f"Artículo no encontrado: {article_id}")
            return None, None, None
        
        content = f"""🔵 Nuevo artículo publicado

{article['titulo']}

{article['resumen']}

En este artículo exploro algunas ideas que me parecen fundamentales para entender {article['tags'].split(',')[0] if article.get('tags') else 'este tema'}.

Me encantaría conocer tu perspectiva. ¿Qué pensás?

👉 Link en comentarios

#Reflexiones #Pensamiento"""
        
        return content, article.get("url"), article.get("titulo")
    
    def _generate_thought_template(self) -> str:
        """Generar post de pensamiento."""
        temas = self.voice.temas
        if temas:
            tema = random.choice(temas)
            return f"""Una reflexión sobre {tema}:

A veces me pregunto si no estamos confundiendo la profundidad con la complejidad.

Pensar bien no es acumular capas de abstracción.
Es llegar al núcleo de las cosas.
Sin adornos innecesarios.

¿Qué pensás? ¿Cómo distinguimos la claridad de la simplificación?

#Reflexiones #Pensamiento #Filosofía"""
        
        return """A veces me pregunto si no estamos confundiendo la profundidad con la complejidad.

Pensar bien no es acumular capas de abstracción.
Es llegar al núcleo de las cosas.

¿Qué pensás?

#Reflexiones #Pensamiento #Filosofía"""
    
    def _generate_story_template(self) -> str:
        """Generar post tipo historia."""
        return """Hace un tiempo me pasó algo que me hizo repensar cómo trabajo.

Estaba en medio de un proyecto importante y me di cuenta de que había estado optimizando lo incorrecto.

Me enfocaba en la eficiencia.
Debería haberme enfocado en la dirección.

A veces dar un paso atrás es la forma más rápida de avanzar.

¿Te pasó algo similar alguna vez?

#Productividad #Aprendizaje #Reflexiones"""
    
    def _generate_insight_template(self) -> str:
        """Generar post tipo insight profesional."""
        return """3 cosas que aprendí este año sobre automatización:

1️⃣ La mejor automatización es la que no notás
   → Debe integrarse naturalmente en tu flujo

2️⃣ Automatizar lo incorrecto es peor que no automatizar
   → Primero entendé el proceso, después automatizá

3️⃣ La revisión humana sigue siendo esencial
   → La IA asiste, no reemplaza el criterio

¿Cuál agregarías?

#Automatización #Productividad #IA #Tecnología"""
    
    def _build_prompt(self, post_type: str, article_id: Optional[int] = None) -> str:
        """Construir prompt para LLM."""
        # Obtener temas del perfil de voz para sugerir hashtags
        temas = self.voice.temas or []
        hashtags_sugeridos = [f"#{t.replace(' ', '')}" for t in temas[:5]]
        
        prompt_parts = [
            "Genera un post profesional para LinkedIn en español siguiendo este perfil de voz:",
            "",
            self.voice.to_prompt(),
            "",
            "IMPORTANTE sobre el formato de LinkedIn:",
            "- Los posts de LinkedIn pueden ser más largos (hasta 3000 caracteres)",
            "- Usa saltos de línea para mejorar la legibilidad",
            "- Evita bloques de texto muy densos",
            "- El tono debe ser profesional pero accesible",
            "- Puedes usar emojis con moderación (1-3 máximo)",
            "- Termina invitando a la interacción o reflexión",
            "",
            "HASHTAGS (OBLIGATORIO):",
            "- SIEMPRE incluye entre 3 y 5 hashtags relevantes al final del post",
            "- Los hashtags deben estar en una línea separada al final",
            "- Usa hashtags en español o inglés según el contexto",
            f"- Hashtags sugeridos basados en tu perfil: {', '.join(hashtags_sugeridos)}" if hashtags_sugeridos else "",
            "- Ejemplos de formato: #InteligenciaArtificial #Filosofía #Tecnología",
            "",
        ]
        
        if post_type == "promo" and article_id:
            article = self.db.fetchone("SELECT * FROM articulos WHERE id = ?", (article_id,))
            if article:
                prompt_parts.extend([
                    "Tipo de post: Promoción de artículo",
                    f"Título del artículo: {article['titulo']}",
                    f"Resumen: {article['resumen']}",
                    f"Plataforma original: {article.get('plataforma', 'blog')}",
                    f"Tags: {article.get('tags', '')}",
                    "",
                    "Genera un post que:",
                    "- Presente el artículo de forma atractiva y profesional",
                    "- Incluya un hook inicial que genere interés",
                    "- Resuma las ideas principales",
                    "- NO incluya el enlace en el texto (se agrega por separado)",
                    "- Invite a leer el artículo completo",
                    "- Termine con una pregunta o invitación a comentar",
                    "- Use 500-1000 caracteres aproximadamente",
                ])
        
        elif post_type == "thought":
            prompt_parts.extend([
                "Tipo de post: Reflexión o pensamiento",
                "",
                "Genera un post que:",
                "- Exprese una tesis o reflexión sobre algún tema de mi expertise",
                "- Sea conceptualmente denso pero accesible",
                "- Use formato de párrafos cortos o lista",
                "- Invite a la reflexión o al debate",
                "- Use 400-800 caracteres aproximadamente",
            ])
        
        elif post_type == "story":
            prompt_parts.extend([
                "Tipo de post: Historia o anécdota profesional",
                "",
                "Genera un post que:",
                "- Cuente una historia breve o anécdota profesional",
                "- Extraiga una lección o aprendizaje",
                "- Sea personal pero profesional",
                "- Conecte emocionalmente con el lector",
                "- Termine con una pregunta o reflexión",
                "- Use 500-1000 caracteres aproximadamente",
            ])
        
        elif post_type == "insight":
            prompt_parts.extend([
                "Tipo de post: Insight o lista profesional",
                "",
                "Genera un post que:",
                "- Comparta insights o aprendizajes en formato de lista (3-5 puntos)",
                "- Sea práctico y aplicable",
                "- Use emojis para los puntos (números o iconos)",
                "- Termine invitando a agregar más puntos",
                "- Use 400-800 caracteres aproximadamente",
            ])
        
        prompt_parts.append("\nGenera SOLO el texto del post, sin comillas ni explicaciones adicionales.")
        
        return "\n".join(prompt_parts)
    
    def save_post(self, post: Dict) -> int:
        """Guardar post de LinkedIn en base de datos."""
        # Usamos la misma tabla pero con metadata diferente
        db_post = {
            "content": post["content"],
            "content_hash": post["content_hash"],
            "tweet_type": f"linkedin_{post['post_type']}",  # Prefijo para distinguir
            "article_id": post.get("article_id"),
            "metadata": post.get("metadata", "{}")
        }
        return self.db.insert("tweet_candidates", db_post)
    
    def generate_batch(self, mix: Dict[str, int]) -> List[int]:
        """Generar lote de posts según mix especificado."""
        post_ids = []
        
        # Obtener artículos disponibles para promoción
        articles = self.db.fetchall(
            """
            SELECT id FROM articulos
            WHERE id NOT IN (
                SELECT DISTINCT article_id 
                FROM tweet_candidates 
                WHERE article_id IS NOT NULL
                AND tweet_type LIKE 'linkedin_%'
            )
            ORDER BY fecha_publicacion DESC
            """
        )
        
        article_pool = [a["id"] for a in articles]
        
        for post_type, count in mix.items():
            for i in range(count):
                article_id = None
                if post_type == "promo" and article_pool:
                    article_id = article_pool[i % len(article_pool)]
                
                posts = self.generate(post_type, article_id, count=1)
                
                if posts:
                    post_id = self.save_post(posts[0])
                    post_ids.append(post_id)
                    logger.info(f"Post de LinkedIn generado y guardado: {post_type} (ID: {post_id})")
        
        return post_ids
