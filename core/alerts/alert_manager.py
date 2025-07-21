"""
Gerenciador de alertas hidrológicos - Versão sem duplicatas
"""
import os
import joblib
import pandas as pd
import logging
from datetime import datetime, timedelta
from config.settings import ALERT_CONFIG, ML_CONFIG
from core.database.models import WeatherData, AlertData
from core.ml_models.data_processor import DataProcessor

logger = logging.getLogger(__name__)

class AlertManager:
    """Gerenciador principal de alertas"""
    
    def __init__(self):
        # Usa os limiares oficiais do CEMADEN-RJ (do código original do usuário)
        self.thresholds = {
            'MUITO_ALTO': {'1h': 100, '4h': 130, '24h': 220},
            'ALTO': {'1h': 70, '4h': 90, '24h': 150},
            'MODERADO': {'1h': 50, '4h': 65, '24h': 100},  # Corrigido typo "MEDIADO"
            'BAIXO': {'1h': 35, '4h': 50, '24h': 75},
            'MUITO_BAIXO': {'1h': 0, '4h': 0, '24h': 0}
        }
        
        self.colors = ALERT_CONFIG['colors']
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.last_alert_time = None  # NOVO: Controla último alerta salvo
        self.last_alert_level = None  # NOVO: Controla último nível de alerta
        self._load_model()
    
    def _load_model(self):
        """Carrega modelo de ML de forma segura"""
        try:
            model_path = ML_CONFIG['model_path']
            
            if not os.path.exists(model_path):
                logger.warning(f"⚠️ Modelo não encontrado em: {model_path}")
                logger.info("💡 Execute 'python simple_training.py' para criar o modelo")
                return False
            
            # Carrega dados do modelo
            model_data = joblib.load(model_path)
            
            # Verifica se é o formato antigo (só o modelo) ou novo (dict com metadados)
            if hasattr(model_data, 'predict'):
                # Formato antigo - só o modelo
                self.model = model_data
                self.feature_names = ['precip_1h', 'precip_4h', 'precip_24h', 'umidade']
                logger.info("✅ Modelo ML carregado (formato antigo)")
            elif isinstance(model_data, dict):
                # Formato novo - dict com metadados
                self.model = model_data.get('model')
                self.scaler = model_data.get('scaler')
                self.feature_names = model_data.get('feature_names', ['precip_1h', 'precip_4h', 'precip_24h', 'umidade'])
                
                if self.model and hasattr(self.model, 'predict'):
                    logger.info("✅ Modelo ML carregado com metadados")
                    if 'created_at' in model_data:
                        logger.info(f"   Data de criação: {model_data['created_at']}")
                    if 'accuracy' in model_data:
                        logger.info(f"   Acurácia: {model_data['accuracy']:.3f}")
                else:
                    logger.error("❌ Modelo no arquivo não é válido")
                    return False
            else:
                logger.error("❌ Formato do modelo não reconhecido")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar modelo: {e}")
            logger.info("💡 Tente executar 'python simple_training.py' para recriar o modelo")
            return False
    
    def classify_by_threshold(self, precip_1h, precip_4h, precip_24h):
        """Classifica alerta baseado em thresholds oficiais"""
        try:
            for nivel, limites in self.thresholds.items():
                if (precip_1h >= limites['1h'] or
                    precip_4h >= limites['4h'] or
                    precip_24h >= limites['24h']):
                    return nivel
            return 'MUITO_BAIXO'
        except Exception as e:
            logger.error(f"Erro na classificação por threshold: {e}")
            return 'MUITO_BAIXO'
    
    def classify_by_ml(self, dados):
        """Classifica alerta usando modelo ML de forma segura"""
        if not self.model:
            logger.debug("Modelo ML não disponível")
            return None
        
        try:
            # Prepara dados de entrada
            input_data = {}
            
            # Garante que temos as features necessárias
            for feature in self.feature_names:
                if feature in dados:
                    input_data[feature] = float(dados[feature])
                else:
                    # Valores padrão se a feature não existir
                    default_values = {
                        'precip_1h': 0.0,
                        'precip_4h': 0.0,
                        'precip_24h': 0.0,
                        'umidade': 70.0,
                        'temperatura': 23.0,
                        'sensacao_termica': 23.0,
                        'vento_max': 0.0,
                        'indice_desconforto': 23.0,
                        'temp_trend': 0.0,
                        'umid_trend': 0.0
                    }
                    input_data[feature] = default_values.get(feature, 0.0)
                    logger.warning(f"Feature '{feature}' não encontrada, usando valor padrão: {input_data[feature]}")
            
            # Cria DataFrame para predição
            X_input = pd.DataFrame([input_data])
            
            # Aplica normalização se disponível
            if self.scaler:
                try:
                    X_input_scaled = self.scaler.transform(X_input)
                    prediction = self.model.predict(X_input_scaled)[0]
                    logger.debug("Predição ML com normalização realizada")
                except Exception as e:
                    logger.warning(f"Erro na normalização, usando dados brutos: {e}")
                    prediction = self.model.predict(X_input)[0]
            else:
                prediction = self.model.predict(X_input)[0]
                logger.debug("Predição ML sem normalização realizada")
            
            logger.debug(f"Predição ML: {prediction} para dados: {input_data}")
            return prediction
            
        except Exception as e:
            logger.error(f"Erro na predição ML: {e}")
            logger.debug(f"Dados recebidos: {dados}")
            logger.debug(f"Features esperadas: {self.feature_names}")
            return None
    
    def _should_save_alert(self, nivel_atual, dados_atuais):
        """Verifica se deve salvar um novo alerta (evita duplicatas)"""
        try:
            # Busca o último alerta salvo
            recent_alerts = AlertData.fetch_recent_alerts(1)
            
            if recent_alerts.empty:
                # Primeiro alerta - pode salvar
                logger.debug("Primeiro alerta - salvando")
                return True
            
            ultimo_alerta = recent_alerts.iloc[0]
            ultimo_nivel = ultimo_alerta['nivel_alerta']
            ultima_data = ultimo_alerta['data_ocorrencia']
            
            # Verifica se o último alerta foi há menos de 1 hora
            agora = datetime.now()
            if pd.notnull(ultima_data):
                # Remove timezone info se necessário
                if hasattr(ultima_data, 'tz_localize'):
                    ultima_data = ultima_data.tz_localize(None)
                
                tempo_desde_ultimo = agora - ultima_data
                
                # Se foi há menos de 1 hora E o nível é o mesmo, NÃO salva
                if tempo_desde_ultimo < timedelta(hours=1) and ultimo_nivel == nivel_atual:
                    logger.debug(f"Alerta duplicado ignorado: {nivel_atual} (último há {tempo_desde_ultimo})")
                    return False
                
                # Se mudou o nível de alerta, sempre salva
                if ultimo_nivel != nivel_atual:
                    logger.info(f"Mudança de nível detectada: {ultimo_nivel} → {nivel_atual}")
                    return True
                
                # Se foi há mais de 1 hora, salva novo alerta
                if tempo_desde_ultimo >= timedelta(hours=1):
                    logger.debug(f"Novo alerta após {tempo_desde_ultimo}: {nivel_atual}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao verificar se deve salvar alerta: {e}")
            # Em caso de erro, não salva para evitar duplicatas
            return False
    
    def check_alerts(self):
        """Verifica e gera alertas de forma robusta"""
        try:
            logger.debug("Iniciando verificação de alertas...")
            
            # Busca dados das últimas 24h
            dados_df = WeatherData.fetch_last_24h()
            if dados_df.empty:
                logger.warning("⚠️ Nenhum dado disponível nas últimas 24 horas")
                return self._create_default_alert()
            
            logger.debug(f"Dados encontrados: {len(dados_df)} registros")
            
            # Processa dados
            processor = DataProcessor()
            
            # Valida qualidade dos dados
            issues = processor.validate_data_quality(dados_df)
            if issues:
                logger.warning(f"Problemas na qualidade dos dados: {issues}")
            
            # Calcula acumulados
            dados_processados = processor.calculate_accumulated(dados_df)
            
            if dados_processados.empty:
                logger.warning("⚠️ Erro no processamento dos dados")
                return self._create_default_alert()
            
            # Último registro
            ultimo_registro = dados_processados.iloc[-1].to_dict()
            logger.debug(f"Último registro: {ultimo_registro}")
            
            # Garante valores padrão para campos obrigatórios
            campos_obrigatorios = {
                'precip_1h': 0.0,
                'precip_4h': 0.0,
                'precip_24h': 0.0,
                'umidade': 70.0,
                'temperatura': 23.0,
                'data': datetime.now().strftime('%Y-%m-%d'),
                'hora_utc': datetime.now().strftime('%H:%M')
            }
            
            for campo, valor_padrao in campos_obrigatorios.items():
                if campo not in ultimo_registro or pd.isna(ultimo_registro[campo]):
                    ultimo_registro[campo] = valor_padrao
                    logger.debug(f"Campo '{campo}' preenchido com valor padrão: {valor_padrao}")
            
            # Classificações
            nivel_threshold = self.classify_by_threshold(
                ultimo_registro['precip_1h'],
                ultimo_registro['precip_4h'],
                ultimo_registro['precip_24h']
            )
            
            nivel_ml = self.classify_by_ml(ultimo_registro)
            
            # Usa ML se disponível, senão threshold
            nivel_final = nivel_ml if nivel_ml else nivel_threshold
            
            # Log das predições
            logger.info(f"🎯 Predição THRESHOLD: {nivel_threshold}")
            if nivel_ml:
                logger.info(f"🤖 Predição ML: {nivel_ml}")
                if nivel_ml != nivel_threshold:
                    logger.info(f"⚖️ Divergência detectada: ML={nivel_ml} vs THRESHOLD={nivel_threshold}")
            else:
                logger.info("🤖 Predição ML: Não disponível")
            
            logger.info(f"🚨 Nível final: {nivel_final}")
            
            # Exibe alerta
            self._display_alert(nivel_final, ultimo_registro)
            
            # NOVO: Só salva se realmente precisar (evita duplicatas)
            if self._should_save_alert(nivel_final, ultimo_registro):
                try:
                    AlertData.log_alert(nivel_final, ultimo_registro)
                    logger.info(f"💾 Novo alerta salvo: {nivel_final}")
                except Exception as e:
                    logger.error(f"Erro ao salvar alerta no banco: {e}")
            else:
                logger.debug(f"🔄 Alerta não salvo (evitando duplicata): {nivel_final}")
            
            # Compara predições se ambas disponíveis
            if nivel_ml and nivel_ml != nivel_threshold:
                self._log_divergence(nivel_ml, nivel_threshold, ultimo_registro)
            
            return {
                'nivel': nivel_final,
                'dados': ultimo_registro,
                'timestamp': datetime.now(),
                'ml_prediction': nivel_ml,
                'threshold_prediction': nivel_threshold,
                'divergencia': nivel_ml != nivel_threshold if nivel_ml else False
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar alertas: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return self._create_default_alert()
    
    def _create_default_alert(self):
        """Cria alerta padrão quando há erros"""
        logger.info("Criando alerta padrão devido a erro/falta de dados")
        return {
            'nivel': 'MUITO_BAIXO',
            'dados': {
                'data': datetime.now().strftime('%Y-%m-%d'),
                'hora_utc': datetime.now().strftime('%H:%M'),
                'precip_1h': 0.0,
                'precip_4h': 0.0,
                'precip_24h': 0.0,
                'umidade': 70.0,
                'temperatura': 23.0
            },
            'timestamp': datetime.now(),
            'ml_prediction': None,
            'threshold_prediction': 'MUITO_BAIXO',
            'divergencia': False,
            'erro': 'Dados insuficientes ou erro no processamento'
        }
    
    def _display_alert(self, nivel, dados):
        """Exibe alerta colorido no terminal"""
        cores = {
            'MUITO_BAIXO': '\033[94m',  # Azul
            'BAIXO': '\033[36m',        # Ciano
            'MODERADO': '\033[33m',     # Amarelo
            'ALTO': '\033[91m',         # Vermelho claro
            'MUITO_ALTO': '\033[31m'    # Vermelho escuro
        }
        reset_cor = '\033[0m'
        
        cor = cores.get(nivel, '\033[37m')  # Branco como padrão
        
        mensagem = f"""
    {cor}=== ALERTA HIDROLÓGICO ==={reset_cor}
    🏙️ Cidade: Nova Friburgo - RJ
    🚨 Nível: {cor}{nivel}{reset_cor}
    📅 Data: {dados.get('data', 'N/A')} {dados.get('hora_utc', 'N/A')} UTC
    💧 Precipitação:
       - 1h: {dados.get('precip_1h', 0):.1f} mm
       - 4h: {dados.get('precip_4h', 0):.1f} mm
       - 24h: {dados.get('precip_24h', 0):.1f} mm
    🌡️ Temperatura: {dados.get('temperatura', 0):.1f}°C
    💨 Umidade: {dados.get('umidade', 0):.1f}%
        """
        print(mensagem)
        
        # Log em arquivo
        try:
            with open("logs/alertas.log", "a", encoding='utf-8') as log:
                log.write(f"{datetime.now()} - {nivel} - Precip: {dados.get('precip_24h', 0):.1f}mm/24h\n")
        except Exception as e:
            logger.warning(f"Erro ao escrever log de alerta: {e}")
    
    def _log_divergence(self, ml_pred, threshold_pred, dados):
        """Registra divergências entre predições"""
        try:
            with open("logs/divergencias_alerta.log", "a", encoding='utf-8') as log:
                log.write(
                    f"{datetime.now()} - {dados.get('data')} {dados.get('hora_utc')} | "
                    f"ML = {ml_pred} | THRESHOLD = {threshold_pred} | "
                    f"Precip_24h = {dados.get('precip_24h', 0):.1f}mm\n"
                )
            logger.debug(f"Divergência registrada: ML={ml_pred} vs THRESHOLD={threshold_pred}")
        except Exception as e:
            logger.warning(f"Erro ao registrar divergência: {e}")
    
    def get_alert_color(self, nivel):
        """Retorna cor do alerta"""
        return self.colors.get(nivel, '#808080')
    
    def get_alert_description(self, nivel):
        """Retorna descrição do alerta"""
        descriptions = {
            'MUITO_BAIXO': 'Situação normal. Sem riscos identificados.',
            'BAIXO': 'Atenção. Monitoramento recomendado.',
            'MODERADO': 'Cuidado. Possível risco de alagamentos pontuais.',
            'ALTO': 'Alerta. Risco de alagamentos e deslizamentos.',
            'MUITO_ALTO': 'Perigo. Alto risco de eventos extremos!'
        }
        return descriptions.get(nivel, 'Nível desconhecido')
    
    def force_reload_model(self):
        """Força recarregamento do modelo"""
        logger.info("🔄 Forçando recarregamento do modelo...")
        self.model = None
        self.scaler = None
        self.feature_names = None
        return self._load_model()
    
    def get_model_info(self):
        """Retorna informações sobre o modelo carregado"""
        if not self.model:
            return {
                'status': 'Não carregado',
                'features': None,
                'tipo': None
            }
        
        return {
            'status': 'Carregado',
            'features': self.feature_names,
            'tipo': type(self.model).__name__,
            'tem_scaler': self.scaler is not None
        }
    
    def clear_duplicate_alerts(self):
        """Remove alertas duplicados (utilitário de manutenção)"""
        try:
            from core.database.connection import db_manager
            
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Remove alertas duplicados (mesmo nível em menos de 1 hora)
                cursor.execute("""
                    DELETE FROM alertas_log a1
                    USING alertas_log a2
                    WHERE a1.id > a2.id
                    AND a1.nivel_alerta = a2.nivel_alerta
                    AND a1.data_ocorrencia - a2.data_ocorrencia < INTERVAL '1 hour'
                """)
                
                removed = cursor.rowcount
                conn.commit()
                
                logger.info(f"🧹 Removidos {removed} alertas duplicados")
                return removed
                
        except Exception as e:
            logger.error(f"Erro ao limpar alertas duplicados: {e}")
            return 0