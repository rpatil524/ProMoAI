from powl.objects.tagged_powl import Activity, ChoiceGraph, PartialOrder

from powl.objects.tagged_powl.choice_graph import _ChoiceGraphEnd, _ChoiceGraphStart

from promoai.prompting.prompt_engineering import import_statement


def translate_powl_to_code(powl_obj):
    """
    Translates a POWL object from pm4py into code using ModelGenerator.

    Args:
        powl_obj: The POWL object to translate.

    Returns:
        A string containing the Python code that constructs the equivalent POWL model using ModelGenerator.
    """
    code_lines = [import_statement, "gen = ModelGenerator()"]

    var_counter = [0]

    def get_new_var_name():
        var_name = f"var_{var_counter[0]}"
        var_counter[0] += 1
        return var_name

    def process_powl(powl):
        if isinstance(powl, Activity):
            var_name = get_new_var_name()
            if powl.label is None:
                code_lines.append(f"{var_name} = None")
            else:
                label = powl.label
                if powl.organization is not None and powl.role is not None:
                    code_lines.append(
                        f"{var_name} = gen.activity('{label}', pool='{powl.organization}',  lane='{powl.role}')"
                    )
                else:
                    code_lines.append(f"{var_name} = gen.activity('{label}')")
            return var_name

        elif isinstance(powl, _ChoiceGraphEnd) or isinstance(powl, _ChoiceGraphStart):
            return None

        elif isinstance(powl, PartialOrder) or isinstance(powl, ChoiceGraph):
            nodes = powl._g.nodes
            if isinstance(powl, PartialOrder):
                order = powl.transitive_reduction()
            elif isinstance(powl, ChoiceGraph):
                order = powl
            else:
                raise Exception("Unknown POWL object! This should not be possible!")
            node_var_map = {node: process_powl(node) for node in nodes}
            dependencies = []
            nodes_in_edges = set()
            # to make it robust against PartialOrders and ChoiceGraphs
            edge_checker = (
                order.is_edge if hasattr(order, "is_edge") else order.has_edge
            )
            for source in nodes:
                for target in nodes:
                    source_var = node_var_map[source]
                    target_var = node_var_map[target]
                    if edge_checker(source, target):
                        dependencies.append(f"({source_var}, {target_var})")
                        nodes_in_edges.update([source, target])

            if isinstance(powl, PartialOrder):
                # Include nodes not in any edge as singleton tuples
                for node in nodes:
                    if node not in nodes_in_edges:
                        var = node_var_map[node]
                        dependencies.append(f"({var},)")

            dep_str = ", ".join(dependencies)
            var_name = get_new_var_name()
            code_lines.append(
                f"{var_name} = gen.partial_order(dependencies=[{dep_str}])"
            ) if isinstance(powl, PartialOrder) else code_lines.append(
                f"{var_name} = gen.decision_graph(dependencies=[{dep_str}])"
            )
            return var_name

        else:
            raise Exception(
                f"Unknown POWL object {type(powl)}! This should not be possible!"
            )

    final_var = process_powl(powl_obj)
    code_lines.append(f"final_model = {final_var}")

    return "\n".join(code_lines)
