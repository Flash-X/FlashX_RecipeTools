from loguru import logger
import sys
import json

import FlashX_RecipeTools as flashx


def main():
    d = flashx.utils.header2dict("Simulation.h")

    with open("__dump.json", "w") as f:
        json.dump(d, f, indent=2)


if __name__ == "__main__":

    logger.remove(0)
    logger.add(sys.stdout, level=0)
    logger.enable(flashx.__name__)

    main()
