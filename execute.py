#! python
# (c) DL, UTA, 2009 - 2011
import sys, string, time
import random

wordsize = 24  # everything is a word
numregbits = 3  # actually +1, msb is indirect bit
opcodesize = 5
addrsize = wordsize - (opcodesize + numregbits + 1)  # num bits in address
memloadsize = 1024  # change this for larger programs
numregs = 2 ** numregbits
regmask = (numregs * 2) - 1  # including indirect bit
addmask = (2 ** (wordsize - addrsize)) - 1
nummask = (2 ** (wordsize)) - 1
opcposition = wordsize - (opcodesize + 1)  # shift value to position opcode
reg1position = opcposition - (numregbits + 1)  # first register position
reg2position = reg1position - (numregbits + 1)
memaddrimmedposition = reg2position  # mem address or immediate same place as reg2
realmemsize = memloadsize * 1  # this is memory size, should be (much) bigger than a program
# memory management regs
codeseg = numregs - 1  # last reg is a code segment pointer
dataseg = numregs - 2  # next to last reg is a data segment pointer
# ints and traps
trapreglink = numregs - 3  # store return value here
trapval = numregs - 4  # pass which trap/int
mem = [0] * realmemsize  # this is memory, init to 0
reg = [0] * numregs  # registers
clock = 0  # clock starts ticking
ic = 0  # instruction count
numcoderefs = 0  # number of times instructions read
numdatarefs = 0  # number of times data read
starttime = time.time()
curtime = starttime
endtime = 0
stage = 0

ip = 0  # start execution at codeseg location 0
########################################
ir_arr = [0,0,0,0,0]
reg1_arr = [0,0,0,0,0]
reg2_arr = [0,0,0,0,0]
operand1_arr = [0,0,0,0,0]
operand2_arr = [0,0,0,0,0]
result_arr = [0,0,0,0,0]
opcode_arr = [0,0,0,0,0]
ip_arr = [0,0,0,0,0]
memdata_arr = [0,0,0,0,0]
addr_arr = [0,0,0,0,0]
scoreboard = [-1,-1,-1,-1,-1]
opcodes_to_check = [1,2,3,4,7,9]
stall = 0
control_hazard = 0
data_hazard = 0
stall_count = 0
#######################################
####branch predictor###
bit_predictor_dict = {}
predictor_counter = {}
bit_predictor = 1
####branck predictor###
#####caching#######
#no_lines = 16
#width = 2
offset_bits = 1
index_bits = 3
tag_bits = wordsize - (offset_bits+index_bits)
associativity = 2
cache = [[-1 for x in range((2**offset_bits)*2)] for x in range((2**index_bits)*associativity)]
data_cache = [[-1 for x in range((2**offset_bits)*2)] for x in range((2**index_bits)*associativity)]
split_cache = True
cache_hit = 0.0
cache_miss = 0.0
data_cache_hit = 0.0
data_cache_miss = 0.0
###################

def startexechere(p):
    # start execution at this address
    reg[codeseg] = p


def loadmem():  # get binary load image
    curaddr = 0
    for line in open("a.out", 'r').readlines():
        token = string.split(string.lower(line))  # first token on each line is mem word, ignore rest
        if (token[0] == 'go'):
            startexechere(int(token[1]))
        else:
            mem[curaddr] = int(token[0], 0)
            curaddr = curaddr = curaddr + 1

def get_cache(address):
    offset = address & ((2**offset_bits)-1)
    index = (address >> offset_bits) & ((2**index_bits)-1)
    address_tag = (address >> (offset_bits+index_bits)) & ((2**tag_bits)-1)
    #print offset
    #print index
    #cache_tag = cache[index][offset*2]
    tag_list = [cache[index*associativity][offset*2]]
    for i in range(1, associativity-1):
        tag_list.append([cache[(index*associativity)+i][offset*2]])
    if address_tag in tag_list:
        print 'cache hit success'
        global cache_hit
        cache_hit+=1
        tag_index = tag_list.index(address_tag)
        return cache[(index*associativity)+tag_index][offset*2+1]

    else:
        if -1 in tag_list:
            tag_index = tag_list.index(-1)
        else:
            tag_index = random.randint(0,associativity-1)
        print 'cache miss'
        global cache_miss
        cache_miss+=1
        for i in xrange(2**offset_bits):
            temp = address-offset+i
            #index = (address >> offset_bits) & ((2**index_bits)-1)
            temp_tag = (temp >> (offset_bits+index_bits)) & ((2**tag_bits)-1)
            cache[(index*associativity)+tag_index][i*2+1] = mem[temp]
            cache[(index*associativity)+tag_index][i*2] = temp_tag
        return cache[(index*associativity)+tag_index][offset*2+1]

