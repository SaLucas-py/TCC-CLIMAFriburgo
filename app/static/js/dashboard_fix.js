
// Adicione este código no final do dashboard.js para corrigir o carregamento

// Função para carregar alertas com timeout
async function loadAlertsWithTimeout() {
    const tableBody = document.getElementById('alertsTableBody');
    if (!tableBody) return;
    
    // Mostra carregando
    tableBody.innerHTML = `
        <tr>
            <td colspan="5" style="text-align: center; padding: 1rem;">
                <i class="fas fa-spinner fa-spin"></i> Carregando...
            </td>
        </tr>
    `;
    
    try {
        // Timeout de 5 segundos
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        const response = await fetch('/api/alertas/recentes', {
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
            const alerts = await response.json();
            dashboard.updateAlertsTable(alerts);
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
        
    } catch (error) {
        console.log('Erro ao carregar alertas, usando dados de exemplo:', error);
        
        // Dados de exemplo se falhar
        const exampleAlerts = [
            {
                id: 1,
                nivel_alerta: 'BAIXO',
                data_ocorrencia: new Date().toISOString(),
                precipitacao_1h: 2.3,
                precipitacao_4h: 5.7,
                precipitacao_24h: 12.4,
                umidade: 75,
                status: 'Exemplo'
            }
        ];
        
        dashboard.updateAlertsTable(exampleAlerts);
    }
}

// Substitui o carregamento original
if (window.dashboard) {
    // Aguarda 2 segundos e carrega alertas
    setTimeout(loadAlertsWithTimeout, 2000);
}
        