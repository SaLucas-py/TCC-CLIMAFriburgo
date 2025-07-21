"""
Gerenciamento de conexões com banco de dados
"""
import psycopg2
import pandas as pd
import logging
from contextlib import contextmanager
from config.settings import DB_CONFIG

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gerenciador de conexões com PostgreSQL"""
    
    def __init__(self):
        self.config = DB_CONFIG
    
    @contextmanager
    def get_connection(self):
        """Context manager para conexões seguras"""
        conn = None
        try:
            conn = psycopg2.connect(**self.config)
            yield conn
        except psycopg2.Error as e:
            logger.error(f"Erro na conexão com banco: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query, params=None):
        """Executa query com tratamento de erro"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                if query.strip().upper().startswith('SELECT'):
                    return cursor.fetchall()
                conn.commit()
                return cursor.rowcount
            except psycopg2.Error as e:
                logger.error(f"Erro ao executar query: {e}")
                conn.rollback()
                raise
    
    def fetch_dataframe(self, query, params=None):
        """Retorna DataFrame a partir de query"""
        try:
            with self.get_connection() as conn:
                return pd.read_sql(query, conn, params=params)
        except Exception as e:
            logger.error(f"Erro ao carregar DataFrame: {e}")
            return pd.DataFrame()
    
    def test_connection(self):
        """Testa conexão com o banco"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Falha no teste de conexão: {e}")
            return False

# Instância global
db_manager = DatabaseManager()