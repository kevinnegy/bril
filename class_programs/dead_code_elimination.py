import json
import sys
import itertools
import uuid

TERMINATORS = ['jmp', 'br', 'ret']
newest_name = 'a'

# Borrowed from bril/examples/util.py
def flatten(ll):
    return list(itertools.chain(*ll))

def create_blocks(func):
    blocks = []
    block = []
    num_instr = 0
    for instr in func['instrs']:
        num_instr += 1 
        if instr.get('op') in TERMINATORS:
            block.append(instr)
            blocks.append(block)
            block = []
        elif 'label' in instr:
            blocks.append(block)
            block = []
            block.append(instr)
        else:
            block.append(instr)
    if (len(block) > 0):
        blocks.append(block)


    num_block_instructions = 0
    for block in blocks:
        num_block_instructions += len(block)
    assert(num_instr == num_block_instructions)
    return blocks

# Print out new program with no dead code and print how many lines were removed
def DCE(func):
    num_deleted = 0
    blocks = create_blocks(func)
    new_block =[]

    # Find instructions to delete
    for block in blocks:
        definitions = {} # key = variable, value = instruction where variable defined last, but not used
        deletion = []
        for instr in block:
            # So const instructions can be duplicated?
            if 'args' in instr:
                # Remove args from definition dictionary 
                for arg in instr['args']:
                    if arg in definitions:
                        del definitions[arg]

            # We've had a definition before this one and it wasn't used
            if 'dest' in instr and instr['dest'] in definitions:
                deletion.append(definitions[instr['dest']])

            # Put new definition in definitions list 
            if 'dest' in instr:
                definitions[instr['dest']] = instr    
        
        num_deleted += len(deletion)

        # Delete code from block
#        print("deleting:")
        for instr in deletion:
#            print(instr)
            block.remove(instr)

    func['instrs'] = flatten(blocks)
#    print("number deleted this func: ", num_deleted)
    return num_deleted

# For arguments that have no clear expression, just make them self-reference in the table
def add_noop_arg_to_lvn(arg, environment, table):
    #Add to table
    table.append(((arg,), arg))

    #add to environment 
    environment[arg] = len(table) -1 


def create_expr_tuple(instr, environment, table):
    new_tuple = (instr['op'],)

    if instr['op'] == "const":
        new_tuple = new_tuple + (instr['value'],)
        return new_tuple

    if 'args' not in instr:
        return new_tuple

    for arg in instr['args']:
        # Assume arg has been defined in a different block or from a previous pointer op
        if arg not in environment:
           add_noop_arg_to_lvn(arg, environment, table) 
            
        new_tuple = new_tuple + (environment[arg],)

    return new_tuple

def find_in_table(expr_tuple, table):
    table_index = -1 
    for i, row in enumerate(table):
        if row[0] == expr_tuple:
            table_index = i
            break

    return table_index

def add_instr_to_lvn(instr, expr_tuple, table, environment):

    table_index = find_in_table(expr_tuple, table)

    # Not in table, add
    if 'dest' not in instr :
        return
    elif table_index < 0 and instr['op'] != "br":
        table.append((expr_tuple, instr['dest']))

        # Add destination variable to environment
        environment[instr['dest']] = len(table) -1

    # Is in table, just add to environment with index
    else:
        environment[instr['dest']] = table_index
    return

def new_name():
    return uuid.uuid4().hex
    
def LVN(func):

    blocks = create_blocks(func) 

    for block in blocks:
        new_block = []
        table = [] # Each row in list is a tuple (value tuple, canonical variable)
        environment = {} # dictionary of variable to table index 

        for instr in block:
            
            # Just skip if label or ptr operations
            if 'label' in instr or instr['op'] in ['store', 'free', 'alloc', 'ptradd', 'load', 'ret']:
                new_block.append(instr)
                continue

#            # If instr dest is the canonical variable, need to rename canon var in its old row in the table
#            if 'dest' in instr and instr['dest'] in environment:
#                if instr['dest'] == table[environment[instr['dest']]][1]:
#                    # Rename
#                    new_dest = new_name()
#                    table[environment[instr['dest']]] = (table[environment[instr['dest']]][0], new_dest)
#                    # Emit new instruction for new name variable 
#                    new_instr = {}
#                    new_instr['dest'] = new_dest
#                    new_instr['op'] = "id"
#                    new_instr['args'] = instr['dest']
#                    new_block.append(new_instr)
#                    
#                    # Add to environment
#                    environment[new_dest] = environment[instr['dest']]

            expr_tuple = create_expr_tuple(instr, environment, table)
    
            # Add to table/environment
            if instr['op'] not in ['print', 'br', 'jmp']:
                add_instr_to_lvn(instr, expr_tuple, table, environment)
    
#            print("pre instruction")
#            print(instr)

            # Generate new instruction and store into new block
            
            # If instr dest points to a table row where it is not its own canon variable, create new instr 
            if 'dest' in instr and instr['dest'] != table[environment[instr['dest']]][1]:
                    new_instr = {}
                    new_instr['dest'] = instr["dest"]
                    new_instr['op'] = "id"
                    new_instr['args'] = [table[environment[instr['dest']]][1]]
                    new_instr['type'] = instr['type']
                    new_block.append(new_instr)
                    continue


            # Check if new arguments 
            for i, arg in enumerate(expr_tuple):
                if i == 0 and arg == "const":
                    break 
                if i == 0:
                    instr['args'] = []
                    continue
                instr['args'].append(table[arg][1])

#            print("postinstruction")
#            print(instr)

            new_block.append(instr)
            

        # new block complete, replace old block
        block[:] = new_block
        
    func['instrs'] = flatten(blocks)

    return 0


if __name__ == "__main__":
    prog = json.load(sys.stdin)
    num_deleted = 1
    total_deleted = 0

    # LVN - does no deletion, just takes care of copy propagation and common subexpression
    for func in prog['functions']:
        LVN(func)

    # DCE
    while (num_deleted != 0):
        num_deleted = 0
        for func in prog['functions']:
            num_deleted += DCE(func)
            total_deleted += num_deleted
#    print("Number deleted ", total_deleted)

#    for func in prog['functions']:
#        for instr in func['instrs']:
#            print(instr)

    json.dump(prog, sys.stdout)
    
