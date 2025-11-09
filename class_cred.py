import lightgbm as lgb
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib

def train_credit_model():
    print("Entrenamiento lightgbm")
    
    try:
        data = pd.read_csv('data/agricultores_sinteticos.csv')
    except FileNotFoundError:
        print("No hay datos'")
        return

    print(f"Datos cargados: {data.shape[0]} filas, {data.shape[1]} columnas")

    y = data['Score_Categorico'].astype('category').cat.codes
    
    score_categories = dict(enumerate(data['Score_Categorico'].astype('category').cat.categories))
    
    categorical_features = [
        'Ubicacion_Estado',
        'Tipo_Negocio',
        'Tamano_Operacion',
        'Frecuencia_Ingresos',
        'Escolaridad'
    ]
    
    for col in categorical_features:
        data[col] = data[col].astype('category').cat.codes
    
    X = data.drop(columns=['Score_Categorico'])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    clf = lgb.LGBMClassifier(
        objective='multiclass',
        num_class=len(score_categories),
        random_state=42,
        n_jobs=-1
    )
    
    clf.fit(
        X_train, 
        y_train,
        categorical_feature=categorical_features,
        eval_set=[(X_test, y_test)],
        eval_metric='multi_logloss'
    )
    
    # Entrenamiento listo

    y_pred = clf.predict(X_test)
    
    # Resultados de la accuracy
    
    accuracy = accuracy_score(y_test, y_pred)
    print(f'LightGBM Model accuracy score: {accuracy:.4f}')

    print(f'Training set score: {clf.score(X_train, y_train):.4f}')
    print(f'Test set score: {clf.score(X_test, y_test):.4f}')

    target_names = [score_categories[i] for i in sorted(score_categories)]
    print("\nReporte de Clasificación (qué tan bien predice cada score):")
    print(classification_report(y_test, y_pred, target_names=target_names))
    
    model_filename = 'credit_scoring_model.pkl'
    joblib.dump(clf, model_filename)
    print(f"\n Modelo de scoring guardado en: {model_filename}")

if __name__ == "__main__":
    train_credit_model()