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


def chunk(text):
  return text.split("\n\n")

def get_text(node_id, all_notes):
  k = [note for note in all_notes if note.id == node_id]
  assert len(k) == 1
  return orl.NoteNode(k[0]).text

class CommentPair(object):
  def __init__(self, parent_node, child_node, node_map, tokenize_client):

    self.parent_node = parent_node
    self.child_node = child_node

    self.parent_chunks = self._get_parent_chunks()

    self.child_chunks = self._get_child_chunks(node_map)

    self.qas = self._get_qa_chunks(tokenize_client)

    self.example = QAExample(self.parent_node.note_id, self.parent_chunks,
        self.child_node.note_id, self.child_chunks, self.qas)



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
    for j, parent_chunk in enumerate(self.parent_chunks):
      questions_by_punct = get_questions(parent_chunk, client)
      for question in questions_by_punct:
        qas.append(QACandidate(j, None, question))
      for i, child_chunk in enumerate(self.child_chunks):
        prefix = longest_starting_prefix(parent_chunk, child_chunk)
        if parent_chunk and (nltk.edit_distance(parent_chunk, child_chunk) < 5
            and i < len(self.child_chunks) - 1):
          qas.append(QACandidate(j, i, None))
        elif len(prefix) > 10 or prefixExistsAndNotAlpha(prefix):
          qas.append(QACandidate(j, i+1, None))
    return [qa._asdict() for qa in qas]
            
def get_questions(text, client):
  conll_text = client.annotate(text)
  listified = conll_lib.listify_non_doc_lines(conll_text.split("\n"))
  questions = []
  for sentence in listified:
    if sentence[-1][TOKEN] == "?":
      questions.append(" ".join(fields[TOKEN] for fields in sentence))

  return questions

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
  for i, c1 in enumerate(chunk1):
    if i == len(chunk2) or not chunk2[i] == c1:
      return chunk1[:i]
  return chunk1


def prefixExistsAndNotAlpha(prefix):
  return prefix and not prefix.strip().isalpha()



ANNOTATORS = "tokenize ssplit pos lemma".split()
IDX, TOKEN, LEMMA, POS = range(4)

def get_mini_node_map(structure, node_map):
  all_node_ids = set(structure.keys()).union(set(structure.values())) - set([None])
  return {node_id:node_map[node_id] for node_id in all_node_ids}

def main():

  dataset_file, output_prefix = sys.argv[1:]

  with corenlp.CoreNLPClient(annotators=ANNOTATORS, output_format='conll') as corenlp_client:
    for split, dataset in orl.get_datasets(dataset_file).items():
    
      qa_pairs = []

      for forum, structure in tqdm(dataset.forum_map.items()):
        mini_node_map = get_mini_node_map(structure, dataset.node_map)

        for child, parent in structure.items():
          maybe_nodes = get_nodes_from_map(child, parent, mini_node_map)
          if maybe_nodes is None:
            continue
          child, parent = maybe_nodes
          new_qa_pair = CommentPair(
              parent, child, mini_node_map, corenlp_client)
          qa_pairs.append(new_qa_pair.example._asdict())

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
