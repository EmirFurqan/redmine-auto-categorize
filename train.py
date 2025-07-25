import os
from dotenv import load_dotenv
import pandas as pd
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
import torch
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import pickle

# .env dosyasını yükle
load_dotenv()

# Token'ı environment değişkeninden al
token = os.getenv("HF_TOKEN")
if token is None:
    raise ValueError("Hugging Face token is not set in environment variables (HF_TOKEN).")

# 1. CSV'den oku
df = pd.read_csv("veri.csv")

# 2. Label encode et
le = LabelEncoder()
df['label_enc'] = le.fit_transform(df['label'])

# 3. Train/test ayır (stratify ile dengeli sınıflar)
train_df, val_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df['label_enc'])

# 4. Huggingface Dataset formatına dönüştür
train_df_clean = train_df[['text', 'label_enc']].rename(columns={'label_enc': 'labels'})
val_df_clean = val_df[['text', 'label_enc']].rename(columns={'label_enc': 'labels'})

train_dataset = Dataset.from_pandas(train_df_clean)
val_dataset = Dataset.from_pandas(val_df_clean)

tokenizer = AutoTokenizer.from_pretrained(
    "xlm-roberta-base",
    token=token
)

def tokenize(batch):
    return tokenizer(batch["text"], padding=True, truncation=True, max_length=256)

train_dataset = train_dataset.map(tokenize, batched=True)
val_dataset = val_dataset.map(tokenize, batched=True)

train_dataset = train_dataset.remove_columns(['text'])
val_dataset = val_dataset.remove_columns(['text'])

train_dataset = train_dataset.with_format("torch")
val_dataset = val_dataset.with_format("torch")

num_labels = len(le.classes_)

model = AutoModelForSequenceClassification.from_pretrained(
    "xlm-roberta-base",
    token=token,
    num_labels=num_labels
)

training_args = TrainingArguments(
    output_dir="./results",
    eval_strategy="epoch",
    save_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
    save_total_limit=1,
    load_best_model_at_end=True,
    metric_for_best_model="accuracy",
    greater_is_better=True,
    logging_dir='./logs',
    logging_steps=10,
    report_to="none",
    dataloader_pin_memory=False,
    use_cpu=False
)

def compute_metrics(pred):
    labels = pred.label_ids
    preds = np.argmax(pred.predictions, axis=1)
    precision, recall, f1, _ = precision_recall_fscore_support(labels, preds, average='weighted')
    acc = accuracy_score(labels, preds)
    return {
        'accuracy': acc,
        'f1': f1,
        'precision': precision,
        'recall': recall
    }

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    compute_metrics=compute_metrics,
)

trainer.train()

model.save_pretrained("./trained_model")
tokenizer.save_pretrained("./trained_model")

with open("./trained_model/label_encoder.pkl", "wb") as f:
    pickle.dump(le, f)

def predict(texts):
    model.cpu()
    tokens = tokenizer(texts, padding=True, truncation=True, max_length=256, return_tensors="pt")
    tokens = {k: v.cpu() for k, v in tokens.items()}
    with torch.no_grad():
        outputs = model(**tokens)
    preds = torch.argmax(outputs.logits, dim=1).cpu().numpy()
    return le.inverse_transform(preds)

print("Model eğitimi tamamlandı!")
print("Örnek tahmin:", predict(["Yeni ekip üyesi için sistem erişim hazırlığı"]))


