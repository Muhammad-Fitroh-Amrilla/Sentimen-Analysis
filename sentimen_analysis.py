# -*- coding: utf-8 -*-
"""Sentimen Analysis

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1fBK6Mwq2wkjsynVihmxqmVunzuODBC4w
"""

# Install PyTorch dan transformers untuk pre-trained model IndoBert
!pip install torch torchvision
!pip install transformers

#clone untuk menyimpan dataset IndoNLU
!git clone https://github.com/indobenchmark/indonlu

"""<h2> Import Library <h2>

"""

import random
import numpy as np
import pandas as pd
import torch
from torch import optim
import torch.nn.functional as F
from tqdm import tqdm
 
from transformers import BertForSequenceClassification, BertConfig, BertTokenizer
from nltk.tokenize import TweetTokenizer
 
from indonlu.utils.forward_fn import forward_sequence_classification
from indonlu.utils.metrics import document_sentiment_metrics_fn
from indonlu.utils.data_utils import DocumentSentimentDataset, DocumentSentimentDataLoader

"""definisikan fungsi umum sebagai berikut.

* **set_seed** : Mengatur dan menetapkan random seed.
* **count_param** : Menghitung jumlah parameter dalam model
* **get_lr** : Mengatur learning rate
* **metrics_to_string** : Mengonversi metriks ke dalam string
"""

###
# common functions
###
def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    
def count_param(module, trainable=False):
    if trainable:
        return sum(p.numel() for p in module.parameters() if p.requires_grad)
    else:
        return sum(p.numel() for p in module.parameters())
    
def get_lr(optimizer):
    for param_group in optimizer.param_groups:
        return param_group['lr']
 
def metrics_to_string(metric_dict):
    string_list = []
    for key, value in metric_dict.items():
        string_list.append('{}:{:.2f}'.format(key, value))
    return ' '.join(string_list)

# Set random seed
set_seed(11112022)

# Load Tokenizer and Config
tokenizer = BertTokenizer.from_pretrained('indobenchmark/indobert-base-p1')
config = BertConfig.from_pretrained('indobenchmark/indobert-base-p1')
config.num_labels = DocumentSentimentDataset.NUM_LABELS
 
# Instantiate model
model = BertForSequenceClassification.from_pretrained('indobenchmark/indobert-base-p1', config=config)

model

count_param(model)

train_dataset_path = '/content/indonlu/dataset/smsa_doc-sentiment-prosa/train_preprocess.tsv'
valid_dataset_path = '/content/indonlu/dataset/smsa_doc-sentiment-prosa/valid_preprocess.tsv'
test_dataset_path = '/content/indonlu/dataset/smsa_doc-sentiment-prosa/test_preprocess_masked_label.tsv'

# class DocumentSentimentDataset(Dataset):
#     # Static constant variable
#     LABEL2INDEX = {'positive': 0, 'neutral': 1, 'negative': 2} # Map dari label string ke index
#     INDEX2LABEL = {0: 'positive', 1: 'neutral', 2: 'negative'} # Map dari Index ke label string
#     NUM_LABELS = 3 # Jumlah label
   
#     def load_dataset(self, path):
#         df = pd.read_csv(path, sep='\t', header=None) # Baca tsv file dengan pandas
#         df.columns = ['text','sentiment'] # Berikan nama pada kolom tabel
#         df['sentiment'] = df['sentiment'].apply(lambda lab: self.LABEL2INDEX[lab]) # Konversi string label ke index
#         return df
   
#     def __init__(self, dataset_path, tokenizer, *args, **kwargs):
#         self.data = self.load_dataset(dataset_path) # Load tsv file
 
#         # Assign tokenizer, disini kita menggunakan tokenizer subword dari HuggingFace
#         self.tokenizer = tokenizer 
 
#     def __getitem__(self, index):
#         data = self.data.loc[index,:] # Ambil data pada baris tertentu dari tabel
#         text, sentiment = data['text'], data['sentiment'] # Ambil nilai text dan sentiment
#         subwords = self.tokenizer.encode(text) # Tokenisasi text menjadi subword
    
#     # Return numpy array dari subwords dan label
#         return np.array(subwords), np.array(sentiment), data['text']
   
#     def __len__(self):
#         return len(self.data)  # Return panjang dari dataset

# class DocumentSentimentDataLoader(DataLoader):
#     def __init__(self, max_seq_len=512, *args, **kwargs):
#         super(DocumentSentimentDataLoader, self).__init__(*args, **kwargs)
#         self.max_seq_len = max_seq_len # Assign batas maksimum subword
#         self.collate_fn = self._collate_fn # Assign fungsi collate_fn dengan fungsi yang kita definisikan
       
#     def _collate_fn(self, batch):
#         batch_size = len(batch) # Ambil batch size
#         max_seq_len = max(map(lambda x: len(x[0]), batch)) # Cari panjang subword maksimal dari batch 
#         max_seq_len = min(self.max_seq_len, max_seq_len) # Bandingkan dengan batas yang kita tentukan sebelumnya
       
#     # Buat buffer untuk subword, mask, dan sentiment labels, inisialisasikan semuanya dengan 0
#         subword_batch = np.zeros((batch_size, max_seq_len), dtype=np.int64)
#         mask_batch = np.zeros((batch_size, max_seq_len), dtype=np.float32)
#         sentiment_batch = np.zeros((batch_size, 1), dtype=np.int64)
       
#     # Isi semua buffer
#         for i, (subwords, sentiment, raw_seq) in enumerate(batch):
#             subwords = subwords[:max_seq_len]
#             subword_batch[i,:len(subwords)] = subwords
#             mask_batch[i,:len(subwords)] = 1
#             sentiment_batch[i,0] = sentiment
           
