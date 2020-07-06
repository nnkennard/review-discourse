import json
import openreview
import sys

import openreview_lib as orl


def main():
  dataset_file = sys.argv[1]

  with open(dataset_file, 'r') as f:
    examples = json.loads(f.read())

  guest_client = openreview.Client(baseurl='https://openreview.net')
  conference = examples["conference"]
  assert conference in orl.Conference.ALL 

  non_orphans = {}
  for set_split, forum_ids in examples["id_map"].items():
    dataset = orl.Dataset(forum_ids, guest_client, conference, set_split)
    non_orphans[set_split] = dataset.get_non_orphans()

  assert "_split" in dataset_file
  out_file = dataset_file.replace("_split", "_nonorphans")
  with open(out_file, 'w') as f:
    f.write(json.dumps(non_orphans))


if __name__ == "__main__":
  main()
