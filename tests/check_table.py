"""
Script para configurar e verificar o banco de dados
Cria todas as tabelas necessárias para o sistema
"""
import psycopg2
import logging
from config.settings import DB_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_connection():
    """Testa conexão com o banco de dados"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("✅ Conexão com banco estabelecida")
        
        # Testa uma query simples
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        logger.info(f"📊 PostgreSQL: {version[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na conexão: {e}")
        return False

def check_tables():
    """Verifica quais tabelas existem"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Lista todas as tabelas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        existing_tables = [table[0] for table in tables]
        
        logger.info("📋 Tabelas existentes:")
        for table in existing_tables:
            logger.info(f"   ✅ {table}")
        
        cursor.close()
        conn.close()
        
        return existing_tables
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar tabelas: {e}")
        return []

def create_tables():
    """Cria todas as tabelas necessárias"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        logger.info("🔧 Criando tabelas...")
        
        # 1. Tabela de dados climáticos
        logger.info("   ↳ Criando tabela: dados_climaticos")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dados_climaticos (
                id SERIAL PRIMARY KEY,
                data DATE NOT NULL,
                hora_utc TIME NOT NULL,
                precipitacao NUMERIC(5,2) DEFAULT 0,
                umidade NUMERIC(5,2) DEFAULT 0,
                temperatura NUMERIC(5,2) DEFAULT 0,
                sensacao_termica NUMERIC(5,2) DEFAULT 0,
                temp_minima NUMERIC(5,2) DEFAULT 0,
                temp_maxima NUMERIC(5,2) DEFAULT 0,
                umidade_minima NUMERIC(5,2) DEFAULT 0,
                vento_max NUMERIC(5,2) DEFAULT 0,
                uv_max NUMERIC(5,2) DEFAULT 0,
                data_hora_captura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(data, hora_utc)
            );
        """)
        
        # 2. Tabela de log de alertas
        logger.info("   ↳ Criando tabela: alertas_log")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alertas_log (
                id SERIAL PRIMARY KEY,
                nivel_alerta VARCHAR(20) NOT NULL,
                data_ocorrencia TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                precipitacao_1h NUMERIC(5,2) DEFAULT 0,
                precipitacao_4h NUMERIC(5,2) DEFAULT 0,
                precipitacao_24h NUMERIC(5,2) DEFAULT 0,
                umidade NUMERIC(5,2) DEFAULT 0,
                temperatura NUMERIC(5,2) DEFAULT 0,
                dados_extras JSONB
            );
        """)
        
        # 3. Tabela de configurações (opcional)
        logger.info("   ↳ Criando tabela: configuracoes")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracoes (
                id SERIAL PRIMARY KEY,
                chave VARCHAR(100) UNIQUE NOT NULL,
                valor TEXT,
                descricao TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 4. Tabela de histórico de coletas (opcional)
        logger.info("   ↳ Criando tabela: historico_coletas")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_coletas (
                id SERIAL PRIMARY KEY,
                fonte VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL,
                registros_coletados INTEGER DEFAULT 0,
                data_coleta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                detalhes JSONB,
                tempo_execucao_ms INTEGER
            );
        """)
        
        # Cria índices para performance
        logger.info("   ↳ Criando índices...")
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dados_climaticos_data_hora 
            ON dados_climaticos(data_hora_captura DESC);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alertas_log_data 
            ON alertas_log(data_ocorrencia DESC);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alertas_log_nivel 
            ON alertas_log(nivel_alerta);
        """)
        
        # Confirma alterações
        conn.commit()
        
        logger.info("✅ Todas as tabelas foram criadas com sucesso!")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas: {e}")
        return False

def insert_sample_data():
    """Insere dados de exemplo para teste"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        logger.info("📊 Inserindo dados de exemplo...")
        
        # Dados climáticos de exemplo
        from datetime import datetime, timedelta
        import random
        
        base_time = datetime.now() - timedelta(hours=24)
        
        for i in range(24):  # 24 horas de dados
            current_time = base_time + timedelta(hours=i)
            
            cursor.execute("""
                INSERT INTO dados_climaticos (
                    data, hora_utc, precipitacao, umidade, temperatura, 
                    sensacao_termica, temp_minima, temp_maxima, 
                    umidade_minima, vento_max, uv_max
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (data, hora_utc) DO NOTHING;
            """, (
                current_time.date(),
                current_time.time(),
                round(random.uniform(0, 5), 1),      # precipitacao
                round(random.uniform(60, 90), 1),    # umidade
                round(random.uniform(18, 28), 1),    # temperatura
                round(random.uniform(19, 30), 1),    # sensacao_termica
                round(random.uniform(15, 20), 1),    # temp_minima
                round(random.uniform(25, 32), 1),    # temp_maxima
                round(random.uniform(50, 70), 1),    # umidade_minima
                round(random.uniform(2, 8), 1),      # vento_max
                round(random.uniform(3, 9), 1)       # uv_max
            ))
        
        # Alertas de exemplo
        alertas_exemplo = [
            ('MUITO_BAIXO', 0.5, 1.2, 3.5, 75, 22),
            ('BAIXO', 1.8, 4.2, 8.1, 82, 24),
            ('MODERADO', 3.2, 8.5, 15.2, 88, 26)
        ]
        
        for nivel, p1h, p4h, p24h, umid, temp in alertas_exemplo:
            cursor.execute("""
                INSERT INTO alertas_log (
                    nivel_alerta, precipitacao_1h, precipitacao_4h, 
                    precipitacao_24h, umidade, temperatura
                ) VALUES (%s, %s, %s, %s, %s, %s);
            """, (nivel, p1h, p4h, p24h, umid, temp))
        
        # Configurações de exemplo
        configuracoes_exemplo = [
            ('ultima_coleta', str(datetime.now()), 'Timestamp da última coleta de dados'),
            ('modelo_versao', '1.0', 'Versão do modelo ML atual'),
            ('intervalo_coleta', '180', 'Intervalo de coleta em segundos')
        ]
        
        for chave, valor, desc in configuracoes_exemplo:
            cursor.execute("""
                INSERT INTO configuracoes (chave, valor, descricao) 
                VALUES (%s, %s, %s)
                ON CONFLICT (chave) DO UPDATE SET 
                    valor = EXCLUDED.valor,
                    data_atualizacao = CURRENT_TIMESTAMP;
            """, (chave, valor, desc))
        
        conn.commit()
        
        # Verifica quantos registros foram inseridos
        cursor.execute("SELECT COUNT(*) FROM dados_climaticos;")
        count_dados = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM alertas_log;")
        count_alertas = cursor.fetchone()[0]
        
        logger.info(f"✅ Dados inseridos:")
        logger.info(f"   dados_climaticos: {count_dados} registros")
        logger.info(f"   alertas_log: {count_alertas} registros")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao inserir dados de exemplo: {e}")
        return False

