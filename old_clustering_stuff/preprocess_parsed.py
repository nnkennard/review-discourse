import collections
import gzip
import re
import sys

import encode

def process_token(token, pos, unigram_map, rare_threshold=4000):
  token = token.lower()
  if '_' in token:
    return "SYMB"
  if token.isdigit():
    return "NUM"
  else:
    parts = re.split("[0-9]+", token)
    if len(parts) > 1:
      return "NUM".join(parts)
    else:
      if not token.isalpha():
        if token in """.,?!;:'"`""":
          return token
        else:
          return "SYMB"
      print(unigram_map[token])
      if unigram_map[token] < rare_threshold and pos in ["NN", "NNS"]:
        return "RARE"
      else:
        return token

def build_unigram_map(unigram_file):
  unigram_counts = collections.Counter()
  with gzip.open(unigram_file, 'r') as f:
    for line in f:
      count, word = line.strip().split()
      unigram_counts[word.decode('utf-8').lower()] += int(count)
  return unigram_counts



def main():
  unigram_file, conll_file = sys.argv[1:3]
  conll_output_file = conll_file.replace(
      ".parse", ".parse.proc")

  unigram_map = build_unigram_map(unigram_file)
  with open(conll_file, 'r') as f:
    with open(conll_output_file, 'w') as g:
      for line in f:
        if not line.split():
          g.write(line)
        else:
          fields = line.split("\t")
          new_token = fields[encode.TOKEN]
          new_token = process_token(
              fields[encode.TOKEN], fields[encode.POS],  unigram_map)
          new_fields = fields[
            :encode.TOKEN + 1] + [new_token] + fields[encode.TOKEN + 1:]
          g.write("\t".join(fields))



if __name__ == "__main__":
  main()
