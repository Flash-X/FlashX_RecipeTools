import FlashX_RecipeTools as flashx
import milhoja
from pathlib import Path


CWD = Path(__file__).parent.absolute()

def test_preprocessor():

    opspec_fnames = ["Hydro_op1_2D.json", "Hydro_spark_allLevels.json", "Hydro_spark_perLevels.json"]

    for fname in opspec_fnames:
        opspec_fname = fname
        output_fname = "__" + opspec_fname

        opspec = flashx.OperationSpec(CWD / opspec_fname)

        opspec.write2json(CWD / output_fname)

        milhoja_logger = milhoja.BasicLogger(level=1)
        milhoja.SubroutineGroup.from_milhoja_json(CWD / output_fname, logger=milhoja_logger)


if __name__ == "__main__":

    test_preprocessor()
