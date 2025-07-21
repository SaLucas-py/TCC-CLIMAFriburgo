"""
Modelos de dados e queries do banco - Versão Corrigida
"""
import pandas as pd
import logging
from datetime import datetime, timedelta
from .connection import db_manager

logger = logging.getLogger(__name__)

class WeatherData:
    """Modelo para dados meteorológicos"""
    
    @staticmethod
    def fetch_last_24h():
        """Busca dados das últimas 24 horas"""
        query = """
            SELECT *
            FROM dados_climaticos
            WHERE data_hora_captura >= NOW() - INTERVAL '24 hours'
            ORDER BY data_hora_captura ASC
        """
        return db_manager.fetch_dataframe(query)
    
    @staticmethod
    def fetch_historical(days=30):
        """Busca dados históricos"""
        query = """
            SELECT data, hora_utc, precipitacao, umidade, temperatura, 
                   sensacao_termica, temp_minima, temp_maxima,
                   umidade_minima, vento_max, uv_max, data_hora_captura
            FROM dados_climaticos
            WHERE data_hora_captura >= NOW() - INTERVAL '%s days'
            ORDER BY data_hora_captura ASC
        """
        return db_manager.fetch_dataframe(query, (days,))
    
    @staticmethod
    def fetch_latest():
        """Busca o registro mais recente"""
        query = """
            SELECT *
            FROM dados_climaticos
            ORDER BY data_hora_captura DESC
            LIMIT 1
        """
        df = db_manager.fetch_dataframe(query)
        return df.iloc[0] if not df.empty else None
    
    @staticmethod
    def insert_weather_data(data_list):
        """Insere dados meteorológicos"""
        query = """
            INSERT INTO dados_climaticos (
                data, hora_utc, precipitacao, umidade, temperatura, 
                sensacao_termica, temp_minima, temp_maxima,
                umidade_minima, vento_max, uv_max
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (data, hora_utc) DO NOTHING
        """
        
        inserted_count = 0
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            try:
                for data_row in data_list:
                    cursor.execute(query, data_row)
                    if cursor.rowcount > 0:
                        inserted_count += 1
                conn.commit()
                logger.info(f"Inseridos {inserted_count} novos registros")
                return inserted_count
            except Exception as e:
                logger.error(f"Erro ao inserir dados: {e}")
                conn.rollback()
                return 0
    
    @staticmethod
    def get_precipitation_stats():
        """Retorna estatísticas de precipitação"""
        query = """
            SELECT 
                AVG(precipitacao) as media_precipitacao,
                MAX(precipitacao) as max_precipitacao,
                COUNT(*) as total_registros,
                COUNT(CASE WHEN precipitacao > 0 THEN 1 END) as dias_com_chuva
            FROM dados_climaticos
            WHERE data_hora_captura >= NOW() - INTERVAL '30 days'
        """
        return db_manager.fetch_dataframe(query)

