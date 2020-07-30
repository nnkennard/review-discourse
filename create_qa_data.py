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
  'parent_chunk_idx child_chunk_idx maybe_question_text')


def chunk_text(text):
  return text.split("\n\n")

class CommentPair(object):
  def __init__(self, parent_node, child_node, node_map, tokenize_client):

    self.parent_node = parent_node
    self.child_node = child_node

    self.parent_chunks = self._get_parent_chunks()

    self.child_chunks = self._get_child_chunks(node_map)

    self.qas = self._get_qa_chunks(tokenize_client)

    self.example = QAExample(self.parent_node.note_id, 
        tokenize_chunks(self.parent_chunks, tokenize_client),
        self.child_node.note_id, tokenize_chunks(self.child_chunks,
          tokenize_client), self.qas)



  def _get_parent_chunks(self):
    return chunk(self.parent_node.text)

  def _get_child_chunks(self, node_map):
    author = self.child_node.author
    additional_replies = []
    children_to_check = [self.child_node]
    while children_to_check:
      this_child = children_to_check.pop(0)
      for maybe_grandchild in node_map.values():
        if (maybe_grandchild.reply_to_id == this_child
            and maybe_grandchild.author == author):
          additional_replies.append(maybe_grandchild)
          children_to_check.append(maybe_grandchild)
    child_nodes = [self.child_node] + additional_replies
    return sum([chunk(child_node.text) for child_node in child_nodes], [])

  def _get_qa_chunks(self, client):
    qas = []
    
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
  text1 = " ".join(chunk1)
  text2 = " ".join(chunk2)
  for i, c1 in enumerate(text1):
    if i == len(text2) or not text2[i] == c1:
      return text1[:i]
  return text1


def prefixExistsAndNotAlpha(prefix):
  return prefix and not prefix.strip().isalpha()



ANNOTATORS = "tokenize ssplit pos lemma".split()
IDX, TOKEN, LEMMA, POS = range(4)

def get_mini_node_map(structure, node_map):
  all_node_ids = set(structure.keys()).union(set(structure.values())) - set([None])
  return {node_id:node_map[node_id] for node_id in all_node_ids}


class SuperNode(object):
  def __init__(self, top_node):
    self.text = top_node.text
    self.top_node_id = top_node.note_id
    self.node_id = self.top_node_id + "_super"
    self.included_comment_ids = [self.top_node_id]
    self.processed = False

  def add_node(self, new_node):
    self.text += "\n" + new_node.text
    self.included_comment_ids.append(new_node.note_id)

  def process(self, tokenize_client):
    chunks = chunk_text(self.text)
    self.tokenized_chunks = []
    self.question_map = collections.defaultdict(list)
    for i, chunk in enumerate(chunks):
      tokenized_chunk = []
      annotated_sentences = tokenize_client.annotate(chunk)
      listified_sentences = conll_lib.listify_non_doc_lines(
          annotated_sentences.split("\n"))
      for sentence in listified_sentences:
        if sentence[-1][TOKEN] == "?":
          self.question_map[i].append(" ".join(fields[TOKEN] for fields in sentence))
        tokenized_chunk += [fields[TOKEN] for fields in sentence]
      self.tokenized_chunks.append(tokenized_chunk) 
    self.processed = True

def mini_edit_distance(chunk_tokens_1, chunk_tokens_2):
  return nltk.edit_distance(" ".join(chunk_tokens_1)[:100], 
      " ".join(chunk_tokens_2)[:100])

def find_chunk_pairs(parent_snode, child_snode):
  print("Finding chunk pairs", parent_snode.node_id, child_snode.node_id)
  qas = []
  for i, parent_chunk in enumerate(parent_snode.tokenized_chunks):
    for question in parent_snode.question_map[i]:
      qas.append(QACandidate(i, None, question))
    for j, child_chunk in enumerate(child_snode.tokenized_chunks):
      if parent_chunk == child_chunk:
        dsds
      prefix = longest_starting_prefix(parent_chunk, child_chunk)
      if (parent_chunk
          and mini_edit_distance(parent_chunk, child_chunk) < 5
          and j < len(child_snode.tokenized_chunks) - 1):
        qas.append(QACandidate(i, j, None))
      elif len(prefix) > 10 or prefixExistsAndNotAlpha(prefix):
        qas.append(QACandidate(i, j+1, None))
  return [qa._asdict() for qa in qas]


def condense_long_comments(forum_structure, mini_node_map):
  maybe_roots = [key for key, val in forum_structure.items() if val is None]
  assert len(maybe_roots) == 1
  root_id, = maybe_roots

  stack = [root_id] # ids of comments to check

  super_node_parent = {}
  super_node_map = {} # Should be a map from a super node to its supe rnode parent
  follow_on_map = {}

  while stack:
    curr_node_id = stack.pop(0)
    curr_node = mini_node_map[curr_node_id]

    super_node = super_node_map.get(curr_node_id, None)
    if super_node is None:
      super_node = SuperNode(curr_node)
      super_node_map[curr_node_id] = super_node
    child_ids = [child
        for child, parent in forum_structure.items()
        if parent == curr_node_id]
    for child_id in child_ids:
      stack.append(child_id)
      child_node = mini_node_map[child_id]
      if child_node.author == curr_node.author:
        # This is a follow up
        super_node.add_node(child_node)
        follow_on_map[child_id] = super_node.node_id


  print("Printing super node map")
  for k,v in super_node_map.items():
    print(k, v)

  super_node_structure = {child.node_id:parent.node_id for child, parent in
      super_node_map.items()}
  print("Printing super node structire")
  for k,v in super_node_structure.items():
    print(k, v)

  all_super_nodes = set(
      super_node_map.keys()).union(set(super_node_map.values())) 
  super_node_id_map = {}
  for super_node in all_super_nodes:
    super_node_id_map[super_node.node_id] = super_node

  return super_node_structure, super_node_id_map, follow_on_map


def main():

  dataset_file, output_prefix = sys.argv[1:]

  with corenlp.CoreNLPClient(annotators=ANNOTATORS, output_format='conll') as corenlp_client:
    for split, dataset in orl.get_datasets(dataset_file, debug=True).items():
    
      qa_pairs = []

      for forum, structure in tqdm(dataset.forum_map.items()):
        mini_node_map = get_mini_node_map(structure, dataset.node_map)
        super_node_structure, super_node_id_map, follow_on_map = condense_long_comments(structure, mini_node_map)
        for super_node in super_node_id_map.values():
          super_node.process(corenlp_client)

        for child, parent in super_node_structure.items():
          print("*", child, parent)
          maybe_nodes = get_nodes_from_map(child, parent, super_node_id_map)
          if maybe_nodes is None:
            continue
          child, parent = maybe_nodes
          qa_pairs.append(find_chunk_pairs(parent, child))

      output_obj = {
      "conference": dataset.conference,
      "split": split,
      "qa_pairs": qa_pairs
      }

      output_filename = "_".join(
          [output_prefix + "qaPairs", dataset.conference, dataset.split + ".json"])
      with open(output_filename, 'w') as f:
        f.write(json.dumps(output_obj))


if __name__ == "__main__":
  main()
