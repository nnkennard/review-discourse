import collections
import json
import openreview
import sys
import random

from tqdm import tqdm

import openreview_lib as orl

def get_forum_ids(guest_client, invitation):
  submissions = openreview.tools.iterget_notes(
        guest_client, invitation=invitation)
  return [n.forum for n in submissions]

TRAIN, DEV, TEST = ("train", "dev", "test")

def split_forums(forums):
  random.shuffle(forums)
  train_threshold = int(0.6 * len(forums))
  dev_threshold = int(0.8 * len(forums))

  return (forums[:train_threshold],
      forums[train_threshold:dev_threshold], forums[dev_threshold:])

class Forum(object):
  def __init__(self, forum_id, client):
    self.forum_id = forum_id
    notes = client.get_notes(forum=forum_id)
    self.num_notes = len(notes)

def main():

  conference = sys.argv[1]

  guest_client = openreview.Client(baseurl='https://openreview.net')

  forum_ids = get_forum_ids(guest_client, orl.INVITATION_MAP[conference])

  len_counter = collections.Counter()

  forums = []
  for forum_id in tqdm(forum_ids):
    new_forum = Forum(forum_id, guest_client)
    len_counter[new_forum.num_notes] += 1
    forums.append(new_forum)

  total_notes = sum(len_counter.values())
  bottom_quintile_count = int(0.2 * total_notes)
  top_quintile_count = int(0.8 * total_notes)

  bottom_quintile_num_posts = None
  top_quintile_num_posts = None

  num_notes_seen = 0
  for num_posts in sorted(len_counter.keys()):
    num_notes = len_counter[num_posts]
    num_notes_seen += num_notes
    if bottom_quintile_num_posts is None:
      if num_notes_seen > bottom_quintile_count:
        bottom_quintile_num_posts = num_posts
    elif top_quintile_num_posts is None:
      if num_notes_seen > top_quintile_count:
        top_quintile_num_posts = num_posts
        break

  small_forums = [forum for forum in forums if forum.num_notes <=
    bottom_quintile_num_posts]

  large_forums = [forum for forum in forums if forum.num_notes >=
    top_quintile_num_posts]

  medium_forums = [forum 
    for forum in forums
    if forum not in small_forums and forum not in large_forums]

  forum_name_map = collections.defaultdict(list)

  for forum_set in [medium_forums, small_forums, large_forums]:
    train, dev, test = split_forums(forum_set)
    forum_name_map[TRAIN] += [forum.forum_id for forum in train]
    forum_name_map[DEV] += [forum.forum_id for forum in dev]
    forum_name_map[TEST] += [forum.forum_id for forum in test]


  dataset = {
    "conference": conference,
    "url": orl.INVITATION_MAP[conference],
    "id_map": forum_name_map}

  with open(conference + "_split.json", 'w') as f:
    f.write(json.dumps(dataset))


if __name__ == "__main__":
  main()
