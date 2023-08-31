import json
import sys

TERMINATORS = ['jmp', 'br', 'ret']

def count_terminators(prog):
    num_terminators = 0
    for func in prog['functions']:
        for instr in func['instrs']:
            if instr.get('op') in TERMINATORS:
                num_terminators = num_terminators + 1
    print("Number of terminators: ", num_terminators)

if __name__ == "__main__":
    prog = json.load(sys.stdin)
    count_terminators(prog)
