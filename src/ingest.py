"""Importación de artículos desde CSV y JSON."""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .db import Database
from .utils import parse_datetime, setup_logging

logger = setup_logging()


class ArticleImporter:
    """Importador de artículos."""
    
    def __init__(self, db: Database):
        """Inicializar importador."""
        self.db = db
    
    def import_from_csv(self, file_path: Path) -> int:
        """Importar artículos desde archivo CSV."""
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        imported = 0
        skipped = 0
        errors = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    article = self._parse_csv_row(row)
                    
                    # Verificar si ya existe
                    existing = self.db.fetchone(
                        "SELECT id FROM articulos WHERE url = ?",
                        (article["url"],)
                    )
                    
                    if existing:
                        logger.info(f"Artículo ya existe: {article['titulo']}")
                        skipped += 1
                        continue
                    
                    # Insertar artículo
                    self.db.insert("articulos", article)
                    logger.info(f"Artículo importado: {article['titulo']}")
                    imported += 1
                    
                except Exception as e:
                    logger.error(f"Error importando artículo: {e}")
                    errors += 1
        
        logger.info(f"Importación completada: {imported} importados, {skipped} omitidos, {errors} errores")
        return imported
    
    def import_from_json(self, file_path: Path) -> int:
        """Importar artículos desde archivo JSON."""
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            data = [data]
        
        imported = 0
        skipped = 0
        errors = 0
        
        for item in data:
            try:
                article = self._parse_json_item(item)
                
                # Verificar si ya existe
                existing = self.db.fetchone(
                    "SELECT id FROM articulos WHERE url = ?",
                    (article["url"],)
                )
                
                if existing:
                    logger.info(f"Artículo ya existe: {article['titulo']}")
                    skipped += 1
                    continue
                
                # Insertar artículo
                self.db.insert("articulos", article)
                logger.info(f"Artículo importado: {article['titulo']}")
                imported += 1
                
            except Exception as e:
                logger.error(f"Error importando artículo: {e}")
                errors += 1
        
        logger.info(f"Importación completada: {imported} importados, {skipped} omitidos, {errors} errores")
        return imported
    
    def add_article_interactive(self) -> Optional[int]:
        """Agregar artículo de forma interactiva."""
        from rich.prompt import Prompt
        
        print("\n=== Agregar Artículo ===\n")
        
        titulo = Prompt.ask("Título")
        url = Prompt.ask("URL")
        plataforma = Prompt.ask("Plataforma", choices=["linkedin", "substack", "otro"], default="linkedin")
        fecha_str = Prompt.ask("Fecha de publicación (YYYY-MM-DD)", default=datetime.now().strftime("%Y-%m-%d"))
        tags = Prompt.ask("Tags (separados por coma)", default="")
        resumen = Prompt.ask("Resumen breve", default="")
        idioma = Prompt.ask("Idioma", choices=["es", "en"], default="es")
        
        try:
            fecha = parse_datetime(fecha_str)
            
            article = {
                "titulo": titulo,
                "url": url,
                "plataforma": plataforma,
                "fecha_publicacion": fecha.strftime("%Y-%m-%d"),
                "tags": tags,
                "resumen": resumen,
                "idioma": idioma
            }
            
            # Verificar si ya existe
            existing = self.db.fetchone(
                "SELECT id FROM articulos WHERE url = ?",
                (article["url"],)
            )
            
            if existing:
                logger.warning(f"Artículo ya existe con ID: {existing['id']}")
                return existing['id']
            
            # Insertar artículo
            article_id = self.db.insert("articulos", article)
            logger.info(f"Artículo agregado con ID: {article_id}")
            print(f"\n✓ Artículo agregado exitosamente (ID: {article_id})")
            
            return article_id
            
        except Exception as e:
            logger.error(f"Error agregando artículo: {e}")
            print(f"\n✗ Error: {e}")
            return None
    
    def _parse_csv_row(self, row: Dict[str, str]) -> Dict[str, str]:
        """Parsear fila de CSV a diccionario de artículo."""
        fecha = parse_datetime(row.get("fecha_publicacion", ""))
        
        return {
            "titulo": row["titulo"],
            "url": row["url"],
            "plataforma": row.get("plataforma", "otro"),
            "fecha_publicacion": fecha.strftime("%Y-%m-%d"),
            "tags": row.get("tags", ""),
            "resumen": row.get("resumen", ""),
            "idioma": row.get("idioma", "es")
        }
    
    def _parse_json_item(self, item: Dict) -> Dict[str, str]:
        """Parsear item de JSON a diccionario de artículo."""
        fecha = parse_datetime(item.get("fecha_publicacion", ""))
        
        return {
            "titulo": item["titulo"],
            "url": item["url"],
            "plataforma": item.get("plataforma", "otro"),
            "fecha_publicacion": fecha.strftime("%Y-%m-%d"),
            "tags": item.get("tags", ""),
            "resumen": item.get("resumen", ""),
            "idioma": item.get("idioma", "es")
        }
    
    def list_articles(self, limit: int = 10) -> List[Dict]:
        """Listar artículos importados."""
        return self.db.fetchall(
            """
            SELECT id, titulo, url, plataforma, fecha_publicacion, tags, idioma
            FROM articulos
            ORDER BY fecha_publicacion DESC
            LIMIT ?
            """,
            (limit,)
        )
    
    def get_article(self, article_id: int) -> Optional[Dict]:
        """Obtener artículo por ID."""
        return self.db.fetchone(
            "SELECT * FROM articulos WHERE id = ?",
            (article_id,)
        )
    
    def search_articles(self, query: str) -> List[Dict]:
        """Buscar artículos por título o tags."""
        return self.db.fetchall(
            """
            SELECT id, titulo, url, plataforma, fecha_publicacion, tags, idioma
            FROM articulos
            WHERE titulo LIKE ? OR tags LIKE ?
            ORDER BY fecha_publicacion DESC
            """,
            (f"%{query}%", f"%{query}%")
        )
