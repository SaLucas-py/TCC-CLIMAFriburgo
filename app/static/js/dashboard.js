/**
 * Modern Dashboard JavaScript - Versão Corrigida para Histórico de Alertas
 */

class ModernHydroDashboard {
    constructor() {
        this.apiUrl = '/api';
        this.updateInterval = 2 * 60 * 1000; // 2 minutos
        this.charts = {};
        this.lastUpdate = null;
        this.isLoading = false;
        
        this.alertConfig = {
            'MUITO_BAIXO': {
                color: '#10B981',
                icon: 'fas fa-shield-alt',
                description: 'Situação normal. Sem riscos identificados.'
            },
            'BAIXO': {
                color: '#22C55E',
                icon: 'fas fa-shield-alt',
                description: 'Atenção. Monitoramento recomendado.'
            },
            'MODERADO': {
                color: '#F59E0B',
                icon: 'fas fa-exclamation-triangle',
                description: 'Cuidado. Possível risco de alagamentos pontuais.'
            },
            'ALTO': {
                color: '#EF4444',
                icon: 'fas fa-exclamation-triangle',
                description: 'Alerta. Risco de alagamentos e deslizamentos.'
            },
            'MUITO_ALTO': {
                color: '#DC2626',
                icon: 'fas fa-exclamation-circle',
                description: 'Perigo. Alto risco de eventos extremos!'
            }
        };
        
        this.init();
    }
    
    async init() {
        console.log('🚀 Inicializando Modern HydroDashboard...');
        
        try {
            // Mostra loading inicial
            this.showLoadingScreen(true);
            
            // Simula carregamento inicial
            await this.simulateLoading();
            
            // Carrega dados iniciais
            await this.loadInitialData();
            
            // Inicializa componentes
            this.initializeCharts();
            this.setupEventListeners();
            this.startAutoUpdate();
            
            // Esconde loading screen
            this.showLoadingScreen(false);
            
            // Mostra notificação de sucesso
            this.showNotification('Sistema inicializado com sucesso!', 'success');
            
            console.log('✅ Dashboard inicializado com sucesso!');
            
        } catch (error) {
            console.error('❌ Erro ao inicializar dashboard:', error);
            this.showLoadingScreen(false);
            this.showNotification('Erro ao carregar dados iniciais', 'error');
        }
    }
    
    async simulateLoading() {
        const progressBar = document.querySelector('.loading-progress');
        const loadingText = document.querySelector('.loading-text p');
        
        const steps = [
            { progress: 20, text: 'Conectando com servidor...' },
            { progress: 40, text: 'Carregando dados meteorológicos...' },
            { progress: 60, text: 'Processando alertas...' },
            { progress: 80, text: 'Inicializando gráficos...' },
            { progress: 100, text: 'Finalizando...' }
        ];
        
        for (const step of steps) {
            if (progressBar) progressBar.style.width = `${step.progress}%`;
            if (loadingText) loadingText.textContent = step.text;
            await new Promise(resolve => setTimeout(resolve, 500));
        }
    }
    
    showLoadingScreen(show) {
        const loadingScreen = document.getElementById('loadingScreen');
        if (!loadingScreen) return;
        
        if (show) {
            loadingScreen.style.display = 'flex';
        } else {
            loadingScreen.style.opacity = '0';
            setTimeout(() => {
                loadingScreen.style.display = 'none';
            }, 500);
        }
    }
    
    async loadInitialData() {
        try {
            console.log('📊 Carregando dados iniciais...');
            
            const [weatherData, alertData, historicalData, recentAlerts] = await Promise.all([
                this.fetchWeatherData(),
                this.fetchAlertData(),
                this.fetchHistoricalData('24h'),
                this.fetchRecentAlerts() // ADICIONADO: Carrega alertas recentes
            ]);
            
            if (weatherData) {
                this.updateWeatherDisplay(weatherData);
            }
            
            if (alertData) {
                this.updateAlertDisplay(alertData);
            }
            
            if (historicalData) {
                this.updateChartsData(historicalData);
            }
            
            // NOVO: Atualiza tabela de alertas
            if (recentAlerts) {
                this.updateAlertsTable(recentAlerts);
            } else {
                console.warn('⚠️ Nenhum alerta recente encontrado');
                this.showEmptyAlertsTable();
            }
            
            this.updateLastUpdateTime();
            
        } catch (error) {
            console.error('Erro ao carregar dados iniciais:', error);
            // Carrega dados de exemplo para demonstração
            this.loadDemoData();
        }
    }
    
