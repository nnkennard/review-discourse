
import collections
import json
import openreview
import os
import pptree
import sys
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



def get_forum_ids(guest_client, invitation):
  submissions = openreview.tools.iterget_notes(
        guest_client, invitation='ICLR.cc/2019/Conference/-/Blind_Submission')
  return [n.forum for n in submissions]


def get_author(signatures):
 return "_".join(sorted(sig.split("/")[-1] for sig in signatures))


class NoteNode(object):

  def __init__(self, note, reply_to=None):
    self.note_id = note.id
    self.tcdate = note.tcdate
    self.author = get_author(note.signatures)
    self.creation_time = get_strdate(note)
    self.replies = []
    if reply_to:
      self.depth = reply_to.depth + 1
      reply_to.replies.append(self)
      self.reply_to_id = reply_to.note_id
    else:
      self.depth = 0
      self.reply_to_id = None

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

def shortened_author(author):
  if author.startswith("AnonReviewer"):
    return "R"
  if author.startswith("Author"):
    return "A"
  if author.startswith("Conference"):
    return "X"
  if author.startswith("Area_Chair"):
    return "C"
  if author.startswith("(anonymous)"):
    return "S" # Spectator
  else:
    return "N" # Actual name


def get_parent_index(node, ordered_nodes):
  if node.reply_to_id is None:
    return len(ordered_nodes)
  print("reply to, ", node.reply_to_id)
  print(list(n.note_id for n in ordered_nodes))
  for i, maybe_parent in enumerate(ordered_nodes):
    if maybe_parent.note_id == node.reply_to_id:
      return i
  dsds

class FlatTree(object):
  def __init__(self, forum):
    ordered_nodes = sorted(forum.node_map.values(), key=lambda x:x.tcdate)
    tree_list = [
        (shortened_author(node.author), get_parent_index(node, ordered_nodes))
        for node in ordered_nodes
        ]

    for j in tree_list:
      print(j)

    print()

    for i in ordered_nodes:
      print(i.note_id, i.creation_time)
    print()
    pass


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

  def print_out_comments(self, output_dir, prefix):
    lines = []
    for note_id, note in self.note_map.items():
      output_file = os.path.join(output_dir, prefix + note_id + ".txt")
      if "comment" in note.content:
        lines.append("\t".join(
          [self.forum_id, note_id,
            note.content["comment"].replace("\t", " ").replace("\n", "NEWLINE")]))

    return lines


def main():

  output_dir = sys.argv[1]

  guest_client = openreview.Client(baseurl='https://openreview.net')
  INVITATION = 'ICLR.cc/2019/Conference/-/Blind_Submission'

  forum_ids = get_forum_ids(guest_client, INVITATION)

  print("Got ", len(forum_ids), " forum ids.")

  all_lines = []
  for forum_id in tqdm(forum_ids):
    new_forum = Forum(forum_id, guest_client)
    all_lines += new_forum.print_out_comments(output_dir, "ICLR2019_")

  with open(os.path.join(output_dir, "ICLR_2019_notes.txt"), 'w') as f:
    f.write("\n".join(all_lines))


    
if __name__ == "__main__":
  main()
