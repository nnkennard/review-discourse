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
      annotators=ANNOTATORS, timeout=100000, be_quiet=False,
      output_format="conll") as client:
    guest_client = openreview.Client(baseurl='https://openreview.net')
    conference = examples["conference"]
    assert conference in orl.Conference.ALL 

    for split, dataset in non_orphans.items():
      filepath = conference + "/" + split + ".txt"
      dataset.dump_to_conll(filepath, client)

    assert "_split" in dataset_file
    out_file = dataset_file.replace("_split", "_nonorphans")
    with open(out_file, 'w') as f:
      f.write(json.dumps(non_orphans))


if __name__ == "__main__":
  main()
