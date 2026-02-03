# Model Evaluation Report

## Summary

- Total models evaluated: 12
- Number of classes: 3
- Classes: MSS/TMB-H, MSS/TMB-L, MSI-H

## Best Model

**xgboost_combined**

- F1: 0.6403
- Balanced Accuracy: 0.7145
- Weighted F1: 0.6990
- ROC-AUC (OvR): 0.8191

### Per-Class Performance

| Class | F1 | Precision | Recall | ROC-AUC |
|-------|----|-----------|---------|---------|
| MSS/TMB-H | 0.5882 | 0.4545 | 0.8333 | 0.9553 |
| MSS/TMB-L | 0.7899 | 0.8545 | 0.7344 | 0.8361 |
| MSI-H | 0.5429 | 0.5135 | 0.5758 | 0.6658 |

## Top 5 Models

| Rank | Model | F1 | Balanced Acc | ROC-AUC |
|------|-------|----------|--------------|----------|
| 11 | xgboost_combined | 0.6403 | 0.7145 | 0.8191 |
| 5 | random_forest_class_weight | 0.6161 | 0.6602 | 0.8305 |
| 3 | xgboost_class_weight | 0.6129 | 0.7050 | 0.8358 |
| 8 | xgboost_smote | 0.6074 | 0.6891 | 0.8103 |
| 1 | random_forest_smote | 0.5857 | 0.6086 | 0.7965 |

## Model Insights

### Performance by Imbalance Strategy

- **combined**: 0.5761
- **smote**: 0.5578
- **weight**: 0.5539

### Performance by Model Type

- **xgboost**: 0.6239
- **random_forest_class**: 0.6161
- **xgboost_class**: 0.6129
- **random_forest**: 0.5857
- **mlp**: 0.5429
- **logistic_regression_class**: 0.5334
- **logistic_regression**: 0.5153
- **mlp_class**: 0.4533
