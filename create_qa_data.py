import collections
import conll_lib
import corenlp
import json
import nltk
import openreview
import sys

from tqdm import tqdm

import openreview_lib as orl


QAExample = collections.namedtuple('QAExample',
  'parent_id parent_chunks child_id child_chunks qas')

QACandidate = collections.namedtuple('QACandidate',
  'parent_id parent_chunk_idx child_id child_chunk_idx maybe_question_text')


def chunk_text(text):
  return text.split("\n\n")
   
def get_nodes_from_map(child, parent, node_map):
  if parent is None:
    return None
  child_node = node_map[child]
  parent_node = node_map[parent]
  if child_node.text and parent_node.text:
    return child_node, parent_node
  else:
    return None


def longest_starting_prefix(chunk1, chunk2):
  text1 = squish(chunk1)
  text2 = squish(chunk2)
  for i, c1 in enumerate(text1):
    if i == len(text2) or not text2[i] == c1:
      return text1[:i]
  return text1


def prefixExistsAndNotAlpha(prefix):
  return prefix and not prefix.strip().isalpha()


ANNOTATORS = "tokenize ssplit".split()
IDX, TOKEN = range(2)


def get_mini_node_map(structure, node_map):
  all_node_ids = set(structure.keys()).union(set(structure.values())) - set([None])
  return {node_id:node_map[node_id] for node_id in all_node_ids}


def squish(chunk):
  return " ".join(sum(chunk, []))

def mini_edit_distance(chunk_tokens_1, chunk_tokens_2):
  return nltk.edit_distance(squish(chunk_tokens_1)[:100], 
      squish(chunk_tokens_2)[:100])


def find_chunk_pairs(parent_snode, child_snode):
  parent_id, child_id = parent_snode.node_id, child_snode.node_id
  qas = []
  for i, parent_chunk in enumerate(parent_snode.tokenized_chunks):
    for question in parent_snode.question_map[i]:
      qas.append(QACandidate(parent_id, i, child_id, None, question))
    for j, child_chunk in enumerate(child_snode.tokenized_chunks):
      prefix = longest_starting_prefix(parent_chunk, child_chunk)
      if (parent_chunk
          and mini_edit_distance(parent_chunk, child_chunk) < 5
          and j < len(child_snode.tokenized_chunks) - 1):
        qas.append(QACandidate(parent_id, i, child_id, j, None))
      elif len(prefix) > 10 or prefixExistsAndNotAlpha(prefix):
        qas.append(QACandidate(parent_id, i, child_id, j+1, None))
  return [qa._asdict() for qa in qas]


class SuperNode(object):
  def __init__(self, node_id, title, text, author):
    self.original_id = node_id
    self.node_id = superify(node_id)
    self.title = title
    self.text = text
    self.author = author
    self.children = []
    self.included_nodes = [node_id]
    self.question_map = None
    self.tokenized_chunks = None


  def serialize(self):
    return {
        "node_id": self.node_id,
        "included_nodes": self.included_nodes,
        "text": [sum(chunk, []) for chunk in self.tokenized_chunks]
        }

  def add_child(self, child):
    self.children.append(child)

  def absorb_node(self, node):
    self.text += "\n\n" + node.text
    self.children += node.children
    self.included_nodes.append(node.original_id)

  def process(self, tokenize_client):
    chunks = chunk_text(self.text)
    self.tokenized_chunks = []
    for chunk in chunks:
      tokenized = tokenize_client.annotate(chunk)
      listified = conll_lib.listify_non_doc_lines(tokenized.split("\n"))
      sentences = []
      for sentence in listified:
        sentence_tokens = [fields[TOKEN] for fields in sentence if fields]
        sentences.append(sentence_tokens)
      if sentences:
        self.tokenized_chunks.append(sentences)

  def get_questions(self):
    self.question_map = collections.defaultdict(list)
    for i, chunk in enumerate(self.tokenized_chunks):
      for sentence in chunk:
        if sentence[-1] == "?":
          self.question_map[i].append(" ".join(sentence))

  def __str__(self):
    return self.node_id

def superify(old_id):
  return old_id + "_super"

def restructure(forum_structure, node_map, tokenize_client):
  supernode_map = {superify(key):SuperNode(
    value.note_id, value.title, value.text, value.author) for key, value in node_map.items()}

  supernode_structure = {}
  for child, parent in forum_structure.items():
    if parent is None:
      supernode_structure[superify(child)] = None
    else:
      supernode_structure[superify(child)] = superify(parent)

  for child, parent in supernode_structure.items():
    if parent is None:
      continue
    child_node = supernode_map[child]
    parent_node = supernode_map[parent]
    if child_node.author == parent_node.author:
      parent_node.absorb_node(child_node)
    else:
      parent_node.children.append(child)

  new_supernode_structure = {}
  root, = [child
      for child, parent in supernode_structure.items() if parent is None]
  stack = [(root, None)]
  while stack:
    curr_node, parent = stack.pop(0)
    new_children = supernode_map[curr_node].children
    stack += [(child, curr_node) for child in new_children]
    new_supernode_structure[curr_node] = parent

  final_nodes = set(new_supernode_structure.keys()).union(
      set(new_supernode_structure.values())) - set([None])
  for node in final_nodes:
    supernode_map[node].process(tokenize_client)

  original_nodes = set(supernode_structure.keys()).union(
      set(supernode_structure.values())) - set([None])

  for parent_node_id in set(new_supernode_structure.values()):
    # If it's not a parent, questions cannot have been answered
    if parent_node_id is None:
      continue
    supernode_map[parent_node_id].get_questions()

  supernode_map = {key: value for key, value in supernode_map.items() if key in
      final_nodes}

  qas = []
  for child, parent in new_supernode_structure.items():
    if parent is None:
      continue
    qas += find_chunk_pairs(supernode_map[parent], supernode_map[child])

  return supernode_map, qas



def main():

  dataset_file, output_prefix = sys.argv[1:]

  with corenlp.CoreNLPClient(annotators=ANNOTATORS, output_format='conll') as corenlp_client:
    for split, dataset in orl.get_datasets(dataset_file).items():

      all_nodes = []
      all_qas = []

      for forum, structure in tqdm(dataset.forum_map.items()):
        mini_node_map = get_mini_node_map(structure, dataset.node_map)
        nodes, qas = restructure(structure, mini_node_map,
            corenlp_client)
        all_nodes += nodes.values()
        all_qas += qas
    
      output_obj = {
      "conference": dataset.conference,
      "split": split,
      "nodes": [node.serialize() for node in all_nodes],
      "qa_pairs": all_qas
      }

      output_filename = "_".join(
          [output_prefix + "qaPairs", dataset.conference, dataset.split + ".json"])
      with open(output_filename, 'w') as f:
        f.write(json.dumps(output_obj))


if __name__ == "__main__":
  main()
