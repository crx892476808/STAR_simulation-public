import copy
from ts_helper import is_equal_path_segment_list, new_RSP_id
import networkx as nx

def initial_switch_info_from_topo_STAR(topo):
    max_allow_default_path = 8
    switch_info = {}
    ini_path_to_switch = {}
    switch_list = []
    server_list = []
    ext_path_switch_to_switch = {} # key path , value (from_switch, dst_switch, path_id)

    for u, v in topo.edges:
        topo.edges[u, v]['weight_initial_rules'] = 1  # for shortest path computation
    # define switch_info
    for node in topo.nodes:
        if topo.nodes[node]['node_type'] == 0:
            switch_info[node] = {'entry_number': 0, 'classification': {}, 'declassification': {},
                                 'RSP_id': [], 'next_hop': [],
                                 'ini_path_to_switch': {}, # key = switch_id, value = next hop
                                 'ext_path_switch_to_switch': {} # key = (from_switch, dst_switch, path_id),
                                                                # value = (key: path_id) (value: next hop)
                                }
            switch_list.append(node)
        elif topo.nodes[node]['node_type'] == 1:
            switch_info[node] = {}  # 暂时不做处理
            server_list.append(node)

    for node in switch_list:
        for neighbor_node in nx.neighbors(topo, node):
            switch_info[node]['next_hop'].append(neighbor_node)
            switch_info[node]['entry_number'] += 1
    # 到每个直接相连接server的源路由规则
    for node in server_list:
        connected_switch = topo.nodes[node]['connected_switch']
        switch_info[connected_switch]['next_hop'].append(node)
        switch_info[connected_switch]['entry_number'] += 1

    # 预先计算初始默认路径(只计算switch to switch)
    for switch_from in switch_list:
        for switch_to in switch_list:
            shortest_path = nx.shortest_path(topo, switch_from, switch_to, weight='weight_initial_rules')
            ini_path_to_switch[switch_from, switch_to] = shortest_path
            switch_info[switch_from]['ext_path_switch_to_switch'][(switch_from, switch_to)] = {}

    return switch_info, ini_path_to_switch, ext_path_switch_to_switch

