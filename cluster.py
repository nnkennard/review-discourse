import collections
import tqdm
import json
import math
import numpy as np
import sys
import pandas as pd
import pickle
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE


def main():

  bert_map_file  = sys.argv[1]

  with open(bert_map_file, 'rb') as f:
    bert_map = pickle.load(f)

  ordered_vectors = []
  ordered_sentences = []

  for para_id in tqdm.tqdm(sorted(bert_map.keys())):
    sentence, vector = bert_map[para_id]
    np_vec = np.array([vector[key] for key in sorted(vector.keys())])
    ordered_vectors.append(np_vec)
    ordered_sentences.append(sentence)

  X = np.array(ordered_vectors)

  # Find elbow

  #distortions = []
  #for i in range(1, 20):
  #  km = KMeans(n_clusters=i, init='random',
  #      n_init=10, max_iter=300,  tol=1e-04, random_state=0)
  #  km.fit(X)
  #  distortions.append(km.inertia_)
 

  #plt.plot(range(1, 20), distortions, marker='o')
  #plt.xlabel('Number of clusters')
  #plt.ylabel('Distortion')
  #plt.savefig("distortions.png")
  
  #exit()
  
  kmeans = KMeans(n_clusters=8, init='random', n_init=4, max_iter=50,
      tol=1e-04, random_state=0, verbose=1)
  
  y_km = kmeans.fit_predict(X)

  clusters = collections.defaultdict(list)

  for cluster, key, sentence in zip(list(y_km), sorted(bert_map.keys()),
      ordered_sentences):
    clusters[str(cluster)].append(sentence)
  

  for cluster, sentences in clusters.items():
    for sentence in sorted(sentences):
      print(str(cluster)+"\t"+sentence)
    print()


if __name__ == "__main__":
  main()
