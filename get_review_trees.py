import sys
import json
import openreview
import pptree
import collections
import time


class NoteNode(object):

  def __init__(self, note, reply_to=None):
    self.note_id = note.id
    self.author = note.signatures[0].split("/")[-1]
    self.creation_time = get_strdate(note)
    self.replies = []
    if reply_to:
      self.depth = reply_to.depth + 1
      reply_to.replies.append(self)
    else:
      self.depth = 0

  def __str__(self):
    return self.author


def add_child(child, parent, node_map, note_map, parents):
  if parent not in node_map:
    grandparent = parents[parent]
    add_child(parent, grandparent, node_map, note_map, parents)
  child_note = note_map[child]
  new_node = NoteNode(child_note, node_map[child_note.replyto])
  node_map[child] = new_node

def mean(vals):
  return sum(vals)/float(len(vals))

class Forum(object):
  def __init__(self, forum_id, client):

    self.forum_id = forum_id
    notes = client.get_notes(forum=forum_id)
    print(notes[0].content.get("rating", ""))
    self.note_map = {note.id:note for note in notes}

    parent_map = {note.id: note.replyto for note in notes
        if note.replyto is not None}

    children, parents = zip(*((k,v) for k,v in parent_map.items()))
    roots = set(parents) - set(children)
    #TODO Fix this assumption
    for root in roots:
      try:

        self.node_map = {}

        root_note = self.note_map[root]
        root_node = NoteNode(root_note)
        self.node_map[root] = root_node

        for non_root in children:
          if non_root == root:
            continue
          note = self.note_map[non_root]
          if note.replyto is None:
            continue
          add_child(non_root, note.replyto, self.node_map, self.note_map, parent_map)
        self.root_node = self.node_map[root]
        break
      except KeyError:
        pass

  def get_branching_factor(self):
    num_non_root = len(self.node_map) - 1
    num_non_leaf = len([node for node in self.node_map.values() if not
        node.replies])
    return num_non_root/num_non_leaf

  def get_stats(self):
    depths = [node.depth for node in self.node_map.values()]
    mean_depth = mean(depths)
    max_depth = max(depths)
    num_messages = len(self.node_map)
    num_participants = len(set(node.author for node in self.node_map.values()))
    branching_factor = self.get_branching_factor()
    return (self.forum_id, mean_depth, max_depth, branching_factor, num_messages,
        num_participants)


def get_strdate(note):
  return time.strftime(
      '%Y-%m-%d %H:%M:%S', time.localtime(note.tmdate/1000))

def get_forum_ids():
  forum_ids = []
  with open("iclr19_metadata.jsonl", 'r') as f:
    for line in f:
      forum_ids.append(json.loads(line)["forum"])
  return forum_ids

def main():
  guest_client = openreview.Client(baseurl='https://openreview.net')

  forum_ids = get_forum_ids()

  forums = {}
  records = []
  for forum_id in forum_ids:
    try:
      new_forum = Forum(forum_id, guest_client)
      forums[forum_id] = new_forum

      sys.stdout = open("trees/"+forum_id+".txt", 'w')
      pptree.print_tree(new_forum.root_node, "replies")
      records.append(new_forum.get_stats())
      
    except AttributeError as e:
      print(e)
  with open("tree_details.tsv", 'w') as f:
    for i, record in enumerate(records[:100]):
      f.write("\t".join(str(i) for i in record) + "\n")
      


if __name__ == "__main__":
  main()
