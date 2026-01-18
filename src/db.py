"""Gestión de base de datos SQLite."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils import get_data_dir, setup_logging

logger = setup_logging()


class Database:
    """Gestor de base de datos SQLite."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Inicializar conexión a la base de datos."""
        if db_path is None:
            db_path = get_data_dir() / "tweets.db"
        
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
        logger.info(f"Base de datos inicializada: {db_path}")
    
    def _init_schema(self):
        """Crear esquema de base de datos."""
        cursor = self.conn.cursor()
        
        # Tabla de artículos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articulos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                plataforma TEXT NOT NULL,
                fecha_publicacion DATE NOT NULL,
                tags TEXT,
                resumen TEXT,
                idioma TEXT DEFAULT 'es',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de candidatos a tweets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tweet_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE,
                tweet_type TEXT NOT NULL,
                article_id INTEGER,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articulos(id)
            )
        """)
        
        # Tabla de cola de tweets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tweet_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                status TEXT DEFAULT 'drafted',
                scheduled_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (candidate_id) REFERENCES tweet_candidates(id)
            )
        """)
        
        # Tabla de tweets publicados
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tweets_publicados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                tweet_id TEXT,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                platform_response TEXT,
                FOREIGN KEY (candidate_id) REFERENCES tweet_candidates(id)
            )
        """)
        
        # Tabla de configuración
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Índices
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_fecha 
            ON articulos(fecha_publicacion)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_queue_status 
            ON tweet_queue(status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_queue_scheduled 
            ON tweet_queue(scheduled_at)
        """)

        # Índice único para evitar duplicados en el mismo slot
        # Solo para posts que están programados o publicados
        # Esto previene problemas si dos procesos intentan programar al mismo tiempo
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_slot
            ON tweet_queue(scheduled_at)
            WHERE status IN ('scheduled', 'posted')
        """)
        
        self.conn.commit()
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Ejecutar query SQL."""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor
    
    def fetchone(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Ejecutar query y obtener un resultado."""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def fetchall(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Ejecutar query y obtener todos los resultados."""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """Insertar registro en tabla."""
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        cursor = self.execute(query, tuple(data.values()))
        return cursor.lastrowid
    
    def update(self, table: str, data: Dict[str, Any], where: str, params: tuple = ()) -> int:
        """Actualizar registros en tabla."""
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        
        cursor = self.execute(query, tuple(data.values()) + params)
        return cursor.rowcount
    
    def delete(self, table: str, where: str, params: tuple = ()) -> int:
        """Eliminar registros de tabla."""
        query = f"DELETE FROM {table} WHERE {where}"
        cursor = self.execute(query, params)
        return cursor.rowcount
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Obtener valor de configuración."""
        result = self.fetchone("SELECT value FROM settings WHERE key = ?", (key,))
        return result["value"] if result else default
    
    def set_setting(self, key: str, value: Any):
        """Establecer valor de configuración."""
        self.execute(
            """
            INSERT INTO settings (key, value, updated_at) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET 
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, str(value))
        )
    
    def log(self, level: str, message: str, context: Optional[str] = None):
        """Registrar log en base de datos."""
        self.insert("logs", {
            "level": level,
            "message": message,
            "context": context
        })
    
    def close(self):
        """Cerrar conexión a la base de datos."""
        self.conn.close()
        logger.info("Conexión a base de datos cerrada")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
