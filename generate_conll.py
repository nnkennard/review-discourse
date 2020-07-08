import corenlp
import json
import openreview
import sys

import openreview_lib as orl

ANNOTATORS = "tokenize ssplit pos lemma ner depparse".split()
def main():
  dataset_file = sys.argv[1]

  with open(dataset_file, 'r') as f:
    examples = json.loads(f.read())


  with corenlp.CoreNLPClient(
      annotators=ANNOTATORS, timeout=100000,
      output_format="conll") as client:
    guest_client = openreview.Client(baseurl='https://openreview.net')
    conference = examples["conference"]
    assert conference in orl.Conference.ALL 

    for set_split, forum_ids in examples["id_map"].items():
      dataset = orl.Dataset(forum_ids, guest_client, conference, set_split)
      filepath = conference + "/" + set_split + "/"
      dataset.dump_to_conll(filepath, client)


if __name__ == "__main__":
  main()
