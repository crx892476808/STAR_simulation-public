import networkx as nx
from networkx import NetworkXNoPath

def serve_a_request(topo, installed_VNF_list, request):
    # return when request can not be served
    fail_ret = (False, [], [])

    # build residual
    residue_topo = nx.Graph()
    for node in topo.nodes:
        if topo.nodes[node]['node_type'] == 0:
            residue_topo.add_node(node, node_type=0)
        elif topo.nodes[node]['node_type'] == 1:
            residue_topo.add_node(node, node_type=1, connected_switch=topo.nodes[node]['connected_switch'])

    for u, v in topo.edges:
        if topo.edges[u, v]['remain_bandwidth'] >= request['traffic_rate'] * len(request['SFC']):
            residue_topo.add_edge(u, v, bandwidth=topo.edges[u, v]['bandwidth'],
                                  remain_bandwidth=topo.edges[u, v]['remain_bandwidth'],
                                  delay=topo.edges[u, v]['delay'],
                                  edge_type=topo.edges[u, v]['edge_type'],
                                  weight=1 / topo.edges[u, v]['remain_bandwidth'])
    # # build A/B graph in previous, based on the residual graph 提前构建用于计算最短路径的A，B 图，在残差图的基础上做
    # link_A_topo = nx.Graph()
    # link_B_topo = nx.Graph()
    # for node in residue_topo.nodes:
    #     if residue_topo.nodes[node]['node_type'] == 0:
    #         link_A_topo.add_node(node,node_type=0)
    #         link_B_topo.add_node(node,node_type=0)
    #     elif residue_topo.nodes[node]['node_type'] == 1:
    #         link_A_topo.add_node(node,node_type=1,connected_switch=residue_topo.nodes[node]['connected_switch'])
    #         #link_A_topo.add_edge(node, link_A_topo.nodes[node]['connected_switch'],weight=0)
    #         link_B_topo.add_node(node, node_type=1, connected_switch=residue_topo.nodes[node]['connected_switch'])
    #         #link_B_topo.add_edge(node, link_B_topo.nodes[node]['connected_switch'], weight=0)
    # for u, v in residue_topo.edges:
    #     if residue_topo.edges[u,v]['edge_type'] == 'A':
    #         link_A_topo.add_edge(u,v,weight=1/residue_topo.edges[u,v]['remain_bandwidth'])
    #     elif residue_topo.edges[u,v]['edge_type'] == 'B':
    #         link_B_topo.add_edge(u,v,weight=1/residue_topo.edges[u,v]['remain_bandwidth'])

    # calculate the global shortest path, build the multi-layer graph
    multi_layer_topo = nx.Graph()
    # build by layer
    current_id_add = 0  # add 100 per layer
    for VNF_idx, VNF in enumerate(request['SFC']):  # current layer is responsible for the forwarding for next layer
        available_server_list = []
        for vnf_instance in installed_VNF_list:
            if vnf_instance['type'] == VNF and vnf_instance['remain_cap'] >= request['traffic_rate'] and \
                    vnf_instance['server'] not in available_server_list:  # avoid multi edges
                available_server_list.append(vnf_instance['server'])
        # vertice first
        for node in residue_topo.nodes:
            if residue_topo.nodes[node]['node_type'] == 0:
                if node + current_id_add not in multi_layer_topo.nodes:
                    multi_layer_topo.add_node(node + current_id_add, node_type=0)
        # add links
        for u, v in residue_topo.edges:
            if request['type_req'][VNF_idx] == 'all' or \
                    request['type_req'][VNF_idx] == 'A' and residue_topo.edges[u, v]['edge_type'] == 'A' or \
                    request['type_req'][VNF_idx] == 'B' and residue_topo.edges[u, v]['edge_type'] == 'B':
                multi_layer_topo.add_edge(u + current_id_add,
                                          v + current_id_add,
                                          weight=residue_topo.edges[u, v]['weight'])

        # switch to server，server to next-layer switch
        for server in available_server_list:
            connected_switch = residue_topo.nodes[server]['connected_switch']

            multi_layer_topo.add_edge(connected_switch + current_id_add, server + current_id_add, weight=0)
            multi_layer_topo.add_edge(server + current_id_add, connected_switch + current_id_add + 100, weight=0)
        current_id_add = current_id_add + 100
    # the last layer: go to the egress switch
    for node in residue_topo.nodes:
        if residue_topo.nodes[node]['node_type'] == 0:  #
            if node + current_id_add not in multi_layer_topo.nodes:  #
                multi_layer_topo.add_node(node + current_id_add, node_type=0)
    for u, v in residue_topo.edges:
        if request['type_req'][len(request['SFC'])] == 'all' or \
                request['type_req'][len(request['SFC'])] == 'A' and residue_topo.edges[u, v]['edge_type'] == 'A' or \
                request['type_req'][len(request['SFC'])] == 'B' and residue_topo.edges[u, v]['edge_type'] == 'B':
            multi_layer_topo.add_edge(u + current_id_add,
                                      v + current_id_add,
                                      weight=residue_topo.edges[u, v]['weight'])
    # shortest path
    try:
        shortest_path_multi_layer = nx.shortest_path(multi_layer_topo, request['src'], request['dst'] + current_id_add,
                                                 weight='weight')
    except NetworkXNoPath:
        return fail_ret
    # return
    ret_server_and_VNF_list = []
    ret_path_segment_list = []
    current_id_add = 0
    current_iter_on_path = 0
    # pass-by VNF
    for VNF_idx, VNF in enumerate(request['SFC']):
        new_path_segment = []
        while 1:
            current_node = shortest_path_multi_layer[current_iter_on_path] - current_id_add
            if topo.nodes[current_node]['node_type'] == 0:
                new_path_segment.append(current_node)
                current_iter_on_path += 1

            else:  # server
                for vnf_instance in installed_VNF_list:
                    if vnf_instance['type'] == VNF and vnf_instance['server'] == current_node:
                        ret_server_and_VNF_list.append({'VNF': vnf_instance['id'], 'server': current_node})
                        break
                current_iter_on_path += 1
                break

        ret_path_segment_list.append(list(new_path_segment))
        current_id_add = current_id_add + 100
    # reach the egress
    new_path_segment = []
    while current_iter_on_path < len(shortest_path_multi_layer):
        current_node = shortest_path_multi_layer[current_iter_on_path] - current_id_add
        new_path_segment.append(current_node)
        current_iter_on_path += 1
    ret_path_segment_list.append(new_path_segment)


    # update the topology
    # update the link first
    for path_segment in ret_path_segment_list:
        for u_idx, u in enumerate(path_segment):
            if u_idx == len(path_segment) - 1:
                continue
            v = path_segment[u_idx + 1]
            topo.edges[u,v]['remain_bandwidth'] = topo.edges[u,v]['remain_bandwidth'] - request['traffic_rate']
    # update available capacity of vnf instance
    for server_vnf in ret_server_and_VNF_list:
        for vnf_instance in installed_VNF_list:
            if vnf_instance['id'] == server_vnf['VNF']:
                vnf_instance['remain_cap'] = vnf_instance['remain_cap'] - request['traffic_rate']

    # return the result
    return True, ret_server_and_VNF_list, ret_path_segment_list

    # print(ret_path_segment_list)
    # print(ret_server_and_VNF_list)
    #
    # print(installed_VNF_list)
    # print(request)
    # print(len(residue_topo.edges))
    # print(len(multi_layer_topo.nodes))
    # print(len(multi_layer_topo.edges))
    # print(nx.shortest_path(multi_layer_topo, request['src'], request['dst'] + current_id_add, weight='weight'))
    # print(nx.shortest_path_length(multi_layer_topo, request['src'], request['dst'] + current_id_add, weight='weight'))

    # for u,v in algorithm_topo.edges:
    #     print(algorithm_topo.edges[u,v])