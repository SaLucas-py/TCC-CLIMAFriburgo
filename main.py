#!/usr/bin/env python3
"""
Sistema de Monitoramento Hidrológico - Nova Friburgo
Ponto de entrada principal da aplicação
"""
import sys
import time
import logging
import argparse
import os
from datetime import datetime

# Configurar encoding para Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

def setup_logging():
    """Configura sistema de logging sem emojis"""
    
    # Cria diretório de logs se não existir
    os.makedirs('logs', exist_ok=True)
    
    # Configuração de logging sem emojis
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Handler para arquivo
    file_handler = logging.FileHandler('logs/app.log', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Configurar logger raiz
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )

def collect_weather_data():
    """Coleta dados meteorológicos das fontes"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Iniciando coleta de dados meteorológicos...")
        
        from core.data_collection.inmet_collector import INMETCollector, CPTECCollector
        from core.database.models import WeatherData
        
        # Coleta dados INMET
        with INMETCollector() as inmet_collector:
            dados_inmet = inmet_collector.collect_data()
        
        # Coleta dados CPTEC
        with CPTECCollector() as cptec_collector:
            dados_cptec = cptec_collector.collect_data()
        
        if not dados_inmet or not dados_cptec:
            logger.warning("Falha na coleta de dados de uma ou mais fontes")
            return 0
        
        # Combina dados e salva no banco
        novos_registros = 0
        for dados_linha in dados_inmet:
            try:
                # Prepara dados unificados
                dados_unificados = (
                    dados_linha[0],  # data
                    dados_linha[1],  # hora_utc
                    float(dados_linha[2]) if dados_linha[2] else 0,  # precipitacao
                    float(dados_linha[3]) if dados_linha[3] else 0,  # umidade
                    float(dados_linha[4]) if dados_linha[4] else 0,  # temperatura
                    float(dados_linha[5]) if dados_linha[5] else 0,  # sensacao_termica
                    float(dados_cptec.get("temp_minima", 0)) if dados_cptec.get("temp_minima") else 0,
                    float(dados_cptec.get("temp_maxima", 0)) if dados_cptec.get("temp_maxima") else 0,
                    float(dados_cptec.get("umidade_minima", 0)) if dados_cptec.get("umidade_minima") else 0,
                    float(dados_cptec.get("vento_max", 0)) if dados_cptec.get("vento_max") else 0,
                    float(dados_cptec.get("uv_max", 0)) if dados_cptec.get("uv_max") else 0
                )
                
                # Insere no banco
                inserted = WeatherData.insert_weather_data([dados_unificados])
                novos_registros += inserted
                
            except Exception as e:
                logger.error(f"Erro ao processar linha de dados: {e}")
                continue
        
        logger.info(f"Coleta concluída: {novos_registros} novos registros inseridos")
        return novos_registros
        
    except Exception as e:
        logger.error(f"Erro durante coleta de dados: {e}")
        return 0

def create_sample_data():
    """Cria dados de exemplo se não houver dados suficientes"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Criando dados de exemplo para treinamento...")
        
        from core.database.models import WeatherData
        import numpy as np
        from datetime import timedelta
        
        # Cria dados sintéticos
        sample_data = []
        base_date = datetime.now() - timedelta(days=30)
        
        np.random.seed(42)  # Para reprodutibilidade
        
        for i in range(200):  # 200 registros de exemplo
            current_date = base_date + timedelta(hours=i)
            
            # Dados realísticos para Nova Friburgo
            precipitacao = abs(np.random.exponential(1.5))
            umidade = max(0, min(100, np.random.normal(75, 15)))
            temperatura = np.random.normal(22, 6)
            sensacao = temperatura + np.random.normal(0, 2)
            
            data_row = (
                current_date.strftime('%Y-%m-%d'),  # data
                current_date.strftime('%H:%M'),     # hora_utc
                round(precipitacao, 2),             # precipitacao
                round(umidade, 2),                  # umidade
                round(temperatura, 2),              # temperatura
                round(sensacao, 2),                 # sensacao_termica
                round(temperatura - np.random.uniform(2, 5), 2),  # temp_minima
                round(temperatura + np.random.uniform(2, 5), 2),  # temp_maxima
                round(max(30, umidade - np.random.uniform(10, 20)), 2),  # umidade_minima
                round(abs(np.random.normal(8, 3)), 2),  # vento_max
                round(abs(np.random.normal(6, 2)), 2)   # uv_max
            )
            sample_data.append(data_row)
        
        # Insere no banco
        inserted = WeatherData.insert_weather_data(sample_data)
        logger.info(f"Dados de exemplo criados: {inserted} registros")
        return inserted
        
    except Exception as e:
        logger.error(f"Erro ao criar dados de exemplo: {e}")
        return 0

