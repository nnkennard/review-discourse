def listify_conll_dataset(filename):
  with open(filename, 'r') as f:
    lines = f.readlines()
    return listify_conll_lines(lines)


def listify_conll_lines(lines):
 
  dataset = []
  curr_doc = []
  curr_sent = []

  for line in lines:
    if "\t" in line:
      fields = line.strip().split("\t")
    else:
      fields = line.strip().split()

    if line.startswith("#begin"):
      assert not curr_doc
      curr_doc.append([fields])

    elif line.startswith("#end"):
      curr_doc.append([fields])
      dataset.append(curr_doc)
      curr_doc = []

    elif not line.strip():
      if curr_sent:
        curr_doc.append(curr_sent)
        curr_sent = []

    else: # Empty line signifies the end of a sentence
      curr_sent.append(fields)

  return dataset


def listify_non_doc_lines(lines):
  document = []
  curr_sent = []
  for line in lines:
    if "\t" in line:
      fields = line.strip().split("\t")
    else:
      fields = line.strip().split()

    if not line.strip():
      if curr_sent:
        document.append(curr_sent)
        curr_sent = []

    else: # Empty line signifies the end of a sentence
      curr_sent.append(fields)
  return document