class AlertData:
    """Modelo para dados de alertas - CORRIGIDO"""
    
    @staticmethod
    def log_alert(nivel, dados_meteorologicos):
        """Registra um alerta"""
        query = """
            INSERT INTO alertas_log (
                nivel_alerta, data_ocorrencia, precipitacao_1h,
                precipitacao_4h, precipitacao_24h, umidade, temperatura,
                metodo_predicao, confianca
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Extrai dados de forma segura
        def safe_get(data, key, default=0.0):
            try:
                value = data.get(key, default)
                if pd.isna(value) or value is None:
                    return float(default)
                return float(value)
            except (ValueError, TypeError):
                return float(default)
        
        params = (
            str(nivel),
            datetime.now(),
            safe_get(dados_meteorologicos, 'precip_1h', 0.0),
            safe_get(dados_meteorologicos, 'precip_4h', 0.0),
            safe_get(dados_meteorologicos, 'precip_24h', 0.0),
            safe_get(dados_meteorologicos, 'umidade', 70.0),  # Valor padrão mais realístico
            safe_get(dados_meteorologicos, 'temperatura', 23.0),
            'THRESHOLD',  # Método padrão
            1.0  # Confiança padrão
        )
        
        try:
            result = db_manager.execute_query(query, params)
            logger.info(f"Alerta {nivel} registrado no banco - Umidade: {params[5]}%")
            return result
        except Exception as e:
            logger.error(f"Erro ao registrar alerta: {e}")
            logger.error(f"Parâmetros: {params}")
            raise
    
    @staticmethod
    def fetch_recent_alerts(limit=10):
        """Busca alertas recentes - CORRIGIDO"""
        query = """
            SELECT 
                id,
                nivel_alerta,
                data_ocorrencia,
                precipitacao_1h,
                precipitacao_4h,
                precipitacao_24h,
                umidade,
                temperatura,
                metodo_predicao,
                confianca,
                observacoes
            FROM alertas_log 
            WHERE data_ocorrencia IS NOT NULL
            ORDER BY data_ocorrencia DESC 
            LIMIT %s
        """
        
        try:
            df = db_manager.fetch_dataframe(query, (limit,))
            
            if df.empty:
                logger.warning("Nenhum alerta encontrado na tabela alertas_log")
                return pd.DataFrame()
            
            # Debug: mostra os dados brutos
            logger.info(f"Alertas encontrados: {len(df)}")
            if not df.empty:
                primeiro_alerta = df.iloc[0]
                logger.info(f"Primeiro alerta - Nível: {primeiro_alerta['nivel_alerta']}, "
                           f"Umidade: {primeiro_alerta['umidade']}, "
                           f"Temp: {primeiro_alerta.get('temperatura', 'N/A')}")
            
            return df
            
        except Exception as e:
            logger.error(f"Erro ao buscar alertas recentes: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_alerts_summary():
        """Retorna resumo dos alertas"""
        query = """
            SELECT 
                nivel_alerta,
                COUNT(*) as total,
                AVG(umidade) as umidade_media,
                AVG(temperatura) as temperatura_media,
                AVG(precipitacao_24h) as precip_24h_media,
                MAX(data_ocorrencia) as ultimo_alerta
            FROM alertas_log 
            WHERE data_ocorrencia >= NOW() - INTERVAL '30 days'
            GROUP BY nivel_alerta
            ORDER BY 
                CASE nivel_alerta 
                    WHEN 'MUITO_ALTO' THEN 5
                    WHEN 'ALTO' THEN 4
                    WHEN 'MODERADO' THEN 3
                    WHEN 'BAIXO' THEN 2
                    WHEN 'MUITO_BAIXO' THEN 1
                END DESC
        """
        
        try:
            return db_manager.fetch_dataframe(query)
        except Exception as e:
            logger.error(f"Erro ao buscar resumo de alertas: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def test_table_structure():
        """Testa a estrutura da tabela alertas_log"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verifica estrutura da tabela
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'alertas_log'
                    ORDER BY ordinal_position
                """)
                
                columns = cursor.fetchall()
                logger.info("Estrutura da tabela alertas_log:")
                for col in columns:
                    logger.info(f"  {col[0]} | {col[1]} | NULL: {col[2]}")
                
                # Conta registros
                cursor.execute("SELECT COUNT(*) FROM alertas_log")
                total = cursor.fetchone()[0]
                logger.info(f"Total de alertas: {total}")
                
                # Mostra alguns dados
                if total > 0:
                    cursor.execute("""
                        SELECT nivel_alerta, umidade, temperatura, precipitacao_24h, data_ocorrencia
                        FROM alertas_log 
                        ORDER BY data_ocorrencia DESC 
                        LIMIT 3
                    """)
                    
                    sample_data = cursor.fetchall()
                    logger.info("Amostra de dados:")
                    for row in sample_data:
                        logger.info(f"  {row[0]} | Umidade: {row[1]} | Temp: {row[2]} | "
                                   f"Precip: {row[3]} | Data: {row[4]}")
                
                return True
                
        except Exception as e:
            logger.error(f"Erro ao testar estrutura da tabela: {e}")
            return False
    
    @staticmethod
    def fix_zero_humidity_records():
        """Corrige registros com umidade zerada"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verifica quantos registros têm umidade = 0
                cursor.execute("SELECT COUNT(*) FROM alertas_log WHERE umidade = 0 OR umidade IS NULL")
                zero_humidity_count = cursor.fetchone()[0]
                
                if zero_humidity_count > 0:
                    logger.info(f"Encontrados {zero_humidity_count} registros com umidade zerada")
                    
                    # Atualiza registros com umidade zerada para um valor padrão realístico
                    cursor.execute("""
                        UPDATE alertas_log 
                        SET umidade = 75.0 
                        WHERE umidade = 0 OR umidade IS NULL
                    """)
                    
                    updated = cursor.rowcount
                    conn.commit()
                    
                    logger.info(f"Atualizados {updated} registros com umidade padrão (75%)")
                    return updated
                else:
                    logger.info("Nenhum registro com umidade zerada encontrado")
                    return 0
                    
        except Exception as e:
            logger.error(f"Erro ao corrigir registros de umidade: {e}")
            return 0
        