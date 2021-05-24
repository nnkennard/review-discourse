import csv
import sys
import torch
from transformers import BertForQuestionAnswering
from transformers import BertTokenizer

import openreview_lib as orl
import conll_lib


def find_answer(question, passage, tokenizer, model):
  input_ids = tokenizer.encode(question, passage, max_length=512)
  tokens = tokenizer.convert_ids_to_tokens(input_ids)

  sep_index = input_ids.index(tokenizer.sep_token_id)
  num_seg_a = sep_index + 1

  input_ids = input_ids[:512]

  num_seg_b = len(input_ids) - num_seg_a
  segment_ids = [0]*num_seg_a + [1]*num_seg_b
  assert len(segment_ids) == len(input_ids)
  
  start_scores, end_scores = model(
      torch.tensor([input_ids]), 
      token_type_ids=torch.tensor([segment_ids]))

  answer_start = torch.argmax(start_scores)
  answer_end = torch.argmax(end_scores)

  return ' '.join(tokens[answer_start:answer_end+1])

TOKEN_IDX = 4

def get_questions_from_comment(note_id):
  filename = "./const/iclr19/train/" + note_id + ".txt"
  try:
    listified_dataset = conll_lib.listify_conll_dataset(filename)
  except FileNotFoundError:
    return []

  questions = []
  for document in listified_dataset:
    for sentence in document:
      last_token = sentence[-1]
      if last_token[0].startswith("#"): # This is a begin or end
        continue
      if last_token[TOKEN_IDX] == "?":
        questions.append(" ".join([token[TOKEN_IDX] for token in sentence]))
     
  return questions


def create_qa_examples(dataset):
  qa_examples = []
  for root, forum_structure in dataset.forum_map.items():
    for child, parent in forum_structure.items():
      if parent is None:
        continue
      questions = get_questions_from_comment(parent)
      qa_examples += [
          (parent, child, question, dataset.node_map[child].text)
          for question in questions]

  return qa_examples
    
def main():
  
  dataset_file = sys.argv[1]

  datasets = orl.get_datasets(dataset_file)
  qa_examples = create_qa_examples(datasets["train"])

  model = BertForQuestionAnswering.from_pretrained('bert-large-uncased-whole-word-masking-finetuned-squad')
  tokenizer = BertTokenizer.from_pretrained('bert-large-uncased-whole-word-masking-finetuned-squad')

  records = []
  with open('iclr19_train_qa.csv', 'w', newline='') as csvfile:
    spamwriter = csv.writer(csvfile, delimiter='|')

    for parent, child, question, passage in qa_examples:
      spamwriter.writerow([
        parent, child, question,
        find_answer(question, passage, tokenizer, model)])


if __name__ == "__main__":
  main()
