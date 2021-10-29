from Simulator import Simulator

def main():
    simulator = Simulator(topo_file_name="sample_topo/sample_topo",request_file_name="sample_request/sample_request",
                          orche_name="SGH",ts_name="NSH",served_request_num_threshold=100,
                          served_request_num_list=[20,40,60,80,100],
                          entries_threshold=2000,log_file_name="sample_log")
    simulator.run_simulation()

if __name__ == "__main__":
    main()
