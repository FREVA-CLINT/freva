from .pbs import PBSJob


class MoabJob(PBSJob):
    submit_command = "msub"
    cancel_command = "canceljob"
    config_name = "moab"
