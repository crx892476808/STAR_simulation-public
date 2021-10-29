import networkx as nx
from networkx import NetworkXNoPath
import VNF as VNF_module
import sys

class OrchesAlgorithmParam:
    alpha = 1
    gamma = 1
    cost_VNF = [1, 1, 1, 1]
    cost_traffic = 0.001

def serve_a_request(topo, installed_VNF_list, request):
    # �޷����������ʱ�ķ���ֵ
    fail_ret = (False, [], [])

    # �����в�����
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
    # ��������ͼ
    # �����޳��޷���ɰ�װ��server
    total_core_req = 0
    for VNF_type in request['SFC']:
        total_core_req = total_core_req + VNF_module.VNF_type_list_orche[VNF_type]['core_req']
    # ����ͼ���㣬һ���ǿ��еĶ���Ż�����ڸ���ͼ
    stage_node = dict()
    stage_node[0, 1] = {'switch': request['src'], 'cost': 0}  # ���
    state_num_layer = {}
    state_num_layer[0] = 1
    cur_stage = 1
    for VNF_type in request['SFC']: # state�ļ�����1��ʼ
        state_num = 0
        # ����Ѱ�װVNFʵ����״̬�ڵ�
        used_server_list = []
        for VNF_id, VNF in enumerate(installed_VNF_list):
            if VNF['type'] == VNF_type and VNF['remain_cap'] >= request['traffic_rate']:
                server = VNF['server']
                switch = resi_topo.nodes[server]['connected_switch']
                state_num = state_num + 1
                stage_node[cur_stage, state_num] = {'switch': switch, 'server': server, "is_installed": True,
                                                    'VNF': VNF_id, 'cost': 0}
                used_server_list.append(server)
        # ���δ��װVNFʵ����״̬�ڵ�
        for server in [node for node in list(topo.nodes) if topo.nodes[node]['node_type'] == 1]:
            if topo.nodes[server]['remain_core'] < total_core_req or server in used_server_list:
                continue
            switch = resi_topo.nodes[server]['connected_switch']
            state_num = state_num + 1
            stage_node[cur_stage, state_num] = {'switch': switch, 'server': server, "is_installed": False,
                                                'cost': OrchesAlgorithmParam.cost_VNF[VNF_type] *
                                                        OrchesAlgorithmParam.alpha
                                                }
        state_num_layer[cur_stage] = state_num  # ��¼ÿһ���״̬����
        cur_stage = cur_stage + 1
    state_num_layer[cur_stage] = 1
    stage_node[len(request['SFC'])+1, 1] = {'switch': request['dst'], 'cost': 0}  # �յ�

    # ���һ�����ս��
    # for i in range(len(request['SFC']) + 2):
    #     for j in range(1,state_num_layer[i]+1):
    #         print('stage_node[{0}][{1}]='.format(i, j)+str(stage_node[i, j]), end=' ')
    #     print('\n')

    # ����ͼ�ıߣ������׶εĵ㲻һ�����б�����
    stage_edge = {}
    for i in range(len(request['SFC']) + 1):
        for j in range(1, state_num_layer[i]+1):
            for k in range(1, state_num_layer[i+1]+1):
                stage_switch = stage_node[i, j]['switch']
                next_stage_switch = stage_node[i+1, k]['switch']
                try:
                    stage_shortest_path = nx.shortest_path(resi_topo, stage_switch, next_stage_switch, weight='delay')
                    stage_edge_cost = request['traffic_rate'] * len(stage_shortest_path) * \
                                  OrchesAlgorithmParam.cost_traffic * OrchesAlgorithmParam.gamma
                    stage_edge[i, j, i+1, k] = {'cost': stage_edge_cost}
                except NetworkXNoPath:
                    pass
    # ���һ�����ս��
    # for i in range(len(request['SFC']) + 1):
    #     for j in range(1, state_num_layer[i]+1):
    #         for k in range(1, state_num_layer[i+1]+1):
    #             print(stage_edge[i, j, i+1, k]['cost'])

    # ��̬�滮����
    result = {}
    result[0,1] = {'cost':0,'last':-1} # last ��ʾ��һ�����õĽڵ�
    for i in range(1,len(request['SFC']) + 2): # �ӵ�һ�㵽���һ�㶼��Ҫ��̬�滮����
        for j in range(1, state_num_layer[i]+1): # ��ǰ������нڵ㶼��Ҫ����
            min_cost = sys.maxsize
            choose_last = -1
            node_cost = stage_node[i, j]['cost']
            for k in range(1, state_num_layer[i-1]+1):
                last_cost = result[i-1, k]['cost']
                if (i-1, k, i, j) not in stage_edge or last_cost == sys.maxsize:  # ������ͼ�еı߲�����ʱ������һ�������ǹ¶���ʱ
                    continue
                edge_cost = stage_edge[i-1, k, i, j]['cost']

                if last_cost + node_cost + edge_cost < min_cost:
                    choose_last = k
                    min_cost = node_cost + edge_cost
            result[i,j] = {'cost':min_cost, 'last':choose_last}


    # ���ݵõ��⣬result���ڻ��ݣ�����ѡ��ĵ�����recursive_result
    # ��Ĵ����Լ�飬���ͨ���㷨����û�п��н⣬��ֹͣ�������󣬸�֪�ϲ�ģ��
    if result[len(request['SFC'])+1, 1]['cost'] == sys.maxsize:
        return fail_ret
    recursive_stage = result[len(request['SFC'])+1, 1]
    recursive_result = [stage_node[len(request['SFC'])+1, 1]]
    cur_stage_idx = len(request['SFC']) + 1
    while recursive_stage['last'] != -1:
        last_idx = recursive_stage['last']
        cur_stage_idx = cur_stage_idx - 1
        recursive_stage = result[cur_stage_idx, last_idx]
        recursive_result.insert(0,stage_node[cur_stage_idx, last_idx])


    # ���ظ�·������ģ���VNF��
    ret_server_and_VNF_list = []
    # ����������������ȸ������繦�ܰ�װ���
    for i in range(1,len(request['SFC'])+1):  # ���м�״̬�ڵ㿪ʼ
        choose_VNF = -1
        choose_server = -1
        # ������Ѱ�װ��VNFʵ���ڵ㣬��ȥ��Ӧ��remain_capacity
        if recursive_result[i]['is_installed'] == True:
            choose_VNF = recursive_result[i]['VNF']
            choose_server = recursive_result[i]['server']
            # �޸�installed_VNF_list[VNF_id]
            installed_VNF_list[choose_VNF]['remain_cap'] -= request['traffic_rate']
        else:
            choose_server = recursive_result[i]['server']
            # ����VNF ʵ��
            choose_VNF = len(installed_VNF_list)
            VNF_type = request['SFC'][i-1]
            remain_cap = VNF_module.VNF_type_list_orche[VNF_type]['capacity'] - request['traffic_rate']
            core_req = VNF_module.VNF_type_list_orche[VNF_type]['core_req']
            installed_VNF_list.append({
                'id': choose_VNF,
                'type': VNF_type,
                'server': choose_server,
                'remain_cap':remain_cap
            })
            topo.nodes[choose_server]['remain_core'] -= core_req
        ret_server_and_VNF_list.append({'VNF':choose_VNF,'server':choose_server})


    # ���ظ�·������ģ���·����
    ret_path_segment_list = []
    # ������������·����
    for i in range(0, len(request['SFC'])+1):
        u = recursive_result[i]['switch']
        v = recursive_result[i+1]['switch']
        stage_shortest_path = nx.shortest_path(resi_topo,u,v,weight='delay')
        for idx,_ in enumerate(stage_shortest_path):
            if idx == len(stage_shortest_path) - 1:
                break
            from_node = stage_shortest_path[idx]
            to_node = stage_shortest_path[idx+1]
            topo.edges[from_node,to_node]['remain_bandwidth'] -= request['traffic_rate']
        ret_path_segment_list.append(stage_shortest_path)

    # for debug
    # print("request", request)
    # print("ret_server_VNF_list", ret_server_and_VNF_list)
    # print("ret_path_segment_list", ret_path_segment_list)
    # print("installed_VNF_list", installed_VNF_list)

    return True, ret_server_and_VNF_list, ret_path_segment_list