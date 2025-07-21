# 🌊 Sistema de Monitoramento Hidrológico - Nova Friburgo

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://postgresql.org)
[![Machine Learning](https://img.shields.io/badge/ML-Random%20Forest-orange.svg)](https://scikit-learn.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Sistema inteligente de monitoramento e alertas hidrológicos para prevenção de desastres naturais na região de Nova Friburgo, RJ. Utiliza **Machine Learning** e dados meteorológicos em tempo real para classificar riscos de alagamentos e deslizamentos.

## 📸 Screenshots

| Dashboard Principal | Alertas em Tempo Real | Histórico de Dados |
|:---:|:---:|:---:|
| ![Dashboard](screenshots/dashboard.png) | ![Alertas](screenshots/alerts.png) | ![Histórico](screenshots/history.png) |

## 🎯 Funcionalidades

- **🤖 Machine Learning**: Classificação inteligente com Random Forest
- **📊 Dashboard Moderno**: Interface responsiva com gráficos interativos
- **⚠️ Sistema de Alertas**: 5 níveis de risco em tempo real
- **📡 Coleta Automática**: Dados do INMET e CPTEC/INPE via web scraping
- **📈 Análise Histórica**: Visualização de tendências e padrões
- **🔄 Tempo Real**: Atualizações automáticas a cada 2 minutos
- **📱 Responsivo**: Funciona em desktop, tablet e mobile

## 🏗️ Arquitetura do Sistema

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   INMET/CPTEC   │────│  Data Collectors │────│   PostgreSQL    │
│  (Web Scraping) │    │    (Selenium)    │    │    Database     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Dashboard     │◄───│  Flask API      │◄───│  ML Model       │
│  (React/HTML)   │    │   (Routes)      │    │ (Random Forest) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🗄️ Estrutura do Banco de Dados

### Tabela: `dados_climaticos`
Armazena dados meteorológicos coletados em tempo real.

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `id` | SERIAL | Identificador único | 1 |
| `data` | DATE | Data da coleta | 2025-01-18 |
| `hora_utc` | TIME | Hora UTC da coleta | 14:30:00 |
| `precipitacao` | NUMERIC(5,2) | Precipitação atual (mm) | 2.5 |
| `umidade` | NUMERIC(5,2) | Umidade relativa (%) | 78.5 |
| `temperatura` | NUMERIC(5,2) | Temperatura (°C) | 23.1 |
| `sensacao_termica` | NUMERIC(5,2) | Sensação térmica (°C) | 25.3 |
| `temp_minima` | NUMERIC(5,2) | Temperatura mínima (°C) | 18.2 |
| `temp_maxima` | NUMERIC(5,2) | Temperatura máxima (°C) | 28.7 |
| `umidade_minima` | NUMERIC(5,2) | Umidade mínima (%) | 65.0 |
| `vento_max` | NUMERIC(5,2) | Velocidade máxima do vento (m/s) | 4.2 |
| `uv_max` | NUMERIC(5,2) | Índice UV máximo | 7.0 |
| `data_hora_captura` | TIMESTAMP | Timestamp da inserção | 2025-01-18 14:30:15 |

**Constraints:**
- `UNIQUE(data, hora_utc)` - Evita duplicatas
- `CHECK (umidade >= 0 AND umidade <= 100)` - Valida umidade
- `CHECK (precipitacao >= 0)` - Valida precipitação

### Tabela: `alertas_log`
Registra histórico de alertas gerados pelo sistema.

| Campo | Tipo | Descrição | Valores Possíveis |
|-------|------|-----------|-------------------|
| `id` | SERIAL | Identificador único | 1, 2, 3... |
| `nivel_alerta` | VARCHAR(20) | Nível do alerta | MUITO_BAIXO, BAIXO, MODERADO, ALTO, MUITO_ALTO |
| `data_ocorrencia` | TIMESTAMP | Quando o alerta foi gerado | 2025-01-18 14:30:15 |
| `precipitacao_1h` | NUMERIC(5,2) | Acumulado 1 hora (mm) | 5.2 |
| `precipitacao_4h` | NUMERIC(5,2) | Acumulado 4 horas (mm) | 12.8 |
| `precipitacao_24h` | NUMERIC(5,2) | Acumulado 24 horas (mm) | 35.4 |
| `umidade` | NUMERIC(5,2) | Umidade no momento (%) | 85.2 |
| `temperatura` | NUMERIC(5,2) | Temperatura no momento (°C) | 21.8 |
| `metodo_predicao` | VARCHAR(20) | Método usado | THRESHOLD, ML, MANUAL |
| `confianca` | NUMERIC(3,2) | Confiança da predição (0-1) | 0.87 |
| `observacoes` | TEXT | Observações adicionais | "Chuva intensa detectada" |

**Constraints:**
- `CHECK (nivel_alerta IN ('MUITO_BAIXO', 'BAIXO', 'MODERADO', 'ALTO', 'MUITO_ALTO'))`
- `CHECK (confianca >= 0 AND confianca <= 1)`
- `CHECK (precipitacao_1h >= 0 AND precipitacao_4h >= 0 AND precipitacao_24h >= 0)`

### Tabela: `configuracoes_sistema`
Configurações gerais do sistema.

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `id` | SERIAL | Identificador único | 1 |
| `chave` | VARCHAR(100) | Nome da configuração | intervalo_coleta_minutos |
| `valor` | TEXT | Valor da configuração | 180 |
| `descricao` | TEXT | Descrição da configuração | Intervalo de coleta em minutos |
| `data_atualizacao` | TIMESTAMP | Última atualização | 2025-01-18 10:00:00 |

**Configurações Padrão:**
- `intervalo_coleta_minutos`: 180
- `intervalo_monitoramento_minutos`: 60
- `cidade_monitoramento`: Nova Friburgo
- `alertas_email_habilitado`: false
- `modelo_ml_versao`: 1.0

## 🤖 Sistema de Machine Learning

### Algoritmo: Random Forest Classifier

**Configuração do Modelo:**
```python
RandomForestClassifier(
    n_estimators=200,      # 200 árvores
    max_depth=10,          # Profundidade máxima
    min_samples_split=10,  # Mínimo para divisão
    min_samples_leaf=5,    # Mínimo por folha
    class_weight='balanced', # Balanceamento de classes
    random_state=42        # Reprodutibilidade
)
```

### Features (Variáveis de Entrada)

| Feature | Descrição | Unidade |
|---------|-----------|---------|
| `precip_1h` | Precipitação acumulada em 1 hora | mm |
| `precip_4h` | Precipitação acumulada em 4 horas | mm |
| `precip_24h` | Precipitação acumulada em 24 horas | mm |
| `umidade` | Umidade relativa do ar | % |
| `temperatura` | Temperatura atual | °C |
| `sensacao_termica` | Sensação térmica | °C |
| `vento_max` | Velocidade máxima do vento | m/s |

### Classes de Saída (Níveis de Alerta)

| Nível | Cor | Threshold (mm) | Descrição |
|-------|-----|---------------|-----------|
| **MUITO_BAIXO** | 🟢 #10B981 | < 35/50/75 | Situação normal |
| **BAIXO** | 🟡 #22C55E | 35/50/75 | Atenção recomendada |
| **MODERADO** | 🟠 #F59E0B | 50/65/100 | Risco de alagamentos pontuais |
| **ALTO** | 🔴 #EF4444 | 70/90/150 | Risco de alagamentos e deslizamentos |
| **MUITO_ALTO** | ⚫ #DC2626 | 100/130/220 | Alto risco de eventos extremos |

*Thresholds baseados nos critérios oficiais do CEMADEN-RJ para região serrana.*

## 📊 Métricas de Performance

### Avaliação do Modelo
- **Acurácia Média**: 87% ± 3%
- **Cross-Validation**: 5-fold
- **F1-Score por Classe**:
  - MUITO_BAIXO: 0.96
  - BAIXO: 0.71
  - MODERADO: 0.80
  - ALTO: 0.87
  - MUITO_ALTO: 0.90

### Sistema Híbrido
O sistema combina duas abordagens:
1. **Thresholds Oficiais** (CEMADEN-RJ): Regras baseadas em estudos científicos
2. **Machine Learning**: Detecção de padrões complexos nos dados históricos

## 🚀 Instalação e Uso

### Pré-requisitos
- Python 3.8+
- PostgreSQL 13+
- ChromeDriver (para web scraping)

### Instalação Rápida
```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/hydro-alert-system.git
cd hydro-alert-system

# 2. Instale dependências
pip install -r requirements.txt

# 3. Configure banco de dados
python setup_database.py

# 4. Treine o modelo
python simple_training.py

# 5. Inicie o servidor
python server.py
```

### Acesso
- **Dashboard**: http://localhost:5000
- **API**: http://localhost:5000/api/
- **Health Check**: http://localhost:5000/api/health

## 📡 API Endpoints

| Endpoint | Método | Descrição | Exemplo de Resposta |
|----------|--------|-----------|-------------------|
| `/api/clima` | GET | Dados meteorológicos atuais | `{"city": "Nova Friburgo", "temperature": 23.5}` |
| `/api/alerta` | GET | Alerta atual do sistema | `{"nivel": "BAIXO", "descricao": "Monitoramento"}` |
| `/api/historico` | GET | Dados históricos | `{"timestamps": [...], "precipitation": [...]}` |
| `/api/alertas/recentes` | GET | Histórico de alertas | `[{"nivel_alerta": "MODERADO", "data": "..."}]` |
| `/api/estatisticas` | GET | Estatísticas do sistema | `{"total_alertas": 150, "distribuicao": {...}}` |
| `/api/health` | GET | Status do sistema | `{"status": "healthy", "checks": {...}}` |

## 🔧 Configuração

### Variáveis de Ambiente (.env)
```env
# Banco de Dados
DB_HOST=localhost
DB_NAME=alerta_hidrologico
DB_USER=postgres
DB_PASSWORD=sua_senha
DB_PORT=5432

# Aplicação
SECRET_KEY=sua_chave_secreta
DEBUG=False
PORT=5000

# Selenium
CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
SELENIUM_HEADLESS=True
```

## 📈 Monitoramento

### Logs do Sistema
- `logs/app.log` - Logs principais da aplicação
- `logs/alertas.log` - Histórico de alertas gerados
- `logs/divergencias_alerta.log` - Divergências entre ML e thresholds

### Comandos Úteis
```bash
# Coleta única de dados
python main.py --collect

# Monitoramento contínuo
python main.py --monitor

# Treinamento do modelo
python main.py --train

# Avaliação do modelo
python main.py --evaluate
```

## 🤝 Contribuição

1. Fork o projeto
2. Crie sua feature branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request


## 🙏 Agradecimentos

- **INMET** - Instituto Nacional de Meteorologia
- **CPTEC/INPE** - Centro de Previsão de Tempo e Estudos Climáticos  
- **CEMADEN** - Centro Nacional de Monitoramento e Alertas de Desastres Naturais
- **Universidade** - Orientação acadêmica
- **Defesa Civil de Nova Friburgo** - Validação dos critérios de alerta


⚡ **Desenvolvido para salvar vidas e proteger comunidades** ⚡

![Nova Friburgo](https://img.shields.io/badge/Nova%20Friburgo-RJ-blue)
![TCC](https://img.shields.io/badge/TCC-2025-green)
![Status](https://img.shields.io/badge/Status-Ativo-brightgreen)