#     # Return subword, mask, dan sentiment data
#         return subword_batch, mask_batch, sentiment_batch

train_dataset = DocumentSentimentDataset(train_dataset_path, tokenizer, lowercase=True)
valid_dataset = DocumentSentimentDataset(valid_dataset_path, tokenizer, lowercase=True)
test_dataset = DocumentSentimentDataset(test_dataset_path, tokenizer, lowercase=True)
 
train_loader = DocumentSentimentDataLoader(dataset=train_dataset, max_seq_len=512, batch_size=32, num_workers=16, shuffle=True)  
valid_loader = DocumentSentimentDataLoader(dataset=valid_dataset, max_seq_len=512, batch_size=32, num_workers=16, shuffle=False)  
test_loader = DocumentSentimentDataLoader(dataset=test_dataset, max_seq_len=512, batch_size=32, num_workers=16, shuffle=False)

print(train_dataset[0])

w2i, i2w = DocumentSentimentDataset.LABEL2INDEX, DocumentSentimentDataset.INDEX2LABEL
print(w2i)
print(i2w)

"""<h2> Uji Model <h2>"""

text = 'Bahagia hatiku melihat pernikahan putri sulungku yang cantik jelita'
subwords = tokenizer.encode(text)
subwords = torch.LongTensor(subwords).view(1, -1).to(model.device)
 
logits = model(subwords)[0]
label = torch.topk(logits, k=1, dim=-1)[1].squeeze().item()
 
print(f'Text: {text} | Label : {i2w[label]} ({F.softmax(logits, dim=-1).squeeze()[label] * 100:.3f}%)')

optimizer = optim.Adam(model.parameters(), lr=3e-6)
model = model.cuda()

# Train
n_epochs = 5
for epoch in range(n_epochs):
    model.train()
    torch.set_grad_enabled(True)
 
    total_train_loss = 0
    list_hyp, list_label = [], []
 
    train_pbar = tqdm(train_loader, leave=True, total=len(train_loader))
    for i, batch_data in enumerate(train_pbar):
        # Forward model
        loss, batch_hyp, batch_label = forward_sequence_classification(model, batch_data[:-1], i2w=i2w, device='cuda')
 
        # Update model
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
 
        tr_loss = loss.item()
        total_train_loss = total_train_loss + tr_loss
 
        # Calculate metrics
        list_hyp += batch_hyp
        list_label += batch_label
 
        train_pbar.set_description("(Epoch {}) TRAIN LOSS:{:.4f} LR:{:.8f}".format((epoch+1),
            total_train_loss/(i+1), get_lr(optimizer)))
 
    # Calculate train metric
    metrics = document_sentiment_metrics_fn(list_hyp, list_label)
    print("(Epoch {}) TRAIN LOSS:{:.4f} {} LR:{:.8f}".format((epoch+1),
        total_train_loss/(i+1), metrics_to_string(metrics), get_lr(optimizer)))
 
    # Evaluate on validation
    model.eval()
    torch.set_grad_enabled(False)
    
    total_loss, total_correct, total_labels = 0, 0, 0
    list_hyp, list_label = [], []
 
    pbar = tqdm(valid_loader, leave=True, total=len(valid_loader))
    for i, batch_data in enumerate(pbar):
        batch_seq = batch_data[-1]        
        loss, batch_hyp, batch_label = forward_sequence_classification(model, batch_data[:-1], i2w=i2w, device='cuda')
        
        # Calculate total loss
        valid_loss = loss.item()
        total_loss = total_loss + valid_loss
 
        # Calculate evaluation metrics
        list_hyp += batch_hyp
        list_label += batch_label
        metrics = document_sentiment_metrics_fn(list_hyp, list_label)
 
        pbar.set_description("VALID LOSS:{:.4f} {}".format(total_loss/(i+1), metrics_to_string(metrics)))
        
    metrics = document_sentiment_metrics_fn(list_hyp, list_label)
    print("(Epoch {}) VALID LOSS:{:.4f} {}".format((epoch+1),
        total_loss/(i+1), metrics_to_string(metrics)))

# Evaluate on test
model.eval()
torch.set_grad_enabled(False)
 
total_loss, total_correct, total_labels = 0, 0, 0
list_hyp, list_label = [], []
 
pbar = tqdm(test_loader, leave=True, total=len(test_loader))
for i, batch_data in enumerate(pbar):
    _, batch_hyp, _ = forward_sequence_classification(model, batch_data[:-1], i2w=i2w, device='cuda')
    list_hyp += batch_hyp
 
# Save prediction
df = pd.DataFrame({'label':list_hyp}).reset_index()
df.to_csv('pred.txt', index=False)
 
print(df)
# Evaluate on test
model.eval()
torch.set_grad_enabled(False)
 
total_loss, total_correct, total_labels = 0, 0, 0
list_hyp, list_label = [], []
 
pbar = tqdm(test_loader, leave=True, total=len(test_loader))
for i, batch_data in enumerate(pbar):
    _, batch_hyp, _ = forward_sequence_classification(model, batch_data[:-1], i2w=i2w, device='cuda')
    list_hyp += batch_hyp
 
# Save prediction
df = pd.DataFrame({'label':list_hyp}).reset_index()
df.to_csv('pred.txt', index=False)
 
print(df)

text = 'Sayang, aku marah'
subwords = tokenizer.encode(text)
subwords = torch.LongTensor(subwords).view(1, -1).to(model.device)
 
logits = model(subwords)[0]
label = torch.topk(logits, k=1, dim=-1)[1].squeeze().item()
 
print(f'Text: {text} | Label : {i2w[label]} ({F.softmax(logits, dim=-1).squeeze()[label] * 100:.3f}%)')