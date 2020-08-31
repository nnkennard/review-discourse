import json
import math 
import sys

import openreview_lib as orl

from tqdm import tqdm

WINDOW = 7
Q = 2124749677  # Is this too big for Python int


def myhash(tokens):
  tok_str = "".join(tokens)
  hash_acc = 0
  for i, ch in enumerate(reversed(tok_str)):
    hash_acc += math.pow(2, i) * ord(ch)

  return hash_acc % Q


def get_hashes(tokens):
  return {i:myhash(tokens[i:i+WINDOW]) for i in range(len(tokens) - WINDOW)}


def karp_rabin(tokens_1, tokens_2):
  hashes_1 = get_hashes(tokens_1)
  hashes_2 = get_hashes(tokens_2)
  results = []
  for k1, v1 in hashes_1.items():
    for k2, v2 in hashes_2.items():
      if v1 == v2:
        results.append((k1, k2))
  return sorted(results)


def find_parent(child_node, forum_map):
  for forum_head, forum in forum_map.items():
    if child_node in forum.keys():
      return forum_head, forum[child_node]

  return None


def get_examples_from_nodes_and_map(nodes, forum_map):
  chunk_map = {}
  pairs = []
  for node in nodes:
    top_node = node["included_nodes"][0]
    ancestor_id, parent_id = find_parent(top_node, forum_map)
    for maybe_parent in nodes:
      if parent_id in maybe_parent["included_nodes"]:
        chunk_map[parent_id] = chunk_tokens(maybe_parent["tokens"])
        chunk_map[top_node] = chunk_tokens(node["tokens"])
        pairs.append((ancestor_id, top_node, parent_id,))
        break

  return pairs, chunk_map


def chunk_tokens(tokens):
  chunks = []
  current_chunk = []
  for token in tokens:
    if token == "__NEWLINE":
      if current_chunk:
        chunks.append(current_chunk)
        current_chunk = []
    else:
      current_chunk.append(token)
  return chunks


def get_lcs(chunk1, chunk2, start_indices):
  current_lcs = []
  for start1, start2 in start_indices:
    j = 0
    while start1 + j < len(chunk1) and start2 + j < len(chunk2):
      if chunk1[start1:start1+j] == chunk2[start2:start2+j]:
        j += 1
      elif j-1 > len(current_lcs):
        current_lcs = chunk2[start2:start2+j-1]
  return current_lcs


class CommentPair(object):
  def __init__(self, ancestor, child_node, parent_node, chunk_map):
    child_chunks = chunk_map[child_node]
    parent_chunks = chunk_map[parent_node]
    child_chunks_mapped = {i:None for i in range(len(child_chunks))}
    parent_chunks_mapped = {i:None for i in range(len(parent_chunks))}
    lcs_map ={}
    for i, child_chunk in enumerate(child_chunks):
      for j, parent_chunk in enumerate(parent_chunks):
        x = karp_rabin(child_chunk, parent_chunk)
        if x:
          child_chunks_mapped[i], parent_chunks_mapped[j] = j, i
          lcs_map[(i,j)] = child_chunk[x[0][0]:x[0][0]+WINDOW] 
    assert len(parent_chunks) == len(parent_chunks_mapped)
    assert len(child_chunks) == len(child_chunks_mapped)

    self.data = {
        "child": child_node,
        "parent": parent_node,
        "ancestor": ancestor,
        "child_chunks": child_chunks_mapped,
        "parent_chunks": parent_chunks_mapped,
        "lcs" : list(lcs_map.values())
        }

    


def main():

  forum_info_file, input_file = sys.argv[1:]

  with open(input_file, 'r') as f:
    nodes = json.loads(f.read())["nodes"]
  
  dataset = orl.get_datasets(forum_info_file, debug=False)["train"]
  pairs, chunk_map = get_examples_from_nodes_and_map(nodes, dataset.forum_map)
  matches = []

  for ancestor, x, y in tqdm(pairs):
    cp = CommentPair(ancestor, x, y, chunk_map)
    matches.append(cp.data)

  with open('kr_ouptut.json', 'w') as f:
    f.write(json.dumps(matches))

if __name__ == "__main__":
  main()