    async fetchRecentAlerts() {
        try {
            console.log('🔍 Buscando alertas recentes...');
            const response = await fetch(`${this.apiUrl}/alertas/recentes?limit=20`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('📋 Alertas recebidos:', data);
            
            return data;
        } catch (error) {
            console.error('❌ Erro ao buscar alertas recentes:', error);
            
            // Testa endpoint alternativo
            try {
                console.log('🔄 Testando endpoint de teste...');
                const response = await fetch(`${this.apiUrl}/alertas/teste`);
                if (response.ok) {
                    const testData = await response.json();
                    console.log('🧪 Dados do teste:', testData);
                }
            } catch (testError) {
                console.error('❌ Endpoint de teste também falhou:', testError);
            }
            
            return null;
        }
    }
    
    updateAlertsTable(alertas) {
        console.log('📊 Atualizando tabela de alertas...', alertas);
        
        const tableBody = document.getElementById('alertsTableBody');
        
        if (!tableBody) {
            console.error('❌ Elemento alertsTableBody não encontrado');
            return;
        }
        
        if (!alertas || alertas.length === 0) {
            this.showEmptyAlertsTable();
            return;
        }
        
        try {
            const rows = alertas.map((alerta, index) => {
                // Função para formatar data
                const formatDate = (dateString) => {
                    try {
                        if (!dateString) return '--';
                        const date = new Date(dateString);
                        return date.toLocaleString('pt-BR', {
                            day: '2-digit',
                            month: '2-digit',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                        });
                    } catch (e) {
                        return '--';
                    }
                };
                
                // Função para formatar números
                const formatNumber = (value) => {
                    try {
                        if (value === null || value === undefined || isNaN(value)) return '--';
                        return parseFloat(value).toFixed(1);
                    } catch (e) {
                        return '--';
                    }
                };
                
                // Função para obter classe CSS do alerta
                const getAlertClass = (nivel) => {
                    const classes = {
                        'MUITO_BAIXO': 'alert-muito-baixo',
                        'BAIXO': 'alert-baixo', 
                        'MODERADO': 'alert-moderado',
                        'ALTO': 'alert-alto',
                        'MUITO_ALTO': 'alert-muito-alto'
                    };
                    return classes[nivel] || 'alert-muito-baixo';
                };
                
                return `
                    <tr>
                        <td>${formatDate(alerta.data_ocorrencia)}</td>
                        <td>
                            <span class="alert-badge ${getAlertClass(alerta.nivel_alerta)}">
                                ${(alerta.nivel_alerta || 'MUITO_BAIXO').replace('_', ' ')}
                            </span>
                        </td>
                        <td>
                            <div class="precip-details">
                                <div>1h: ${formatNumber(alerta.precipitacao_1h)}mm</div>
                                <div>4h: ${formatNumber(alerta.precipitacao_4h)}mm</div>
                                <div>24h: ${formatNumber(alerta.precipitacao_24h)}mm</div>
                            </div>
                        </td>
                        <td>${formatNumber(alerta.umidade)}%</td>
                        <td>
                            <div class="status-info">
                                <span class="method">${alerta.metodo_predicao || 'THRESHOLD'}</span>
                                <span class="confidence">${Math.round((alerta.confianca || 1) * 100)}%</span>
                            </div>
                        </td>
                    </tr>
                `;
            });
            
            tableBody.innerHTML = rows.join('');
            
            console.log(`✅ Tabela atualizada com ${alertas.length} alertas`);
            
            // Anima as linhas
            this.animateTableRows();
            
        } catch (error) {
            console.error('❌ Erro ao atualizar tabela:', error);
            this.showEmptyAlertsTable('Erro ao processar dados');
        }
    }
    
    showEmptyAlertsTable(message = 'Nenhum alerta encontrado') {
        const tableBody = document.getElementById('alertsTableBody');
        
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="no-data">
                        <div class="empty-state">
                            <i class="fas fa-info-circle"></i>
                            <span>${message}</span>
                        </div>
                    </td>
                </tr>
            `;
        }
    }
    
    animateTableRows() {
        const rows = document.querySelectorAll('#alertsTableBody tr');
        rows.forEach((row, index) => {
            setTimeout(() => {
                row.style.opacity = '0';
                row.style.transform = 'translateY(20px)';
                row.style.transition = 'all 0.3s ease-out';
                
                setTimeout(() => {
                    row.style.opacity = '1';
                    row.style.transform = 'translateY(0)';
                }, 50);
            }, index * 100);
        });
    }
    
    loadDemoData() {
        console.log('📊 Carregando dados de demonstração...');
        
        // Dados de exemplo
        const demoWeatherData = {
            city: "Nova Friburgo",
            average_temperature: 23.5,
            average_thermal_sensation: 25.2,
            average_humidity: 78,
            rain_probability: 2.3,
            temp_minima: 18.2,
            temp_maxima: 28.7,
            umidade_minima: 65,
            vento_max: 4.2,
            uv_max: 7
        };
        
        const demoAlertData = {
            nivel: 'BAIXO',
            descricao: 'Situação sob monitoramento'
        };
        
        // Alertas de exemplo
        const demoAlerts = [
            {
                id: 1,
                nivel_alerta: 'BAIXO',
                data_ocorrencia: new Date().toISOString(),
                precipitacao_1h: 5.2,
                precipitacao_4h: 12.8,
                precipitacao_24h: 25.4,
                umidade: 78.5,
                metodo_predicao: 'THRESHOLD',
                confianca: 0.95
            },
            {
                id: 2,
                nivel_alerta: 'MODERADO',
                data_ocorrencia: new Date(Date.now() - 3600000).toISOString(),
                precipitacao_1h: 8.7,
                precipitacao_4h: 18.3,
                precipitacao_24h: 45.6,
                umidade: 82.1,
                metodo_predicao: 'ML',
                confianca: 0.87
            }
        ];
        
        this.updateWeatherDisplay(demoWeatherData);
        this.updateAlertDisplay(demoAlertData);
        this.updateAlertsTable(demoAlerts);
        this.loadDemoCharts();
    }
    
    loadDemoCharts() {
        // Dados de exemplo para gráficos
        const timestamps = [];
        const tempData = [];
        const humidityData = [];
        const precipData = [];
        
        for (let i = 0; i < 24; i++) {
            const hour = new Date();
            hour.setHours(hour.getHours() - (23 - i));
            timestamps.push(hour.toTimeString().substr(0, 5));
            
            tempData.push(20 + Math.random() * 10);
            humidityData.push(60 + Math.random() * 30);
            precipData.push(Math.random() * 5);
        }
        
        this.updateChartsData({
            timestamps,
            temperature: tempData,
            humidity: humidityData,
            precipitation: precipData
        });
    }
    
    // Restante dos métodos permanecem iguais...
    async fetchWeatherData() {
        try {
            const response = await fetch(`${this.apiUrl}/clima`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('Erro ao buscar dados meteorológicos:', error);
            return null;
        }
    }
    
    async fetchAlertData() {
        try {
            const response = await fetch(`${this.apiUrl}/alerta`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('Erro ao buscar dados de alerta:', error);
            return null;
        }
    }
    
    async fetchHistoricalData(period = '24h') {
        try {
            const response = await fetch(`${this.apiUrl}/historico?period=${period}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('Erro ao buscar dados históricos:', error);
            return null;
        }
    }
    
