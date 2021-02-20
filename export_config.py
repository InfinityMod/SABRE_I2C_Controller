import argparse, os
from controllers.ES9038Q2M import DAC_9038Q2M_Control

def export_config(path, name):
    mappers = [DAC_9038Q2M_Control(0x48), DAC_9038Q2M_Control(0x49)]
    for m in mappers:
        m.i2c_init()
        m.exportYaml(os.path.abspath("{0}//{1}_{2}.yaml".format(path, name, hex(m.i2cAddr))))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('path', metavar='Path', type=str, nargs=None,
                            help='path where to save the config')
    parser.add_argument('name', metavar='Name', type=str, nargs=None,
                            help='config name')
    args = parser.parse_args()
    export_config(args.path, args.name)