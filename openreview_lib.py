import time
import collections
import json
import openreview


from tqdm import tqdm

class Conference(object):
  iclr19 = "iclr19"
  iclr20 = "iclr20"
  ALL = [iclr19, iclr20]


INVITATION_MAP = {
    Conference.iclr19:'ICLR.cc/2019/Conference/-/Blind_Submission',
    Conference.iclr20:'ICLR.cc/2020/Conference/-/Blind_Submission',
}


def get_author(signatures):
 return "_".join(sorted(sig.split("/")[-1] for sig in signatures))


def get_strdate(note):
  return time.strftime(
      '%Y-%m-%d %H:%M:%S', time.localtime(note.tmdate/1000))

def get_text_if_any(note):
  if note.replyto is None:
    return ""
  else:
    maybe_content = note.content.get("review", note.content.get("comment",
      note.content.get("withdrawal confirmation", "")))
    return maybe_content


class NoteNode(object):

  def __init__(self, note, reply_to=None):
    self.note_id = note.id
    self.tcdate = note.tcdate
    self.text = get_text_if_any(note)
    self.author = get_author(note.signatures)
    self.creation_time = get_strdate(note)
    self.replies = []
    self.reply_to_id = note.replyto

  def __str__(self):
    return str(self.author) + str(self.reply_to_id) +  str(self.text)



class Dataset(object):
  def __init__(self, forum_list, client, conference, split):
    
    submissions = openreview.tools.iterget_notes(
          client, invitation=INVITATION_MAP[conference])
    self.forums = [n.forum for n in submissions if n.forum in forum_list]
    self.client = client
    self.conference = conference
    self.split = split
    self.forum_map, self.node_map = self._get_forum_map()

  def _get_forum_map(self):
    """Builds a forum map, which maps forum ids to a dict tree of note ids."""
    root_map = {}
    node_map = {}
    for forum_id in tqdm(self.forums):
      forum_structure, forum_node_map = self._get_forum_structure(forum_id)
      root_map[forum_id] = forum_structure
      node_map.update(forum_node_map)

    return root_map, node_map


  def _get_forum_non_orphans(self, parents):

    children = collections.defaultdict(list)
    for child, parent in parents.items():
      children[parent].append(child)

    descendants = sum(children.values(), [])
    ancestors = children.keys()
    nonchildren = set(ancestors) - set(descendants)
    orphans = sorted(list(nonchildren - set([None])))

    while orphans:
      current_orphan = orphans.pop()
      orphans += children[current_orphan]
      del children[current_orphan]

    new_parents = {}
    for parent, child_list in children.items():
      for child in child_list:
        assert child not in new_parents
        new_parents[child] = parent

    return new_parents 


  def get_non_orphans(self):
    non_orphans = set()
    for forum, parent_structure in self.forum_map.items():
      parents = self._get_forum_non_orphans(parent_structure)
      available_notes = set(parents.keys()).union(
        set(parents.values())) - set([None])
      assert not non_orphans.intersection(available_notes)
      non_orphans = non_orphans.union(available_notes)

    return sorted(list(non_orphans))


  def _get_forum_structure(self, forum_id):
    """Builds the reply structure for one forum."""

    notes = self.client.get_notes(forum=forum_id)
    node_map = {note.id:NoteNode(note) for note in notes}
    parents = {note.id:note.replyto for note in notes}

    parents = self._get_forum_non_orphans(parents)
    available_notes = set(parents.keys()).union(
        set(parents.values())) - set([None])
    new_node_map = {note_id: node for note in notes if note in available_notes}

    return parents, new_node_map

  def _context_builder(self, current_note_id, forum_structure, context_map):
    if current_note_id in context_map:
      return
    else:
      parent_id = forum_structure[current_note_id]
      if parent_id is None:
        context_map[current_note_id] = []
      elif parent_id not in context_map:
        self._context_builder(parent_id, forum_structure, context_map)
        context_map[current_note_id] = context_map[parent_id] + [self.node_map[parent_id].text]

  def build_contextualized_examples(self):
    """Adds context for each node."""
    context_map = collections.defaultdict(list)
    context_map[None] = []
    for forum_id, forum_structure in self.forum_map.items():
      for child, parent in forum_structure.items():
        self._context_builder(child, forum_structure, context_map)
    self.context_map = context_map

  def _calculate_leaves(self):
    leaves = []
    for forum, structure in self.forum_map.items():
      # Nodes that are children but never parents
      forum_leaves = set(structure.keys()) - set(structure.values())
      leaves += forum_leaves
    return leaves


  def dump_contextualized_examples(self, leaves_only=False):
    contextualized_examples = {}
    print(len(self.context_map))
    leaves = self._calculate_leaves()
    for example, context in self.context_map.items():
      if example is None:
        continue
      if leaves_only and example not in leaves:
        continue
      contextualized_examples[example] = {
          "context": context,
          "text": self.node_map[example].text
      }
    return json.dumps({
    "conference": self.conference,
    "split": self.split,
    "url": INVITATION_MAP[self.conference],
    "examples": contextualized_examples})
