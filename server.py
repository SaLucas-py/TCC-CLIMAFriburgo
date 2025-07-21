#!/usr/bin/env python3
"""
Servidor web para o Sistema de Monitoramento Hidrológico
"""
import logging
import sys
from app.routes import create_app
from config.settings import APP_CONFIG, LOGGING_CONFIG

def setup_logging():
    """Configura logging para o servidor"""
    logging.basicConfig(
        level=getattr(logging, LOGGING_CONFIG['level']),
        format=LOGGING_CONFIG['format'],
        handlers=[
            logging.FileHandler('logs/server.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Função principal do servidor"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Banner de inicialização
        print("=" * 60)
        print("🌐 SERVIDOR WEB - SISTEMA HIDROLÓGICO NOVA FRIBURGO")
        print("=" * 60)
        print(f"🔗 URL: http://{APP_CONFIG['HOST']}:{APP_CONFIG['PORT']}")
        print(f"🐛 Debug: {'Ativado' if APP_CONFIG['DEBUG'] else 'Desativado'}")
        print(f"📊 Dashboard: http://{APP_CONFIG['HOST']}:{APP_CONFIG['PORT']}/")
        print("=" * 60)
        
        # Cria aplicação Flask
        app = create_app()
        
        # Testa conexão com banco
        from core.database.connection import db_manager
        if not db_manager.test_connection():
            logger.error("❌ Falha na conexão com banco de dados")
            print("❌ Erro: Não foi possível conectar ao banco de dados")
            print("🔧 Verifique as configurações em config/settings.py")
            return 1
        
        logger.info("✅ Conexão com banco de dados estabelecida")
        
        # Inicia servidor
        logger.info(f"Iniciando servidor em {APP_CONFIG['HOST']}:{APP_CONFIG['PORT']}")
        
        app.run(
            host=APP_CONFIG['HOST'],
            port=APP_CONFIG['PORT'],
            debug=APP_CONFIG['DEBUG'],
            use_reloader=False  # Evita reinicializações desnecessárias
        )
        
    except KeyboardInterrupt:
        print("\n🔴 Servidor interrompido pelo usuário")
        logger.info("Servidor finalizado pelo usuário")
        return 0
    except Exception as e:
        print(f"\n❌ Erro ao iniciar servidor: {e}")
        logger.error(f"Erro fatal no servidor: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())