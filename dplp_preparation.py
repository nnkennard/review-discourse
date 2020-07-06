import json
import os
import sys
from tqdm import tqdm



def main():
  input_file = sys.argv[1]
  output_dir = input_file.replace(".txt", "_DPLP")
  #os.makedirs(output_dir)

  with open(input_file, 'r') as f:
    data = json.loads(f.read())
    for example_id, text in tqdm(data["examples"].items()):
      with open(os.path.join(output_dir, example_id + ".txt"), 'w') as g:
        print(example_id)
        print(text["context"])
        print(text["text"])
        g.write("\n".join(text["context"] + [text["text"]]))


if __name__ == "__main__":
  main()