    updateWeatherDisplay(data) {
        if (!data) return;
        
        // Atualiza temperatura principal
        this.updateElement('currentTemp', this.formatNumber(data.average_temperature));
        
        // Atualiza cards de informação
        this.updateElement('tempCurrent', this.formatNumber(data.average_temperature));
        this.updateElement('tempFeels', this.formatNumber(data.average_thermal_sensation));
        this.updateElement('tempMin', this.formatNumber(data.temp_minima));
        this.updateElement('tempMax', this.formatNumber(data.temp_maxima));
        
        this.updateElement('humidCurrent', this.formatNumber(data.average_humidity));
        this.updateElement('humidMin', this.formatNumber(data.umidade_minima));
        this.updateElement('humidityValue', this.formatNumber(data.average_humidity) + '%');
        
        this.updateElement('precipCurrent', this.formatNumber(data.rain_probability));
        this.updateElement('precipValue', this.formatNumber(data.rain_probability) + 'mm');
        
        this.updateElement('windCurrent', this.formatNumber(data.vento_max));
        this.updateElement('windMax', this.formatNumber(data.vento_max));
        this.updateElement('windValue', this.formatNumber(data.vento_max) + 'm/s');
        
        this.updateElement('uvIndex', this.formatNumber(data.uv_max));
        
        // Atualiza barra de progresso da umidade
        const humidityProgress = document.getElementById('humidityProgress');
        if (humidityProgress) {
            humidityProgress.style.width = `${data.average_humidity}%`;
        }
        
        // Atualiza ícone do clima
        this.updateWeatherIcon(data.average_temperature, data.rain_probability);
        
        // Atualiza descrição do clima
        this.updateWeatherDescription(data.average_temperature, data.rain_probability);
        
        // Animação de atualização
        this.animateElements([
            '.temperature-main',
            '.info-card',
            '.stat-card'
        ]);
    }
    
