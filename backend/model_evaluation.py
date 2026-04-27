import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, roc_curve, auc, precision_score, recall_score
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image
import os

# Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XRAY_DATASET_ROOT = os.path.join(BASE_DIR, "scripts", "xray_dataset")
DATA_CSV = os.path.join(XRAY_DATASET_ROOT, "Data_Entry_2017.csv")
MODEL_PATH = os.path.join(BASE_DIR, "scripts", "disease_model.keras")
IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32

# Load the data
df = pd.read_csv(DATA_CSV)

# Get all unique labels
all_labels = np.unique([item for sublist in df['Finding Labels'].str.split('|') for item in sublist])
label_columns = [label for label in all_labels if label != 'No Finding']

# One-hot encode the labels
for label in label_columns:
    df[label] = df['Finding Labels'].apply(lambda x: 1 if label in x else 0)

# Map image filenames to full paths
image_path_map = {}
for root, dirs, files in os.walk(XRAY_DATASET_ROOT):
    for file in files:
        if file.endswith('.png'):
            image_path_map[file] = os.path.join(root, file)

df['Full Path'] = df['Image Index'].map(image_path_map)
df = df[df['Full Path'].notna()]

# Use the same sampling and splitting as training
target_sample_size = 10000
df = df.sample(n=min(target_sample_size, len(df)), random_state=42)
train_df, test_df = train_test_split(df, test_size=0.3, random_state=42)

print(f"Test samples: {len(test_df)}")

print("Loading model...")
model = tf.keras.models.load_model(MODEL_PATH)

# Create test generator (no shuffle to match predictions with labels)
test_datagen = ImageDataGenerator()
test_generator = test_datagen.flow_from_dataframe(
    dataframe=test_df,
    directory=None,
    x_col="Full Path",
    y_col=label_columns,
    target_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="raw",
    shuffle=False
)

print("Generating predictions...")
y_pred_probs = model.predict(test_generator)
y_true = test_df[label_columns].values

# Convert probabilities to binary predictions (threshold = 0.5)
y_pred_binary = (y_pred_probs > 0.5).astype(int)

print("--- Overall Metrics ---")
accuracy = accuracy_score(y_true, y_pred_binary)
f1_weighted = f1_score(y_true, y_pred_binary, average='weighted')
precision_weighted = precision_score(y_true, y_pred_binary, average='weighted')
recall_weighted = recall_score(y_true, y_pred_binary, average='weighted')

# Calculate Average AUC ROC
auc_roc_weighted = roc_auc_score(y_true, y_pred_probs, average='weighted', multi_class='ovr')
auc_roc_macro = roc_auc_score(y_true, y_pred_probs, average='macro', multi_class='ovr')

print(f"Accuracy: {accuracy:.4f}")
print(f"Precision (Weighted): {precision_weighted:.4f}")
print(f"Recall (Weighted): {recall_weighted:.4f}")
print(f"F1 Score (Weighted): {f1_weighted:.4f}")
print(f"Average AUC ROC (Weighted): {auc_roc_weighted:.4f}")
print(f"Average AUC ROC (Macro): {auc_roc_macro:.4f}")

print("\n--- Per-Label Metrics ---")
print(f"{'Label':<20} | Acc    | Prec   | Rec    | F1     | AUC")
print("-" * 70)
for i, label in enumerate(label_columns):
    l_acc = accuracy_score(y_true[:, i], y_pred_binary[:, i])
    l_prec = precision_score(y_true[:, i], y_pred_binary[:, i], zero_division=0)
    l_rec = recall_score(y_true[:, i], y_pred_binary[:, i], zero_division=0)
    l_f1 = f1_score(y_true[:, i], y_pred_binary[:, i], zero_division=0)
    l_auc = roc_auc_score(y_true[:, i], y_pred_probs[:, i])
    print(f"{label:<20} | {l_acc:.4f} | {l_prec:.4f} | {l_rec:.4f} | {l_f1:.4f} | {l_auc:.4f}")

plt.figure(figsize=(12, 8))

for i, label in enumerate(label_columns):
    fpr, tpr, _ = roc_curve(y_true[:, i], y_pred_probs[:, i])
    roc_auc = auc(fpr, tpr)
    plt.plot(fpr, tpr, label=f'{label} (AUC = {roc_auc:.2f})')

plt.plot([0, 1], [0, 1], 'k--', lw=2)
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate (FPR)')
plt.ylabel('True Positive Rate (TPR)')
plt.title('Receiver Operating Characteristic (ROC) Curves')
plt.legend(loc="lower right", fontsize='small', ncol=2)
plt.grid(alpha=0.3)
plt.show()

def get_labels(binary_vector, label_names):
    labels = [label_names[i] for i, val in enumerate(binary_vector) if val == 1]
    return " | ".join(labels) if labels else "No Finding"

num_samples = 6
indices = np.random.choice(len(test_df), num_samples, replace=False)

plt.figure(figsize=(20, 12))
for i, idx in enumerate(indices):
    img_path = test_df.iloc[idx]['Full Path']
    true_labels = get_labels(y_true[idx], label_columns)
    pred_labels = get_labels(y_pred_binary[idx], label_columns)
    
    # Get top 3 predicted findings for more context
    top_3_indices = np.argsort(y_pred_probs[idx])[-3:][::-1]
    top_3_str = "\n".join([f"{label_columns[j]}: {y_pred_probs[idx][j]:.2f}" for j in top_3_indices])

    plt.subplot(2, 3, i + 1)
    img = Image.open(img_path).convert('RGB')
    plt.imshow(img)
    title_color = 'green' if true_labels == pred_labels else 'red'
    plt.title(f"True: {true_labels}\nPred: {pred_labels}\n\nTop 3 Probabilities:\n{top_3_str}", 
              fontsize=10, color=title_color)
    plt.axis('off')

plt.tight_layout()
plt.show()

