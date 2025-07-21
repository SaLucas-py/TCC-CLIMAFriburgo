"""
Coletor de dados do INMET e CPTEC - Versão Robusta
Corrige problemas de conexão e adiciona múltiplas estratégias
"""
import time
import logging
import traceback
import unicodedata
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import requests
import json

logger = logging.getLogger(__name__)

class RobustINMETCollector:
    """Coletor robusto de dados meteorológicos do INMET"""
    
    def __init__(self):
        self.driver = None
        self.url = 'https://portal.inmet.gov.br/'
        self.city = 'Nova Friburgo'
        self.timeout = 30
        self.max_retries = 3
    
    def _create_robust_chrome_options(self):
        """Cria opções robustas para o Chrome"""
        options = Options()
        
        # Configurações básicas para estabilidade
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VizDisplayCompositor")
        
        # Configurações de rede e performance
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-sync")
        
        # Configurações de memória
        options.add_argument("--max_old_space_size=4096")
        options.add_argument("--memory-pressure-off")
        
        # User agent realístico
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Configurações experimentais
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option("detach", True)
        
        # Reduz logs
        options.add_argument("--log-level=3")
        options.add_argument("--silent")
        
        # Configurações de timeout
        options.add_argument("--page-load-strategy=eager")
        
        return options
    
    def _setup_driver_with_manager(self):
        """Configura driver usando WebDriver Manager"""
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            
            logger.info("🔧 Configurando ChromeDriver com WebDriver Manager...")
            
            options = self._create_robust_chrome_options()
            
            # Instala ChromeDriver automaticamente
            chrome_driver_path = ChromeDriverManager().install()
            logger.info(f"   ChromeDriver instalado em: {chrome_driver_path}")
            
            service = Service(chrome_driver_path)
            
            # Configurações adicionais do service
            service.start()
            
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Configurações adicionais do driver
            self.driver.implicitly_wait(10)
            self.driver.set_page_load_timeout(self.timeout)
            
            logger.info("✅ ChromeDriver configurado com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro no WebDriver Manager: {e}")
            return False
    
    def _setup_driver_manual(self):
        """Configuração manual do driver"""
        try:
            logger.info("🔧 Tentando configuração manual do ChromeDriver...")
            
            options = self._create_robust_chrome_options()
            
            # Tenta diferentes caminhos
            chrome_paths = [
                r'C:\chromedriver\chromedriver.exe',
                r'C:\Windows\System32\chromedriver.exe',
                'chromedriver.exe'  # No PATH
            ]
            
            for path in chrome_paths:
                try:
                    logger.info(f"   Tentando: {path}")
                    
                    if path != 'chromedriver.exe':
                        import os
                        if not os.path.exists(path):
                            continue
                    
                    service = Service(path)
                    self.driver = webdriver.Chrome(service=service, options=options)
                    
                    self.driver.implicitly_wait(10)
                    self.driver.set_page_load_timeout(self.timeout)
                    
                    logger.info(f"✅ ChromeDriver configurado: {path}")
                    return True
                    
                except Exception as e:
                    logger.warning(f"   Falhou: {path} - {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro na configuração manual: {e}")
            return False
    
    def _setup_driver(self):
        """Configura driver com múltiplas estratégias"""
        strategies = [
            ("WebDriver Manager", self._setup_driver_with_manager),
            ("Configuração Manual", self._setup_driver_manual)
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                logger.info(f"🔄 Tentando: {strategy_name}")
                if strategy_func():
                    return True
            except Exception as e:
                logger.warning(f"Estratégia {strategy_name} falhou: {e}")
                continue
        
        logger.error("❌ Todas as estratégias de configuração falharam")
        return False
    
    def _normalize_text(self, texto):
        """Normaliza texto removendo acentos"""
        return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    
    def _generate_datetime_utc(self, hora_utc_str):
        """Converte hora UTC para hora local (UTC−3)"""
        try:
            hora_utc = int(hora_utc_str)
            
            # Hora atual em UTC
            agora_utc = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
            hora_dado_utc = agora_utc.replace(hour=hora_utc)
            
            # Converte para UTC-3
            hora_dado_local = hora_dado_utc - timedelta(hours=3)
            
            data_local = hora_dado_local.date().strftime("%Y-%m-%d")
            hora_local = hora_dado_local.strftime("%H:%M")
            
            return data_local, hora_local
            
        except ValueError as e:
            logger.error(f"Erro ao converter hora UTC: {e}")
            return None, None
    
    def _safe_float(self, value):
        """Converte valor para float de forma segura"""
        try:
            return float(value) if value else None
        except (ValueError, TypeError):
            logger.error(f"Erro ao converter para float: {value}")
            return None
    
    def _test_driver_connection(self):
        """Testa se o driver está funcionando"""
        try:
            logger.info("🧪 Testando conexão do driver...")
            self.driver.get("https://httpbin.org/get")
            
            # Aguarda carregamento
            WebDriverWait(self.driver, 10).until(
                lambda driver: "httpbin" in driver.current_url.lower()
            )
            
            logger.info("✅ Driver está funcionando corretamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Teste do driver falhou: {e}")
            return False
    
    def collect_data(self):
        """Coleta dados do INMET com múltiplas tentativas"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🚀 Tentativa {attempt + 1}/{self.max_retries} - Coletando dados INMET...")
                
                # Configura driver se necessário
                if not self.driver:
                    if not self._setup_driver():
                        if attempt == self.max_retries - 1:
                            logger.error("❌ Não foi possível configurar o ChromeDriver")
                            return None
                        continue
                
                # Testa conexão
                if not self._test_driver_connection():
                    self._cleanup_driver()
                    continue
                
                # Acessa portal INMET
                logger.info("🌐 Acessando portal INMET...")
                self.driver.get(self.url)
                
                # Aguarda carregamento da página
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.ID, "search"))
                )
                
                logger.info(f"🔍 Buscando por {self.city}...")
                
                # Busca pela cidade
                search_box = self.driver.find_element(By.XPATH, '//*[@id="search"]')
                search_box.clear()
                search_box.send_keys(self.city)
                time.sleep(2)
                
                # Clica na sugestão
                suggestion = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, 'ui-menu-item-wrapper'))
                )
                suggestion.click()
                time.sleep(3)
                
                logger.info("⏳ Aguardando carregamento do gráfico...")
                
                # Aguarda carregamento do Highcharts
                WebDriverWait(self.driver, self.timeout).until(
                    lambda driver: driver.execute_script(
                        "return typeof Highcharts !== 'undefined' && Highcharts.charts.length > 0"
                    )
                )
                
                # Remove elementos que podem bloquear cliques
                self.driver.execute_script("""
                    // Remove VLibras
                    let vlib = document.querySelector('[vw-access-button]');
                    if (vlib) { vlib.remove(); }
                    
                    // Remove outros overlays
                    let overlays = document.querySelectorAll('.overlay, .modal, .popup');
                    overlays.forEach(el => el.remove());
                """)
                
                logger.info("📊 Abrindo menu de exportação...")
                
                # Encontra e clica no botão de exportação
                export_button = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'highcharts-exporting-group'))
                )
                
                # Scroll para o elemento e clica
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", export_button)
                time.sleep(1)
                
                # Tenta clicar usando JavaScript se o clique normal falhar
                try:
                    export_button.click()
                except:
                    self.driver.execute_script("arguments[0].click();", export_button)
                
                time.sleep(2)
                
                logger.info("📋 Selecionando opção de tabela...")
                
                # Clica na opção de tabela
                table_option = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, 
                        "//div[contains(@class, 'highcharts-menu')]//div[contains(text(), 'Visualizar tabela de dados')] | " +
                        "//div[contains(@class, 'highcharts-menu')]//div[9] | " +
                        "/html/body/div[4]/div[5]/div/div/div/div[2]/div/div/div/div[9]"))
                )
                
                try:
                    table_option.click()
                except:
                    self.driver.execute_script("arguments[0].click();", table_option)
                
                logger.info("⏳ Aguardando carregamento da tabela...")
                
                # Aguarda tabela carregar
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".highcharts-data-table table tbody"))
                )
                
                logger.info("📈 Extraindo dados da tabela...")
                
                # Extrai dados da tabela
                table = self.driver.find_element(By.CSS_SELECTOR, ".highcharts-data-table table tbody")
                rows = table.find_elements(By.TAG_NAME, "tr")
                
                valid_data = []
                for row in rows:
                    try:
                        cells = row.find_elements(By.XPATH, ".//th | .//td")
                        row_data = [self._normalize_text(cell.text.strip()) for cell in cells]
                        
                        if len(row_data) >= 5 and all(row_data[:5]):
                            data, hora = self._generate_datetime_utc(row_data[0])
                            if data and hora:
                                formatted_row = [data, hora] + row_data[1:]
                                valid_data.append(formatted_row)
                    except Exception as e:
                        logger.warning(f"Erro ao processar linha da tabela: {e}")
                        continue
                
                logger.info(f"✅ Coletados {len(valid_data)} registros do INMET")
                
                if valid_data:
                    return valid_data
                else:
                    logger.warning("⚠️ Nenhum dado válido encontrado")
                    if attempt == self.max_retries - 1:
                        return None
                
            except TimeoutException as e:
                logger.error(f"❌ Timeout na tentativa {attempt + 1}: {e}")
                self._cleanup_driver()
                if attempt < self.max_retries - 1:
                    time.sleep(5)  # Aguarda antes da próxima tentativa
                
            except WebDriverException as e:
                logger.error(f"❌ Erro do WebDriver na tentativa {attempt + 1}: {e}")
                self._cleanup_driver()
                if attempt < self.max_retries - 1:
                    time.sleep(5)
                
            except Exception as e:
                logger.error(f"❌ Erro geral na tentativa {attempt + 1}: {e}")
                logger.error(traceback.format_exc())
                self._cleanup_driver()
                if attempt < self.max_retries - 1:
                    time.sleep(5)
        
        logger.error("❌ Todas as tentativas de coleta INMET falharam")
        return None
    
    def _cleanup_driver(self):
        """Limpa recursos do driver"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                time.sleep(2)
        except:
            pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup_driver()


class RobustCPTECCollector:
    """Coletor robusto de dados do CPTEC/INPE"""
    
    def __init__(self):
        self.driver = None
        self.url = 'https://www.cptec.inpe.br/'
        self.city = 'Nova Friburgo'
        self.timeout = 30
        self.max_retries = 3
    
    def _setup_driver(self):
        """Usa a mesma configuração robusta do INMET"""
        collector = RobustINMETCollector()
        if collector._setup_driver():
            self.driver = collector.driver
            return True
        return False
    
    def collect_data(self):
        """Coleta dados do CPTEC com múltiplas tentativas"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🚀 Tentativa {attempt + 1}/{self.max_retries} - Coletando dados CPTEC...")
                
                # Configura driver se necessário
                if not self.driver:
                    if not self._setup_driver():
                        if attempt == self.max_retries - 1:
                            logger.error("❌ Não foi possível configurar o ChromeDriver para CPTEC")
                            return None
                        continue
                
                # Acessa portal CPTEC
                logger.info("🌐 Acessando portal CPTEC/INPE...")
                self.driver.get(self.url)
                
                # Tenta fechar pop-up se existir
                try:
                    close_alert = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, 
                            "//button[contains(@class, 'close')] | " +
                            "/html/body/div[2]/div/div/div[1]/button"))
                    )
                    close_alert.click()
                    logger.info("✅ Pop-up fechado")
                except:
                    logger.info("ℹ️ Nenhum pop-up detectado")
                
                logger.info(f"🔍 Buscando por {self.city}...")
                
                # Busca pela cidade
                search_box = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="searchbox"]'))
                )
                search_box.clear()
                search_box.send_keys(self.city)
                time.sleep(1)
                
                # Clica no botão de busca
                search_button = self.driver.find_element(By.XPATH, 
                    '/html/body/main/div[1]/div/div[1]/button')
                search_button.click()
                time.sleep(3)
                
                logger.info("📊 Coletando dados da tabela CPTEC...")
                
                # Encontra tabela de previsão
                table = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'mb-3.tabela-prev.sem-hover'))
                )
                
                rows = table.find_elements(By.CLASS_NAME, 'centro-tabela')
                
                valid_data = {}
                for row in rows:
                    try:
                        cells = row.find_elements(By.TAG_NAME, 'td')
                        if len(cells) >= 6:
                            # Extrai dados das células
                            temp_minima = cells[0].text.strip().split('\n')[0].replace('°C', '').strip()
                            temp_maxima = cells[1].text.strip().split('\n')[0].replace('°C', '').strip()
                            vento_max = cells[2].text.strip().split('\n')[0].replace('m/s', '').strip()
                            uv_max = cells[3].text.strip().split('\n')[0].replace('%', '').strip()
                            umidade_minima = cells[5].text.strip().split('\n')[0].replace('%', '').strip()
                            
                            valid_data = {
                                "temp_minima": temp_minima,
                                "temp_maxima": temp_maxima,
                                "vento_max": vento_max,
                                "uv_max": uv_max,
                                "umidade_minima": umidade_minima
                            }
                            
                            logger.info(f"✅ Dados CPTEC coletados: {valid_data}")
                            return valid_data
                            time.sleep(1800) # Espera 30 minutos antes de nova coleta
                    except Exception as e:
                        logger.warning(f"Erro ao processar linha CPTEC: {e}")
                        continue
                
                if not valid_data:
                    logger.warning("⚠️ Nenhum dado CPTEC encontrado")
                
            except Exception as e:
                logger.error(f"❌ Erro na tentativa {attempt + 1} CPTEC: {e}")
                logger.error(traceback.format_exc())
                
                if attempt < self.max_retries - 1:
                    time.sleep(5)
        
        logger.error("❌ Todas as tentativas de coleta CPTEC falharam")
        return None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


# Aliases para compatibilidade com código existente
INMETCollector = RobustINMETCollector
CPTECCollector = RobustCPTECCollector