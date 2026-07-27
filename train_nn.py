"""
train_nn.py — Antrenare retea neuronala cu validare incrucisata (k-fold) + SHAP.

Reteaua: MLP — straturi dense. Pentru date tabulare, arhitectura corecta.

k-fold: antreneaza de 5 ori, fiecare data testand pe o portiune diferita
pe care reteaua NU a vazut-o. Asa stim daca rezultatul e stabil.
"""

import os
import warnings
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_class_weight

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import shap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

np.random.seed(42)
tf.random.set_seed(42)

DATASET_PATH = "data/dataset_accumulated.csv"
TARGET_COL = "recommendation"
N_FOLDS = 5


def build_model(n_features, n_classes):
    """Construieste un MLP nou. In functie ca fiecare fold sa aiba o
    retea PROASPATA (altfel fold 2 ar continua antrenarea fold 1)."""
    model = keras.Sequential([
        keras.Input(shape=(n_features,)),
        layers.Dense(64, activation="relu"),
        layers.BatchNormalization(),
        layers.Dropout(0.3),
        layers.Dense(32, activation="relu"),
        layers.BatchNormalization(),
        layers.Dropout(0.3),
        layers.Dense(16, activation="relu"),
        layers.Dropout(0.2),
        layers.Dense(n_classes, activation="softmax"),
    ])
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


# === 1. INCARCARE DATE ===
print("=" * 60)
print("1. INCARCARE DATE")
print("=" * 60)

df = pd.read_csv(DATASET_PATH)
print(f"Dataset: {df.shape[0]} pacienti, {df.shape[1]} coloane")

EXCLUDE = {"patient_id", "recommendation", "all_specialists", "all_diseases"}
FEATURE_COLS = [c for c in df.columns
                if c not in EXCLUDE and pd.api.types.is_numeric_dtype(df[c])]
print(f"Feature-uri folosite ({len(FEATURE_COLS)}): {FEATURE_COLS}")

X = df[FEATURE_COLS].copy()
y = df[TARGET_COL].copy()
print(f"\nDistributie clase:")
print(y.value_counts().to_string())


# === 2. PREPROCESARE ===
print("\n" + "=" * 60)
print("2. PREPROCESARE")
print("=" * 60)

imputer = SimpleImputer(strategy="median")
X_imputed = imputer.fit_transform(X)
print("✓ Valori lipsa completate cu mediana")

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_imputed)
print("✓ Feature-uri scalate (StandardScaler)")

label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)
n_classes = len(label_encoder.classes_)
print(f"✓ Etichete codificate: {list(label_encoder.classes_)}")


# === 3. VALIDARE INCRUCISATA K-FOLD ===
print("\n" + "=" * 60)
print(f"3. VALIDARE INCRUCISATA ({N_FOLDS}-FOLD)")
print("=" * 60)
print(f"Antrenam reteaua de {N_FOLDS} ori, fiecare data testand pe o")
print("portiune diferita pe care NU a vazut-o la antrenare.\n")

skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=42)
fold_accuracies = []

for fold, (train_idx, test_idx) in enumerate(skf.split(X_scaled, y_encoded), 1):
    X_tr, X_te = X_scaled[train_idx], X_scaled[test_idx]
    y_tr, y_te = y_encoded[train_idx], y_encoded[test_idx]

    cw_arr = compute_class_weight("balanced", classes=np.unique(y_tr), y=y_tr)
    cw = {i: w for i, w in enumerate(cw_arr)}

    model = build_model(X_tr.shape[1], n_classes)
    early_stop = keras.callbacks.EarlyStopping(
        monitor="val_loss", patience=15, restore_best_weights=True)
    model.fit(X_tr, y_tr, validation_split=0.2, epochs=200, batch_size=32,
              class_weight=cw, callbacks=[early_stop], verbose=0)

    _, acc = model.evaluate(X_te, y_te, verbose=0)
    fold_accuracies.append(acc)
    print(f"  Fold {fold}/{N_FOLDS}:  acuratete = {acc:.3f}  "
          f"({len(train_idx)} antrenare / {len(test_idx)} testare)")

mean_acc = np.mean(fold_accuracies)
std_acc = np.std(fold_accuracies)
print(f"\n  {'-' * 40}")
print(f"  ACURATETE MEDIE: {mean_acc:.3f}  (±{std_acc:.3f})")
print(f"  {'-' * 40}")
if std_acc < 0.03:
    print("  ✓ Deviatie mica -> rezultat STABIL, de incredere")
else:
    print("  ~ Deviatie mai mare -> rezultatul variaza intre fold-uri")


# === 4. MODEL FINAL ===
print("\n" + "=" * 60)
print("4. MODEL FINAL (antrenat pe 80%, evaluat pe 20% held-out)")
print("=" * 60)

