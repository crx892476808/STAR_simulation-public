import networkx as nx

def read_file_to_topo_orche(file_name):
    f = open(file_name,'r')
    f_line_list = f.readlines()
    topo = nx.Graph()
    node_num = int(f_line_list[0])
    cur_line = 1
    for i in range(node_num):
        node_str = f_line_list[cur_line]
        node_str_split = node_str.split('\t')
        node_id = int(node_str_split[0])
        node_type = int(node_str_split[1])
        if node_type == 0:
            topo.add_node(node_id,node_type=node_type)
        elif node_type == 1:
            connected_switch = int(node_str_split[2])
            core = int(node_str_split[3])
            remain_core = int(node_str_split[4])
            topo.add_node(node_id, node_type=node_type, connected_switch=connected_switch,
                          core=core, remain_core=remain_core)
        cur_line = cur_line + 1
    edge_num = int(f_line_list[cur_line])
    cur_line = cur_line + 1
    for i in range(edge_num):
        edge_str = f_line_list[cur_line]
        edge_str_split = edge_str.split('\t')
        u = int(edge_str_split[0])
        v = int(edge_str_split[1])
        bandwidth = int(edge_str_split[2])
        delay=int(edge_str_split[3])
        remain_bandwidth=int(edge_str_split[4])
        topo.add_edge(u, v, bandwidth=bandwidth, delay=delay, remain_bandwidth=remain_bandwidth)
        cur_line = cur_line + 1
    return topo


def read_file_to_topo_FPTAS(file_name):
    f = open(file_name,'r')
    f_line_list = f.readlines()
    topo = nx.Graph()
    node_num = int(f_line_list[0])
    cur_line = 1
    for i in range(node_num):
        node_str = f_line_list[cur_line]
        node_str_split = node_str.split('\t')
        node_id = int(node_str_split[0])
        node_type = int(node_str_split[1])
        if node_type == 0:
            topo.add_node(node_id,node_type=node_type)
        elif node_type == 1:
            connected_switch = int(node_str_split[2])
            topo.add_node(node_id, node_type=node_type, connected_switch=connected_switch)
        cur_line = cur_line + 1
    edge_num = int(f_line_list[cur_line])
    cur_line = cur_line + 1
    for i in range(edge_num):
        edge_str = f_line_list[cur_line]
        edge_str_split = edge_str.split('\t')
        u = int(edge_str_split[0])
        v = int(edge_str_split[1])
        edge_type = str(edge_str_split[2])
        bandwidth = int(edge_str_split[3])
        delay=int(edge_str_split[4])
        remain_bandwidth=int(edge_str_split[5])
        topo.add_edge(u, v, edge_type=edge_type, bandwidth=bandwidth,
                      delay=delay, remain_bandwidth=remain_bandwidth)
        cur_line = cur_line + 1
    return topo


def read_file_to_request_list_FPTAS(file_name):
    f = open(file_name, 'r')
    line_list = f.readlines()
    ret = []

    for line in line_list:
        request = {}
        request_str = line.split('\t')
        request['src'] = int(request_str[0])
        request['dst'] = int(request_str[1])
        request['SFC'] = [int(str_vnf) for str_vnf in request_str[2].split(' ')]
        request['traffic_rate'] = int(request_str[3])
        request['delay_bound'] = int(request_str[4])
        request['type_req'] = [edge_type for edge_type in request_str[5].split(' ')]
        ret.append(request)
    return ret


def read_file_to_request_list(file_name):
    f = open(file_name, 'r')
    line_list = f.readlines()
    ret = []

    for line in line_list:
        request = {}
        request_str = line.split('\t')
        request['src'] = int(request_str[0])
        request['dst'] = int(request_str[1])
        request['SFC'] = [int(str_vnf) for str_vnf in request_str[2].split(' ')]
        request['traffic_rate'] = float(request_str[3])
        ret.append(request)
    return ret


def calculate_total_entry_num(switch_info):
    total_entry_num = 0
    for k in switch_info:
        if 'entry_number' in switch_info[k]:
            total_entry_num += switch_info[k]['entry_number']
    return total_entry_num


def give_max_entry_number(switch_info):
    max_entry_num = 0
    max_entry_num_switch = -1
    for k in switch_info:
        if 'entry_number' in switch_info[k] and max_entry_num < switch_info[k]['entry_number']:
            max_entry_num = switch_info[k]['entry_number']
            max_entry_num_switch = k
    return (max_entry_num_switch, max_entry_num)