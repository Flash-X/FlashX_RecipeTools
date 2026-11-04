__version__ = "0.1.0"

from loguru import logger
logger.disable(__name__)

from .utils import (
    generate_op_spec,
)

from .ArithmeticHelperContract import (
    ArithmeticHelperContract,
    ArithmeticHelperContractError,
)
from .ComputationSourceGenerator import (
    ComputationSourceGenerationError,
    ComputationSourceGenerator,
)
from .KernelBoundaryContract import (
    KernelBoundaryContract,
    KernelBoundaryContractError,
)


__all__ = [
    "ArithmeticHelperContract",
    "ArithmeticHelperContractError",
    "ComputationSourceGenerationError",
    "ComputationSourceGenerator",
    "KernelBoundaryContract",
    "KernelBoundaryContractError",
    "OperationRecipe",
    "TimeStepIR",
    "TimeStepRecipe",
    "generate_op_spec",
]


def __getattr__(name):
    """Load generation APIs only when they are requested.

    Contract inspection intentionally has no dependency on the Milhoja Python
    package.  The generation APIs retain their existing public package names,
    but importing FlashX_RecipeTools no longer initializes the full stack.
    """
    if name in {"TimeStepRecipe", "TimeStepIR"}:
        from .TimeStepRecipe import TimeStepIR, TimeStepRecipe

        globals().update(TimeStepRecipe=TimeStepRecipe, TimeStepIR=TimeStepIR)
        return globals()[name]
    if name == "OperationRecipe":
        from .OperationRecipe import OperationRecipe

        globals()[name] = OperationRecipe
        return OperationRecipe
    raise AttributeError("module {!r} has no attribute {!r}".format(__name__, name))


def __dir__():
    return sorted(set(globals()) | set(__all__))

