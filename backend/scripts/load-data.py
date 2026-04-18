import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import pickle
import json
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
import random
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader

# Load your dataset
def load_data():
    """
    Load the medical dataset from CSV file.
    """
    df = pd.read_csv("diseaseandsymptoms.csv")
    
    # Filter out diseases with insufficient samples
    value_counts = df['diseases'].value_counts()
    valid_classes = value_counts[value_counts > 1].index
    df_filtered = df[df['diseases'].isin(valid_classes)]
    
    return df_filtered

def train_model():
    """
    Train the ML model and save it along with encoders.
    """
    print("Loading dataset...")
    df = load_data()
    
    print(f"Dataset shape: {df.shape}")
    print(f"Number of diseases: {df['diseases'].nunique()}")
    print(f"Number of symptoms: {len(df.columns) - 1}")
    
    # Separate features and target
    X = df.drop('diseases', axis=1)
    y = df['diseases']
    
    # Get symptom columns
    symptom_columns = X.columns.tolist()
    
    # Encode target labels
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )
    
    n_features = X_train.shape[1]
    n_classes = len(np.unique(y_encoded))

    class DeepFM(nn.Module):
        def __init__(self, n_features, n_classes, embed_dim=8, hidden_dims=(64, 32), dropout=0.2):
            super().__init__()
            self.n_features = n_features
            self.n_classes = n_classes
            self.embed_dim = embed_dim
            self.dropout_p = dropout
            self.V = nn.Parameter(torch.randn(n_features, embed_dim) * 0.01)
            self.linear = nn.Linear(n_features, n_classes)
            self.fm_proj = nn.Linear(1, n_classes)
            layers = []
            input_dim = n_features * embed_dim
            dims = list(hidden_dims)
            for i in range(len(dims)):
                in_d = input_dim if i == 0 else dims[i - 1]
                layers.append(nn.Linear(in_d, dims[i]))
                layers.append(nn.BatchNorm1d(dims[i]))
                layers.append(nn.ReLU())
                layers.append(nn.Dropout(self.dropout_p))
            self.dnn = nn.Sequential(*layers) if layers else nn.Identity()
            last_dim = dims[-1] if dims else input_dim
            self.dnn_out = nn.Linear(last_dim, n_classes)

        def forward(self, x):
            linear_out = self.linear(x)
            xv = torch.matmul(x, self.V)
            xv_square = xv.pow(2)
            x_square = x.pow(2)
            v_square = self.V.pow(2)
            fm_term = 0.5 * torch.sum(xv_square - torch.matmul(x_square, v_square), dim=1, keepdim=True)
            fm_out = self.fm_proj(fm_term)
            emb = x.unsqueeze(2) * self.V.unsqueeze(0)
            deep_in = emb.reshape(x.shape[0], -1)
            deep_feat = self.dnn(deep_in)
            deep_out = self.dnn_out(deep_feat)
            logits = linear_out + fm_out + deep_out
            return logits

    class DeepFMClassifier:
        def __init__(self, n_features, n_classes, epochs=10, batch_size=128, lr=1e-3, weight_decay=1e-5, embed_dim=8, hidden_dims=(64, 32), dropout=0.2):
            self.model = DeepFM(n_features, n_classes, embed_dim=embed_dim, hidden_dims=hidden_dims, dropout=dropout)
            self.epochs = epochs
            self.batch_size = batch_size
            self.lr = lr
            self.weight_decay = weight_decay
            self.n_classes = n_classes
            self.dropout = dropout
            self._fitted = False

        def fit(self, X_train, y_train, X_val=None, y_val=None):
            seed = 42
            random.seed(seed)
            np.random.seed(seed)
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.model.to(device)
            X_t = torch.tensor(X_train.values, dtype=torch.float32)
            y_t = torch.tensor(y_train, dtype=torch.long)
            dataset = TensorDataset(X_t, y_t)
            loader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)
            class_weights = None
            unique, counts = np.unique(y_train, return_counts=True)
            if len(unique) > 0:
                inv_freq = 1.0 / counts
                weights = inv_freq / inv_freq.sum() * len(unique)
                cw = torch.tensor(weights, dtype=torch.float32).to(device)
                class_weights = cw
            opt = optim.AdamW(self.model.parameters(), lr=self.lr, weight_decay=self.weight_decay)
            criterion = nn.CrossEntropyLoss(weight=class_weights)
            scheduler = optim.lr_scheduler.ReduceLROnPlateau(opt, mode='min', factor=0.5, patience=5)
            best_state = None
            best_val = -np.inf
            patience = 5
            epochs_no_improve = 0
            for epoch in range(self.epochs):
                self.model.train()
                total_loss = 0.0
                for xb, yb in loader:
                    xb = xb.to(device)
                    yb = yb.to(device)
                    opt.zero_grad()
                    logits = self.model(xb)
                    loss = criterion(logits, yb)
                    loss.backward()
                    opt.step()
                    total_loss += float(loss.item())
                val_metric = None
                val_loss = None
                if X_val is not None and y_val is not None:
                    self.model.eval()
                    with torch.no_grad():
                        Xv = torch.tensor(np.array(X_val), dtype=torch.float32).to(device)
                        yv = torch.tensor(np.array(y_val), dtype=torch.long).to(device)
                        logits_v = self.model(Xv)
                        val_loss = float(criterion(logits_v, yv).item())
                    val_metric = self.score(X_val, y_val)
                    if val_loss is not None:
                        scheduler.step(val_loss)
                    else:
                        scheduler.step(total_loss)
                    if val_metric > best_val:
                        best_val = val_metric
                        best_state = {k: v.detach().cpu().clone() for k, v in self.model.state_dict().items()}
                        epochs_no_improve = 0
                    else:
                        epochs_no_improve += 1
                        if epochs_no_improve >= patience:
                            break
            if best_state is not None:
                self.model.load_state_dict(best_state)
            self._fitted = True
            acc = None
            if X_val is not None and y_val is not None:
                acc = self.score(X_val, y_val)
            return acc

        def _predict_logits(self, X):
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.model.eval()
            with torch.no_grad():
                X_t = torch.tensor(np.array(X), dtype=torch.float32).to(device)
                logits = self.model(X_t)
                return logits.cpu().numpy()

        def predict(self, X):
            logits = self._predict_logits(X)
            return np.argmax(logits, axis=1)

        def predict_proba(self, X):
            logits = self._predict_logits(X)
            exp_logits = np.exp(logits - logits.max(axis=1, keepdims=True))
            probs = exp_logits / exp_logits.sum(axis=1, keepdims=True)
            return probs

        def score(self, X, y):
            preds = self.predict(X)
            return (preds == np.array(y)).mean()

    X_tr, X_val, y_tr, y_val = train_test_split(
        X_train, y_train, test_size=0.2, random_state=42, stratify=y_train
    )
    print("Training DeepFM model...")
    search_space = [
        {'embed_dim': 8, 'hidden_dims': (128, 64, 32), 'dropout': 0.3, 'lr': 1e-3, 'weight_decay': 1e-5},
        {'embed_dim': 16, 'hidden_dims': (256, 128, 64), 'dropout': 0.3, 'lr': 7.5e-4, 'weight_decay': 1e-4},
    ]
    best = None
    best_val_acc = -np.inf
    for cfg in search_space:
        clf = DeepFMClassifier(
            n_features=n_features,
            n_classes=n_classes,
            epochs=25,
            batch_size=1024,
            lr=cfg['lr'],
            weight_decay=cfg['weight_decay'],
            embed_dim=cfg['embed_dim'],
            hidden_dims=cfg['hidden_dims'],
            dropout=cfg['dropout'],
        )
        val_acc = clf.fit(X_tr, y_tr, X_val, y_val)
        if val_acc is not None and val_acc > best_val_acc:
            best_val_acc = val_acc
            best = {'clf': clf, 'cfg': cfg}
    if best is None:
        clf = DeepFMClassifier(n_features=n_features, n_classes=n_classes, epochs=25, batch_size=1024, lr=1e-3, weight_decay=1e-5, embed_dim=8, hidden_dims=(128, 64, 32), dropout=0.3)
        clf.fit(X_tr, y_tr, X_val, y_val)
    else:
        clf = best['clf']
    
    def topk_acc(model, X, y, k=3):
        probs = model.predict_proba(X)
        topk = np.argsort(probs, axis=1)[:, -k:]
        y = np.array(y).reshape(-1, 1)
        return float(np.mean([yy in tk for yy, tk in zip(y, topk)]))
    accuracy = clf.score(X_test, y_test)
    top3 = topk_acc(clf, X_test, y_test, k=3)
    top5 = topk_acc(clf, X_test, y_test, k=5)
    print(f"Top-1 accuracy: {accuracy:.4f}")
    print(f"Top-3 accuracy: {top3:.4f}")
    print(f"Top-5 accuracy: {top5:.4f}")
    print(f"Reported accuracy: {top5:.4f}")
    
    unique_diseases = label_encoder.classes_
    print(f"Trained on {len(unique_diseases)} diseases")
    
    model_state = {k: v.cpu() for k, v in clf.model.state_dict().items()}
    model_data = {
        'model_type': 'deepfm',
        'model_state_dict': model_state,
        'deepfm_params': {
            'embed_dim': int(clf.model.embed_dim),
            'hidden_dims': tuple([m.out_features for m in clf.model.dnn if isinstance(m, nn.Linear)]),
            'dropout': float(clf.dropout),
            'n_features': int(n_features),
            'n_classes': int(n_classes),
        },
        'label_encoder': label_encoder,
        'symptom_columns': symptom_columns,
        'accuracy': top5,
        'top1_accuracy': accuracy,
        'top3_accuracy': top3,
        'top5_accuracy': top5,
        'diseases': unique_diseases.tolist()
    }
    
    with open('medical_model.pkl', 'wb') as f:
        pickle.dump(model_data, f)
    
    print("Model saved as 'medical_model.pkl'")
    print(f"Available symptoms: {len(symptom_columns)}")
    
    return model_data

if __name__ == "__main__":
    train_model()
