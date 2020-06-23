import collections
import glob
import os
import sys

def get_fields(line, field_map):
  fields = line.strip().split()
  selection_map = {}
  for field_name, index in field_map.items():
    selection_map[field_name] = fields[index]
  return selection_map


def listify(merge_filename, field_map):

  with open(merge_filename, 'r') as f:
    lines = f.readlines()

  overall_maps = {name: [] for name in field_map.keys()}
  current_sentence = collections.defaultdict(list)

  for line in lines:
    if not line.strip():
      for k, v in current_sentence.items():
        overall_maps[k].append(v)
      current_sentence = collections.defaultdict(list)
    else:
      selected_fields = get_fields(line, field_map)
      for name, value in selected_fields.items():
        current_sentence[name].append(value)
  if current_sentence:
    assert False

  spans = {}
  token_labels = sum(overall_maps["EDU"], []) + ["DUMMY"]
  span_start_finder = 0
  span_end_finder = 0

  while span_end_finder < len(token_labels) - 1: # -1 due to dummy
    while token_labels[span_end_finder] == token_labels[span_start_finder]:
      span_end_finder += 1
    assert token_labels[span_start_finder] == token_labels[span_end_finder - 1]
    spans[token_labels[span_start_finder]] = (span_start_finder,
        span_end_finder)
    span_start_finder = span_end_finder
  
  overall_maps["spans"] = spans

  brackets_file = merge_filename.replace(".merge", ".brackets")
  overall_maps["brackets"] = {}
  with open(brackets_file, 'r') as f:
    for line in f:
      (edu_span, link, link_type) = eval(line)

      assert edu_span not in overall_maps["brackets"]
      overall_maps["brackets"][edu_span] = (link, link_type)

  return overall_maps


FIELDS_MAP = {
    "TOKEN": 2,
    "EDU": -1
    }



def main():

  input_dir = sys.argv[1]

  for merge_filename in glob.glob(input_dir +"/*.merge"):
    listified_dataset = listify(merge_filename, FIELDS_MAP)
    exit()


  pass


if __name__ == "__main__":
  main()
