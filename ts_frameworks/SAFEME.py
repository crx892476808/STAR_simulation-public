# coding=utf8
import networkx as nx
import copy

def initial_switch_info_from_topo_SAFE_ME(topo):
    # MODIFIED: 指定了权值才能默认用dijkstra，否则会用默认的无权值计算方法
    for u, v in topo.edges:
        topo.edges[u, v]['weight_initial_rules'] = 1
    switch_info = {}
    switch_default_path_switch = {}
    switch_list = []
    for node in topo.nodes:
        if topo.nodes[node]['node_type'] == 0:
            switch_list.append(node)
            switch_info[node] = {'default_path_to_VNF': {}, 'default_path_to_switch': {},
                                 'SFC_table_entry': {}, 'entry_number': 0}
        elif topo.nodes[node]['node_type'] == 1:
            switch_info[node] = {}  # 未来或许需要考虑OVS的情况，这里在当前暂时不考虑
    for switch_from in switch_list:  # 求到达其它每个交换机的最短路径
        for switch_to in switch_list:
            if switch_from == switch_to:
                continue
            shortest_path = nx.shortest_path(topo, switch_from, switch_to, weight='weight_initial_rules')
            switch_default_path_switch[switch_from, switch_to] = shortest_path
            switch_info[switch_from]['default_path_to_switch'][switch_to] = shortest_path[1]  # 记录下一跳
            switch_info[switch_from]['entry_number'] += 1

    for switch_from in switch_list:
        for switch_to in switch_list:
            if switch_from == switch_to:
                continue
            shortest_path = switch_default_path_switch[switch_from, switch_to]
            for v_idx, v in enumerate(shortest_path):
                if v == switch_to:
                    break
                if shortest_path[v_idx + 1] != switch_info[v]['default_path_to_switch'][switch_to]:
                    print("path from {0} to {1}".format(switch_from, switch_to), shortest_path)
                    print("next hop of switch {0}".format(v), switch_info[v]['default_path_to_switch'][switch_to])

    return switch_info, switch_default_path_switch

def rules_install_with_SAFE_ME(topo, switch_info, installed_VNF_list,
                                           switch_default_path_VNF, switch_default_path_switch,
                                           server_VNF_list, path_segment_list, request_id,
                                           entries_threshold=2000):
    # entries_threshold = 10000
    switch_info_ = copy.deepcopy(switch_info)
    switch_default_path_VNF_ = copy.deepcopy(switch_default_path_VNF)

    new_rules_OVS = 0

    # For new VNF instances, insert default rules
    # check if default rules have been installed
    sample_switch = list(switch_info_.keys())[0]
    # print(sample_switch)
    for VNF in installed_VNF_list:
        if (sample_switch, VNF['id']) not in switch_default_path_VNF_:

            server = VNF['server']
            VNF_switch = topo.nodes[server]['connected_switch']
            for switch in switch_info_.keys():  # install default rules for all switches
                if topo.nodes[switch]['node_type'] == 1:  # except for server
                    new_rules_OVS += 1
                    continue
                if switch == VNF_switch:  # to server
                    switch_info_[switch]['default_path_to_VNF'][VNF['id']] = server
                    switch_default_path_VNF_[switch, VNF['id']] = [switch]
                else:
                    shortest_path = nx.shortest_path(topo, switch, VNF_switch)
                    switch_info_[switch]['default_path_to_VNF'][VNF['id']] = shortest_path[1]
                    switch_default_path_VNF_[switch, VNF['id']] = shortest_path

                if switch_info_[switch]['entry_number'] + 1 > entries_threshold:
                    return False, new_rules_OVS
                switch_info_[switch]['entry_number'] += 1

            # shortest_path = nx.shortest_path(topo, switch, VNF_switch)
            # for u_idx, u in enumerate(shortest_path):
            #     if VNF['id'] not in switch_info_[u]['default_path_to_VNF']:
            #         print('switch_default_path_VNF_[{0},{1}]'.format(u,VNF['id']),switch_default_path_VNF_[u,VNF['id']])
            #         x = input()
            #         if u_idx == len(shortest_path) - 1:
            #             switch_info_[u]['default_path_to_VNF'][VNF['id']] = server
            #
            #         else:
            #             switch_info_[u]['default_path_to_VNF'][VNF['id']] = shortest_path[u_idx + 1]
            #         switch_info_[u]['entry_number'] = switch_info_[u]['entry_number'] + 1

    # check if existing default paths conflict with the selected paths
    is_conflict = False
    for i in range(len(path_segment_list)):
        if i == len(path_segment_list) - 1:  # check switch_default_path_switch
            src = path_segment_list[i][0]
            dst = path_segment_list[i][-1]
            # if (src,dst) in switch_default_path_switch: default path exist
            if src == dst:
                continue
            if len(switch_default_path_switch[src, dst]) != len(path_segment_list[i]):
                is_conflict = True
                break
            else:
                for node_idx, node in enumerate(path_segment_list[i]):
                    if node != switch_default_path_switch[src, dst][node_idx]:
                        is_conflict = True
                        break
        else:  # check switch_default_path_VNF_
            switch_src = path_segment_list[i][0]
            switch_dst = path_segment_list[i][-1]
            server_dst = server_VNF_list[i]['server']
            VNF_dst = server_VNF_list[i]['VNF']
            # if (switch_src, VNF_dst) in switch_default_path_VNF_:
            if len(switch_default_path_VNF_[switch_src, VNF_dst]) != len(path_segment_list[i]):
                is_conflict = True
                break
            else:
                for node_idx, node in enumerate(path_segment_list[i]):
                    if node != switch_default_path_VNF_[switch_src, VNF_dst][node_idx]:
                        is_conflict = True
                        break
        if is_conflict == True:
            break

    if is_conflict:
        return False, new_rules_OVS

    # install rules for SFC table

    # get SFC tuple
    SFC_tuple = []
    for element in server_VNF_list:
        SFC_tuple.append(element['VNF'])
    SFC_tuple = tuple(SFC_tuple)
    request_source = path_segment_list[0][0]  # ingress
    request_destination = path_segment_list[-1][-1]  # egress
    switch_info_[request_source]['SFC_table_entry'][request_id] = SFC_tuple
    if switch_info_[request_source]['entry_number'] + 1 > entries_threshold:
        return False, new_rules_OVS
    switch_info_[request_source]['entry_number'] += 1
    # switch_info_[request_destination]['SFC_table_entry_de'][request_id] = SFC_tuple
    # switch_info_[request_destination]['entry_number'] += 1

    switch_info.clear()
    for k in switch_info_:
        switch_info[k] = copy.deepcopy(switch_info_[k])
    switch_default_path_VNF.clear()
    for k in switch_default_path_VNF_:
        switch_default_path_VNF[k] = switch_default_path_VNF_[k]
    return True, new_rules_OVS