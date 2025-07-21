"""
Rotas da aplicação Flask - Versão Corrigida
"""
import logging
import pandas as pd  # ADICIONADO: Import do pandas
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from core.database.models import WeatherData, AlertData
from core.alerts.alert_manager import AlertManager
from core.ml_models.data_processor import DataProcessor
from config.settings import APP_CONFIG

logger = logging.getLogger(__name__)

def create_app():
    """Factory function para criar aplicação Flask"""
    app = Flask(__name__)
    app.config.update(APP_CONFIG)
    
    # Configurar CORS
    CORS(app)
    
    # Inicializar componentes
    alert_manager = AlertManager()
    data_processor = DataProcessor()
    
    @app.route('/')
    def dashboard():
        """Página principal do dashboard"""
        return render_template('dashboard.html')
    
    @app.route('/api/clima')
    def get_weather_data():
        """Endpoint para dados meteorológicos atuais"""
        try:
            # Busca dados das últimas 24h
            dados = WeatherData.fetch_last_24h()
            
            if dados.empty:
                logger.warning("Nenhum dado meteorológico encontrado")
                return jsonify({"error": "Sem dados disponíveis"}), 404
            
            # Processa dados para obter o mais recente
            agora = datetime.now()
            dados["data_hora_captura"] = dados["data_hora_captura"].dt.tz_localize(None)
            dados["data_hora_captura"] = dados["data_hora_captura"] - timedelta(hours=3)
            
            # Filtra dados até o horário atual
            dados_passado = dados[dados["data_hora_captura"] <= agora]
            
            if dados_passado.empty:
                logger.warning("Sem dados anteriores ao horário atual")
                return jsonify({"error": "Sem dados anteriores ao horário atual"}), 404
            
            # Seleciona o mais próximo do horário atual
            dados_passado["dif"] = abs(dados_passado["data_hora_captura"] - agora)
            mais_proximo = dados_passado.sort_values("dif").iloc[0]
            
            # Gera alerta atual
            alerta_info = alert_manager.check_alerts()
            nivel_alerta = alerta_info['nivel'] if alerta_info else 'MUITO_BAIXO'
            
            resposta = {
                "city": "Nova Friburgo",
                "average_temperature": float(mais_proximo["temperatura"]) if mais_proximo["temperatura"] else 0,
                "average_thermal_sensation": float(mais_proximo["sensacao_termica"]) if mais_proximo["sensacao_termica"] else 0,
                "average_humidity": float(mais_proximo["umidade"]) if mais_proximo["umidade"] else 0,
                "rain_probability": float(mais_proximo["precipitacao"]) if mais_proximo["precipitacao"] else 0,
                "captured_at": str(mais_proximo["data_hora_captura"]),
                "cemaden_alerts": [[nivel_alerta]],
                
                # Dados adicionais
                "temp_minima": float(mais_proximo["temp_minima"]) if mais_proximo["temp_minima"] else 0,
                "temp_maxima": float(mais_proximo["temp_maxima"]) if mais_proximo["temp_maxima"] else 0,
                "umidade_minima": float(mais_proximo["umidade_minima"]) if mais_proximo["umidade_minima"] else 0,
                "vento_max": float(mais_proximo["vento_max"]) if mais_proximo["vento_max"] else 0,
                "uv_max": float(mais_proximo["uv_max"]) if mais_proximo["uv_max"] else 0,
                
                # Metadados
                "data_quality": "good",
                "last_model_update": datetime.now().isoformat()
            }
            
            return jsonify(resposta)
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados climáticos: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/alerta')
    def get_alert_data():
        """Endpoint para dados de alerta atual"""
        try:
            alerta_info = alert_manager.check_alerts()
            
            if not alerta_info:
                return jsonify({
                    "status": "Sem dados suficientes",
                    "nivel": "MUITO_BAIXO",
                    "descricao": "Dados insuficientes para análise"
                })
            
            return jsonify({
                "status": "Alerta ativo" if alerta_info['nivel'] != 'MUITO_BAIXO' else "Normal",
                "nivel": alerta_info['nivel'],
                "descricao": alert_manager.get_alert_description(alerta_info['nivel']),
                "cor": alert_manager.get_alert_color(alerta_info['nivel']),
                "timestamp": alerta_info['timestamp'].isoformat(),
                "dados_meteorologicos": {
                    "precipitacao_1h": alerta_info['dados'].get('precip_1h', 0),
                    "precipitacao_4h": alerta_info['dados'].get('precip_4h', 0),
                    "precipitacao_24h": alerta_info['dados'].get('precip_24h', 0),
                    "umidade": alerta_info['dados'].get('umidade', 0),
                    "temperatura": alerta_info['dados'].get('temperatura', 0)
                },
                "predicoes": {
                    "ml_prediction": alerta_info.get('ml_prediction'),
                    "threshold_prediction": alerta_info.get('threshold_prediction')
                }
            })
            
        except Exception as e:
            logger.error(f"Erro ao gerar alerta: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/historico')
    def get_historical_data():
        """Endpoint para dados históricos"""
        try:
            # Parâmetros da query
            period = request.args.get('period', '24h')
            
            # Mapeia período para dias
            period_map = {
                '24h': 1,
                '7d': 7,
                '30d': 30
            }
            
            days = period_map.get(period, 1)
            
            # Busca dados históricos
            dados = WeatherData.fetch_historical(days)
            
            if dados.empty:
                logger.warning(f"Nenhum dado histórico encontrado para {period}")
                return jsonify({
                    "timestamps": [],
                    "temperature": [],
                    "humidity": [],
                    "precipitation": []
                })
            
            # Processa dados
            dados = data_processor.calculate_accumulated(dados)
            
            # Prepara resposta
            timestamps = dados['data_hora_captura'].dt.strftime('%d/%m %H:%M').tolist()
            temperature = dados['temperatura'].fillna(0).tolist()
            humidity = dados['umidade'].fillna(0).tolist()
            precipitation = dados['precipitacao'].fillna(0).tolist()
            
            logger.info(f"Dados históricos retornados: {len(timestamps)} pontos para {period}")
            
            return jsonify({
                "timestamps": timestamps,
                "temperature": temperature,
                "humidity": humidity,
                "precipitation": precipitation,
                "period": period,
                "total_points": len(dados)
            })
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados históricos: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/alertas/recentes')
    def get_recent_alerts():
        """Endpoint para alertas recentes - CORRIGIDO"""
        try:
            limit = request.args.get('limit', 5, type=int)  # Reduzido para 10
            
            logger.info(f"Buscando {limit} alertas recentes...")
            
            # Busca alertas da tabela alertas_log
            alertas = AlertData.fetch_recent_alerts(limit)
            
            if alertas.empty:
                logger.warning("Nenhum alerta encontrado na tabela alertas_log")
                return jsonify([])
            
            logger.info(f"Encontrados {len(alertas)} alertas na tabela")
            
            # Converte para formato JSON com melhor tratamento de erros
            alertas_json = []
            for index, alerta in alertas.iterrows():
                try:
                    # Função para verificar e converter valores
                    def safe_get(data, key, default_value, data_type=str):
                        try:
                            value = data.get(key, default_value)
                            if pd.isna(value) or value is None:
                                return default_value
                            
                            if data_type == float:
                                return float(value)
                            elif data_type == int:
                                return int(value)
                            else:
                                return str(value)
                        except (ValueError, TypeError, KeyError):
                            return default_value
                    
                    # Processa dados com validação robusta
                    alerta_data = {
                        "id": safe_get(alerta, 'id', index, int),
                        "nivel_alerta": safe_get(alerta, 'nivel_alerta', 'MUITO_BAIXO'),
                        "data_ocorrencia": safe_get(alerta, 'data_ocorrencia', datetime.now().isoformat()),
                        "precipitacao_1h": safe_get(alerta, 'precipitacao_1h', 0.0, float),
                        "precipitacao_4h": safe_get(alerta, 'precipitacao_4h', 0.0, float), 
                        "precipitacao_24h": safe_get(alerta, 'precipitacao_24h', 0.0, float),
                        "umidade": safe_get(alerta, 'umidade', 0.0, float),
                        "temperatura": safe_get(alerta, 'temperatura', 0.0, float),
                        "metodo_predicao": safe_get(alerta, 'metodo_predicao', 'THRESHOLD'),
                        "confianca": safe_get(alerta, 'confianca', 1.0, float)
                    }
                    
                    # Formata data se necessário
                    if hasattr(alerta['data_ocorrencia'], 'isoformat'):
                        alerta_data["data_ocorrencia"] = alerta['data_ocorrencia'].isoformat()
                    
                    alertas_json.append(alerta_data)
                    
                except Exception as e:
                    logger.warning(f"Erro ao processar alerta {index}: {e}")
                    # Cria entrada padrão em caso de erro total
                    try:
                        fallback_alerta = {
                            "id": index,
                            "nivel_alerta": "MUITO_BAIXO",
                            "data_ocorrencia": datetime.now().isoformat(),
                            "precipitacao_1h": 0.0,
                            "precipitacao_4h": 0.0,
                            "precipitacao_24h": 0.0,
                            "umidade": 0.0,
                            "temperatura": 0.0,
                            "metodo_predicao": "THRESHOLD",
                            "confianca": 1.0
                        }
                        alertas_json.append(fallback_alerta)
                    except:
                        # Se até o fallback falhar, pula este registro
                        continue
            
            # Remove duplicatas e filtra alertas válidos
            alertas_filtrados = []
            seen_ids = set()
            
            for alerta in alertas_json:
                # Remove duplicatas por ID
                if alerta['id'] not in seen_ids:
                    seen_ids.add(alerta['id'])
                    alertas_filtrados.append(alerta)
                
                # Limita a 10 alertas
                if len(alertas_filtrados) >= 10:
                    break
            
            logger.info(f"Retornando {len(alertas_filtrados)} alertas válidos")
            return jsonify(alertas_filtrados)
            
        except Exception as e:
            logger.error(f"Erro ao buscar alertas recentes: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/alertas/teste')
    def test_alerts_table():
        """Endpoint para testar a tabela de alertas"""
        try:
            from core.database.connection import db_manager
            
            # Testa conexão
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verifica se tabela existe
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'alertas_log'
                    );
                """)
                table_exists = cursor.fetchone()[0]
                
                if not table_exists:
                    return jsonify({
                        "error": "Tabela alertas_log não existe",
                        "solucao": "Execute: python setup_database.py"
                    }), 404
                
                # Conta registros
                cursor.execute("SELECT COUNT(*) FROM alertas_log")
                total_alertas = cursor.fetchone()[0]
                
                # Busca últimos 5 registros
                cursor.execute("""
                    SELECT id, nivel_alerta, data_ocorrencia, precipitacao_24h 
                    FROM alertas_log 
                    ORDER BY data_ocorrencia DESC 
                    LIMIT 5
                """)
                ultimos_alertas = cursor.fetchall()
                
                return jsonify({
                    "tabela_existe": True,
                    "total_alertas": total_alertas,
                    "ultimos_alertas": [
                        {
                            "id": alerta[0],
                            "nivel": alerta[1], 
                            "data": alerta[2].isoformat() if alerta[2] else None,
                            "precip_24h": float(alerta[3]) if alerta[3] else 0
                        } for alerta in ultimos_alertas
                    ]
                })
                
        except Exception as e:
            logger.error(f"Erro no teste da tabela alertas: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/estatisticas')
    def get_statistics():
        """Endpoint para estatísticas gerais"""
        try:
            # Estatísticas de precipitação
            stats_precip = WeatherData.get_precipitation_stats()
            
            # Dados das últimas 24h para contagem
            dados_24h = WeatherData.fetch_last_24h()
            
            # Alertas recentes
            alertas_recentes = AlertData.fetch_recent_alerts(100)  # Últimos 100 para análise
            
            resposta = {
                "precipitacao": {
                    "media_30_dias": float(stats_precip.iloc[0]['media_precipitacao']) if not stats_precip.empty else 0,
                    "maxima_30_dias": float(stats_precip.iloc[0]['max_precipitacao']) if not stats_precip.empty else 0,
                    "dias_com_chuva": int(stats_precip.iloc[0]['dias_com_chuva']) if not stats_precip.empty else 0
                },
                "dados_coletados": {
                    "total_registros": int(stats_precip.iloc[0]['total_registros']) if not stats_precip.empty else 0,
                    "ultimas_24h": len(dados_24h)
                },
                "alertas": {
                    "total_recentes": len(alertas_recentes),
                    "distribuicao": alertas_recentes['nivel_alerta'].value_counts().to_dict() if not alertas_recentes.empty else {}
                },
                "sistema": {
                    "ultima_atualizacao": datetime.now().isoformat(),
                    "status": "operacional"
                }
            }
            
            return jsonify(resposta)
            
        except Exception as e:
            logger.error(f"Erro ao gerar estatísticas: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/health')
    def health_check():
        """Endpoint para verificação de saúde da aplicação"""
        try:
            # Testa conexão com banco
            from core.database.connection import db_manager
            db_healthy = db_manager.test_connection()
            
            # Verifica dados recentes
            dados_recentes = WeatherData.fetch_last_24h()
            data_healthy = not dados_recentes.empty
            
            # Verifica alertas
            alertas_recentes = AlertData.fetch_recent_alerts(1)
            alerts_healthy = not alertas_recentes.empty
            
            # Status geral
            status = "healthy" if (db_healthy and data_healthy) else "unhealthy"
            
            return jsonify({
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "checks": {
                    "database": "ok" if db_healthy else "error",
                    "data_availability": "ok" if data_healthy else "error",
                    "alerts_table": "ok" if alerts_healthy else "warning",
                    "data_points_24h": len(dados_recentes) if data_healthy else 0,
                    "recent_alerts": len(alertas_recentes) if alerts_healthy else 0
                }
            }), 200 if status == "healthy" else 503
            
        except Exception as e:
            logger.error(f"Erro no health check: {e}")
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 503
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint não encontrado"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Erro interno: {error}")
        return jsonify({"error": "Erro interno do servidor"}), 500
    
    
    @app.route('/api/precipitacao')
    def get_precipitation_data():
        """Endpoint específico para dados de precipitação acumulada"""
        try:
            # Busca dados de alerta que contém precipitação acumulada
            alerta_info = alert_manager.check_alerts()
            
            if not alerta_info or 'dados' not in alerta_info:
                return jsonify({
                    "precip_1h": 0.0,
                    "precip_4h": 0.0,
                    "precip_24h": 0.0,
                    "timestamp": datetime.now().isoformat()
                })
            
            dados = alerta_info['dados']
            
            return jsonify({
                "precip_1h": float(dados.get('precip_1h', 0)),
                "precip_4h": float(dados.get('precip_4h', 0)),
                "precip_24h": float(dados.get('precip_24h', 0)),
                "precipitacao_atual": float(dados.get('precipitacao', 0)),
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados de precipitação: {e}")
            return jsonify({"error": str(e)}), 500
            
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(
        host=APP_CONFIG['HOST'],
        port=APP_CONFIG['PORT'],
        debug=APP_CONFIG['DEBUG']
    )