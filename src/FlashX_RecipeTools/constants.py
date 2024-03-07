###############################################################################
#
# TODO: These should be pulled out into an official language specification
# somewhere so that the same specification can easily be shared and used
# consistently in different places.  Should
# - Milhoja define its language with the expectation that applications use it
#   correctly? or
# - Should each application be free to define its own language so long as their
#   language includes and uses a certain set of keys that it passes to Milhoja
#   and uses in accord with Milhoja's design?
# The latter sounds nice, but seems like more work.  Indeed, it still implies
# that applications have to learn about Milhoja and how to configure it
# correctly.  The former seems simpler and is more explicit - let the consumer
# of the content dictate the same language to everyone.  TBD.
#

# TODO: Should there be a single global verbose default or should each set of
#       CG-Kit tools define its own default value?
VERBOSE_DEFAULT = False

KEEP_KEY = "keep"
DEVICE_KEY = "device"
DEVICE_NONE = "None"
DEVICE_DEFAULT = "Default"
DEVICE_CHANGE_KEY = DEVICE_KEY + "_change"
# HOME_MEMORY_KEY   = "home_memory_system"

###############################################################################
#
# FINE NODE ATTRIBUTES NEEDED BY MILHOJA.
# TODO: We should likely *not* define these here, but rather import from
# milhoja.
#

# TODO: Can't code get this from the node name?  Note that I don't believe that
# the name is the node's attributes.
MILHOJA_ROUTINE_KEY = "routine"
MILHOJA_CONTEXT_KEY = "context"
MILHOJA_TF_KEY = "task_function_name"
MILHOJA_ARGS_KEY = "arguments"

# All elements must be lowercase
# TODO: Include MPI, Collective, or Barrier?  Should we have action, collective,
# and barrier nodes?  Eos or GC nodes?
MILHOJA_DEVICE_LIST = ["gpu", "cpu"]

###############################################################################

OPSPEC_KEY = "operation"
ORCHESTRATION_KEY = "orchestration"

