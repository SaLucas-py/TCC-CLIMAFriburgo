"""
Classificador de alertas usando Machine Learning
"""
import os
import joblib
import pandas as pd
import numpy as np
import logging
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
from config.settings import ML_CONFIG
from core.database.models import WeatherData
from .data_processor import DataProcessor

logger = logging.getLogger(__name__)

class AlertClassifier:
    """Classificador de alertas hidrológicos"""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.processor = DataProcessor()
        self.model_path = ML_CONFIG['model_path']
        
        # Cria diretório se não existir
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
    
    def train_model(self, retrain=False):
        """Treina novo modelo de classificação"""
        try:
            logger.info("Iniciando treinamento do modelo...")
            
            # Busca dados históricos
            dados = WeatherData.fetch_historical(days=180)  # 6 meses
            
            if dados.empty or len(dados) < ML_CONFIG['min_data_points']:
                logger.error(f"Dados insuficientes para treinamento: {len(dados)} registros")
                return False
            
            logger.info(f"Dados carregados: {len(dados)} registros")
            
            # Validação da qualidade
            issues = self.processor.validate_data_quality(dados)
            if issues:
                logger.warning(f"Problemas detectados nos dados: {issues}")
            
            # Processamento
            dados = self.processor.calculate_accumulated(dados)
            dados = self.processor.add_weather_features(dados)
            dados = self.processor.create_labels_for_training(dados)
            
            # Preparação de features
            X, feature_names = self.processor.prepare_features_for_ml(dados)
            
            if X.empty:
                logger.error("Erro na preparação das features")
                return False
            
            # Target
            if 'alerta' not in dados.columns:
                logger.error("Coluna 'alerta' não encontrada")
                return False
            
            y = dados['alerta']
            
            # Remove registros com target nulo
            valid_mask = y.notna()
            X = X[valid_mask]
            y = y[valid_mask]
            
            if len(X) < ML_CONFIG['min_data_points']:
                logger.error(f"Dados válidos insuficientes: {len(X)} registros")
                return False
            
            logger.info(f"Distribuição das classes:")
            for classe, count in y.value_counts().items():
                logger.info(f"  {classe}: {count} ({count/len(y)*100:.1f}%)")
            
            # Nota: Com limiares oficiais CEMADEN-RJ, a maioria dos dados será MUITO_BAIXO
            # Isso é esperado, pois eventos extremos são raros
            if y.value_counts().get('MUITO_BAIXO', 0) / len(y) > 0.9:
                logger.warning("Mais de 90% dos dados são MUITO_BAIXO - isso é normal com limiares oficiais")
                logger.info("Considera-se ajustar pesos das classes ou usar SMOTE para balanceamento")
            
            # Split treino/teste
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.3, random_state=42, stratify=y
            )
            
            # Normalização
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Treinamento
            self.model = RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                min_samples_split=10,
                min_samples_leaf=5,
                class_weight='balanced',
                random_state=42,
                n_jobs=-1
            )
            
            logger.info("Treinando modelo...")
            self.model.fit(X_train_scaled, y_train)
            
            # Avaliação
            y_pred = self.model.predict(X_test_scaled)
            
            # Cross-validation
            cv_scores = cross_val_score(
                self.model, X_train_scaled, y_train, cv=5, scoring='accuracy'
            )
            
            logger.info(f"Acurácia CV: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
            logger.info("Relatório de classificação:")
            logger.info(f"\n{classification_report(y_test, y_pred)}")
            
            # Importância das features
            feature_importance = pd.DataFrame({
                'feature': feature_names,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            logger.info("Importância das features:")
            for _, row in feature_importance.head(10).iterrows():
                logger.info(f"  {row['feature']}: {row['importance']:.3f}")
            
            # Salva modelo
            self.feature_names = feature_names
            self._save_model()
            
            logger.info("Modelo treinado e salvo com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"Erro no treinamento: {e}")
            return False
    
    def load_model(self):
        """Carrega modelo existente"""
        try:
            if not os.path.exists(self.model_path):
                logger.warning("Modelo não encontrado")
                return False
            
            model_data = joblib.load(self.model_path)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            
            logger.info("Modelo carregado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao carregar modelo: {e}")
            return False
    
    def _save_model(self):
        """Salva modelo, scaler e metadados"""
        try:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names,
                'created_at': pd.Timestamp.now(),
                'version': '1.0'
            }
            
            joblib.dump(model_data, self.model_path)
            logger.info(f"Modelo salvo em: {self.model_path}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar modelo: {e}")
    
    def predict(self, dados):
        """Faz predição para novos dados"""
        try:
            if not self.model or not self.scaler:
                logger.error("Modelo não carregado")
                return None
            
            # Prepara features
            if isinstance(dados, dict):
                df = pd.DataFrame([dados])
            else:
                df = dados.copy()
            
            # Garante que todas as features necessárias existem
            for feature in self.feature_names:
                if feature not in df.columns:
                    df[feature] = 0
            
            # Seleciona apenas features do modelo
            X = df[self.feature_names]
            
            # Normaliza
            X_scaled = self.scaler.transform(X)
            
            # Predição
            prediction = self.model.predict(X_scaled)
            probabilities = self.model.predict_proba(X_scaled)
            
            # Retorna resultado
            if len(prediction) == 1:
                return {
                    'prediction': prediction[0],
                    'confidence': probabilities[0].max(),
                    'probabilities': dict(zip(self.model.classes_, probabilities[0]))
                }
            else:
                return {
                    'predictions': prediction,
                    'probabilities': probabilities
                }
                
        except Exception as e:
            logger.error(f"Erro na predição: {e}")
            return None
    
    def evaluate_model(self):
        """Avalia modelo com dados recentes"""
        try:
            if not self.model:
                logger.error("Modelo não carregado")
                return None
            
            # Busca dados recentes para avaliação
            dados = WeatherData.fetch_historical(days=30)
            
            if dados.empty:
                logger.warning("Sem dados para avaliação")
                return None
            
            # Processamento
            dados = self.processor.calculate_accumulated(dados)
            dados = self.processor.create_labels_for_training(dados)
            
            X, _ = self.processor.prepare_features_for_ml(dados)
            y_true = dados['alerta']
            
            # Predição
            result = self.predict(X)
            if not result:
                return None
            
            y_pred = result['predictions']
            
            # Métricas
            accuracy = (y_true == y_pred).mean()
            
            logger.info(f"Avaliação do modelo (últimos 30 dias):")
            logger.info(f"Acurácia: {accuracy:.3f}")
            logger.info(f"Total de predições: {len(y_pred)}")
            
            return {
                'accuracy': accuracy,
                'total_predictions': len(y_pred),
                'classification_report': classification_report(y_true, y_pred, output_dict=True)
            }
            
        except Exception as e:
            logger.error(f"Erro na avaliação: {e}")
            return None