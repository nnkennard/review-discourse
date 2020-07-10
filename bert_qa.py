import torch
from transformers import BertForQuestionAnswering
from transformers import BertTokenizer


def find_answer(question, passage, tokenizer, model):
  input_ids = tokenizer.encode(question, answer_text)

  tokens = tokenizer.convert_ids_to_tokens(input_ids)


#question = "How many parameters does BERT-large have?"
#answer_text = "BERT-large is really big... it has 24-layers and an embedding size of 1,024, for a total of 340M parameters! Altogether it is 1.34GB, so expect it to take a couple minutes to download to your Colab instance."
# Apply the tokenizer to the input text, treating them as a text-pair.

print('The input has a total of {:} tokens.'.format(len(input_ids)))
# tokenizer's behavior, let's also get the token strings and display them.

# For each token and its id...
for token, id in zip(tokens, input_ids):
  # If this is the [SEP] token, add some space around it to make it stand out.
  if id == tokenizer.sep_token_id:
    print('')
  # Print the token string and its ID in two columns.
  print('{:<12} {:>6,}'.format(token, id))
  if id == tokenizer.sep_token_id:
      print('')

# Search the input_ids for the first instance of the `[SEP]` token.
sep_index = input_ids.index(tokenizer.sep_token_id)

# The number of segment A tokens includes the [SEP] token istelf.
num_seg_a = sep_index + 1

# The remainder are segment B.
num_seg_b = len(input_ids) - num_seg_a

# Construct the list of 0s and 1s.
segment_ids = [0]*num_seg_a + [1]*num_seg_b

# There should be a segment_id for every input token.
assert len(segment_ids) == len(input_ids)

# Run our example through the model.
start_scores, end_scores = model(torch.tensor([input_ids]), # The tokens representing our input text.
                                     token_type_ids=torch.tensor([segment_ids]))
# The segment IDs to differentiate question from answer_text

# Find the tokens with the highest `start` and `end` scores.
answer_start = torch.argmax(start_scores)
answer_end = torch.argmax(end_scores)

# Combine the tokens in the answer and print it out.
answer = ' '.join(tokens[answer_start:answer_end+1])

print('Answer: "' + answer + '"')

def main():
  model = BertForQuestionAnswering.from_pretrained('bert-large-uncased-whole-word-masking-finetuned-squad')
  tokenizer = BertTokenizer.from_pretrained('bert-large-uncased-whole-word-masking-finetuned-squad')


if __name__ == "__main__":
  main()
