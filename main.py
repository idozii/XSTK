import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Input
from tensorflow.keras.optimizers import Adam
from keras.callbacks import EarlyStopping
from keras.layers import Dropout, BatchNormalization
from sklearn.impute import SimpleImputer

sns.set_style('whitegrid')
sns.set_palette('colorblind')

#* Load the data
avghouseholdsize_data = pd.read_csv('data/avg-household-size.csv')
cancereg_data = pd.read_csv('data/cancer_reg.csv')

#! Filter and clean the data
numeric_cols = cancereg_data.select_dtypes(include=['float64', 'int64']).columns.tolist()
if numeric_cols:
    numeric_imputer = SimpleImputer(strategy='median')
    cancereg_data[numeric_cols] = numeric_imputer.fit_transform(cancereg_data[numeric_cols])

object_cols = cancereg_data.select_dtypes(include=['object']).columns.tolist()
if object_cols:
    cat_imputer = SimpleImputer(strategy='most_frequent')
    cancereg_data[object_cols] = cat_imputer.fit_transform(cancereg_data[object_cols])

#* Merge the data
merged_data = pd.merge(avghouseholdsize_data, cancereg_data, on='geography', how='inner')
all_features = numeric_cols + object_cols
if 'target_deathrate' in all_features:
    all_features.remove('target_deathrate')
    
#! Prepare the data for modeling using Random Forest
X = merged_data[all_features]
if object_cols:
    X = pd.get_dummies(X, columns=object_cols, drop_first=True)
y = merged_data['target_deathrate']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

rf_for_selection = RandomForestRegressor(random_state=42)
rf_for_selection.fit(X, y)
feature_importance = pd.DataFrame({
    'Feature': X.columns,
    'Importance': rf_for_selection.feature_importances_
}).sort_values('Importance', ascending=False)
top_features = feature_importance.head(20)['Feature']

#! Neural Network
scaler = StandardScaler()
X_train_top = X_train[top_features]
X_test_top = X_test[top_features]
X_train_top_scaled = scaler.fit_transform(X_train_top)
X_test_top_scaled = scaler.transform(X_test_top)

early_stopping = EarlyStopping(
    min_delta=0.001, 
    patience=20, 
    restore_best_weights=True,     
)
nn_model = Sequential()
nn_model.add(Input(shape=(X_train_top_scaled.shape[1],)))
nn_model.add(Dense(64, activation='relu'))
nn_model.add(BatchNormalization())
nn_model.add(Dropout(0.2))
nn_model.add(Dense(32, activation='relu'))
nn_model.add(BatchNormalization())
nn_model.add(Dropout(0.2))
nn_model.add(Dense(16, activation='relu'))
nn_model.add(BatchNormalization())
nn_model.add(Dropout(0.2))
nn_model.add(Dense(1))
nn_model.compile(
    optimizer=Adam(learning_rate=0.001), 
    loss='mean_squared_error',
)

history = nn_model.fit(
    X_train_top_scaled, y_train,
    validation_data=(X_test_top_scaled, y_test),
    batch_size=32,
    epochs=1000,
    callbacks=[early_stopping],
    verbose=1,
)

#* Plot training history
history_df = pd.DataFrame(history.history)
plt.figure(figsize=(10, 6))
plt.plot(history_df['loss'], label='Training Loss')
plt.plot(history_df['val_loss'], label='Validation Loss')
plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.legend()
plt.title('Training and Validation Loss Over Epochs')
plt.show()

#* Evaluate the model
y_pred_nn = nn_model.predict(X_test_top_scaled)
mae_nn = mean_absolute_error(y_test, y_pred_nn)
mse_nn = mean_squared_error(y_test, y_pred_nn)
r2_nn = r2_score(y_test, y_pred_nn)

print("Neural Network Regressor")
print(f'Mean Absolute Error: {mae_nn}')
print(f'Mean Squared Error: {mse_nn}')
print(f'R2 Score: {r2_nn}')

error_df = pd.DataFrame({
    'Actual': y_test,
    'Predicted': y_pred_nn.flatten(),
    'Error': abs(y_test - y_pred_nn.flatten())
})
print("Best Predictions")
print(error_df.sort_values('Error').head(5))
print("Worst Predictions")
print(error_df.sort_values('Error', ascending=False).head(5))