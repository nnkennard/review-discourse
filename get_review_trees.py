import sys
import json
import openreview
import pptree
import collections
import time
from tqdm import tqdm

def get_strdate(note):
  return time.strftime(
      '%Y-%m-%d %H:%M:%S', time.localtime(note.tmdate/1000))

def get_stats(self):
  depths = [node.depth for node in self.node_map.values()]
  mean_depth = mean(depths)
  max_depth = max(depths)
  num_messages = len(self.node_map)
  num_participants = len(set(node.author for node in self.node_map.values()))
  branching_factor = self.get_branching_factor()
  return (self.forum_id, mean_depth, max_depth, branching_factor,
      num_messages, num_participants)



def get_forum_ids():
  forum_ids = []
  with open("iclr19_metadata.jsonl", 'r') as f:
    for line in f:
      forum_ids.append(json.loads(line)["forum"])
  return forum_ids

def get_author(signatures):
 return "_".join(sorted(sig.split("/")[-1] for sig in signatures))


class NoteNode(object):

  def __init__(self, note, reply_to=None):
    self.note_id = note.id
    self.author = get_author(note.signatures)
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
    if parent not in parents:
      return False
    grandparent = parents[parent]
    maybe_success = add_child(parent, grandparent, node_map, note_map, parents)
    return maybe_success
  child_note = note_map[child]
  new_node = NoteNode(child_note, node_map[child_note.replyto])
  node_map[child] = new_node
  return True

def mean(vals):
  return sum(vals)/float(len(vals))

class Forum(object):
  def __init__(self, forum_id, client):

    self.forum_id = forum_id
    notes = client.get_notes(forum=forum_id)
    self.note_map = {note.id:note for note in notes}

    parents = {note.id:note.replyto for note in notes}

    candidate_roots = [note for note in notes if note.replyto is None]
    assert len(candidate_roots) == 1
    root_note, = candidate_roots
    self.root_node = NoteNode(root_note)

    self.node_map = {root_note.id: self.root_node}

    for note_id, note in self.note_map.items():
      if note_id in self.node_map:
        continue
      else:
        assert note.id is not None
        status = add_child(note_id, note.replyto,
            self.node_map, self.note_map, parents)

    
  def get_branching_factor(self):
    num_non_root = len(self.node_map) - 1
    num_non_leaf = len([node for node in self.node_map.values() if not
        node.replies])
    return num_non_root/num_non_leaf


def main():
  guest_client = openreview.Client(baseurl='https://openreview.net')

  forum_ids = get_forum_ids()

  forums = {}
  records = []
  for forum_id in tqdm(forum_ids):
    new_forum = Forum(forum_id, guest_client)
    forums[forum_id] = new_forum


if __name__ == "__main__":
  main()