X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded)

cw_arr = compute_class_weight("balanced", classes=np.unique(y_train), y=y_train)
class_weights = {i: w for i, w in enumerate(cw_arr)}

model = build_model(X_train.shape[1], n_classes)
model.summary()

early_stop = keras.callbacks.EarlyStopping(
    monitor="val_loss", patience=30, restore_best_weights=True)

print("\nAntrenare model final...")
history = model.fit(
    X_train, y_train, validation_split=0.2, epochs=200, batch_size=32,
    class_weight=class_weights, callbacks=[early_stop], verbose=2)


# === 5. EVALUARE ===
print("\n" + "=" * 60)
print("5. EVALUARE PE TEST")
print("=" * 60)

test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
print(f"Acuratete model final pe test: {test_acc:.3f}")

y_pred = model.predict(X_test, verbose=0).argmax(axis=1)

print("\nClassification report:")
print(classification_report(y_test, y_pred,
                            target_names=label_encoder.classes_))

print("Confusion matrix (rind=adevarat, coloana=prezis):")
cm = confusion_matrix(y_test, y_pred)
print(pd.DataFrame(cm, index=label_encoder.classes_,
                   columns=label_encoder.classes_).to_string())

# Matrice de confuzie ca imagine
fig, ax = plt.subplots(figsize=(8, 7))
im = ax.imshow(cm, cmap="Blues")
labels = list(label_encoder.classes_)
ax.set_xticks(range(len(labels)))
ax.set_yticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=45, ha="right")
ax.set_yticklabels(labels)
ax.set_xlabel("Clasa prezisa")
ax.set_ylabel("Clasa adevarata")
ax.set_title(f"Matrice de confuzie — acuratete {test_acc:.1%}")
thresh = cm.max() / 2
for i in range(len(labels)):
    for j in range(len(labels)):
        ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                color="white" if cm[i, j] > thresh else "black")
plt.colorbar(im)
plt.tight_layout()
plt.savefig("confusion_matrix.png", dpi=120, bbox_inches="tight")
plt.close()
print("\n✓ Salvat confusion_matrix.png")


# === 6. SHAP ===
print("\n" + "=" * 60)
print("6. SHAP — ce analize conteaza pentru fiecare pacient")
print("=" * 60)

background = X_train[np.random.choice(X_train.shape[0],
                                       min(100, X_train.shape[0]),
                                       replace=False)]
explainer = shap.DeepExplainer(model, background)
shap_values = explainer.shap_values(X_test)
print(f"✓ SHAP values calculate pentru {X_test.shape[0]} pacienti")


def explain_patient(idx):
    pred_class = y_pred[idx]
    pred_name = label_encoder.classes_[pred_class]
    sv = shap_values
    if isinstance(sv, list):
        patient_shap = sv[pred_class][idx]
    else:
        patient_shap = sv[idx, :, pred_class]
    contributii = sorted(zip(FEATURE_COLS, patient_shap),
                         key=lambda x: abs(x[1]), reverse=True)
    print(f"\nPacient #{idx} — prezis: {pred_name}")
    print("Top 5 analize care au contat:")
    for feat, val in contributii[:5]:
        directie = "creste" if val > 0 else "scade"
        print(f"  {feat:20} SHAP={val:+.3f}  ({directie} sansa {pred_name})")


for i in range(min(3, X_test.shape[0])):
    explain_patient(i)

print("\nGenerare grafic SHAP global -> shap_summary.png")
try:
    shap.summary_plot(shap_values, X_test, feature_names=FEATURE_COLS,
                      class_names=list(label_encoder.classes_), show=False)
    plt.tight_layout()
    plt.savefig("shap_summary.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("✓ Salvat shap_summary.png")
except Exception as e:
    print(f"⚠ Nu s-a putut genera graficul: {e}")


# === 7. SALVARE ===
print("\n" + "=" * 60)
print("7. SALVARE")
print("=" * 60)

os.makedirs("models", exist_ok=True)
model.save("models/specialist_nn.keras")
joblib.dump({
    "scaler": scaler,
    "imputer": imputer,
    "label_encoder": label_encoder,
    "feature_names": FEATURE_COLS,
    "cv_accuracy_mean": float(mean_acc),
    "cv_accuracy_std": float(std_acc),
}, "models/nn_preprocessing.pkl")

print("✓ Model salvat -> models/specialist_nn.keras")
print("✓ Preprocesare salvata -> models/nn_preprocessing.pkl")
print()
print("=" * 60)
print("REZUMAT")
print("=" * 60)
print(f"  Validare {N_FOLDS}-fold: {mean_acc:.3f} (±{std_acc:.3f})")
print(f"  Model final pe test:  {test_acc:.3f}")
print("  Fisiere: confusion_matrix.png, shap_summary.png")
print("GATA.")