def verify_data():
    """Verifica se os dados foram inseridos corretamente"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        logger.info("🔍 Verificando dados...")
        
        # Verifica dados climáticos
        cursor.execute("""
            SELECT COUNT(*), MIN(data_hora_captura), MAX(data_hora_captura)
            FROM dados_climaticos;
        """)
        dados_info = cursor.fetchone()
        
        logger.info(f"📊 Dados climáticos:")
        logger.info(f"   Total: {dados_info[0]} registros")
        logger.info(f"   Período: {dados_info[1]} até {dados_info[2]}")
        
        # Verifica alertas
        cursor.execute("""
            SELECT nivel_alerta, COUNT(*) 
            FROM alertas_log 
            GROUP BY nivel_alerta 
            ORDER BY nivel_alerta;
        """)
        alertas_info = cursor.fetchall()
        
        logger.info(f"🚨 Alertas por nível:")
        for nivel, count in alertas_info:
            logger.info(f"   {nivel}: {count} registros")
        
        # Verifica último registro
        cursor.execute("""
            SELECT data, hora_utc, temperatura, umidade, precipitacao
            FROM dados_climaticos 
            ORDER BY data_hora_captura DESC 
            LIMIT 1;
        """)
        ultimo = cursor.fetchone()
        
        if ultimo:
            logger.info(f"🕐 Último registro:")
            logger.info(f"   Data/Hora: {ultimo[0]} {ultimo[1]}")
            logger.info(f"   Temperatura: {ultimo[2]}°C")
            logger.info(f"   Umidade: {ultimo[3]}%")
            logger.info(f"   Precipitação: {ultimo[4]}mm")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar dados: {e}")
        return False

def main():
    """Função principal de configuração do banco"""
    print("🗄️ CONFIGURAÇÃO DO BANCO DE DADOS")
    print("Sistema de Monitoramento Hidrológico - Nova Friburgo")
    print("=" * 60)
    
    # 1. Testa conexão
    print("\n1️⃣ Testando conexão...")
    if not test_connection():
        print("❌ Falha na conexão! Verifique:")
        print("   - PostgreSQL está rodando?")
        print("   - Credenciais em config/settings.py estão corretas?")
        print("   - Banco 'alerta_hidrologico' existe?")
        return
    
    # 2. Verifica tabelas existentes
    print("\n2️⃣ Verificando tabelas...")
    existing_tables = check_tables()
    
    required_tables = ['dados_climaticos', 'alertas_log']
    missing_tables = [table for table in required_tables if table not in existing_tables]
    
    if missing_tables:
        print(f"⚠️ Tabelas em falta: {missing_tables}")
    else:
        print("✅ Todas as tabelas necessárias existem")
    
    # 3. Cria tabelas se necessário
    if missing_tables or len(existing_tables) == 0:
        print("\n3️⃣ Criando tabelas...")
        if not create_tables():
            print("❌ Falha ao criar tabelas!")
            return
    else:
        print("\n3️⃣ Tabelas já existem, pulando criação...")
    
    # 4. Pergunta se quer inserir dados de exemplo
    print("\n4️⃣ Dados de exemplo...")
    resposta = input("   Deseja inserir dados de exemplo? (s/n): ")
    
    if resposta.lower() in ['s', 'sim', 'y', 'yes']:
        if insert_sample_data():
            print("✅ Dados de exemplo inseridos!")
        else:
            print("❌ Falha ao inserir dados de exemplo")
    
    # 5. Verifica dados finais
    print("\n5️⃣ Verificação final...")
    verify_data()
    
    print("\n" + "=" * 60)
    print("🎉 CONFIGURAÇÃO CONCLUÍDA!")
    print("💡 Agora você pode executar:")
    print("   python simple_training.py    # Treina modelo")
    print("   python main.py --collect     # Coleta dados")
    print("   python server.py             # Inicia servidor")

if __name__ == "__main__":
    main()