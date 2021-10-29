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
    # 无法服务该请求时的返回值
    fail_ret = (False, [], [])

    # 构建残差网络
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
    # 构建辅助图
    # 用于剔除无法完成安装的server
    total_core_req = 0
    for VNF_type in request['SFC']:
        total_core_req = total_core_req + VNF_module.VNF_type_list_orche[VNF_type]['core_req']
    # 辅助图顶点，一定是可行的顶点才会出现在辅助图
    stage_node = dict()
    stage_node[0, 1] = {'switch': request['src'], 'cost': 0}  # 起点
    state_num_layer = {}
    state_num_layer[0] = 1
    cur_stage = 1
    for VNF_type in request['SFC']: # state的计数从1开始
        state_num = 0
        # 添加已安装VNF实例的状态节点
        used_server_list = []
        for VNF_id, VNF in enumerate(installed_VNF_list):
            if VNF['type'] == VNF_type and VNF['remain_cap'] >= request['traffic_rate']:
                server = VNF['server']
                switch = resi_topo.nodes[server]['connected_switch']
                state_num = state_num + 1
                stage_node[cur_stage, state_num] = {'switch': switch, 'server': server, "is_installed": True,
                                                    'VNF': VNF_id, 'cost': 0}
                used_server_list.append(server)
        # 添加未安装VNF实例的状态节点
        for server in [node for node in list(topo.nodes) if topo.nodes[node]['node_type'] == 1]:
            if topo.nodes[server]['remain_core'] < total_core_req or server in used_server_list:
                continue
            switch = resi_topo.nodes[server]['connected_switch']
            state_num = state_num + 1
            stage_node[cur_stage, state_num] = {'switch': switch, 'server': server, "is_installed": False,
                                                'cost': OrchesAlgorithmParam.cost_VNF[VNF_type] *
                                                        OrchesAlgorithmParam.alpha
                                                }
        state_num_layer[cur_stage] = state_num  # 记录每一层的状态数量
        cur_stage = cur_stage + 1
    state_num_layer[cur_stage] = 1
    stage_node[len(request['SFC'])+1, 1] = {'switch': request['dst'], 'cost': 0}  # 终点

    # 输出一下最终结果
    # for i in range(len(request['SFC']) + 2):
    #     for j in range(1,state_num_layer[i]+1):
    #         print('stage_node[{0}][{1}]='.format(i, j)+str(stage_node[i, j]), end=' ')
    #     print('\n')

    # 辅助图的边，两个阶段的点不一定会有边相连
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
    # 输出一下最终结果
    # for i in range(len(request['SFC']) + 1):
    #     for j in range(1, state_num_layer[i]+1):
    #         for k in range(1, state_num_layer[i+1]+1):
    #             print(stage_edge[i, j, i+1, k]['cost'])

    # 动态规划计算
    result = {}
    result[0,1] = {'cost':0,'last':-1} # last 表示上一层所用的节点
    for i in range(1,len(request['SFC']) + 2): # 从第一层到最后一层都需要动态规划计算
        for j in range(1, state_num_layer[i]+1): # 当前层的所有节点都需要计算
            min_cost = sys.maxsize
            choose_last = -1
            node_cost = stage_node[i, j]['cost']
            for k in range(1, state_num_layer[i-1]+1):
                last_cost = result[i-1, k]['cost']
                if (i-1, k, i, j) not in stage_edge or last_cost == sys.maxsize:  # 当辅助图中的边不存在时，或上一个顶点是孤儿点时
                    continue
                edge_cost = stage_edge[i-1, k, i, j]['cost']

                if last_cost + node_cost + edge_cost < min_cost:
                    choose_last = k
                    min_cost = node_cost + edge_cost
            result[i,j] = {'cost':min_cost, 'last':choose_last}


    # 回溯得到解，result用于回溯，真正选择的点存放在recursive_result
    # 解的存在性检查，如果通过算法发现没有可行解，则停止服务请求，告知上层模块
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


    # 返回给路径部署模块的VNF组
    ret_server_and_VNF_list = []
    # 更新网络情况，首先更新网络功能安装情况
    for i in range(1,len(request['SFC'])+1):  # 从中间状态节点开始
        choose_VNF = -1
        choose_server = -1
        # 如果是已安装的VNF实例节点，减去相应的remain_capacity
        if recursive_result[i]['is_installed'] == True:
            choose_VNF = recursive_result[i]['VNF']
            choose_server = recursive_result[i]['server']
            # 修改installed_VNF_list[VNF_id]
            installed_VNF_list[choose_VNF]['remain_cap'] -= request['traffic_rate']
        else:
            choose_server = recursive_result[i]['server']
            # 新增VNF 实例
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


    # 返回给路径部署模块的路径组
    ret_path_segment_list = []
    # 接下来更新链路带宽
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