    updateAlertDisplay(data) {
        if (!data || !data.nivel) return;
        
        const alertConfig = this.alertConfig[data.nivel];
        if (!alertConfig) return;
        
        // Atualiza indicador de alerta
        const alertLevel = document.getElementById('alertLevel');
        const alertLevelIcon = document.querySelector('.alert-level-icon');
        const alertLevelText = document.getElementById('alertLevelText');
        const alertLevelDesc = document.getElementById('alertLevelDesc');
        
        if (alertLevelIcon) {
            alertLevelIcon.style.background = alertConfig.color;
            alertLevelIcon.querySelector('i').className = alertConfig.icon;
        }
        
        if (alertLevelText) {
            alertLevelText.textContent = data.nivel.replace('_', ' ');
        }
        
        if (alertLevelDesc) {
            alertLevelDesc.textContent = alertConfig.description;
        }
        
        // Mostra banner de alerta se necessário
        if (data.nivel !== 'MUITO_BAIXO') {
            this.showAlertBanner(data.nivel, alertConfig);
        }
    }
    
    showAlertBanner(nivel, config) {
        const banner = document.getElementById('alertBanner');
        const title = document.getElementById('alertTitle');
        const description = document.getElementById('alertDescription');
        
        if (banner && title && description) {
            title.textContent = `Alerta ${nivel.replace('_', ' ')}`;
            description.textContent = config.description;
            
            banner.style.display = 'flex';
            banner.style.background = `linear-gradient(135deg, ${config.color}, ${this.darkenColor(config.color, 20)})`;
        }
    }
    
    updateWeatherIcon(temperature, precipitation) {
        const weatherIcon = document.getElementById('weatherIcon');
        if (!weatherIcon) return;
        
        let iconClass = 'fas fa-sun';
        
        if (precipitation > 10) {
            iconClass = 'fas fa-cloud-rain';
        } else if (precipitation > 2) {
            iconClass = 'fas fa-cloud-sun-rain';
        } else if (temperature > 30) {
            iconClass = 'fas fa-sun';
        } else if (temperature < 15) {
            iconClass = 'fas fa-snowflake';
        } else {
            iconClass = 'fas fa-cloud-sun';
        }
        
        weatherIcon.className = iconClass;
    }
    
    updateWeatherDescription(temperature, precipitation) {
        const weatherDesc = document.getElementById('weatherDescription');
        if (!weatherDesc) return;
        
        let description = 'Tempo agradável';
        
        if (precipitation > 10) {
            description = 'Chuva forte';
        } else if (precipitation > 2) {
            description = 'Chuva fraca';
        } else if (temperature > 30) {
            description = 'Muito quente';
        } else if (temperature < 15) {
            description = 'Muito frio';
        } else if (temperature > 25) {
            description = 'Quente';
        } else if (temperature < 20) {
            description = 'Fresco';
        }
        
        weatherDesc.textContent = description;
    }
    
    updateChartsData(data) {
        if (!data) return;
        
        // Atualiza gráfico de precipitação
        if (this.charts.precipitation) {
            this.charts.precipitation.data.labels = data.timestamps || [];
            this.charts.precipitation.data.datasets[0].data = data.precipitation || [];
            this.charts.precipitation.update('none');
        }
        
        // Atualiza gráfico de temperatura
        if (this.charts.temperature) {
            this.charts.temperature.data.labels = data.timestamps || [];
            this.charts.temperature.data.datasets[0].data = data.temperature || [];
            this.charts.temperature.data.datasets[1].data = data.humidity || [];
            this.charts.temperature.update('none');
        }
    }
    
