import fypp
import json
from pathlib import Path
from json.decoder import JSONDecodeError


class OperationSpec():

    def __init__(self, fname:str):
        self.fname = Path(fname).resolve()

        if Path(fname).is_symlink():
            self.fname = Path(fname)

        assert self.fname.is_file(), (
            f"{self.fname} is not a file"
        )

        _rawdata = self._load_json()
        _rawdata = self._preprocess(_rawdata)
        _rawdata = self._postprocess(_rawdata)

        self.data = _rawdata

    def write2json(self, fname:str):
        with open(fname, 'w') as f:
            json.dump(self.data, f, indent=2)

    def _load_json(self) -> dict:
        with open(self.fname, 'r') as f:
            d = json.load(f)
        return d


    def _preprocess(self, raw_d:dict) -> dict:
        """
        Take dictionary contains preprocess macros
        then return a dictionary with expanded all macros
        """

        # assure the include files are located in the same directory of JSON
        include_fnames = list()
        for include in list(raw_d["__includes"]):
            path = (self.fname.parent / include).relative_to(self.fname.parent)
            assert path.is_file(), (
                f"include file {path} is not a file"
            )
            include_fnames.append(path)

        # insert header files to json string
        include_lines = "\n".join([f'#:include "{fname}"' for fname in include_fnames])
        json_str = json.dumps(raw_d, indent=2)
        json_str = include_lines + "\n" + json_str

        # fypp process
        options = fypp.FyppOptions()
        options.line_length = 1000  # prevent line folding
        tool = fypp.Fypp(options)
        raw = tool.process_text(json_str)

        raw_d = json.loads(raw)

        return raw_d


    def _postprocess(self, data:dict) -> dict:
        """
        Traverse each field of dictionary and
        delete unnecessary items,
        apply self._unstringfy to try to cast stringfied objects
        """
        d = dict()
        for key, value in data.items():
            if isinstance(value, dict):
                _value = self._postprocess(value)
            else:
                _value = self._unstringfy(value)
            if not key.startswith("__"):
                d[key] = _value
        return d

    def _unstringfy(self, value):
        """
        try to convert string to integers
        """
        if isinstance(value, list):
            vList = []
            for _v in value:
                vList.append(self._unstringfy(_v))
            return vList
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except JSONDecodeError:
                pass
            return value
        return value

