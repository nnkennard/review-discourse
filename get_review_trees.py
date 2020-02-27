import openreview
import pptree
import collections
import time


PUBLIC_COMMENT_URL = 'ICLR.cc/2019/Conference/-/Paper.*/Public_Comment'
OFFICIAL_REVIEW_URL = 'ICLR.cc/2019/Conference/-/Paper.*/Official_Review'

class Note:

  def __init__(self, note_id, author, creation_time, reply_to=None):
    self.note_id = note_id
    self.author = author
    self.creation_time = creation_time
    self.replies = []
    if reply_to:
        reply_to.replies.append(self)

  def __str__(self):
    return self.note_id


def get_notes_from_url(client, invitation):
  return list(
      openreview.tools.iterget_notes(client, invitation=invitation))

def add_children(parent, children, node_map, parents):
  if parent not in node_map:
    grandparent = parents[parent]
    add_children(grandparent, children[grandparent], node_map, parents)
  new_node = pptree.Node(child, node_map[parent])
  node_map[child] = new_node



def add_child(parent, child, node_map, parents):
  if parent not in node_map:
    grandparent = parents[parent]
    add_child(grandparent, parent, node_map, parents)
  new_node = pptree.Node(child, node_map[parent])
  node_map[child] = new_node

def convert_note_list_to_trees(note_list):
  pairs = [(note.id, note.replyto) for note in note_list]
  children, parents = zip(*pairs)
  roots = sorted(list(set(parents) - set(children)))

  node_map = {root:pptree.Node(root) for root in roots}

  children = collections.defaultdict(list)
  parents = {}
  for child, parent in pairs:
    children[parent].append(child)
    parents[child] = parent

  for parent, children in children.items():
    for child in children:
      add_child(parent, child, node_map, parents)

  return node_map, roots

class NoteNode:

    def __init__(self, or_note, head=None):
        self.or_note = or_note
        self.replies = []
        if head:
            head.replies.append(self)

    def __str__(self):
        return "huh"

def get_strdate(note):
  return time.strftime(
      '%Y-%m-%d %H:%M:%S', time.localtime(note.tmdate/1000))

def main():
  guest_client = openreview.Client(baseurl='https://openreview.net')

  note_list = sum([
      get_notes_from_url(guest_client, PUBLIC_COMMENT_URL),
      get_notes_from_url(guest_client, OFFICIAL_REVIEW_URL)], [])

  note_map = {note.id + " " + get_strdate(note):note for note in note_list}

  node_map, roots = convert_note_list_to_trees(note_list)

  for root in roots:
    pptree.print_tree(node_map[root])

  _unused_stuff = """
  signature_tails = []
  for k, v in note_map.items():
    signature_tails.append(v.signatures[0].split("/")[-1])

  b = collections.Counter(signature_tails)

  for k,v in b.most_common():
    print(str(v) + "\t" + k)"""

if __name__ == "__main__":
  main()
