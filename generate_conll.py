import corenlp
import json
import openreview
import sys

import openreview_lib as orl


ANNOTATORS = "tokenize ssplit pos lemma".split()


def main():
  dataset_file = sys.argv[1]

  with corenlp.CoreNLPClient(
      annotators=ANNOTATORS, timeout=200000,
      output_format="conll") as conll_client:

    with corenlp.CoreNLPClient(
        annotators=ANNOTATORS, timeout=200000,
        output_format="json") as json_client:

      conference = "iclr19"
      datasets = orl.get_datasets(dataset_file)
      for set_split, dataset in datasets.items():
        filepath = "tokenized/" + conference + "/" + set_split + "/"
        dataset.dump_to_conll(filepath, conll_client, json_client,
            no_parse=True)


if __name__ == "__main__":
  main()
