import collections
import corenlp
import json
import openreview
import sys
import tqdm

class Dataset(object):
  def __init__(self, iclr_client, nlp_client, forums):
    self.forums = []
    for forum_id in tqdm.tqdm(forums):
      self.forums.append(Forum(iclr_client, nlp_client, forum_id))

  def get_all_notes(self):
    return sum([forum.get_all_notes() for forum in self.forums], [])

class Forum(object):
  def __init__(self, iclr_client, nlp_client, forum_id):
    original_notes = iclr_client.get_notes(forum=forum_id)
    self.notes = [Note(note.content.get("comment", ""), note.id, nlp_client, forum_id)
        for note in original_notes]

  def get_all_notes(self):
    return sum([note.parses for note in self.notes], [])


def get_parses(paragraph):
  return []

def mostly_alpha(text):
  nonspace = "".join(text.split())
  if not nonspace:
    return False
  total_chars = len(nonspace)
  alpha_chars = len([c for c in nonspace if c.isalpha()])
  ratio = alpha_chars/total_chars
  return ratio > 0.8

class Note(object):
  def __init__(self, note, note_id, nlp_client, forum_id):
    self.paragraphs = self.get_text_paragraphs(note)
    self.parses = self.get_paragraph_parses(nlp_client, forum_id, note_id)

  def get_text_paragraphs(self, comment):
    return [para
            for para in comment.split("\n")
            if para.split() and mostly_alpha(para)]

  def get_paragraph_parses(self, nlp_client, forum_id, note_id):
    parse_lines = []
    for i, para in enumerate(self.paragraphs):
      if not para.split():
        continue
      conll_lines = nlp_client.annotate(para).split("\n")
      for line in conll_lines:
        if line.strip():
          parse_lines.append("\t".join([forum_id, note_id, str(i), line]))
        else:
          parse_lines.append(line)
    return parse_lines

def main():
  dataset_file = sys.argv[1]

  with corenlp.CoreNLPClient(
      annotators="tokenize ssplit pos lemma ner depparse".split(),
      endpoint="http://localhost:9191", timeout=1000000, be_quiet=False,
      output_format="conll") as nlp_client:

    iclr_client = openreview.Client(baseurl='https://openreview.net')
    with open(dataset_file, 'r') as f:
      dataset_obj = json.loads(f.read())

  for set_split in ["dev", "test"]:
    split_set = Dataset(iclr_client, nlp_client,
        dataset_obj["id_map"][set_split])

    with open(dataset_file.split(".")[0] + "_" + set_split + ".parse", 'w') as f:
      f.write("\n".join(split_set.get_all_notes()))
  

if __name__ == "__main__":
  main()
