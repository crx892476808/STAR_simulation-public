# coding=utf8
import networkx as nx
import copy
from ts_helper import is_equal_path_segment_list,new_RSP_id

def initial_switch_info_NSH(topo):
    switch_list = []
    server_list = []
    switch_info = {}
    for node in topo.nodes:
        if topo.nodes[node]['node_type'] == 0:
            switch_list.append(node)
            switch_info[node] = {'classification': {}, 'declassification': {}, 'RSP_id': [], "entry_number": 0}
        elif topo.nodes[node]['node_type'] == 1:
            server_list.append(node)
            switch_info[node] = {}
    return switch_info

def rules_install_with_NSH(switch_info, SP_list,
                                       installed_VNF_list, server_VNF_list, path_segment_list, request_id,
                                       entries_threshold=2000):
    entries_threshold = entries_threshold
    switch_info_ = copy.deepcopy(switch_info)
    SP_list_ = copy.deepcopy(SP_list)

    # NEWFEA: The newly installed rules in the OVS
    new_rules_OVS = 0
    # judge: The current path == Existing RSP ?
    # first obtain the VNF instance list for current path
    VNF_instance_list = []
    for element in server_VNF_list:
        VNF_instance_list.append(element['VNF'])
    VNF_tuple = tuple(VNF_instance_list)
    request_src = path_segment_list[0][0]  # ingress of request
    request_dst = path_segment_list[-1][-1]  # egress of request
    if VNF_tuple in SP_list_:
        related_RSP_list_ = SP_list_[VNF_tuple]
        for RSP_id in related_RSP_list_:
            # bingo! new path == Existing RSP
            if is_equal_path_segment_list(path_segment_list, related_RSP_list_[RSP_id]['path_segment_list']):
                SP_list_[VNF_tuple][RSP_id]['request_list'].append(request_id)
                switch_info_[request_src]['classification'][request_id] = RSP_id
                if switch_info_[request_src]['entry_number'] + 1 > entries_threshold:
                    return False, new_rules_OVS
                switch_info_[request_src]['entry_number'] += 1
                switch_info_[request_dst]['declassification'][request_id] = RSP_id
                if switch_info_[request_dst]['entry_number'] + 1 > entries_threshold:
                    return False, new_rules_OVS
                switch_info_[request_dst]['entry_number'] += 1
                # same path and VNF_tuple
                switch_info.clear()
                for k in switch_info_:
                    switch_info[k] = copy.deepcopy(switch_info_[k])
                SP_list.clear()
                for k in SP_list_:
                    SP_list[k] = copy.deepcopy(SP_list_[k])
                return True, new_rules_OVS
    # obtain new RSP_id, install classification rules on src
    RSP_id = new_RSP_id(SP_list_)
    if VNF_tuple not in SP_list_:
        SP_list_[VNF_tuple] = {}
    SP_list_[VNF_tuple][RSP_id] = {'path_segment_list': list(path_segment_list), 'request_list': [request_id]}
    # ingress classification
    switch_info_[request_src]['classification'][request_id] = RSP_id
    if switch_info_[request_src]['entry_number'] + 1 > entries_threshold:
        return False, new_rules_OVS
    switch_info_[request_src]['entry_number'] += 1
    # egress declassification
    switch_info_[request_dst]['declassification'][request_id] = RSP_id
    if switch_info_[request_dst]['entry_number'] + 1 > entries_threshold:
        return False, new_rules_OVS
    switch_info_[request_dst]['entry_number'] += 1

    # for each path segment, install the rules
    for path_segment_idx, path_segment in enumerate(path_segment_list):
        for node_idx, node in enumerate(path_segment):
            if (path_segment_idx == 0 and node_idx == 0) or \
                    (path_segment_idx == len(path_segment_list) - 1 and node_idx == len(path_segment) - 1):
                continue
            if path_segment_idx >= 1 and path_segment_idx <= len(server_VNF_list) - 1:
                if server_VNF_list[path_segment_idx]['server'] == server_VNF_list[path_segment_idx - 1]['server']:
                    break
            switch_info_[node]['RSP_id'].append(RSP_id)
            if switch_info_[node]['entry_number'] + 1 > entries_threshold:
                return False, new_rules_OVS
            switch_info_[node]['entry_number'] += 1
        # NEWFEA
        if path_segment_idx == 0 or path_segment_idx == len(path_segment_list) - 1:
            new_rules_OVS += 1
        else:
            # if path_segment_idx >= 1 and path_segment_idx <= len(server_VNF_list) - 1:
            if server_VNF_list[path_segment_idx]['server'] == server_VNF_list[path_segment_idx - 1][
                'server']:  # pass the same server for multiple times
                new_rules_OVS += 1
            else:
                new_rules_OVS += 2

    switch_info.clear()
    for k in switch_info_:
        switch_info[k] = copy.deepcopy(switch_info_[k])
    SP_list.clear()
    for k in SP_list_:
        SP_list[k] = copy.deepcopy(SP_list_[k])
    return True, new_rules_OVS