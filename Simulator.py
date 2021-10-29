import helper
from orche_algorithms import SGH,FPTAS,VNF,H_OP
from ts_frameworks import NSH,SAFEME,STAR,ip_5_tuple

class Simulator:
    def __init__(self,topo_file_name=None, request_file_name=None, orche_name=None, ts_name=None,
                 served_request_num_threshold=None, served_request_num_list=None, entries_threshold=0,
                 log_file_name=None):
        self.topo_file_name = topo_file_name
        self.request_file_name = request_file_name
        self.orche_name = orche_name
        self.ts_name = ts_name
        self.served_request_num_threshold = served_request_num_threshold
        self.served_request_num_list = served_request_num_list
        self.entries_threshold = entries_threshold
        self.log_file_name = log_file_name
        assert topo_file_name is not None and request_file_name is not None and orche_name is not None and \
            ts_name is not None and served_request_num_threshold is not None and served_request_num_list is not None \
            and entries_threshold is not None and log_file_name is not None

    def configuration(self):
        pass

    def run_simulation(self):
        log_file = open("logs/"+self.log_file_name,'w')
        if self.orche_name != "FPTAS":
            topo = helper.read_file_to_topo_orche(self.topo_file_name)
            request_list = helper.read_file_to_request_list(self.request_file_name)
            installed_VNF_list = []
        else:
            installed_VNF_list = VNF.read_file_to_installed_VNF_instance_list_FPTAS("sample_topo/sample_VNF")
            topo = helper.read_file_to_topo_FPTAS(self.topo_file_name)
            request_list = helper.read_file_to_request_list_FPTAS(self.request_file_name)
        served_request_num = 0

        if self.ts_name == "NSH":
            switch_info = NSH.initial_switch_info_NSH(topo) # NSH
            SP_list = {}
            request_id = 0
            deployed_request_number = 0
        elif self.ts_name == "SAFEME":
            switch_info, switch_default_path_switch = \
                SAFEME.initial_switch_info_from_topo_SAFE_ME(topo)  # SAFE-ME
            entry_number = helper.calculate_total_entry_num(switch_info)
            switch_default_path_VNF = {}
            deployed_request_number = 0
            request_id = 0
        elif self.ts_name == "STAR":
            switch_info, ini_path_to_switch, ext_path_switch_to_switch = STAR.initial_switch_info_from_topo_STAR(topo)
            SP_list = {}
            request_id = 0
            deployed_request_number = 0
        elif self.ts_name == "5-tuple":
            switch_info = ip_5_tuple.initial_switch_info_5_tuple(topo) # 5-tuple
            request_id = 0
            deployed_request_number = 0



        issued_rules_list = []
        last_entry_number = helper.calculate_total_entry_num(switch_info)
        max_newly_installed_entry_number = 0
        total_newly_installed_entry_number = 0
        avg_newly_installed_entry_number = 0


        for a_request in request_list:
            if served_request_num >= self.served_request_num_threshold:  # 限制 served request number 的数量
                break
            if self.orche_name == "SGH":
                is_served, server_VNF_list, path_segment_list = SGH.serve_a_request_SGH(topo=topo,
                                                                              installed_VNF_list=installed_VNF_list,
                                                                              request=a_request)
            elif self.orche_name == "FPTAS":
                is_served,server_VNF_list, path_segment_list = FPTAS.serve_a_request(topo=topo,
                                                                              installed_VNF_list=installed_VNF_list,
                                                                              request=a_request)
            elif self.orche_name == "H-OP":
                is_served, server_VNF_list, path_segment_list = H_OP.serve_a_request(topo=topo,
                                                                           installed_VNF_list=installed_VNF_list,
                                                                            request=a_request)
            if is_served:
                served_request_num += 1

                if self.ts_name == "NSH":
                    is_deployed, new_rules_OVS = NSH.rules_install_with_NSH(switch_info=switch_info,SP_list=SP_list,
                                                                            installed_VNF_list=installed_VNF_list,
                                           server_VNF_list=server_VNF_list, path_segment_list=path_segment_list,
                                            request_id=request_id, entries_threshold=self.entries_threshold)
                elif self.ts_name == "SAFEME":
                    is_deployed, new_rules_OVS =SAFEME.rules_install_with_SAFE_ME(topo=topo,switch_info=switch_info,
                        installed_VNF_list=installed_VNF_list,switch_default_path_VNF=switch_default_path_VNF,
                        switch_default_path_switch=switch_default_path_switch,server_VNF_list=server_VNF_list,
                        path_segment_list=path_segment_list,request_id=request_id,
                        entries_threshold=self.entries_threshold)
                elif self.ts_name == "STAR":
                    is_deployed, new_rules_OVS = STAR.rules_install_with_STAR(topo, switch_info,
                                                                                       ini_path_to_switch,
                                                                                       ext_path_switch_to_switch,
                                                                                       SP_list, server_VNF_list,
                                                                                       path_segment_list, request_id,
                                                                                       self.entries_threshold)
                elif self.ts_name == '5-tuple':
                    is_deployed, new_rules_OVS = ip_5_tuple.rules_install_with_5_tuple(topo=topo,
                        switch_info=switch_info,installed_VNF_list=installed_VNF_list,
                        server_VNF_list=server_VNF_list,path_segment_list=path_segment_list,
                        request_id=request_id,entries_threshold=self.entries_threshold)
                if is_deployed:
                    # print("is_deployed", deployed_request_number)
                    entry_number = helper.calculate_total_entry_num(switch_info)
                    # print('entry number', entry_number) for debug
                    newly_installed_entry_num = entry_number - last_entry_number + new_rules_OVS
                    issued_rules_list.append(newly_installed_entry_num)
                    last_entry_number = entry_number
                    if newly_installed_entry_num > max_newly_installed_entry_number:
                        max_newly_installed_entry_number = newly_installed_entry_num
                    total_newly_installed_entry_number += newly_installed_entry_num
                    # avg_newly_installed_entry_number += newly_installed_entry_num
                    deployed_request_number += 1
                request_id = request_id + 1
            if served_request_num in self.served_request_num_list:
                print('------------------------------------------', file=log_file)
                print('served request number = ', served_request_num, file=log_file)
                print('entry number of each physical switch:', file=log_file)
                total_entry_num = 0
                for i in switch_info:
                    if 'entry_number' in switch_info[i]:
                        print(i, switch_info[i]['entry_number'], file=log_file)
                        total_entry_num += switch_info[i]['entry_number']
                print("total_entry_num", entry_number, file=log_file)
                print("served_request_num", served_request_num, file=log_file)
                print("deployed request num", deployed_request_number, file=log_file)
                print("deployed rate", deployed_request_number / served_request_num, file=log_file)
                max_entry_num_switch, max_entry_num = helper.give_max_entry_number(switch_info)
                print("max entry number switch=", max_entry_num_switch, file=log_file)
                print("max entry number", max_entry_num, file=log_file)
                print("entry per request", entry_number / deployed_request_number, file=log_file)
                print("max entry per switch", max_entry_num / deployed_request_number, file=log_file)
                avg_newly_installed_entry_number = total_newly_installed_entry_number / deployed_request_number
                print("max newly installed entry number counted OVS", max_newly_installed_entry_number, file=log_file)
                print("avg newly installed entry number counted OVS", avg_newly_installed_entry_number, file=log_file)
                print('------------------------------------------', file=log_file)
            print(served_request_num)