def get_data_c(address):
    if not split_cache:
        return get_cache(address)
    offset = address & ((2**offset_bits)-1)
    index = (address >> offset_bits) & ((2**index_bits)-1)
    address_tag = (address >> (offset_bits+index_bits)) & ((2**tag_bits)-1)
    #print offset
    #print index
    #cache_tag = cache[index][offset*2]
    tag_list = [data_cache[index*associativity][offset*2]]
    for i in range(1, associativity-1):
        tag_list.append([data_cache[(index*associativity)+i][offset*2]])
    if address_tag in tag_list:
        print 'cache hit success'
        global data_cache_hit
        data_cache_hit+=1
        tag_index = tag_list.index(address_tag)
        return data_cache[(index*associativity)+tag_index][offset*2+1]

    else:
        if -1 in tag_list:
            tag_index = tag_list.index(-1)
        else:
            tag_index = random.randint(0,associativity-1)
        print 'cache miss'
        global data_cache_miss
        data_cache_miss+=1
        for i in xrange(2**offset_bits):
            temp = address-offset+i
            #index = (address >> offset_bits) & ((2**index_bits)-1)
            temp_tag = (temp >> (offset_bits+index_bits)) & ((2**tag_bits)-1)
            data_cache[(index*associativity)+tag_index][i*2+1] = mem[temp]
            data_cache[(index*associativity)+tag_index][i*2] = temp_tag
        return data_cache[(index*associativity)+tag_index][offset*2+1]


def getcodemem(a):
    # get code memory at this address
    address = a + reg[codeseg]
    memval = get_cache(address)
    globals()['numcoderefs']=globals()['numcoderefs']+1
    return (memval)

def getdatamem(a):
    # get code memory at this address
    address = a + reg[dataseg]
    memval = get_data_c(address)
    #memval = mem[a + reg[dataseg]]
    globals()['numdatarefs']+=1
    return (memval)


def getregval(r):
    # get reg or indirect value
    if ((r & (1 << numregbits)) == 0):  # not indirect
        rval = reg[r]
    else:
        rval = getdatamem(reg[r - numregs])  # indirect data with mem address
    return (rval)


def checkres(v1, v2, res):
    v1sign = (v1 >> (wordsize - 1)) & 1
    v2sign = (v2 >> (wordsize - 1)) & 1
    ressign = (res >> (wordsize - 1)) & 1
    if ((v1sign) & (v2sign) & (not ressign)):
        return (1)
    elif ((not v1sign) & (not v2sign) & (ressign)):
        return (1)
    else:
        return (0)


def dumpstate(d):
    if (d == 1):
        print reg
    elif (d == 2):
        print mem
    elif (d == 3):
        print 'clock=', clock, 'IC=', ic, 'Coderefs=', numcoderefs, 'Datarefs=', numdatarefs, 'Start Time=', starttime, 'Currently=', time.time(), 'Total time=', time.time()-starttime


def trap(t):
    # unusual cases
    # trap 0 illegal instruction
    # trap 1 arithmetic overflow
    # trap 2 sys call
    # trap 3+ user
    rl = trapreglink  # store return value here
    rv = trapval
    print 'Trap called:', str(t)
    if ((t == 0) | (t == 1)):
        dumpstate(1)
        dumpstate(2)
        dumpstate(3)
    elif (t == 2):  # sys call, reg trapval has a parameter
        what = reg[trapval]
        if (what == 1):
            a = 1  # elapsed time
    return (-1, -1)
    return (rv, rl)


# opcode type (1 reg, 2 reg, reg+addr, immed), mnemonic
opcodes = {1: (2, 'add'), 2: (2, 'sub'),
           3: (1, 'dec'), 4: (1, 'inc'),
           7: (3, 'ld'), 8: (3, 'st'), 9: (3, 'ldi'),
           12: (3, 'bnz'), 13: (3, 'brl'),
           14: (1, 'ret'),
           16: (3, 'int')}
startexechere(0)  # start execution here if no "go"
loadmem()  # load binary executable

# while instruction is not halt