    initializeCharts() {
        this.initPrecipitationChart();
        this.initTemperatureChart();
    }
    
    initPrecipitationChart() {
        const ctx = document.getElementById('precipitationChart');
        if (!ctx) return;
        
        this.charts.precipitation = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Precipitação (mm)',
                    data: [],
                    borderColor: '#45B7D1',
                    backgroundColor: 'rgba(69, 183, 209, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#45B7D1',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        titleColor: '#1E293B',
                        bodyColor: '#475569',
                        borderColor: '#E2E8F0',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#F1F5F9'
                        },
                        ticks: {
                            color: '#64748B',
                            font: {
                                size: 12
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#64748B',
                            font: {
                                size: 12
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }
    
    initTemperatureChart() {
        const ctx = document.getElementById('temperatureChart');
        if (!ctx) return;
        
        this.charts.temperature = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Temperatura (°C)',
                        data: [],
                        borderColor: '#FF6B6B',
                        backgroundColor: 'rgba(255, 107, 107, 0.1)',
                        borderWidth: 3,
                        fill: false,
                        tension: 0.4,
                        yAxisID: 'y',
                        pointBackgroundColor: '#FF6B6B',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        pointRadius: 5,
                        pointHoverRadius: 8
                    },
                    {
                        label: 'Umidade (%)',
                        data: [],
                        borderColor: '#4ECDC4',
                        backgroundColor: 'rgba(78, 205, 196, 0.1)',
                        borderWidth: 3,
                        fill: false,
                        tension: 0.4,
                        yAxisID: 'y1',
                        pointBackgroundColor: '#4ECDC4',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        pointRadius: 5,
                        pointHoverRadius: 8
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        titleColor: '#1E293B',
                        bodyColor: '#475569',
                        borderColor: '#E2E8F0',
                        borderWidth: 1,
                        cornerRadius: 8
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: {
                            color: '#F1F5F9'
                        },
                        ticks: {
                            color: '#64748B',
                            font: {
                                size: 12
                            }
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false,
                        },
                        ticks: {
                            color: '#64748B',
                            font: {
                                size: 12
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#64748B',
                            font: {
                                size: 12
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }
    
    setupEventListeners() {
        // Botões de controle dos gráficos
        document.querySelectorAll('.chart-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.handleChartPeriodChange(e.target.dataset.period, e.target);
            });
        });
        
        // Atualização manual com tecla F5
        document.addEventListener('keydown', (e) => {
            if (e.key === 'F5' || (e.ctrlKey && e.key === 'r')) {
                e.preventDefault();
                this.refreshData();
            }
        });
        
        // Atualização com clique no botão
        const refreshBtn = document.querySelector('[onclick="refreshData()"]');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshData());
        }
    }
    
    async handleChartPeriodChange(period, button) {
        // Atualiza botões ativos
        document.querySelectorAll('.chart-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        button.classList.add('active');
        
        // Carrega dados do período
        this.showChartLoading(true);
        try {
            const data = await this.fetchHistoricalData(period);
            if (data) {
                this.updateChartsData(data);
            }
        } catch (error) {
            console.error('Erro ao alterar período:', error);
            this.showNotification('Erro ao carregar dados do período', 'error');
        } finally {
            this.showChartLoading(false);
        }
    }
    
    showChartLoading(show) {
        const charts = document.querySelectorAll('.chart-container');
        charts.forEach(chart => {
            if (show) {
                chart.classList.add('loading');
            } else {
                chart.classList.remove('loading');
            }
        });
    }
    
    startAutoUpdate() {
        setInterval(() => {
            this.refreshData();
        }, this.updateInterval);
        
        console.log(`🔄 Auto-atualização configurada para ${this.updateInterval / 1000}s`);
    }
    
    async refreshData() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.updateConnectionStatus('updating');
        
        try {
            const [weatherData, alertData, recentAlerts] = await Promise.all([
                this.fetchWeatherData(),
                this.fetchAlertData(),
                this.fetchRecentAlerts() // ADICIONADO: Atualiza alertas também
            ]);
            
            if (weatherData) {
                this.updateWeatherDisplay(weatherData);
            }
            
            if (alertData) {
                this.updateAlertDisplay(alertData);
            }
            
            // NOVO: Atualiza tabela de alertas
            if (recentAlerts) {
                this.updateAlertsTable(recentAlerts);
            }
            
            this.updateLastUpdateTime();
            this.updateConnectionStatus('connected');
            
        } catch (error) {
            console.error('Erro na atualização:', error);
            this.updateConnectionStatus('disconnected');
            this.showNotification('Erro ao atualizar dados', 'error');
        } finally {
            this.isLoading = false;
        }
    }
    
