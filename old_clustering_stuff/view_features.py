import tqdm
import numpy as np
import collections
import pickle
import sys

from encode import Dataset

def print_sentence(sentence):
  print(" ".join(sentence))

def get_top_features(vector, features, k=10):
  return [k for k, _ in collections.Counter(
      {features[i]:list(vector)[i]
        for i in range(len(features))}).most_common(k)]


def print_nearest_neighbors(sentences, main_sentence, indices, features, vectors):
  print("Nearest neighbors of:")
  print_sentence(sentences[main_sentence])
  print()
  for i in indices:
    print_sentence(sentences[i])
  print("_" * 80)

  if features is not None:
    print("|".join(get_top_features(vectors[main_sentence], features)))
    print()
    for i in indices:
      print("|".join(get_top_features(vectors[i], features)))
    print("_" * 80)

def nearest_neighbors_calc(dataset, num_neighbors):

  nearest_neighbor_map = {}

  for i, (sentence_id, vector) in enumerate(zip(dataset.sentence_ids,
    dataset.vectors)):
    distances = np.dot(dataset.vectors, vector)

    nearest_neighbor_map[sentence_id] = np.argsort(distances)[:5]
    print_nearest_neighbors(dataset.sentences, i,
        np.argsort(distances)[-5:], dataset.features, dataset.vectors)

  return nearest_neighbor_map

def main():
  input_pickle_file = sys.argv[1]

  with open(input_pickle_file, 'rb') as f:
    dataset = pickle.load(f)
    
  nn_map = nearest_neighbors_calc(dataset, 5)


if __name__ == "__main__":
  main()
