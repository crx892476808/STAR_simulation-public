import networkx as nx
from networkx import NetworkXNoPath
import copy
import VNF as VNF_module


def serve_a_request_SGH(topo, installed_VNF_list, request):

    # return when SGH is unable to serve the request
    fail_ret = (False, [], [])

    new_VNF_list = []

    # build the residual network
    resi_topo = nx.Graph()
    for node in topo.nodes:
        if topo.nodes[node]['node_type'] == 0:
            resi_topo.add_node(node, node_type=0)
        elif topo.nodes[node]['node_type'] == 1:
            resi_topo.add_node(node, node_type=1, connected_switch=topo.nodes[node]['connected_switch'],
                               core=topo.nodes[node]['core'], remain_core=topo.nodes[node]['remain_core'])
    for u, v in topo.edges:
        if topo.edges[u, v]['remain_bandwidth'] >= request['traffic_rate'] * len(request['SFC']):
            resi_topo.add_edge(u, v, bandwidth=topo.edges[u, v]['bandwidth'], delay=topo.edges[u, v]['delay'],
                               remain_bandwidth=topo.edges[u, v]['remain_bandwidth'])

    # server_list
    server_list = []
    for node in resi_topo.nodes:
        if resi_topo.nodes[node]['node_type'] == 1:
            server_list.append(node)

    # Algorithm's main process
    path_segment_list = []
    server_and_VNF_list = []
    k_now = 0

    while k_now < len(request['SFC']):

        has_reusable_vnf_instance = False
        k = k_now
        for vnf in request['SFC'][k_now:]:
            # first find reuseable VNF instance
            shortest_choice = -1
            reuse_vnf_instance = -1
            for installed_VNF_instance in installed_VNF_list:
                if installed_VNF_instance['type'] == vnf and \
                    installed_VNF_instance['remain_cap'] >= request['traffic_rate']:
                    server = installed_VNF_instance['server']
                    connected_switch = resi_topo.nodes[server]['connected_switch']
                    if len(path_segment_list) == 0:
                        src = request['src']
                    else:
                        src = path_segment_list[-1][-1]
                    try:
                        if nx.shortest_path_length(resi_topo,src,connected_switch,weight='delay') \
                            < shortest_choice or shortest_choice == -1:
                            shortest_choice = nx.shortest_path_length(resi_topo,src,connected_switch,weight='delay')
                            reuse_vnf_instance = installed_VNF_instance['id']
                    except NetworkXNoPath:
                        pass
            if shortest_choice != -1: # got reuseable VNF, build path_segment_list and  vnf_server_list
                for gap in range(k_now, k):#enumerate(request['SFC'][k_now:k]):
                    gap_vnf = request['SFC'][gap]
                    shortest_choice = -1
                    server_to_use = -1
                    path_segment_to_use = []
                    for server in server_list:
                        if resi_topo.nodes[server]['remain_core'] >= VNF_module.VNF_type_list_orche[gap_vnf]['core_req']:
                            connected_switch = resi_topo.nodes[server]['connected_switch']
                            server_to_go = installed_VNF_list[reuse_vnf_instance]['server']
                            switch_to_go = resi_topo.nodes[server_to_go]['connected_switch']
                            if gap == 0:
                                switch_from = request['src']
                            else:
                                switch_from = path_segment_list[-1][-1]
                            try:
                                if nx.shortest_path_length(resi_topo,switch_from,connected_switch,weight='delay') + \
                                    nx.shortest_path_length(resi_topo, connected_switch, switch_to_go,weight='delay') < \
                                    shortest_choice or shortest_choice == -1:
                                    shortest_choice = nx.shortest_path_length(resi_topo,switch_from,connected_switch,weight='delay') + \
                                    nx.shortest_path_length(resi_topo, connected_switch, switch_to_go,weight='delay')
                                    path_segment_to_use = copy.deepcopy(nx.shortest_path(resi_topo,switch_from,connected_switch,weight='delay'))
                                    server_to_use = server
                            except NetworkXNoPath:
                                pass
                    if server_to_use == -1:
                        return fail_ret
                    path_segment = copy.deepcopy(path_segment_to_use)
                    path_segment_list.append(path_segment)
                    choose_VNF = len(installed_VNF_list)
                    VNF_type = gap_vnf
                    choose_server = server_to_use
                    remain_cap = VNF_module.VNF_type_list_orche[gap_vnf]['capacity'] - request['traffic_rate']
                    core_req = VNF_module.VNF_type_list_orche[VNF_type]['core_req']
                    installed_VNF_list.append({
                        'id': choose_VNF,
                        'type': VNF_type,
                        'server': choose_server,
                        'remain_cap': remain_cap
                    })
                    server_and_VNF_list.append({'VNF':choose_VNF,'server':choose_server})
                    new_VNF_list.append(choose_VNF)
                    resi_topo.nodes[choose_server]['remain_core'] -= core_req
                # for reused VNF
                if k == 0:
                    src = request['src']
                else:
                    src = path_segment_list[-1][-1]
                server = installed_VNF_list[reuse_vnf_instance]['server']
                connected_switch = resi_topo.nodes[server]['connected_switch']
                path_segment = nx.shortest_path(resi_topo,src,connected_switch,weight='delay')
                path_segment_list.append(path_segment)
                server_and_VNF_list.append({'VNF':reuse_vnf_instance,'server':server})
                installed_VNF_list[reuse_vnf_instance]['remain_cap'] -= request['traffic_rate']

                # update
                k_now = k+1
                has_reusable_vnf_instance = True
                break
            else:  # do not find
                k = k + 1
                continue

        if has_reusable_vnf_instance == False:
            break

    # For VNFs after k_now, find servers
    vnf_idx = k_now
    for  vnf in request['SFC'][k_now:]:
        shortest_choice = -1
        to_use_server = -1
        for server in server_list:
            #print(resi_topo.nodes[server]['remain_core'])
            if resi_topo.nodes[server]['remain_core'] >=  VNF_module.VNF_type_list_orche[vnf]['core_req']:
                connected_switch = resi_topo.nodes[server]['connected_switch']
                if vnf_idx == 0:
                    src = request['src']
                else:
                    src = path_segment_list[-1][-1]
                try:
                    if nx.shortest_path_length(resi_topo,src,connected_switch,weight='delay') < shortest_choice \
                        or shortest_choice == -1:
                        shortest_choice = nx.shortest_path_length(resi_topo,src,connected_switch,weight='delay')
                        to_use_server = server
                except NetworkXNoPath:
                    pass
        if shortest_choice == -1:
            return fail_ret
        if vnf_idx == 0:
            src = request['src']
        else:
            src = path_segment_list[-1][-1]
        if to_use_server == -1:
            return  fail_ret
        connected_switch = resi_topo.nodes[to_use_server]['connected_switch']
        path_segment = nx.shortest_path(resi_topo, src, connected_switch)
        path_segment_list.append(path_segment)
        choose_VNF = len(installed_VNF_list)
        VNF_type = request['SFC'][vnf_idx]
        remain_cap = VNF_module.VNF_type_list_orche[VNF_type]['capacity'] - request['traffic_rate']
        core_req = VNF_module.VNF_type_list_orche[VNF_type]['core_req']
        installed_VNF_list.append({
            'id': choose_VNF,
            'type': VNF_type,
            'server': to_use_server,
            'remain_cap':remain_cap
        })
        new_VNF_list.append(choose_VNF)
        server_and_VNF_list.append({'VNF': choose_VNF, 'server': to_use_server})
        resi_topo.nodes[to_use_server]['remain_core'] -= core_req
        vnf_idx = vnf_idx + 1

    # reach the destination
    src = path_segment_list[-1][-1]
    try:
        path_segment = nx.shortest_path(resi_topo, src, request['dst'],weight='delay')
        path_segment_list.append(path_segment)
    except NetworkXNoPath:
        return fail_ret

    # server,link resources consumption computation
    for server_and_VNF in server_and_VNF_list:
        if server_and_VNF['VNF'] in new_VNF_list:
            vnf = installed_VNF_list[server_and_VNF['VNF']]['type']
            topo.nodes[server_and_VNF['server']]['remain_core'] -= VNF_module.VNF_type_list_orche[vnf]['core_req']
    for path_segment in path_segment_list:
        for u_idx,u in enumerate(path_segment):
            if u_idx == len(path_segment)-1:
                break
            v = path_segment[u_idx+1]
            topo.edges[u,v]['remain_bandwidth'] -= request['traffic_rate']
    # print(request)
    return True, server_and_VNF_list,path_segment_list