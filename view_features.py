import tqdm
import numpy as np
import collections
import pickle
import sys


def nearest_neighbors_calc(vectors, num_neighbors):
  ordered_vectors = []
  print("Making the vectors")
  for para_id in tqdm.tqdm(sorted(vectors.keys())):
    sentence, vector = vectors[para_id]
    np_vec = np.array([vector[key] for key in sorted(vector.keys())])
    ordered_vectors.append(np_vec)

  X = np.array(ordered_vectors)
  nearest_neighbor_map = []
  ordered_keys = sorted(vectors.keys())
  ordered_vectors = np.array([vectors[k] for k in ordered_keys])
  for sent_id, (sentence, vector) in vectors.items():
    distances = np.dot(vector, ordered_vectors)
    nearest_neighbor_map[sent_id] = [ordered_keys[i] for i in
    np.argsort(distances)[:5]]
    print([ordered_keys[i] for i in np.argsort(distances)[:5]])
    break
  return nearest_neighbor_map

def main():
  input_pickle_file = sys.argv[1]

  with open(input_pickle_file, 'rb') as f:
    feature_map = pickle.load(f)
    nn_map = nearest_neighbors_calc(feature_map, 5)

  #for sent_id, (sentence, vector) in feature_map.items():
  #  print(sentence + "\t" + "|".join(k for k, v in
  #    collections.Counter(vector).most_common() if v > 0.0))


if __name__ == "__main__":
  main()
