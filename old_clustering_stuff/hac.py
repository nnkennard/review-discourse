import numpy as np
import sys
import pickle
from scipy.spatial.distance import squareform
from encode import Dataset
import torch

def dist_mat(query_vectors):
  dist = torch.matmul(query_vectors, query_vectors.transpose(1, 0))
  dist = 2 - 2*dist
  dist = dist.cpu().numpy()
  np.fill_diagonal(dist, 0)
  return squareform(dist)


def main():
  dataset_pickle_file = sys.argv[1]

  print(torch.cuda.is_available())

  with open(dataset_pickle_file, 'rb') as f:
    dataset = pickle.load(f)

  print(dataset)

  query_vecs = torch.from_numpy(dataset.vectors[:6000]).cuda().detach()
  dists = dist_mat(query_vecs)
  print(dists[:10])

if __name__ == "__main__":
  main()