###########################################
def instruction_fetch(instr_index):
    ir = getcodemem(globals()['ip'])  # - fetch
    ir_arr[instr_index] = ir
    globals()['ip'] = globals()['ip'] + 1
    ip_arr[instr_index] = globals()['ip']

    print 'fetching instruction'


def instruction_decode(instr_index):
    opcode_arr[instr_index] = ir_arr[instr_index] >> opcposition  # - decode
    reg1_arr[instr_index] = (ir_arr[instr_index] >> reg1position) & regmask
    reg2_arr[instr_index] = (ir_arr[instr_index] >> reg2position) & regmask
    addr_arr[instr_index] = (ir_arr[instr_index]) & addmask
    opcode = opcode_arr[instr_index]

    global scoreboard, bit_predictor_dict, predictor_counter, ip
    if opcode in opcodes_to_check:
        scoreboard[instr_index]= reg1_arr[instr_index]
    else:
        scoreboard[instr_index] = -1
    if(opcode_arr[instr_index] == 12):
        if(not bit_predictor_dict.has_key(str(ip_arr[instr_index]-1))):
            bit_predictor_dict[str(ip_arr[instr_index]-1)] = 1
            predictor_counter[str(ip_arr[instr_index]-1)] = []
            predictor_counter[str(ip_arr[instr_index]-1)].append(1)
            predictor_counter[str(ip_arr[instr_index]-1)].append(0)
            ip = addr_arr[instr_index]
        else:
            predictor_counter[str(ip_arr[instr_index]-1)][0]+=1
            if(bit_predictor_dict[str(ip_arr[instr_index]-1)]):
                ip = addr_arr[instr_index]
    print 'instruction decode for op-code:', opcode_arr[instr_index]



def check_scoreboard(instr_index):
    if ((reg2_arr[instr_index] & (1 << numregbits)) == 0):  # not indirect
        rval = reg2_arr[instr_index]
    else:
        rval = reg2_arr[instr_index] - numregs
    temp = ((instr_index-1) + 5)%5
    no_stall = 0
    if (scoreboard[temp] == reg1_arr[instr_index]) or (scoreboard[temp] == rval):
        no_stall = 2
        globals()['data_hazard'] = globals()['data_hazard'] + 1
    elif (scoreboard[temp-1] == reg1_arr[instr_index]) or (scoreboard[temp-1] == rval):
        no_stall = 1
        globals()['data_hazard'] = globals()['data_hazard'] + 1
    globals()['stall_count'] = globals()['stall_count'] + no_stall
    return no_stall

def operand_fetch(instr_index):
    #print 'of start', instr_index, opcode_arr[instr_index], reg1_arr[instr_index], reg2_arr[instr_index]

    if not (opcodes.has_key(opcode_arr[instr_index])):
        tval, treg = trap(0)
        if (tval == -1):  # illegal instruction
            return -1
    memdata_arr[instr_index] = 0  # contents of memory for loads
    if opcodes[opcode_arr[instr_index]][0] == 1:  # dec, inc, ret type
        operand1_arr[instr_index] = getregval(reg1_arr[instr_index])  # fetch operands
    elif opcodes[opcode_arr[instr_index]][0] == 2:  # add, sub type
        operand1_arr[instr_index] = getregval(reg1_arr[instr_index])  # fetch operands
        operand2_arr[instr_index] = getregval(reg2_arr[instr_index])
    elif opcodes[opcode_arr[instr_index]][0] == 3:  # ld, st, br type
        operand1_arr[instr_index] = getregval(reg1_arr[instr_index])  # fetch operands
        operand2_arr[instr_index] = addr_arr[instr_index]
    elif opcodes[opcode_arr[instr_index]][0] == 0:  # ? type
        return -1
    if (opcode_arr[instr_index] == 7):  # get data memory for loads
        memdata_arr[instr_index] = getdatamem(operand2_arr[instr_index])
    print 'operand fetch for opcode:', opcode_arr[instr_index]
    #print 'operand1 is:', operand1_arr[instr_index]
    #print 'operand2 is:', operand2_arr[instr_index]

