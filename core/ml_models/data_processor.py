"""
Processamento de dados para ML
"""
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DataProcessor:
    """Processador de dados meteorológicos"""
    
    def __init__(self):
        pass
    
    def calculate_accumulated(self, df):
        """Calcula acumulados de precipitação em janelas de tempo"""
        try:
            # Garante que existe coluna timestamp
            if 'data_hora_captura' not in df.columns:
                if 'data' in df.columns and 'hora_utc' in df.columns:
                    df['timestamp'] = pd.to_datetime(
                        df['data'].astype(str) + ' ' + df['hora_utc'].astype(str), 
                        utc=True
                    )
                else:
                    logger.error("Colunas de data/hora não encontradas")
                    return df
            else:
                df['timestamp'] = pd.to_datetime(df['data_hora_captura'])
            
            # Ordena por timestamp
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Preenche valores nulos
            df['precipitacao'] = df['precipitacao'].fillna(0)
            
            # Calcula acumulados usando rolling window
            df['precip_1h'] = df['precipitacao'].rolling(
                window=1, min_periods=1
            ).sum()
            
            df['precip_4h'] = df['precipitacao'].rolling(
                window=4, min_periods=1
            ).sum()
            
            df['precip_24h'] = df['precipitacao'].rolling(
                window=24, min_periods=1
            ).sum()
            
            logger.info(f"Acumulados calculados para {len(df)} registros")
            return df
            
        except Exception as e:
            logger.error(f"Erro ao calcular acumulados: {e}")
            return df
    
    def add_weather_features(self, df):
        """Adiciona features meteorológicas derivadas"""
        try:
            # Índice de desconforto térmico
            if 'temperatura' in df.columns and 'umidade' in df.columns:
                df['indice_desconforto'] = (
                    df['temperatura'] - 
                    (0.55 - 0.0055 * df['umidade']) * 
                    (df['temperatura'] - 14.5)
                )
            
            # Tendências (diferença com registro anterior)
            if len(df) > 1:
                df['temp_trend'] = df['temperatura'].diff()
                df['umid_trend'] = df['umidade'].diff()
                df['precip_trend'] = df['precipitacao'].diff()
            
            # Classificação de intensidade da chuva
            df['intensidade_chuva'] = pd.cut(
                df['precipitacao'], 
                bins=[0, 0.1, 2.5, 10, 50, float('inf')],
                labels=['Sem chuva', 'Fraca', 'Moderada', 'Forte', 'Muito forte']
            )
            
            logger.info("Features meteorológicas adicionadas")
            return df
            
        except Exception as e:
            logger.error(f"Erro ao adicionar features: {e}")
            return df
    
    def create_labels_for_training(self, df):
        """Cria labels para treinamento do modelo usando limiares oficiais CEMADEN-RJ"""
        try:
            # Limiares oficiais do CEMADEN-RJ para Nova Friburgo (região serrana)
            # Fonte: Sistema original do usuário baseado em estudos técnicos
            limiares_1h = [100, 70, 50, 35]    # MUITO_ALTO, ALTO, MODERADO, BAIXO
            limiares_4h = [130, 90, 65, 50]
            limiares_24h = [220, 150, 100, 75]
            
            def classificar_precipitacao(precip, limiares):
                if precip >= limiares[0]:
                    return 'MUITO_ALTO'
                elif precip >= limiares[1]:
                    return 'ALTO'
                elif precip >= limiares[2]:
                    return 'MODERADO'
                elif precip >= limiares[3]:
                    return 'BAIXO'
                else:
                    return 'MUITO_BAIXO'
            
            # Aplica classificação para cada janela temporal
            df['alerta_1h'] = df['precip_1h'].apply(
                lambda x: classificar_precipitacao(x, limiares_1h)
            )
            df['alerta_4h'] = df['precip_4h'].apply(
                lambda x: classificar_precipitacao(x, limiares_4h)
            )
            df['alerta_24h'] = df['precip_24h'].apply(
                lambda x: classificar_precipitacao(x, limiares_24h)
            )
            
            # Alerta final é o mais alto entre as três janelas
            ordem_alertas = ['MUITO_BAIXO', 'BAIXO', 'MODERADO', 'ALTO', 'MUITO_ALTO']
            
            def max_alerta(row):
                alertas = [row['alerta_1h'], row['alerta_4h'], row['alerta_24h']]
                indices = [ordem_alertas.index(a) for a in alertas]
                return ordem_alertas[max(indices)]
            
            df['alerta'] = df.apply(max_alerta, axis=1)
            
            logger.info("Labels criadas para treinamento")
            return df
            
        except Exception as e:
            logger.error(f"Erro ao criar labels: {e}")
            return df
    
    def prepare_features_for_ml(self, df):
        """Prepara features para o modelo ML"""
        try:
            # Features principais
            feature_columns = ['precip_1h', 'precip_4h', 'precip_24h', 'umidade']
            
            # Adiciona features extras se disponíveis
            optional_features = [
                'temperatura', 'sensacao_termica', 'vento_max', 
                'indice_desconforto', 'temp_trend', 'umid_trend'
            ]
            
            for col in optional_features:
                if col in df.columns:
                    feature_columns.append(col)
            
            # Remove valores infinitos e NaN
            df = df.replace([np.inf, -np.inf], np.nan)
            
            # Seleciona apenas colunas de features que existem
            available_features = [col for col in feature_columns if col in df.columns]
            X = df[available_features].fillna(0)
            
            logger.info(f"Features preparadas: {available_features}")
            return X, available_features
            
        except Exception as e:
            logger.error(f"Erro ao preparar features: {e}")
            return pd.DataFrame(), []
    
    def validate_data_quality(self, df):
        """Valida qualidade dos dados"""
        try:
            issues = []
            
            # Verifica dados vazios
            if df.empty:
                issues.append("DataFrame vazio")
                return issues
            
            # Verifica colunas essenciais
            required_cols = ['precipitacao', 'umidade', 'temperatura']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                issues.append(f"Colunas ausentes: {missing_cols}")
            
            # Verifica valores negativos em precipitação
            if 'precipitacao' in df.columns:
                neg_precip = (df['precipitacao'] < 0).sum()
                if neg_precip > 0:
                    issues.append(f"Precipitação negativa em {neg_precip} registros")
            
            # Verifica umidade fora do range 0-100
            if 'umidade' in df.columns:
                invalid_umid = ((df['umidade'] < 0) | (df['umidade'] > 100)).sum()
                if invalid_umid > 0:
                    issues.append(f"Umidade inválida em {invalid_umid} registros")
            
            # Verifica temperaturas extremas
            if 'temperatura' in df.columns:
                extreme_temp = ((df['temperatura'] < -20) | (df['temperatura'] > 60)).sum()
                if extreme_temp > 0:
                    issues.append(f"Temperaturas extremas em {extreme_temp} registros")
            
            # Verifica dados muito antigos ou futuros
            if 'timestamp' in df.columns:
                now = datetime.now()
                future_data = (df['timestamp'] > now).sum()
                old_data = (df['timestamp'] < now - timedelta(days=365)).sum()
                
                if future_data > 0:
                    issues.append(f"Dados futuros: {future_data} registros")
                if old_data > 0:
                    issues.append(f"Dados muito antigos: {old_data} registros")
            
            if issues:
                logger.warning(f"Problemas na qualidade dos dados: {issues}")
            else:
                logger.info("Qualidade dos dados validada com sucesso")
            
            return issues
            
        except Exception as e:
            logger.error(f"Erro na validação dos dados: {e}")
            return [f"Erro na validação: {e}"]