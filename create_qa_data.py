import collections
import conll_lib
import corenlp
import json
import nltk
import openreview
import sys

from tqdm import tqdm

import openreview_lib as orl

SupNode = collections.namedtuple('SupNode', 'supnode_id tokens')
Question = collections.namedtuple('Question', 'supnode_id start exclusive_end')
Answer = collections.namedtuple('Answer', 'supnode_id question start exclusive_end')

def chunk_text(text):
  return text.split("\n\n")


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

NEWLINE_TOK = "__NEWLINE"

SEPARATOR_CHUNK = [[NEWLINE_TOK, NEWLINE_TOK]]


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
    self.tokenized = False


  def serialize(self):
    return {
        "node_id": self.node_id,
        "included_nodes": self.included_nodes,
        "tokens": sum([sum(chunk, []) for chunk in self.tokenized_chunks], [])
        }

  def add_child(self, child):
    self.children.append(child)

  def absorb_node(self, node):
    self.text += "\n\n" + node.text
    self.children += node.children
    self.included_nodes.append(node.original_id)

  def tokenize(self, tokenize_client):
    if self.tokenized:
      return
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
        if self.tokenized_chunks:
          self.tokenized_chunks.append(SEPARATOR_CHUNK)
        self.tokenized_chunks.append(sentences)
    self.tokenized = True
  
  def get_questions(self):
    assert self.tokenized
    questions = []

    token_offset = 0
    for chunk in self.tokenized_chunks:
      for sentence in chunk:
        if sentence[-1] == "?":
          questions.append(
              Question(self.node_id,
                token_offset, token_offset + len(sentence)))
        token_offset += len(sentence)
    
    return questions

  def __str__(self):
    return self.node_id

def superify(old_id):
  return old_id + "_super"

def restructure(forum_structure, node_map):
  """Collapse continuations over multiple nodes."""
  supernode_map = {superify(key):SuperNode(
    value.note_id, value.title, value.text, value.author) for key, value in node_map.items()}

  # Same structure, with superified names
  supernode_structure = {}
  for child, parent in forum_structure.items():
    if parent is None:
      supernode_structure[superify(child)] = None
    else:
      supernode_structure[superify(child)] = superify(parent)

  # Absorb children with the same author into parent node
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
            for child, parent in supernode_structure.items()
            if parent is None]  # Should only be one such node
  stack = [(root, None)]
  while stack:  # Build new supernode structure
    curr_node, parent = stack.pop(0)
    new_children = supernode_map[curr_node].children
    stack += [(child, curr_node) for child in new_children]
    new_supernode_structure[curr_node] = parent

  # Build map of supernodes that occur in the final structure
  final_nodes = set(new_supernode_structure.keys()).union(
      set(new_supernode_structure.values())) - set([None])

  supernode_map = {key: value for key, value in supernode_map.items() if key in
      final_nodes}

  return new_supernode_structure, supernode_map


def get_chunks(node):
  chunks = []
  assert node.tokenized
  offset = 0
  for chunk in node.tokenized_chunks:
    updated_offset = offset + len(sum(chunk, []))
    if not chunk == SEPARATOR_CHUNK:
      chunks.append(((offset, updated_offset), chunk))
    offset = updated_offset
  return chunks


def find_chunk_pairs(child_node, parent_node):
  parent_chunks = get_chunks(parent_node)
  child_chunks = get_chunks(child_node)

  questions = []
  answers = []
  
  for i, (parent_offsets, parent_chunk) in enumerate(parent_chunks):
    for j, (child_offsets, child_chunk) in enumerate(child_chunks):
      prefix = longest_starting_prefix(parent_chunk, child_chunk)
      if (parent_chunk
          and mini_edit_distance(parent_chunk, child_chunk) < 5
          and j < len(child_chunks) - 1):
        new_question = Question(parent_node.node_id, *parent_offsets)
        questions.append(new_question)
        answer = Answer(child_node.node_id, new_question, *child_offsets)
        answers.append(answer)
      elif len(prefix) > 10 or prefixExistsAndNotAlpha(prefix):
        if j >= len(child_chunks) - 1:
          continue
        next_offsets, next_child_chunk = child_chunks[j+1]
        new_question = Question(parent_node.node_id, *parent_offsets)
        questions.append(new_question)
        answer = Answer(child_node.node_id, new_question._asdict(), *next_offsets)
        answers.append(answer)

  return questions, answers


def get_questions_and_answers(forum_structure, node_map, tokenize_client):


  final_nodes = set(
      forum_structure.keys()).union(
          set(forum_structure.values())) - set([None])

  questions = []
  for node_id in final_nodes:
    node = node_map[node_id]
    node.tokenize(tokenize_client)
    questions += node.get_questions()

  answers = []
  for child, parent in forum_structure.items():
    if parent is None:
      continue
    else:
      new_qs, new_as = find_chunk_pairs(node_map[child], node_map[parent])
      questions += new_qs
      answers += new_as
    
  return questions, answers


def main():

  dataset_file, output_prefix = sys.argv[1:]

  with corenlp.CoreNLPClient(annotators=ANNOTATORS, output_format='conll') as corenlp_client:
    for split, dataset in orl.get_datasets(dataset_file, debug=False).items():

      all_nodes = []
      all_questions = []
      all_answers = []

      for forum, structure in tqdm(dataset.forum_map.items()):
        mini_node_map = get_mini_node_map(structure, dataset.node_map)
        supernode_structure, supernode_map = restructure(structure,
            mini_node_map)
        questions, answers = get_questions_and_answers(
            supernode_structure, supernode_map, corenlp_client)
        all_nodes += supernode_map.values()
        all_questions += questions
        all_answers += answers
    
      output_obj = {
      "conference": dataset.conference,
      "split": split,
      "nodes": [node.serialize() for node in all_nodes],
      "questions": [q._asdict() for q in all_questions],
      "answers": [a._asdict() for a in all_answers]
      }

      output_filename = "_".join(
          [output_prefix + "qaPairs", dataset.conference, dataset.split + ".json"])
      with open(output_filename, 'w') as f:
        f.write(json.dumps(output_obj))


if __name__ == "__main__":
  main()