def execute(instr_index):
    #print 'execute rohan'
    #print opcode_arr[instr_index]
    #print operand1_arr[instr_index]
    #print operand2_arr[instr_index]
    if opcode_arr[instr_index] == 1:  # add
        result_arr[instr_index] = (operand1_arr[instr_index] + operand2_arr[instr_index]) & nummask
        if (checkres(operand1_arr[instr_index], operand2_arr[instr_index], result_arr[instr_index])):
            tval, treg = trap(1)
            if (tval == -1):  # overflow
                return -1
    elif opcode_arr[instr_index] == 2:  # sub
        result_arr[instr_index] = (operand1_arr[instr_index] - operand2_arr[instr_index]) & nummask
        if (checkres(operand1_arr[instr_index], operand2_arr[instr_index], result_arr[instr_index])):
            tval, treg = trap(1)
            if (tval == -1):  # overflow
                return -1
    elif opcode_arr[instr_index] == 3:  # dec
        result_arr[instr_index] = operand1_arr[instr_index] - 1
    elif opcode_arr[instr_index] == 4:  # inc
        result_arr[instr_index] = operand1_arr[instr_index] + 1
    elif opcode_arr[instr_index] == 7:  # load
        result_arr[instr_index] = memdata_arr[instr_index]
    ########################################
    elif opcode_arr[instr_index] == 8:
        result_arr[instr_index] = operand1_arr[instr_index]
    ########################################
    elif opcode_arr[instr_index] == 9:  # load immediate
        result_arr[instr_index] = operand2_arr[instr_index]
    elif opcode_arr[instr_index] == 12:  # conditional branch
        result_arr[instr_index] = operand1_arr[instr_index]
        global bit_predictor, bit_predictor_dict, predictor_counter
        if result_arr[instr_index] <> 0:
            if(not bit_predictor_dict[str(ip_arr[instr_index]-1)]):
                bit_predictor_dict[str(ip_arr[instr_index]-1)] = 1
                predictor_counter[str(ip_arr[instr_index]-1)][1] += 1
                print 'exe \t',' stage:',instr_index,' opcode:',opcode_arr[instr_index],' result:',result_arr[instr_index]
                return 12
        else:
            globals()['ip'] = ip_arr[instr_index]
            if(bit_predictor_dict[str(ip_arr[instr_index]-1)]):
                bit_predictor_dict[str(ip_arr[instr_index]-1)] = 0
                predictor_counter[str(ip_arr[instr_index]-1)][1] += 1
                print 'exe \t',' stage:',instr_index,' opcode:',opcode_arr[instr_index],' result:',result_arr[instr_index]
            key = str(ip_arr[instr_index]-1)
            success = 100*(int(predictor_counter[key][0]) - int(predictor_counter[key][1]))/(float(predictor_counter[key][0]))
            print 'IP=', key, '%age=', success
            bit_predictor_dict.pop(str(ip_arr[instr_index]-1))
            return 12

    elif opcode_arr[instr_index] == 13:  # branch and link
        result_arr[instr_index] = ip_arr[instr_index]
        globals()['ip'] = operand2_arr[instr_index]
    elif opcode_arr[instr_index] == 14:  # return
        globals()['ip'] = operand1_arr[instr_index]
    elif opcode_arr[instr_index] == 16:  # interrupt/sys call
        result = ip_arr[instr_index]
        tval, treg = trap(reg1_arr[instr_index])
        if (tval == -1):
            return -1
        reg1_arr[instr_index] = treg
        globals()['ip'] = operand2_arr[instr_index]
    print 'execute for opcode:', opcode_arr[instr_index]


def write_back(instr_index):
    if ((opcode_arr[instr_index] == 1) | (opcode_arr[instr_index] == 2) |
            (opcode_arr[instr_index] == 3) | (opcode_arr[instr_index] == 4)):  # arithmetic
        reg[reg1_arr[instr_index]] = result_arr[instr_index]
    elif ((opcode_arr[instr_index] == 7) | (opcode_arr[instr_index] == 9)):  # loads
        reg[reg1_arr[instr_index]] = result_arr[instr_index]
    ##############################
    elif opcode_arr[instr_index] == 8:
        mem[operand2_arr[instr_index] + reg[dataseg]] = result_arr[instr_index]
    ##############################
    elif (opcode_arr[instr_index] == 13):  # store return address
        reg[reg1_arr[instr_index]] = result_arr[instr_index]
    elif (opcode_arr[instr_index] == 16):  # store return address
        reg[reg1_arr[instr_index]] = result_arr[instr_index]
    if opcode_arr[instr_index] != 0:
        globals()['ic'] = globals()['ic'] + 1
    #print 'write:',instr_index
    print 'write back instruction for opcode:', opcode_arr[instr_index]
    #print 'write back data for opcode:', result_arr[instr_index]
