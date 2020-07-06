import json
import openreview
import sys

import openreview_lib as orl


def main():
  dataset_file, parse_prefix = sys.argv[1:]


  with open(dataset_file, 'r') as f:
    examples = json.loads(f.read())

  guest_client = openreview.Client(baseurl='https://openreview.net')
  conference = examples["conference"]
  assert conference in orl.Conference.ALL 

  for set_split, forum_ids in examples["id_map"].items():
    dataset = orl.Dataset(forum_ids, guest_client, conference, set_split)
    dataset.build_contextualized_examples()
    out_file = "".join([parse_prefix, "/", conference, "_", set_split,
    "_contextualized_leaves.txt"])
    with open(out_file, 'w') as f:
      f.write(dataset.dump_contextualized_examples(leaves_only=True))
  

if __name__ == "__main__":
  main()