    updateLastUpdateTime() {
        this.lastUpdate = new Date();
        const timeString = this.lastUpdate.toLocaleTimeString('pt-BR', {
            hour: '2-digit',
            minute: '2-digit'
        });
        this.updateElement('lastUpdate', timeString);
    }
    
    updateConnectionStatus(status) {
        const statusElement = document.getElementById('connectionStatus');
        if (!statusElement) return;
        
        statusElement.classList.remove('connected', 'disconnected', 'updating');
        statusElement.classList.add(status);
        
        const statusText = {
            'connected': 'Online',
            'disconnected': 'Offline',
            'updating': 'Atualizando...'
        };
        
        statusElement.textContent = statusText[status] || 'Desconhecido';
    }
    
    showNotification(message, type = 'info') {
        const notifications = document.getElementById('notifications');
        if (!notifications) return;
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <i class="fas fa-${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
            </div>
        `;
        
        notifications.appendChild(notification);
        
        // Remove após 5 segundos
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                if (notifications.contains(notification)) {
                    notifications.removeChild(notification);
                }
            }, 300);
        }, 5000);
    }
    
    getNotificationIcon(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
    
    // Métodos utilitários
    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }
    
    formatNumber(value) {
        if (value === null || value === undefined || isNaN(value)) {
            return '--';
        }
        return parseFloat(value).toFixed(1);
    }
    
    darkenColor(color, percent) {
        const num = parseInt(color.replace("#", ""), 16);
        const amt = Math.round(2.55 * percent);
        const R = (num >> 16) + amt;
        const G = (num >> 8 & 0x00FF) + amt;
        const B = (num & 0x0000FF) + amt;
        return "#" + (0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
            (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
            (B < 255 ? B < 1 ? 0 : B : 255)).toString(16).slice(1);
    }
    
    animateElements(selectors) {
        selectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                element.style.animation = 'none';
                element.offsetHeight; // Trigger reflow
                element.style.animation = 'pulse 0.6s ease-in-out';
            });
        });
    }
}

// Funções globais para compatibilidade
function closeAlert() {
    const banner = document.getElementById('alertBanner');
    if (banner) {
        banner.style.display = 'none';
    }
}

function exportData() {
    console.log('📥 Exportando dados...');
    
    // Busca dados da tabela
    const tableRows = document.querySelectorAll('#alertsTableBody tr');
    if (tableRows.length === 0 || tableRows[0].querySelector('.no-data')) {
        dashboard.showNotification('Nenhum dado para exportar', 'warning');
        return;
    }
    
    // Prepara dados para CSV
    const headers = ['Data/Hora', 'Nível', 'Precipitação 1h', 'Precipitação 4h', 'Precipitação 24h', 'Umidade', 'Método'];
    const csvData = [headers];
    
    tableRows.forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 5) {
            const rowData = [
                cells[0].textContent.trim(),
                cells[1].textContent.trim().replace(/\s+/g, ' '),
                cells[2].textContent.trim().replace(/\D/g, ''), // Só números
                '', // Placeholder para 4h
                '', // Placeholder para 24h  
                cells[3].textContent.trim(),
                cells[4].textContent.trim()
            ];
            csvData.push(rowData);
        }
    });
    
    // Gera CSV
    const csvContent = csvData.map(row => row.join(',')).join('\n');
    
    // Download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `alertas_hidrologicos_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    dashboard.showNotification('Dados exportados com sucesso!', 'success');
}

function refreshData() {
    if (window.dashboard) {
        dashboard.refreshData();
    } else {
        location.reload();
    }
}

function showInfo() {
    const info = `
Sistema de Monitoramento Hidrológico
Nova Friburgo - RJ

Versão: 2.0 Modern
Desenvolvido para prevenção de desastres

Fontes de dados:
• INMET (Instituto Nacional de Meteorologia)
• CPTEC/INPE (Centro de Previsão de Tempo e Estudos Climáticos)

Tecnologias:
• Machine Learning para predição de alertas
• Tempo real com atualização automática
• Interface responsiva e moderna

Última atualização: ${new Date().toLocaleString('pt-BR')}
    `;
    
    if (window.dashboard) {
        dashboard.showNotification(info, 'info');
    } else {
        alert(info);
    }
}

function showHelp() {
    const help = `
Como usar o HydroAlert:

🔄 Atualização automática a cada 2 minutos
⌨️ Pressione F5 para atualização manual
📊 Use os botões nos gráficos para alterar períodos
📱 Interface totalmente responsiva
🎨 Design moderno e intuitivo

Níveis de Alerta:
🟢 Muito Baixo - Situação normal
🟡 Baixo - Atenção recomendada
🟠 Moderado - Cuidado necessário
🔴 Alto - Alerta ativo
⚫ Muito Alto - Perigo iminente

Histórico de Alertas:
📋 Tabela mostra últimos 20 alertas
📥 Botão "Exportar" gera arquivo CSV
🔄 Atualização automática dos dados
    `;
    
    if (window.dashboard) {
        dashboard.showNotification(help, 'info');
    } else {
        alert(help);
    }
}

function showContacts() {
    const contacts = `
Contatos de Emergência:

🚨 Defesa Civil: 199
🚒 Bombeiros: 193
🚑 SAMU: 192
👮 Polícia: 190

Suporte Técnico:
📧 suporte@hydroalert.com
📞 (22) 99999-9999

Prefeitura de Nova Friburgo:
📞 (22) 2522-2000

Em caso de emergência hidrológica:
1. Mantenha a calma
2. Siga rotas de evacuação
3. Evite áreas alagadas
4. Procure abrigo em local seguro
    `;
    
    if (window.dashboard) {
        dashboard.showNotification(contacts, 'info');
    } else {
        alert(contacts);
    }
}

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Inicializando dashboard...');
    window.dashboard = new ModernHydroDashboard();
});

