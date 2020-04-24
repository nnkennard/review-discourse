import collections
import json
import sys
import pickle
import numpy as np
import torch
import tqdm

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

def count_unigrams_bigrams(tokens):
  unigrams = [x.lower() for x in tokens]
  bigrams = [x + "_" + y for x, y in zip(unigrams[:-1], unigrams[1:])]
  return collections.Counter(unigrams + bigrams)

def get_unigram_bigram_vectors(dataset):
  vectors = {}
  for para_id, field_lines in dataset.items():
    for i, sentence_fields in enumerate(field_lines):
      sentence_tokens = get_sentence_tokens(sentence_fields)
      sentence_id = para_id + "_" + str(i)
      uni_bigram_vector = count_unigrams_bigrams(sentence_tokens)
      vectors[sentence_id] = (" ".join(sentence_tokens),
          uni_bigram_vector)

  return vectors

def idf_transform(vectors):
  doc_count = collections.Counter()
  for unused_id, (_, vector_map) in vectors.items():
    doc_count.update(vector_map.keys())

  top_10k_terms =[k for k, v in doc_count.most_common(5000)]

  idf_map = collections.defaultdict(dict)

  for vector_id, (sentence, orig_vector) in tqdm.tqdm(vectors.items()):
    vector_builder = {term: 0.0 for term in top_10k_terms}
    for key, value in orig_vector.items():
      if key in top_10k_terms:
        vector_builder[key] = value / doc_count[key]

    idf_map[vector_id] = sentence, vector_builder

  return idf_map


def main():
  
  input_conll_file = sys.argv[1]
  output_pickle_file = input_conll_file.replace(".parse", ".ub_idf.pkl")

  dataset = read_conll_file(input_conll_file)
  vectors = get_unigram_bigram_vectors(dataset)

  idf_vectors = idf_transform(vectors)

  with open(output_pickle_file, 'wb') as f:
    pickle.dump(idf_vectors, f)

if __name__ == "__main__":
  main()
