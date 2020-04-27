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
from sklearn.cluster import AgglomerativeClustering
from sklearn.manifold import TSNE

from encode import Dataset

def main():

  dataset_file = sys.argv[1]

  with open(dataset_file, 'rb') as f:
    dataset = pickle.load(f)

  kmeans = KMeans(n_clusters=8, init='random', n_init=4, max_iter=10,
      tol=1e-04, random_state=0, verbose=1)

  agg = AgglomerativeClustering(linkage="average")
  
  y_km = agg.fit_predict(dataset.vectors)
  clusters = collections.defaultdict(list)

  for cluster, sentence in zip(list(y_km), 
      dataset.sentences):
    clusters[str(cluster)].append(sentence)
  

  for cluster, sentences in clusters.items():
    for sentence in sorted(sentences):
      print(str(cluster)+"\t"+ " ".join(sentence))
    print()


if __name__ == "__main__":
  main()
