import collections
import glob
import json
import os
import sys
import yaml

ROOT = "ROOT"

def get_fields(line, field_map):
  fields = line.strip().split()
  selection_map = {}
  for field_name, index in field_map.items():
    selection_map[field_name] = fields[index]
  return selection_map

Relation = collections.namedtuple(
  'Relation', 'nuc_start nuc_end sat_start sat_end relation')

def get_relations_from_tree(root):
  relations = [root.get_relation()]
  if root.left is not None:
    relations += get_relations_from_tree(root.left)
  if root.right is not None:
    relations += get_relations_from_tree(root.right)
  return relations


def actual_listify(merge_filename, field_map):

  with open(merge_filename, 'r') as f:
    lines = f.readlines()

  overall_maps = {name: [] for name in field_map.keys()}
  current_sentence = collections.defaultdict(list)

  for line in lines:
    line = line.replace("`", 'TICK')
    if not line.strip():
      for k, v in current_sentence.items():
        overall_maps[k].append(v)
      current_sentence = collections.defaultdict(list)
    else:
      selected_fields = get_fields(line, field_map)
      for name, value in selected_fields.items():
        current_sentence[name].append(value)
  if current_sentence:
    assert False

  return overall_maps

def get_tree_from_brackets(brackets_filename):
  with open(brackets_filename, 'r') as f:
    brackets = [eval(line) for line in f]

  last_edu = brackets[-1][0][1]
  root = Node(1, last_edu, ROOT, ROOT)
  ancestor_stack = [root]

  all_nodes = [root]
  for (start, end), ns, rel in reversed(brackets):
    ancestor = ancestor_stack.pop(-1)
    new_node = Node(start, end, ns, rel, ancestor)
    all_nodes.append(new_node)
    if start > ancestor.start:
      assert ancestor.right is None
      ancestor.right = new_node
    elif end < ancestor.end:
      assert ancestor.left is None
      ancestor.left = new_node
    if ancestor.left is None or ancestor.right is None:
      ancestor_stack.append(ancestor)
    if not start == end:
      ancestor_stack.append(new_node)

  return root



def listify(merge_filename, field_map, comment_id):

  overall_maps = actual_listify(merge_filename, field_map)

  spans = {}
  token_labels = list(int(i) for i in sum(overall_maps["EDU"], [])) + ["DUMMY"]
  span_start_finder = 0
  span_end_finder = 0

  while span_end_finder < len(token_labels) - 1: # -1 due to dummy
    while token_labels[span_end_finder] == token_labels[span_start_finder]:
      span_end_finder += 1
    assert token_labels[span_start_finder] == token_labels[span_end_finder - 1]
    spans[token_labels[span_start_finder]] = (span_start_finder,
        span_end_finder)
    span_start_finder = span_end_finder
  
  brackets_filename = merge_filename.replace(".merge", ".brackets")
  tree = get_tree_from_brackets(brackets_filename)

  relations = get_relations_from_tree(tree)
  should_be_none = relations.pop(0)
  assert should_be_none is None
  
  final_map = {"rels": [],
              "tokens": sum(overall_maps["TOKEN"], []),
              "comment_id": comment_id}

  overall_maps["rels"] = []
  for nuc, sat, rel in relations:
    if rel == "span":
      continue
    final_map["rels"].append(
      (spans[nuc.start][0], spans[nuc.end][1], spans[sat.start][0],
        spans[sat.end][1], rel))

  return final_map

NUCLEUS = "Nucleus"
SATELLITE = "Satellite"
    
class Node(object):
  def __init__(self, span_start, span_end, ns, rel, parent=None):
    self.start = span_start
    self.end = span_end
    self.ns = ns
    self.rel = rel
    if parent is not None:
      self.parent = parent
    self.left = None
    self.right = None

  def __str__(self):
    return "({0}, {1})".format(self.start, self.end)

  def get_relation(self):
    if self.ns == ROOT:
      return None
    
    if self == self.parent.left:
      sibling = self.parent.right
    else:
      assert self == self.parent.right
      sibling = self.parent.left

    maybe_nuc = self
    maybe_sat = sibling

    if self.ns == SATELLITE:
      maybe_nuc, maybe_sat = maybe_sat, maybe_nuc
    else:
      assert self.ns == NUCLEUS

    return maybe_nuc, maybe_sat, self.rel

    
FIELDS_MAP = {
    "TOKEN": 2,
    "EDU": -1
    }


def main():

  input_dir, output_file = sys.argv[1:3]

  output = []

  for merge_filename in glob.glob(input_dir +"/*.merge"):
    comment_id = merge_filename.split("/")[-1].split(".")[0]
    listified_dataset = listify(merge_filename, FIELDS_MAP, comment_id)
    output.append(listified_dataset)

  with open(output_file, 'w') as f:
    f.write(json.dumps(output))
    #f.write(yaml.dump(output))


if __name__ == "__main__":
  main()
