"""
Configurações centralizadas do sistema
"""
import os

# Configurações do Banco de Dados
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'monitoramento_climatico_nfriburgo'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD'),
    'port': os.getenv('DB_PORT', '5432')
}

# Configurações da Aplicação
APP_CONFIG = {
    'SECRET_KEY': os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'),
    'DEBUG': os.getenv('DEBUG', 'False').lower() == 'true',
    'PORT': int(os.getenv('PORT', 5000)),
    'HOST': os.getenv('HOST', '0.0.0.0')
}

# Configurações de Logging
LOGGING_CONFIG = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': os.getenv('LOG_FILE', 'logs/app.log')
}

# Configurações do Selenium
SELENIUM_CONFIG = {
    'chromedriver_path': os.getenv('CHROMEDRIVER_PATH', 'C:/chromedriver/chromedriver.exe'),  # Windows
    'headless': os.getenv('SELENIUM_HEADLESS', 'True').lower() == 'true',
    'timeout': int(os.getenv('SELENIUM_TIMEOUT', 20))
}

# URLs dos serviços
SERVICES_CONFIG = {
    'inmet_url': 'https://portal.inmet.gov.br/',
    'cptec_url': 'https://www.cptec.inpe.br/',
    'city': 'Nova Friburgo'
}

# Configurações do Modelo ML
ML_CONFIG = {
    'model_path': 'data/models/alert_model.pkl',
    'retrain_interval_hours': 24,
    'min_data_points': 100
}

# Configurações de Alertas
ALERT_CONFIG = {
    'thresholds': {
        'MUITO_ALTO': {'1h': 100, '4h': 130, '24h': 220},
        'ALTO': {'1h': 70, '4h': 90, '24h': 150},
        'MODERADO': {'1h': 50, '4h': 65, '24h': 100},
        'BAIXO': {'1h': 35, '4h': 50, '24h': 75},
        'MUITO_BAIXO': {'1h': 0, '4h': 0, '24h': 0}
    },
    'colors': {
        'MUITO_ALTO': '#8B0000',
        'ALTO': '#FF4444',
        'MODERADO': '#FFA500',
        'BAIXO': '#FFD700',
        'MUITO_BAIXO': '#32CD32'
    }
}

# Criar diretórios se não existirem
def create_directories():
    """Cria diretórios necessários"""
    dirs = ['logs', 'data', 'data/models']
    for dir_path in dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"📁 Diretório criado: {dir_path}")

# Executa na importação
create_directories()