###########################################

def flush_pipeline(index):
    temp = result_arr[index]
    globals()['ir_arr'] = [0,0,0,0,0]
    globals()['reg1_arr'] = [0,0,0,0,0]
    globals()['reg2_arr'] = [0,0,0,0,0]
    globals()['operand1_arr'] = [0,0,0,0,0]
    globals()['operand2_arr'] = [0,0,0,0,0]
    globals()['result_arr'] = [0,0,0,0,0]
    #globals()['result_arr'][index] = temp
    globals()['opcode_arr'] = [0,0,0,0,0]
    globals()['ip_arr'] = [0,0,0,0,0]
    globals()['memdata_arr'] = [0,0,0,0,0]
    globals()['addr_arr'] = [0,0,0,0,0]
    globals()['ic'] = globals()['ic'] + 1
    globals()['control_hazard'] = globals()['control_hazard']+1

def shift_arrays(index_to_shift):
    ip_arr[(index_to_shift+2)%5] = ip_arr[(index_to_shift+1)%5]
    ir_arr[(index_to_shift+2)%5] = ir_arr[(index_to_shift+1)%5]

    ip_arr[(index_to_shift+1)%5] = ip_arr[index_to_shift]
    ir_arr[(index_to_shift+1)%5] = ir_arr[index_to_shift]
    opcode_arr[(index_to_shift+1)%5] = opcode_arr[index_to_shift]
    opcode_arr[index_to_shift] = 0
    reg1_arr[(index_to_shift+1)%5] = reg1_arr[index_to_shift]
    reg2_arr[(index_to_shift+1)%5] = reg2_arr[index_to_shift]
    addr_arr[(index_to_shift+1)%5] = addr_arr[index_to_shift]
    scoreboard[(index_to_shift+1)%5] = scoreboard[index_to_shift]
    scoreboard[index_to_shift] = -1


while (1):
    #print '----Starting clock cycle ----'
    #instr_index = (globals()['ic'])%5
    #stage = ic
    # fetch
    clock+=1
    globals()['stage'] = globals()['stage'] + 1
    #global stall
    # write back
    if stage - 5>=0:
        write_back((stage-5)%5)

    #if stall == 0:
        # execute
    exe_return = 0
    if stage - 4>=0:
        exe_return = execute((stage-4)%5)
        if exe_return == -1:
            #print 'execute',ic
            break
        if exe_return == 12:
            flush_pipeline((stage-5)%5)
            #globals()['ic'] = globals()['ic'] + 1
            globals()['stage']=0
    #check scoreboard
    stall = check_scoreboard((stage+2)%5)

    if stall == 0:
        # - operand fetch
        if stage - 3>=0:
            ret_val = operand_fetch((stage-3)%5)
            if ret_val == -1:
                #print 'of',ic
                break


        #decode
        if stage-2>=0:
            instruction_decode((stage-2)%5)
            #if opcode_arr[(stage-2)%5] == 12:
            #    stall = 3

        #if stall == 0:
        if stage-1>=0:
            instruction_fetch((stage-1)%5)
    else:
        shift_arrays((stage-3)%5)
        stall -= 1
    #print '----End clock cycle ----'
    print ''


print mem[50]
endtime=time.time()
print 'clock=', clock, 'IC=', ic, 'Coderefs=', numcoderefs, 'Datarefs=', numdatarefs, 'Start Time=', starttime, 'Currently=', endtime, 'Total time=', endtime-starttime
print 'CPI=', float(clock)/ic
print 'IPS=', ic/(endtime-starttime)
print 'clock speed=', (clock/(endtime-starttime))
print 'data Hazard:', data_hazard
print 'control hazard:', control_hazard
print 'number of stalls:', stall_count
for key in bit_predictor_dict.keys():
    success = 100*(int(predictor_counter[key][0]) - int(predictor_counter[key][1]))/(float(predictor_counter[key][0]))
    print 'IP=', key, '%age=', success
print predictor_counter
if split_cache:
    print 'cache hit ratio', cache_hit/(cache_hit+cache_miss)
    print 'data cache hit ratio', data_cache_hit/(data_cache_hit+data_cache_miss)
else:
    print 'cache hit ratio', cache_hit/(cache_hit+cache_miss)
# end of instruction loop
# end of execution