def train_model():
    """Treina novo modelo de classificação"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Iniciando treinamento do modelo...")
        
        from core.ml_models.alert_classifier import AlertClassifier
        from core.database.models import WeatherData
        
        # Verifica se há dados suficientes
        dados = WeatherData.fetch_historical(days=180)
        
        if dados.empty or len(dados) < 50:
            logger.warning("Dados insuficientes. Criando dados de exemplo...")
            create_sample_data()
        
        # Cria e treina classificador
        classifier = AlertClassifier()
        success = classifier.train_model()
        
        if success:
            logger.info("Modelo treinado com sucesso!")
            return True
        else:
            logger.error("Falha no treinamento do modelo")
            return False
            
    except Exception as e:
        logger.error(f"Erro durante treinamento: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def evaluate_model():
    """Avalia modelo existente"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Avaliando modelo...")
        
        from core.ml_models.alert_classifier import AlertClassifier
        
        classifier = AlertClassifier()
        if not classifier.load_model():
            logger.error("Modelo não encontrado. Execute --train primeiro")
            return False
        
        evaluation = classifier.evaluate_model()
        
        if evaluation:
            logger.info(f"Acurácia do modelo: {evaluation['accuracy']:.3f}")
            logger.info(f"Total de predições avaliadas: {evaluation['total_predictions']}")
            return True
        else:
            logger.warning("Não foi possível avaliar o modelo")
            return False
            
    except Exception as e:
        logger.error(f"Erro durante avaliação: {e}")
        return False

def monitor_alerts():
    """Executa monitoramento contínuo de alertas"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Iniciando monitoramento de alertas...")
        
        from core.alerts.alert_manager import AlertManager
        
        alert_manager = AlertManager()
        
        while True:
            try:
                # Verifica alertas
                alerta_info = alert_manager.check_alerts()
                
                if alerta_info:
                    nivel = alerta_info['nivel']
                    logger.info(f"Alerta atual: {nivel}")
                    
                    # Log adicional para alertas altos
                    if nivel in ['ALTO', 'MUITO_ALTO']:
                        logger.warning(f"ALERTA {nivel} ATIVO!")
                        
                else:
                    logger.warning("Sem dados suficientes para gerar alerta")
                
                # Aguarda próxima verificação (1 hora)
                logger.debug("Aguardando próxima verificação em 1 hora...")
                time.sleep(3600)
                
            except KeyboardInterrupt:
                logger.info("Monitoramento interrompido pelo usuário")
                break
            except Exception as e:
                logger.error(f"Erro durante monitoramento: {e}")
                logger.info("Tentando novamente em 5 minutos...")
                time.sleep(300)
                
    except Exception as e:
        logger.error(f"Erro fatal no monitoramento: {e}")
        return False
    
    return True

def collect_continuous():
    """Executa coleta contínua de dados"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Iniciando coleta contínua de dados...")
        
        while True:
            try:
                logger.info(f"Iniciando coleta em {datetime.now()}")
                
                novos_registros = collect_weather_data()
                
                if novos_registros > 0:
                    logger.info(f"{novos_registros} novos registros coletados")
                else:
                    logger.warning("Nenhum dado novo coletado")
                
                # Aguarda 45 minutos antes da próxima coleta
                logger.debug("Aguardando 45 minutos para próxima coleta...")
                time.sleep(2700)
                
            except KeyboardInterrupt:
                logger.info("Coleta interrompida pelo usuário")
                break
            except Exception as e:
                logger.error(f"Erro durante coleta: {e}")
                logger.info("Tentando novamente em 5 minutos...")
                time.sleep(300)
                
    except Exception as e:
        logger.error(f"Erro fatal na coleta: {e}")
        return False
    
    return True

def main():
    """Função principal"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Parser de argumentos
    parser = argparse.ArgumentParser(
        description='Sistema de Monitoramento Hidrológico - Nova Friburgo'
    )
    parser.add_argument('--train', action='store_true', 
                       help='Treina novo modelo de classificação')
    parser.add_argument('--evaluate', action='store_true',
                       help='Avalia modelo existente')
    parser.add_argument('--collect', action='store_true',
                       help='Executa coleta única de dados')
    parser.add_argument('--collect-continuous', action='store_true',
                       help='Executa coleta contínua de dados')
    parser.add_argument('--monitor', action='store_true',
                       help='Executa monitoramento contínuo (padrão)')
    
    args = parser.parse_args()
    
    # Banner de inicialização
    print("="*60)
    print("SISTEMA DE MONITORAMENTO HIDROLÓGICO - NOVA FRIBURGO")
    print("="*60)
    print("Níveis de alerta: MUITO_BAIXO | BAIXO | MODERADO | ALTO | MUITO_ALTO")
    print("Fontes: INMET, CPTEC/INPE")
    print("Machine Learning: Random Forest Classifier")
    print("="*60)
    
    try:
        # Executa comando específico
        if args.train:
            logger.info("Modo: Treinamento do modelo")
            success = train_model()
            return 0 if success else 1
            
        elif args.evaluate:
            logger.info("Modo: Avaliação do modelo")
            success = evaluate_model()
            return 0 if success else 1
            
        elif args.collect:
            logger.info("Modo: Coleta única")
            novos_registros = collect_weather_data()
            print(f"Coleta concluída: {novos_registros} registros")
            return 0
            
        elif args.collect_continuous:
            logger.info("Modo: Coleta contínua")
            success = collect_continuous()
            return 0 if success else 1
            
        else:
            # Modo padrão: monitoramento
            logger.info("Modo: Monitoramento contínuo (padrão)")
            print("Iniciando monitoramento de alertas...")
            print("Use Ctrl+C para interromper")
            print("Para outros modos, use --help")
            print("-" * 60)
            
            success = monitor_alerts()
            return 0 if success else 1
            
    except KeyboardInterrupt:
        print("\nOperação interrompida pelo usuário")
        logger.info("Aplicação finalizada pelo usuário")
        return 0
    except Exception as e:
        print(f"\nErro fatal: {e}")
        logger.error(f"Erro fatal na aplicação: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())