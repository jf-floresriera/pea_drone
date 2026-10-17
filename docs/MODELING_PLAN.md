# Plan de modelado (Machine Learning / Deep Learning)

## 1. ¿Para qué entrenar modelos?
El objetivo práctico es que el mejorador **decida antes y con menos trabajo de campo**. Las preguntas son:

| # | Pregunta | Variable objetivo | Uso en mejoramiento |
|---|---|---|---|
| P1 | ¿Se puede predecir el rendimiento de una línea antes de cosechar? | `seedyield` (kg/ha) por parcela y BLUE por genotipo | Descartar líneas antes de cosecha; priorizar ensayos |
| P2 | ¿El dron estima la fenología? | `fiftyflowr`, `physmatur` (Pullman) | Reemplazar notas visuales diarias de floración y madurez |
| P3 | ¿El dron estima la arquitectura? | `canopyht`, `vinelength`, `podht` (Pullman) | Altura de vaina para cosecha mecanizada; acame |
| P4 | ¿Los modelos se transfieren a un ambiente nuevo? | P1-P3 con validación entre sitio-año | Usar un modelo entrenado en 2017-2018 en 2019 sin recalibrar |
| P5 | ¿Qué rasgos y qué momento del ciclo importan? | Importancia de variables por fecha y grados-día | Planificar cuántos vuelos y cuándo |

Zhang et al. (2021) respondieron P1-P2 **dentro de cada ambiente** (normalizando por sitio-año). El aporte
nuevo es P4 (transferencia), P5 (momento óptimo) y la comparación justa entre modelos simples y complejos.

## 2. Unidades y tamaño de muestra
- **Unidad de observación:** parcela (≈1160 de arveja con ≥3 fechas; ≈400 de garbanzo).
- **Unidad de decisión:** genotipo dentro de ambiente (media o BLUE de 3 repeticiones).
- **Entradas:** rasgos por parcela y fecha (Fase 3), alineados por grados-día; recortes de imagen por parcela (DL).
- Con n ≈ 10³ parcelas, los modelos de imagen profundos tienen riesgo alto de sobreajuste. Por eso se priorizan
  rasgos espectrales y temporales y se usa DL con preentrenamiento y aumentación como comparación, no como punto de partida.

## 3. Modelos
| Familia | Modelos | Justificación |
|---|---|---|
| Lineal regularizado | **LASSO** (réplica exacta de Zhang), Elastic Net, PLSR | Línea base interpretable; PLSR maneja la colinealidad de índices |
| Ensambles de árboles | Random Forest (como Marzougui et al. 2023), XGBoost | No linealidades e interacciones fecha × índice |
| Temporal | Parámetros de curva + XGBoost; 1D-CNN/TempCNN y LSTM sobre series interpoladas en grados-día | Aprovechar la dinámica del dosel, no fechas aisladas |
| Imagen | CNN (ResNet-18 de 5 canales) sobre recortes multitemporales de parcela; preentrenamiento autosupervisado con recortes sin etiqueta | Textura y estructura que los índices medios no capturan |

## 4. Validación (de la más optimista a la más exigente)
1. **CV-parcela:** k-fold aleatorio por parcela (comparable con Zhang 2021). *Optimista:* las repeticiones del mismo genotipo caen en entrenamiento y prueba.
2. **CV-genotipo:** `GroupKFold` por genotipo; todas las repeticiones salen juntas (como Marzougui et al. 2023).
3. **CV-ambiente:** se deja fuera un sitio-año completo (transferencia, P4).
4. **CV-temporal:** entrenar con 2017-2018 y probar en 2019.

Reglas contra la fuga de información:
- La normalización y la selección de rasgos se ajustan solo con entrenamiento (pipelines de scikit-learn).
- Los hiperparámetros se eligen con CV anidada.
- La calibración radiométrica no usa el rendimiento.

## 5. Métricas
- **Regresión:** R², RMSE, rRMSE (%), sesgo y ρ de Spearman (el orden importa más que el valor en mejoramiento).
- **Selección:** coincidencia del 20 % superior entre la predicción y lo observado.
- **Incertidumbre:** media ± DE sobre repeticiones de la CV.
- **Costo:** tiempo de entrenamiento e inferencia y emisiones de CO₂eq (CodeCarbon).

## 6. Interpretabilidad
- Importancia por permutación y SHAP por rasgo, fecha y grados-día.
- Respuesta a P5: ¿qué vuelo aporta más? Se compara contra lo reportado (área de dosel y NDRE en Zhang 2021;
  GNDVI y TVI en Marzougui 2023).

## 7. Software
Python (scikit-learn, xgboost, PyTorch) y R (SpATS para los modelos mixtos espaciales). Semillas fijas,
versiones en `requirements.txt` y resultados en `outputs/15_models/`.
