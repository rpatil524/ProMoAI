from copy import deepcopy

from powl.objects.tagged_powl import Activity, ChoiceGraph, PartialOrder

from powl.objects.tagged_powl.base import TaggedPOWL
from powl.objects.tagged_powl.builders import loop, silent_activity, xor


def get_node_type(node):
    if node.__class__ is Activity:
        return f"Activity ({node.label})"
    elif node.__class__ is PartialOrder:
        return "PartialOrder"
    elif node.__class__ is ChoiceGraph:
        return "DecisionGraph"
    else:
        return node.__class__


class ModelGenerator:
    def __init__(
        self,
        enable_nested_partial_orders=True,
        copy_duplicates=False,
        enable_nested_decision_graphs=True,
    ):
        self.used_as_submodel = []
        self.nested_partial_orders = enable_nested_partial_orders
        self.copy_duplicates = copy_duplicates
        self.nested_decision_graphs = enable_nested_decision_graphs

    def activity(self, label, pool: str = None, lane: str = None):
        return Activity(label, organization=pool, role=lane)

    def silent_transition(self):
        return silent_activity()

    def create_model(self, node: TaggedPOWL):
        if node is None:
            res = silent_activity()
        else:
            if isinstance(node, str):
                node = self.activity(node)
            elif not isinstance(node, TaggedPOWL):
                raise Exception(
                    f"Only POWL models are accepted as submodels! You provide instead: {type(node)}."
                )
            if node in self.used_as_submodel:
                if self.copy_duplicates:
                    res = deepcopy(node)
                else:
                    node_type = get_node_type(node)
                    raise Exception(
                        f"Ensure that"
                        f" each submodel is used uniquely! Avoid trying to"
                        f" reuse submodels that were used as children of other constructs (xor, loop,"
                        f" or partial_order) before! The error occured when trying to reuse a node of type {node_type}."
                    )
            else:
                res = node
        self.used_as_submodel.append(res)
        return res

    def xor(self, *args):
        if len(args) < 2:
            raise Exception("Cannot create an xor of less than 2 submodels!")
        children = [self.create_model(child) for child in args]
        res = xor(children=children)
        return res

    def loop(self, do, redo):
        if do is None and redo is None:
            raise Exception(
                "Cannot create an empty loop with both the do and redo parts missing!"
            )
        res = loop(do=self.create_model(do), redo=self.create_model(redo))
        return res

    def partial_order(self, dependencies):
        list_children = []
        for dep in dependencies:
            if isinstance(dep, tuple):
                for n in dep:
                    if n not in list_children:
                        list_children.append(n)
            elif isinstance(dep, TaggedPOWL):
                if dep not in list_children:
                    list_children.append(dep)
            else:
                raise Exception(
                    "Invalid dependencies for the partial order! You should provide a list that contains"
                    " tuples of POWL models!"
                )
        if len(list_children) == 1:
            return list_children[0]
        if len(list_children) == 0:
            raise Exception("Cannot create a partial order over 0 submodels!")
        children = dict()
        for child in list_children:
            new_child = self.create_model(child)
            children[child] = new_child

        if self.nested_partial_orders:
            pass
        else:
            for child in children:
                if isinstance(child, PartialOrder):
                    raise Exception(
                        "Do not use partial orders as 'direct children' of other partial orders."
                        " Instead, combine dependencies at the same hierarchical level. Note that it is"
                        " CORRECT to have 'partial_order > xor/loop > partial_order' in the hierarchy,"
                        " while it is"
                        " INCORRECT to have 'partial_order > partial_order' in the hierarchy.'"
                    )
        edges = [
            (dep[i], dep[i + 1]) for dep in dependencies for i in range(len(dep) - 1)
        ]
        res = PartialOrder(nodes=list(children.values()), edges=edges)
        return res

    def decision_graph(self, dependencies):
        list_children = []
        for dep in dependencies:
            if isinstance(dep, tuple):
                if len(dep) != 2:
                    raise Exception(
                        "Invalid dependency tuple in decision graph! Each tuple must contain exactly 2 elements."
                    )
                for n in dep:
                    if n not in list_children and n is not None:
                        list_children.append(n)
            elif isinstance(dep, TaggedPOWL):
                if dep not in list_children:
                    list_children.append(dep)
            else:
                raise Exception(
                    "Invalid dependencies for the decision graph! You should provide a list that contains"
                    " tuples of POWL models!"
                )
        if len(list_children) < 1:
            raise Exception(
                ""
                "A decision graph has at least one node. The provided list should comprise of at least one element."
            )

        children = dict()
        for child in list_children:
            new_child = self.create_model(child)
            children[child] = new_child
        # Identify start and end nodes first
        # Default dict with values 0
        start_nodes, end_nodes = [], []
        empty_path = False
        deps = []
        for dep in dependencies:
            if isinstance(dep, tuple):
                # Add both of them there
                if len(dep) != 2:
                    raise Exception(
                        "Invalid dependency tuple in decision graph! Each tuple must contain exactly 2 elements. "
                        "Note that None can be used to indicate start or end."
                    )
                source = dep[0]
                target = dep[1]
                if source is None and target is None:
                    empty_path = True
                elif source is None:
                    start_nodes.append(children[target])
                elif target is None:
                    end_nodes.append(children[source])
                else:
                    deps.append((children[source], children[target]))
        if len(start_nodes) == 0:
            raise Exception(
                "No start nodes are provided in the partial order, make sure to include them using (None, node)"
            )
        if len(end_nodes) == 0:
            raise Exception(
                "No end nodes are provided in the partial order, make sure to include them using (node, None)"
            )

        min_freq = 0 if empty_path else 1

        order = ChoiceGraph(
            nodes=list(children.values()),
            edges=deps,
            start_nodes=start_nodes,
            end_nodes=end_nodes,
            min_freq=min_freq,
        )
        if self.nested_decision_graphs:
            pass
        else:
            for child in children:
                if isinstance(child, ChoiceGraph):
                    raise Exception(
                        "Do not use decision graphs as 'direct children' of other decision graphs."
                        " Instead, combine dependencies at the same hierarchical level in the same structure. Note that it is"
                        " CORRECT to have 'decision_graph > xor/loop/partial_order > decision_graph in the hierarchy"
                    )
        return order

    def self_loop(self, node: TaggedPOWL):
        if node is None:
            raise Exception("Cannot create a self-loop over an empty model!")
        child = self.create_model(node)
        child.max_freq = None
        return child

    def skip(self, node: TaggedPOWL):
        if node is None:
            raise Exception("Cannot create a skip over an empty model!")
        child = self.create_model(node)
        child.min_freq = 0
        return child

    @staticmethod
    def copy(node: TaggedPOWL):
        return deepcopy(node)
