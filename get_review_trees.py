import openreview
import pptree
import collections


def main():
  guest_client = openreview.Client(baseurl='https://openreview.net')
  pairs = []
  review_iterator = openreview.tools.iterget_notes(guest_client,
      invitation='ICLR.cc/2019/Conference/-/Paper.*/Public_Comment')
  for review in review_iterator:
    pairs.append((review.id, review.replyto))

  review_iterator = openreview.tools.iterget_notes(guest_client,
     invitation='ICLR.cc/2019/Conference/-/Paper.*/Official_Review')
  for review in review_iterator:
    pairs.append((review.id, review.replyto))


  for i, j in pairs:
    if i == j:
      print("oh")

  children, parents = zip(*pairs)
  roots = sorted(list(set(parents) - set(children)))
  print("SkMwpiR9Y7" in parents)
  print("SkMwpiR9Y7" in children)
  print("SkMwpiR9Y7" in roots)

  node_map = {}
  for root in roots:
    new_node = pptree.Node(root)
    node_map[root] = new_node

  children = collections.defaultdict(list)
  parents = {}




  def add_child(parent, child, node_map, parents):
    if parent not in node_map:
      grandparent = parents[parent]
      add_child(grandparent, parent, node_map, parents)
    new_node = pptree.Node(child, node_map[parent])
    node_map[child] = new_node

  for child, parent in pairs:
    children[parent].append(child)
    parents[child] = parent

  for parent, children in children.items():
    for child in children:
      add_child(parent, child, node_map, parents)

  for root in roots:
    pptree.print_tree(node_map[root])



if __name__ == "__main__":
  main()
