from pm4py import PetriNet
from powl import convert_from_workflow_net
from powl.objects.tagged_powl import TaggedPOWL


def convert_workflow_net_to_powl(net: PetriNet) -> TaggedPOWL:
    """
    Convert a Petri net to a POWL model.

    Parameters:
    - net: PetriNet

    Returns:
    - POWL model
    """
    return convert_from_workflow_net(net)