// Adiciona estilos CSS dinâmicos para a tabela de alertas
const alertTableStyles = `
    .alert-badge {
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        color: white;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .alert-muito-baixo { background: linear-gradient(135deg, #10B981, #059669); }
    .alert-baixo { background: linear-gradient(135deg, #22C55E, #16A34A); }
    .alert-moderado { background: linear-gradient(135deg, #F59E0B, #D97706); }
    .alert-alto { background: linear-gradient(135deg, #EF4444, #DC2626); }
    .alert-muito-alto { background: linear-gradient(135deg, #DC2626, #B91C1C); }
    
    .precip-details {
        font-size: 0.8rem;
        line-height: 1.3;
    }
    
    .precip-details div {
        margin: 2px 0;
    }
    
    .status-info {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
    }
    
    .status-info .method {
        font-size: 0.7rem;
        background: #F3F4F6;
        color: #374151;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 500;
    }
    
    .status-info .confidence {
        font-size: 0.75rem;
        color: #10B981;
        font-weight: 600;
    }
    
    .empty-state {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 40px;
        color: #6B7280;
        font-style: italic;
    }
    
    .empty-state i {
        font-size: 1.2rem;
        opacity: 0.7;
    }
    
    #alertsTableBody tr {
        transition: all 0.3s ease;
        opacity: 1;
    }
    
    #alertsTableBody tr:hover {
        background-color: #F9FAFB;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .chart-container.loading {
        opacity: 0.6;
        pointer-events: none;
        position: relative;
    }
    
    .chart-container.loading::after {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 30px;
        height: 30px;
        border: 3px solid #f3f3f3;
        border-top: 3px solid #0066CC;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: translate(-50%, -50%) rotate(0deg); }
        100% { transform: translate(-50%, -50%) rotate(360deg); }
    }
    
    .notification {
        transform: translateX(100%);
        animation: slideInRight 0.3s ease-out forwards;
        max-width: 350px;
        word-wrap: break-word;
    }
    
    @keyframes slideInRight {
        to {
            transform: translateX(0);
        }
    }
    
    #connectionStatus.connected {
        color: #10B981;
    }
    
    #connectionStatus.disconnected {
        color: #EF4444;
    }
    
    #connectionStatus.updating {
        color: #F59E0B;
    }
`;

// Adiciona os estilos ao documento
const styleSheet = document.createElement('style');
styleSheet.textContent = alertTableStyles;
document.head.appendChild(styleSheet);