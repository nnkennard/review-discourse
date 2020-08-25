import json
import math 
import sys

import openreview_lib as orl

WINDOW = 5
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

  for i, hash1 in hashes_1.items():
    for j, hash2 in hashes_2.items():
      if hash1 == hash2:
        print(" ".join(tokens_1[i:i+WINDOW]))
        print(" ".join(tokens_2[j:j+WINDOW]))
        print("*" * 20)
  
  return set(hashes_1.values()).intersection(set(hashes_2.values()))


def find_parent(child_node, forum_map):
  for forum in forum_map.values():
    if child_node in forum.keys():
      return forum[child_node]

  return None


def get_examples_from_nodes_and_map(nodes, forum_map):
  pairs = []
  for node in nodes:
    top_node = node["included_nodes"][0]
    parent_id = find_parent(top_node, forum_map)
    for maybe_parent in nodes:
      if parent_id in maybe_parent["included_nodes"]:
        pairs.append(
            (top_node, parent_id,
              chunk_tokens(node["tokens"]),
              chunk_tokens(maybe_parent["tokens"])))
        break


  for i in pairs:
    print(i)

  return pairs

def chunk_tokens(tokens):
  chunks = []
  current_chunk = []
  for token in tokens:
    if token == "__NEWLINE" and current_chunk:
      chunks.append(current_chunk)
      current_chunk = []
    else:
      current_chunk.append(token)

  return chunks



def main():

  forum_info_file, input_file = sys.argv[1:]

  with open(input_file, 'r') as f:
    nodes = json.loads(f.read())["nodes"]
  
  dataset = orl.get_datasets(forum_info_file, debug=True)["train"]

  examples = get_examples_from_nodes_and_map(nodes, dataset.forum_map)

  for child_id, parent_id, child, parent in examples:
    for child_chunk in child:
      for parent_chunk in parent:
        print(child_id)
        print(parent_id)
        print(karp_rabin(child_chunk, parent_chunk))



if __name__ == "__main__":
  main()
