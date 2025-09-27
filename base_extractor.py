from abc import ABC, abstractmethod
from typing import List, Dict, Any
import json
import logging
from datetime import datetime
from pathlib import Path

# Configuración de logging - se hace en main.py

class BasePlatformExtractor(ABC):
    """
    Clase abstracta base para extractores de plataformas.
    Define la interfaz común para LessWrong, EA Forum, y futuras plataformas.
    """

    def __init__(self, base_output_dir: str = "raw-data"):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.base_output_dir = Path(base_output_dir)
        self.platform_name = self.get_platform_name()
        self.extraction_date = datetime.now().strftime("%Y-%m-%d")
        self.setup_directories()
        self.logger.info(f"Inicializado extractor para {self.platform_name}")

    @abstractmethod
    def get_platform_name(self) -> str:
        """Retorna el nombre de la plataforma (lesswrong, eaforum, etc)"""
        pass

    @abstractmethod
    def extract_top_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Extrae los top N usuarios según criterios de AI Safety.
        Returns: Lista de diccionarios con datos de usuarios
        """
        pass

    @abstractmethod
    def extract_user_posts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Extrae todos los posts históricos de un usuario.
        Returns: Lista de posts con metadata completa
        """
        pass

    @abstractmethod
    def extract_user_comments(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Extrae todos los comentarios de un usuario.
        Returns: Lista de comentarios con contexto
        """
        pass

    def setup_directories(self):
        """Crea la estructura de carpetas necesaria"""
        self.output_dir = self.base_output_dir / self.platform_name / self.extraction_date
        self.posts_dir = self.output_dir / "posts"
        self.comments_dir = self.output_dir / "comments"

        # Crear directorios si no existen
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.posts_dir.mkdir(exist_ok=True)
        self.comments_dir.mkdir(exist_ok=True)

        self.logger.debug(f"Directorios creados en {self.output_dir}")

    def save_to_json(self, data: Any, filepath: Path):
        """Guarda datos en formato JSON con formato legible"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            self.logger.debug(f"Datos guardados en {filepath}")
        except Exception as e:
            self.logger.error(f"Error guardando JSON en {filepath}: {e}")
            raise

    def extract_and_save_all(self, limit: int = 100):
        """Pipeline completo de extracción"""
        self.logger.info(f"Iniciando extracción de {self.platform_name}")

        try:
            # 1. Extraer top usuarios
            self.logger.info(f"Extrayendo top {limit} usuarios...")
            users = self.extract_top_users(limit)
            self.save_to_json(users, self.output_dir / f"users_top{limit}.json")
            self.logger.info(f"Extraídos {len(users)} usuarios")

            # 2. Para cada usuario, extraer posts y comentarios
            for i, user in enumerate(users, 1):
                user_id = user['userId']
                username = user.get('username', user_id)

                self.logger.info(f"Procesando usuario {i}/{len(users)}: {username}")

                try:
                    # Extraer y guardar posts
                    posts = self.extract_user_posts(user_id)
                    self.save_to_json(posts, self.posts_dir / f"user_{user_id}_posts.json")

                    # Extraer y guardar comentarios
                    comments = self.extract_user_comments(user_id)
                    self.save_to_json(comments, self.comments_dir / f"user_{user_id}_comments.json")

                    # Agregar conteos al objeto usuario
                    user['post_count'] = len(posts)
                    user['comment_count'] = len(comments)

                    self.logger.debug(f"Usuario {username}: {len(posts)} posts, {len(comments)} comentarios")

                except Exception as e:
                    self.logger.error(f"Error procesando usuario {username}: {e}")
                    user['extraction_error'] = str(e)
                    continue

                # Checkpoint cada 10 usuarios
                if i % 10 == 0:
                    self.save_checkpoint(users[:i], i)

            # 3. Guardar resumen final
            summary = {
                'platform': self.platform_name,
                'extraction_date': self.extraction_date,
                'total_users': len(users),
                'users': users
            }
            self.save_to_json(summary, self.output_dir / "extraction_summary.json")

            self.logger.info(f"Extracción completada. Datos guardados en {self.output_dir}")

        except Exception as e:
            self.logger.error(f"Error en extracción: {e}")
            raise

    def save_checkpoint(self, users: List[Dict], count: int):
        """Guarda checkpoint de progreso"""
        checkpoint_file = self.output_dir / f"checkpoint_{count}.json"
        self.save_to_json(users, checkpoint_file)
        self.logger.info(f"Checkpoint guardado: {count} usuarios procesados")