def rules_install_with_STAR(topo, switch_info, ini_path_to_switch, ext_path_switch_to_switch,
                                          SP_list, server_VNF_list, path_segment_list, request_id,
                                          entries_threshold=200000):
    max_ext_path = 7  # 本来是8，initial的情况用掉了一条
    switch_info_ = copy.deepcopy(switch_info)
    SP_list_ = copy.deepcopy(SP_list)
    new_rules_OVS = 0 # newly installed rules in OVS
    # first, judge if the path == the list of RSP
    VNF_instance_list = []
    for element in server_VNF_list:
        VNF_instance_list.append(element['VNF'])
    VNF_tuple = tuple(VNF_instance_list)
    request_src = path_segment_list[0][0]  # the ingress of request
    request_dst = path_segment_list[-1][-1]  # the egress of request
    if VNF_tuple in SP_list_:
        related_RSP_list_ = SP_list_[VNF_tuple]
        for RSP_id in related_RSP_list_:
            # bingo! new request path == existing RSP
            if is_equal_path_segment_list(path_segment_list, related_RSP_list_[RSP_id]['path_segment_list']):
                SP_list_[VNF_tuple][RSP_id]['request_list'].append(request_id)
                switch_info_[request_src]['classification'][request_id] = RSP_id
                if switch_info_[request_src]['entry_number'] + 1 > entries_threshold:
                    return False, new_rules_OVS
                switch_info_[request_src]['entry_number'] += 1
                switch_info.clear()
                for k in switch_info_:
                    switch_info[k] = copy.deepcopy(switch_info_[k])
                SP_list.clear()
                for k in SP_list_:
                    SP_list[k] = copy.deepcopy(SP_list_[k])
                # same_RSP_num += 1
                return True, new_rules_OVS
    # get new RSP_id，install classification rules at src
    RSP_id = new_RSP_id(SP_list_)
    if VNF_tuple not in SP_list_:
        SP_list_[VNF_tuple] = {}
    SP_list_[VNF_tuple][RSP_id] = {'path_segment_list': list(path_segment_list), 'request_list': [request_id],
                                  'deploy_method': []}
    # classification
    switch_info_[request_src]['classification'][request_id] = RSP_id
    if switch_info_[request_src]['entry_number'] + 1 > entries_threshold:
        return False, new_rules_OVS
    switch_info_[request_src]['entry_number'] += 1
    # declassification
    switch_info_[request_dst]['declassification'][RSP_id] = True
    if switch_info_[request_dst]['entry_number'] + 1 > entries_threshold:
        return False, new_rules_OVS
    switch_info_[request_dst]['entry_number'] += 1
    # For each path segment, install rules
    for path_segment_idx, path_segment in enumerate(path_segment_list):
        if path_segment_idx == len(path_segment_list) - 1:
            new_rules_OVS += 1
            switch_to = path_segment[-1]
            switch_from = path_segment[0]
            # number of hops is little, Output-Port-based 跳数小，直接用Output-Port 的方式转发
            if len(path_segment) <= 3:
                SP_list_[VNF_tuple][RSP_id]['deploy_method'].append('Output')
            # initial default path
            elif path_segment == ini_path_to_switch[switch_from, switch_to]:
                for node_idx, node in enumerate(path_segment): # along the path, install initial-default-path rules
                    if node_idx == len(path_segment) - 1: # For destination, based on Output Port tag
                        continue
                    elif switch_to not in switch_info_[node]['ini_path_to_switch']:
                        switch_info_[node]['ini_path_to_switch'][switch_to] = path_segment[node_idx + 1]
                        if switch_info_[node]['entry_number'] + 1 > entries_threshold:
                            return False, new_rules_OVS
                        switch_info_[node]['entry_number'] += 1
                SP_list_[VNF_tuple][RSP_id]['deploy_method'].append('INIT')
            # not initial default path, but == extended default path
            elif tuple(path_segment) in ext_path_switch_to_switch:
                SP_list_[VNF_tuple][RSP_id]['deploy_method'].append('EXT')
            # not extended default path, but can add extended default path不是初始默认路径，但还有放新的默认路径的空间
            elif len(switch_info_[switch_from]['ext_path_switch_to_switch'][(switch_from, switch_to)]) < max_ext_path:
                new_path_id = len(switch_info_[switch_from]['ext_path_switch_to_switch'][(switch_from, switch_to)])
                for node_idx, node in enumerate(path_segment):
                    if node_idx == len(path_segment) - 1: # destination: output-port
                        continue
                    else:
                        switch_info_[node]['ext_path_switch_to_switch'][(switch_from, switch_to)] = \
                            {new_path_id: copy.deepcopy(path_segment)}
                    if switch_info_[node]['entry_number'] + 1 > entries_threshold:
                        return False, new_rules_OVS
                    switch_info_[node]['entry_number'] += 1
                # set extended default path
                ext_path_switch_to_switch[tuple(path_segment)] = (switch_from, switch_to, new_path_id)
                SP_list_[VNF_tuple][RSP_id]['deploy_method'].append('EXT')
            else:
                source_routing_forward = -1
                for node_idx in reversed(range(len(path_segment))):
                    node = path_segment[node_idx]
                    if source_routing_forward == 2:
                        switch_info_[node]['RSP_id'].append(RSP_id)
                        if switch_info_[node]['entry_number'] + 1 > entries_threshold:
                            return False, new_rules_OVS
                        switch_info_[node]['entry_number'] += 1
                        source_routing_forward = 0
                    else:
                        source_routing_forward += 1
                SP_list_[VNF_tuple][RSP_id]['deploy_method'].append('RSP_based')
        elif path_segment_idx == 0:
            new_rules_OVS += 1
            server_to = server_VNF_list[path_segment_idx]['server'] # server to reach
            switch_to = topo.nodes[server_to]['connected_switch']
            switch_from = path_segment[0]
            # OutputPort-based
            if len(path_segment) <= 3:
                SP_list_[VNF_tuple][RSP_id]['deploy_method'].append('Output')
            # is initial default path
            elif path_segment == ini_path_to_switch[switch_from, switch_to]:
                for node_idx, node in enumerate(path_segment):
                    if node_idx == 0 or node_idx == len(path_segment) - 1: # Destination:Output-port tag
                        continue
                    elif switch_to not in switch_info_[node]['ini_path_to_switch']:
                        switch_info_[node]['ini_path_to_switch'][switch_to] = path_segment[node_idx + 1]
                        if switch_info_[node]['entry_number'] + 1 > entries_threshold:
                            return False, new_rules_OVS
                        switch_info_[node]['entry_number'] += 1
                SP_list_[VNF_tuple][RSP_id]['deploy_method'].append('INIT')
            elif len(path_segment) <= 3:
                SP_list_[VNF_tuple][RSP_id]['deploy_method'].append('Output')
            elif tuple(path_segment) in ext_path_switch_to_switch:
                SP_list_[VNF_tuple][RSP_id]['deploy_method'].append('EXT')
            elif len(switch_info_[switch_from]['ext_path_switch_to_switch'][(switch_from, switch_to)]) < max_ext_path:
                new_path_id = len(switch_info_[switch_from]['ext_path_switch_to_switch'][(switch_from, switch_to)])
                for node_idx, node in enumerate(path_segment):
                    if node_idx == len(path_segment) - 1: # src: classification
                        continue
                    else:
                        switch_info_[node]['ext_path_switch_to_switch'][(switch_from, switch_to)] = \
                            {new_path_id: copy.deepcopy(path_segment)}
                    if node_idx != 1: # fwd from src can be directly performed
                        if switch_info_[node]['entry_number'] + 1 > entries_threshold:
                            return False, new_rules_OVS
                        switch_info_[node]['entry_number'] += 1
                # set default paths
                ext_path_switch_to_switch[tuple(path_segment)] = (switch_from, switch_to, new_path_id)
                SP_list_[VNF_tuple][RSP_id]['deploy_method'].append('EXT')
            else:
                source_routing_forward = 0
                for node_idx in reversed(range(len(path_segment))):
                    if node_idx == 0:
                        break
                    node = path_segment[node_idx]
                    if source_routing_forward == 2:
                        switch_info_[node]['RSP_id'].append(RSP_id)
                        if switch_info_[node]['entry_number'] + 1 > entries_threshold:
                            return False, new_rules_OVS
                        switch_info_[node]['entry_number'] += 1
                        source_routing_forward = 0
                    else:
                        source_routing_forward += 1
                SP_list_[VNF_tuple][RSP_id]['deploy_method'].append('RSP_based')
        else:
            new_rules_OVS += 1
            server_to = server_VNF_list[path_segment_idx]['server']
            switch_to = topo.nodes[server_to]['connected_switch']
            switch_from = path_segment[0]
            if server_VNF_list[path_segment_idx]['server'] == server_VNF_list[path_segment_idx-1]['server']:
                SP_list_[VNF_tuple][RSP_id]['deploy_method'].append('OVS_based')
                continue
            elif len(path_segment) <= 2:
                SP_list_[VNF_tuple][RSP_id]['deploy_method'].append('Output')
            elif path_segment == ini_path_to_switch[switch_from, switch_to]:
                for node_idx, node in enumerate(path_segment):
                    if node_idx == len(path_segment) - 1:
                        continue
                    elif switch_to not in switch_info_[node]['ini_path_to_switch']:
                        switch_info_[node]['ini_path_to_switch'][switch_to] = path_segment[node_idx + 1]
                        if switch_info_[node]['entry_number'] + 1 > entries_threshold:
                            return False, new_rules_OVS
                        switch_info_[node]['entry_number'] += 1
                SP_list_[VNF_tuple][RSP_id]['deploy_method'].append('INIT')
            elif len(path_segment) <= 2:
                SP_list_[VNF_tuple][RSP_id]['deploy_method'].append('Output')
            elif tuple(path_segment) in ext_path_switch_to_switch:
                SP_list_[VNF_tuple][RSP_id]['deploy_method'].append('EXT')
            elif len(switch_info_[switch_from]['ext_path_switch_to_switch'][(switch_from, switch_to)]) < max_ext_path:
                new_path_id = len(switch_info_[switch_from]['ext_path_switch_to_switch'][(switch_from, switch_to)])
                for node_idx, node in enumerate(path_segment):
                    if node_idx == len(path_segment) - 1:
                        continue
                    else:
                        switch_info_[node]['ext_path_switch_to_switch'][(switch_from, switch_to)] = \
                            {new_path_id: copy.deepcopy(path_segment)}
                    if switch_info_[node]['entry_number'] + 1 > entries_threshold:
                        return False, new_rules_OVS
                    switch_info_[node]['entry_number'] += 1

                ext_path_switch_to_switch[tuple(path_segment)] = (switch_from, switch_to, new_path_id)
                SP_list_[VNF_tuple][RSP_id]['deploy_method'].append('EXT')
            else:
                source_routing_forward = -1
                for node_idx in reversed(range(len(path_segment))):
                    node = path_segment[node_idx]
                    if source_routing_forward == 2:
                        switch_info_[node]['RSP_id'].append(RSP_id)
                        if switch_info_[node]['entry_number'] + 1 > entries_threshold:
                            return False, new_rules_OVS
                        switch_info_[node]['entry_number'] += 1
                        source_routing_forward = 0
                    else:
                        source_routing_forward += 1
                SP_list_[VNF_tuple][RSP_id]['deploy_method'].append('RSP_based')
            new_rules_OVS += 1
    switch_info.clear()
    for k in switch_info_:
        switch_info[k] = copy.deepcopy(switch_info_[k])
    SP_list.clear()
    for k in SP_list_:
        SP_list[k] = copy.deepcopy(SP_list_[k])
    rules_type_list = SP_list[VNF_tuple][RSP_id]
    # os.system("pause")
    return True, new_rules_OVS