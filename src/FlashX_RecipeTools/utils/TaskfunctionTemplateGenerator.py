import cgkit.ctree.srctree as srctree
from ..constants import FLASHX_RECIPETOOLS_ROOT

INTERNAL_TEMPLATE_PATH = FLASHX_RECIPETOOLS_ROOT / "TimeStepRecipe" / "_internal_tpl"

CONN_KEY = srctree.KEY_CONNECTOR
CODE_KEY = srctree.KEY_CODE
INDENT_KEY = srctree.KEY_PARAM_INDENT

class TaskfunctionTemplateGenerator:

    def __init__(self):
        self._tree = srctree.load(INTERNAL_TEMPLATE_PATH / "cg-tpl.TaskfunctionElement.json")
        self._create_properties()

    def getSourceTree(self):
        return self._tree

    def _create_properties(self):
        attributes = [
            "use_interface",
            "var_definition",
            "var_initialization",
            "init_dataitem",
            "delete_dataitem",
        ]
        for attr in attributes:
            self._create_property(attr)

    def _create_property(self, attr_name):
        private_attr_name = f":{attr_name}"

        def getter(self):
            return self._tree[CONN_KEY + private_attr_name][CODE_KEY]

        def setter(self, value):
            if isinstance(value, str):
                getattr(self, attr_name).append(value)
            elif isinstance(value, list):
                for v in value:
                    assert isinstance(v, str), type(v)
                    getattr(self, attr_name).append(v)

        setattr(self.__class__, attr_name, property(getter, setter))

    def getIndent(self):
        return self._tree[INDENT_KEY]

