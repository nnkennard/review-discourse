import collections
import json
import numpy as np
import pickle
import sys
import torch
import tqdm
from transformers import BertModel, BertTokenizer

FORUM_ID, NOTE_ID, IDK_2, IDK_3, TOKEN, MOD_TOKEN, LEMMA, POS = range(8)

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
  return [fields[MOD_TOKEN] for fields in field_list]

def sent_vec_from_bert_output(output):
  return output[0][-1][-1].numpy()

HF_MODEL_SHORTCUT = 'bert-base-uncased'

class Dataset(object):
  def __init__(self, sentences, sentence_ids, vectors, features=None):
    self.sentences = sentences
    self.sentence_ids = sentence_ids
    self.vectors = vectors
    self.features = features

def get_sentences_from_conll_dataset(dataset):
  sentence_map = {}
  for para_id, sentences in dataset.items():
    for i, sentence in enumerate(sentences):
      sentence_map[para_id + "_" + str(i)] = get_sentence_tokens(sentence)
  return sentence_map


def bert_encode(dataset):
  tokenizer = BertTokenizer.from_pretrained(HF_MODEL_SHORTCUT)
  model = BertModel.from_pretrained(HF_MODEL_SHORTCUT)
  
  sentence_map = get_sentences_from_conll_dataset(dataset)
  sentence_ids = sorted(sentence_map.keys())
  sorted_sentences = []
  sorted_vectors = []
  
  with torch.no_grad():
    print("Encoding sentences")
    for sentence_id in tqdm.tqdm(sentence_ids):
      sentence = sentence_map[sentence_id]
      sorted_sentences.append(sentence)
      sentence_str = " ".join(sentence)

      input_ids = torch.tensor([
        tokenizer.encode(sentence,
        add_special_tokens=True)])
      sentence_vector = sent_vec_from_bert_output(model(input_ids))
      sorted_vectors.append(sentence_vector)

  matrix = np.array(sorted_vectors)

  return Dataset(sorted_sentences, sentence_ids, matrix)


def count_unigrams_bigrams(tokens):
  unigrams = [x.lower() for x in tokens if x not in ["RARE", "SYMB"]]
  bigrams = [x + "_" + y for x, y in zip(unigrams[:-1], unigrams[1:])]
  return collections.Counter(unigrams + bigrams)

def get_unigram_bigram_vectors(dataset):
  vectors = {}
  for para_id, field_lines in dataset.items():
    for i, sentence_fields in enumerate(field_lines):
      sentence_tokens = get_sentence_tokens(sentence_fields)
      sentence_id = para_id + "_" + str(i)

      vectors[sentence_id] = (" ".join(sentence_tokens),
          uni_bigram_vector)

  return vectors

def idf_transform(vectors, sentences, num_features=5000):
  print("IDF transformation")
  doc_count = collections.Counter()
  for sentence in sentences:
    doc_count.update(sentence)

  features = [k for k, v in doc_count.most_common(num_features)[100:]]

  idf_map = collections.defaultdict(dict)

  new_vectors = []
  for orig_vector, sentence in tqdm.tqdm(zip(vectors, sentences)):
    vector_builder = {term: 0.0 for term in features}
    for feature, value in orig_vector.items():
      if feature in features:
        vector_builder[feature] = doc_count[feature]
    new_vectors.append(
        np.array([vector_builder[feature] for feature in features]))

  return np.array(new_vectors), features


def bow_encode(conll_dataset, num_features):
  sentence_map = get_sentences_from_conll_dataset(conll_dataset)
  sentence_ids = sorted(sentence_map.keys())
  sorted_sentences = []
  sorted_vectors = []
  
  print("Encoding sentences")
  for sentence_id in tqdm.tqdm(sentence_ids):
    sentence = sentence_map[sentence_id]
    sorted_sentences.append(sentence)
    ub_vector = count_unigrams_bigrams(sentence)
    sorted_vectors.append(ub_vector)

  matrix, features = idf_transform(sorted_vectors, sorted_sentences)

  return Dataset(sorted_sentences, sentence_ids, matrix, features)


  pass

def dump_dataset(dataset, output_file):
  assert output_file.endswith(".pkl")
  with open(output_file, 'wb') as f:
    pickle.dump(dataset, f)


def main():
  input_conll_file = sys.argv[1]
  conll_dataset = read_conll_file(input_conll_file)

  print("Preparing BOW vectors")
  bow_dataset = bow_encode(conll_dataset, 5000)
  bow_output_pickle_file = input_conll_file.replace(
      ".parse.proc", ".parse.proc.ub_idf.pkl")
  dump_dataset(bow_dataset, bow_output_pickle_file)

  print("Preparing BERT vectors")
  bert_dataset = bert_encode(conll_dataset)
  bert_output_pickle_file = input_conll_file.replace(
      ".parse.proc", ".parse.proc.bert.pkl")
  dump_dataset(bert_dataset, bert_output_pickle_file)

if __name__ == "__main__":
  main()
