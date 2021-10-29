
VNF_type_list_orche =[{
    'name': 'FW',
    'core_req': 4,
    'capacity': 900
    },
    {
        'name': 'Proxy',
        'core_req': 4,
        'capacity': 900
    },
    {
        'name': 'NAT',
        'core_req': 2,
        'capacity': 900
    },
    {
        'name': 'IDS',
        'core_req': 8,
        'capacity': 600
    }

]


VNF_type_list_JSAC = [
    {'id':0},
    {'id':1},
    {'id':2},
    {'id':3},
    {'id':4},
    {'id':5},
    {'id':6},
    {'id': 7},
    {'id': 8},
    {'id': 9}
]

def read_file_to_installed_VNF_instance_list_FPTAS(file_name):
    f = open(file_name, 'r')
    f_line_list = f.readlines()
    ret = []
    for line in f_line_list:
        split_list = line.split('\t')
        vnf_instance = {}
        vnf_instance['id'] = int(split_list[0])
        vnf_instance['type'] = int(split_list[1])
        vnf_instance['delay'] = int(split_list[2])
        vnf_instance['remain_cap'] = int(split_list[3])
        vnf_instance['server'] = int(split_list[4])
        ret.append(vnf_instance)
    return ret