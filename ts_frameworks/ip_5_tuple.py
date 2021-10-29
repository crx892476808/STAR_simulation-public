import copy

def initial_switch_info_5_tuple(topo):
    switch_list = []
    server_list = []
    switch_info = {}
    for node in topo.nodes:
        if topo.nodes[node]['node_type'] == 0:
            switch_list.append(node)
            switch_info[node] = {'request_list': [], "entry_number": 0}
        elif topo.nodes[node]['node_type'] == 1:
            server_list.append(node)
            switch_info[node] = {}
    return switch_info

def rules_install_with_5_tuple(topo, switch_info, installed_VNF_list,
                                           server_VNF_list, path_segment_list, request_id, entries_threshold=2000):
    # loop_and_same_in_port_check,
    # cant_forward_check[src,dst] = 1  means have reached dst through the port src-dst
    cant_forward_check = {}
    switch_info_ = copy.deepcopy(switch_info)

    new_rules_OVS = 0
    for path_idx, path in enumerate(path_segment_list):
        if path_idx == 0:
            last_node = -1
        else:
            last_node = server_VNF_list[path_idx - 1]['server']
        for node in path:
            if path_idx <= len(server_VNF_list) - 1:
                if last_node == server_VNF_list[path_idx]['server']:
                    continue
            if (last_node, node) in cant_forward_check:
                return False, 0
            cant_forward_check[(last_node, node)] = 1
            last_node = node
            if switch_info_[node]['entry_number'] >= entries_threshold:
                return False, 0
            switch_info_[node]['entry_number'] += 1
            switch_info_[node]['request_list'].append(request_id)
        # from path segment dst switch to path segment dst server
        if path_idx <= len(server_VNF_list) - 1:
            if (last_node, server_VNF_list[path_idx][
                'server']) in cant_forward_check and path_idx != 0:  # and server_VNF_list[path_idx]['server'] != server_VNF_list[path_idx-1]['server']:
                return False, 0
            cant_forward_check[(last_node, server_VNF_list[path_idx]['server'])] = 1
            last_node = server_VNF_list[path_idx]['server']
        if path_idx == 0 or path_idx == len(path_segment_list) - 1:
            new_rules_OVS += 1
        else:
            if server_VNF_list[path_idx]['server'] == server_VNF_list[path_idx - 1]['server']:
                new_rules_OVS += 1
            else:
                new_rules_OVS += 2

    # new_rules_OVS += 2*(len(server_VNF_list)-2) + 2

    switch_info.clear()
    for k in switch_info_:
        switch_info[k] = copy.deepcopy(switch_info_[k])
    return True, new_rules_OVS