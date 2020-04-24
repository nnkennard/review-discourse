import json
import sys
import pickle
import numpy as np
import torch
import tqdm
from transformers import BertModel, BertTokenizer

FORUM_ID, NOTE_ID, IDK_2, IDK_3, TOKEN = range(5)

def make_para_id(fields):
  return fields[FORUM_ID] + "_" + fields[NOTE_ID]

def read_conll_file(filename):
  with open(filename, 'r') as f:
    conll_lines = f.readlines()

    paragraphs = {}
    
    current_para_id = None
    current_sentence = []
    current_para = []

    for line in conll_lines:

      if not line.strip():
        if current_sentence:
          current_para.append(current_sentence)
        current_sentence = []

      else:
        fields = line.strip().split("\t")
        this_line_para_id = make_para_id(fields)
        if not this_line_para_id == current_para_id:
          assert not current_sentence
          if current_para_id is not None:
            paragraphs[current_para_id] = current_para
          current_para = []
          current_para_id = this_line_para_id
        current_sentence.append(fields)

  return paragraphs

def get_sentence_tokens(field_list):
  return [fields[TOKEN] for fields in field_list]

def sent_vec_from_bert_output(output):
  return output[0][-1][-1].numpy()

def get_bert_vectors_per_para(dataset, tokenizer, model):
  bert_vectors = {}
  with torch.no_grad():
    for para_id, field_list in tqdm.tqdm(dataset.items()):
      sentences = []
      for i, sentence_fields in enumerate(field_list):
        sentence_tokens = get_sentence_tokens(sentence_fields)
        sentence = " ".join(sentence_tokens)
        input_ids = torch.tensor([
          tokenizer.encode(sentence,
          add_special_tokens=True)])
        sentence_vector = sent_vec_from_bert_output(model(input_ids))
        bert_vectors[para_id + "_" + str(i)] =  (sentence, sentence_vector)
  return bert_vectors


HF_MODEL_SHORTCUT = 'bert-base-uncased'

def main():
  
  input_conll_file = sys.argv[1]
  output_pickle_file = input_conll_file.replace(".parse", ".bert.pkl")

  tokenizer = BertTokenizer.from_pretrained(HF_MODEL_SHORTCUT)
  model = BertModel.from_pretrained(HF_MODEL_SHORTCUT)
  
  dataset = read_conll_file(input_conll_file)

  para_bert_vectors = get_bert_vectors_per_para(dataset, tokenizer, model)
  with open(output_pickle_file, 'wb') as f:
    pickle.dump(para_bert_vectors, f)


if __name__ == "__main__":
  main()
